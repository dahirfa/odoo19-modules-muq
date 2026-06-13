from odoo import models, fields


class SaBiometricDevice(models.Model):
    _name           = 'sa.biometric.device'
    _description    = 'Biometric Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
     
    name            = fields.Char(tracking=1)
    externalid      = fields.Integer()
    company_id     = fields.Many2one(comodel_name='res.company', required=True, index=True, default=lambda self: self.env.company)
    

    _sql_constraints = [
        ('unique_externalid', 'UNIQUE(externalid)', 'The external ID must be unique.')
    ]