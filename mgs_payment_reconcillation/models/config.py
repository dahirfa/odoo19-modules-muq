from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    require_reconciliation_on_payment = fields.Boolean()
    
    
class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    require_reconciliation_on_payment = fields.Boolean(related="company_id.require_reconciliation_on_payment", readonly=False)