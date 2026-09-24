from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    income_account_id = fields.Many2one('account.account', config_parameter='tis_property_managment.income_account_id',domain=[('account_type', '=', 'income')])

    agreement_income_account_id = fields.Many2one('account.account', config_parameter='tis_property_managment.agreement_income_account_id',domain=[('account_type', '=', 'income')])

    services_income_account_id = fields.Many2one('account.account', config_parameter='tis_property_managment.services_income_account_id',domain=[('account_type', '=', 'income')])

    maintenance_income_account_id = fields.Many2one('account.account', config_parameter='tis_property_managment.maintenance_income_account_id',domain=[('account_type', '=', 'income')])

    maintenance_expense_account_id = fields.Many2one('account.account', config_parameter='tis_property_managment.maintenance_expense_account_id',domain=[('account_type', '=', 'expense')])

    maintenance_expense_product_id =fields.Many2one('product.product', config_parameter='tis_property_managment.maintenance_expense_product_id',domain=[('can_be_expensed', '=', True)])

    expense_account_id = fields.Many2one('account.account', config_parameter='tis_property_managment.expense_account_id',domain=[('account_type', '=', 'expense')])
    
    deposit_account_id = fields.Many2one('account.account',config_parameter='tis_property_managment.liabilities_account_id')

    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.income_account_id',self.income_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.agreement_income_account_id',self.agreement_income_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.services_income_account_id',self.services_income_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.maintenance_income_account_id',self.maintenance_income_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.maintenance_expense_account_id',self.maintenance_expense_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.maintenance_expense_product_id',self.maintenance_expense_product_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.expense_account_id',self.expense_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('tis_property_managment.deposit_account_id',self.deposit_account_id.id)
