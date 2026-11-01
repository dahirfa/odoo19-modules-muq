from odoo import fields, models


class PropertyDetails(models.Model):
    _inherit = 'property.details'
    
    owner_id = fields.Many2one('res.partner',
                                  string='Owner',
                                  domain=[('user_type', '==', 'owner')])

