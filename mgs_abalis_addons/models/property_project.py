from odoo import fields, models


class PropertyProject(models.Model):
    _inherit = 'property.project'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        copy=False,
        domain="[('company_id', 'in', [company_id, False])]",
        help="Analytic account used to track the rental income and expenses "
             "of the properties in this project.",
    )
    income_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Income Account',
        copy=False,
        domain="[('account_type', 'in', ('income', 'income_other')), ('company_ids', 'parent_of', company_id)]",
        help="Default income account used on the customer invoice lines of the "
             "rent contracts of the properties in this project (Residential and "
             "any type without a specific account). Leave empty to use the "
             "product's income account.",
    )
    commercial_income_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Commercial Income Account',
        copy=False,
        domain="[('account_type', 'in', ('income', 'income_other')), ('company_ids', 'parent_of', company_id)]",
        help="Income account used on the customer invoice lines of the rent "
             "contracts of Commercial properties in this project. Leave empty "
             "to use the default Income Account.",
    )

    def _get_income_account(self, property_type):
        """Return the income account to use for a property of the given type."""
        self.ensure_one()
        if property_type == 'commercial' and self.commercial_income_account_id:
            return self.commercial_income_account_id
        return self.income_account_id
