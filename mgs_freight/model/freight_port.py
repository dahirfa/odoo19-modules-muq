from odoo import fields, models

class FreightPort(models.Model):
    _name = 'freight.port'
    _description = 'Freight Port'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        required=True,
        tracking=True
    )
    code = fields.Char(
        tracking=True
    )
    country_id = fields.Many2one(
        'res.country',
        required=True,
        string='Country',
        help='The Country in which port located',
        tracking=True
        )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True
        )
    
    

class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    measurement_type = fields.Selection(
        selection=[('ctn', 'CTN'), ('cbm', 'CBM')]
        )
    
class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    delivery_id = fields.Many2one(
        'freight.delivery',
        )
    