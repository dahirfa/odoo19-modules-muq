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
        help="Income account used on the customer invoice lines of the rent "
             "contracts of the properties in this project. Leave empty to use "
             "the product's income account.",
    )
