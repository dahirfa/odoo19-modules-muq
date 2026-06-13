# from datetime import datetime, timedelta, date
# from pytz import timezone, UTC
# import pytz

from odoo import models, fields, api


class LatencyRules(models.Model):
    _name = 'latency.rule'
    _description = 'Latency Rules'

    name = fields.Char(required=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    minutes = fields.Float(string="Allowed Minutes", help="For each x minutes an employee comes late, the system is going to detuct 1 hour wage")
    fixed_amount = fields.Float(string="Fixed Amount")
    latency_rule_lines = fields.One2many('latency.rule.line', 'latency_rule_id')

    _sql_constraints = [
        ('structure_type_id_unique',
         'unique(structure_type_id)',
         'structure type id has to be unique!')]

    letency_type = fields.Selection([
        ("wage", "Wage Per Hour"),
        ("fixed", "Fixed Per Hour"),
        ('custom', 'Custom'),
    ], default="wage")


class LatencyRuleLines(models.Model):
    _name = 'latency.rule.line'

    check_in = fields.Integer()
    amount = fields.Integer()
    latency_rule_id = fields.Many2one('latency.rule')


