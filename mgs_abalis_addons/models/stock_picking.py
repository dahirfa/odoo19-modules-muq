from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    property_details = fields.Many2one(
        comodel_name='property.details',
        string='Property Details',
    )
