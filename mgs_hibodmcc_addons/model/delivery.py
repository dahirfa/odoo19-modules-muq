from odoo import api, fields, models, _, http
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class MgsProformaInvoice(models.Model):
    _name = 'mgs.proforma.invoice'
    _description = 'Proforma Invoice Lines'

    picking_id = fields.Many2one('stock.picking', string='Transfer', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')
    unit_price = fields.Float(string='Unit Price', required=True)
    tax_amount = fields.Float(string='Tax Amount')
    net_amount = fields.Float(string='Net Amount', compute='_compute_amounts')
    
    @api.depends('quantity', 'unit_price', 'tax_amount')
    def _compute_amounts(self):
        for record in self:
            record.net_amount = (record.quantity * record.unit_price) + record.tax_amount
            
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.unit_price = self.product_id.list_price
            
            

class Mgs_Stock_Delivery(models.Model):
    _inherit = "stock.picking"
    
    truck_num = fields.Char(string="Truck", tracking=True)
    order_num = fields.Char(string="Order No#", tracking=True)
    driver = fields.Char(string="Driver", tracking=True)
    difference = fields.Float(string="Difference", tracking=True)
    bill_to = fields.Many2one(string="Bill To", comodel_name="res.country.state")
    deliver_to = fields.Many2one(string="Deliver To", comodel_name="res.country.state")
    transporter_id = fields.Many2one(string="Transporter", comodel_name="res.partner")
    intercoms = fields.Char(string="Intercoms")
    intercom_location = fields.Char(string="Intercom Location")
    loading_point = fields.Char(string="Loading Point")    
    proforma_invoice_ids = fields.One2many('mgs.proforma.invoice', 'picking_id', string='Proforma Invoice Lines')
    proforma_total = fields.Float(string='Total Amount', compute='_compute_proforma_total')
    mgs_tax_total = fields.Float(string='Tax Amount', compute='_compute_proforma_total')
    mgs_net = fields.Float(string='Net Amount', compute='_compute_proforma_total')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    

    
    @api.depends('proforma_invoice_ids.net_amount', 'proforma_invoice_ids.tax_amount')
    def _compute_proforma_total(self):
        for picking in self:
            picking.proforma_total = sum((line.net_amount) for line in picking.proforma_invoice_ids)
            picking.mgs_tax_total = sum((line.tax_amount) for line in picking.proforma_invoice_ids)
            picking.mgs_net = sum((line.net_amount) for line in picking.proforma_invoice_ids)
    
class Mgs_Stock_move(models.Model):
    _inherit = "stock.move"
    
    sales_price = fields.Float(string="Price")
    

