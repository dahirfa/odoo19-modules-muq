from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    transport_product_id =fields.Many2one('product.product',domain=[('type', '=', 'service')])
    commision_product_id =fields.Many2one('product.product',domain=[('type', '=', 'service')])
    transport_analytic_plan_id =fields.Many2one('account.analytic.plan')
    
    
    transport_expenseing_type = fields.Selection(
        string='Transport Expenseing Type',
        default='per_vendor',
        required=True,
        selection=[('per_vendor', 'Per Vendor'), ('per_trip', 'Per Trip')],
    )
    
    
    
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    transport_product_id =fields.Many2one('product.product', readonly=False,domain=[('type', '=', 'service')],related='company_id.transport_product_id')
    commision_product_id =fields.Many2one('product.product', readonly=False,domain=[('type', '=', 'service')],related='company_id.commision_product_id')
    transport_analytic_plan_id =fields.Many2one('account.analytic.plan',readonly=False,related='company_id.transport_analytic_plan_id')
    transport_expenseing_type =fields.Selection(string='Transport Expenseing Type',readonly=False,related='company_id.transport_expenseing_type')
    
