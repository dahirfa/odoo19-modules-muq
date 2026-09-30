import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


DAYS_PER_WEEK = 7


class ContainerSizeType(models.Model):
    _name = 'container.size.type'
    _description = 'Container Size/Type'
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(string='Size/Type', required=True, help="e.g. 20DV, 40DV")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    size_feet = fields.Integer(
        string='Size (ft)',
        compute='_compute_size_feet',
        store=True,
        readonly=False,
        help="Container length in feet (20, 40, 45). Used for the container quantity on delivery orders.",
    )
    week1_rate = fields.Monetary(string='Week 1 Rate (per day)', currency_field='currency_id')
    week2_rate = fields.Monetary(string='Week 2 Rate (per day)', currency_field='currency_id')
    week3_rate = fields.Monetary(string='Week 3 Rate (per day)', currency_field='currency_id')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    demurrage_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Demurrage Account',
        check_company=True,
        domain="[('account_type', 'in', ('income', 'income_other'))]",
        help="Account used on the demurrage invoice lines for this size/type.",
    )
    _name_company_uniq = models.Constraint(
        'unique (name, company_id)',
        "This container size/type already exists for this company.",
    )

    @api.depends('name')
    def _compute_size_feet(self):
        for record in self:
            match = re.match(r'\s*(\d+)', record.name or '')
            record.size_feet = int(match.group(1)) if match else 0

    @api.constrains('week1_rate', 'week2_rate', 'week3_rate')
    def _check_rates(self):
        for record in self:
            if min(record.week1_rate, record.week2_rate, record.week3_rate) < 0:
                raise ValidationError(self.env._("Demurrage rates cannot be negative."))

    @api.model
    def _get_rate_week(self, day_number):
        """Return the tier week (1, 2 or 3) for a 1-based demurrage day number."""
        if day_number <= DAYS_PER_WEEK:
            return 1
        if day_number <= DAYS_PER_WEEK * 2:
            return 2
        return 3

    def _get_daily_rate(self, day_number):
        self.ensure_one()
        return self[f'week{self._get_rate_week(day_number)}_rate']

    def _get_tiered_amount(self, demurrage_days):
        self.ensure_one()
        return sum(self._get_daily_rate(day) for day in range(1, demurrage_days + 1))
