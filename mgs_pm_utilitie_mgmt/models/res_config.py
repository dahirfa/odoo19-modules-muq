from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    utility_income_account_id = fields.Many2one('account.account', config_parameter='mgs_pm_utilitie_mgmt.utility_income_account_id', domain=[('account_type', '=', 'income')])
    readings_product_category = fields.Many2one('product.category', config_parameter='mgs_pm_utilitie_mgmt.readings_product_category')
    
    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('mgs_pm_utilitie_mgmt.utility_income_account_id', self.utility_income_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('mgs_pm_utilitie_mgmt.readings_product_category', self.readings_product_category.id)