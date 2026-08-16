from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
class FreightReceipts(models.Model):
    _name = 'freight.receipts'
    _description = 'Freight Receipts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "customer_id"

    name = fields.Char(
        string='Reference',
         tracking=True
        )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company
        )
    customer_id = fields.Many2one(
        'res.partner', 
         string="Customer",
         required=True,
         tracking=True
        )
    freight_receipt_ids = fields.One2many(
        'freight.receipt.line', 
        'receipt_id'
        )
    total_ctn = fields.Float(
        string="Total CTN",  
        store=True, 
        compute="_compute_totals",
        tracking=True
        )
    total_cbm = fields.Float(
        string="Total CBM",  
        store=True, 
        compute="_compute_totals",
        )
    total_ctn_delivered = fields.Float(
        string="Total CTN Delivered",  
        store=True, 
        compute="_compute_totals",
        tracking=True
        )
    total_remaining = fields.Float(
        string="Total Remaining",  
        store=True, 
        compute="_compute_totals"
        )
    
    delivery_count = fields.Integer(
        string="Delivery Count",
        compute="_compute_delivery_count"
    )
    @api.depends('freight_receipt_ids.ctn', 'freight_receipt_ids.ctn_delivered', 'freight_receipt_ids.t_cmb','freight_receipt_ids.remaining')
    def _compute_totals(self): 
        for record in self:
            total_ctn = 0.0
            total_cbm = 0.0
            total_ctn_delivered = 0.0
            total_remaining = 0.0
            for line in record.freight_receipt_ids:
                total_ctn += line.ctn
                total_cbm += line.t_cmb
                total_remaining += line.remaining
                total_ctn_delivered += line.ctn_delivered
            record.total_ctn = total_ctn
            record.total_cbm = total_cbm
            record.total_ctn_delivered = total_ctn_delivered
            record.total_remaining = total_remaining
            
    def action_open_transfer_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer Lines',
            'res_model': 'freight.line.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_receipt_id': self.id,
                
            }
        }
    

    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = self.env['freight.delivery.line'].search_count([
                ('receipt_id', '=', rec.id)
            ])

    def action_view_deliveries(self):
        delivery_lines = self.env['freight.delivery.line'].search([
            ('receipt_id', 'in', self.ids)
        ])
        delivery_ids = delivery_lines.mapped('delivery_id')

        action = self.env["ir.actions.actions"]._for_xml_id(
            'mgs_freight.freight_delivery_action'
        )
        action['domain'] = [('id', 'in', delivery_ids.ids)]

        list_view = False
        form_view = False
        for view in action.get("views", []):
            if view[1] == 'list':
                list_view = view[0]
            if view[1] == 'form':
                form_view = view[0]

        if len(delivery_ids) == 1:
            action['views'] = [(form_view, 'form')]
            action['res_id'] = delivery_ids.id
        else:
            action['views'] = [
                (list_view, 'list'),
                (form_view, 'form'),
            ]
            action['res_id'] = False

        return action





class FreightReceiptsLine(models.Model):
   
    _name = 'freight.receipt.line'
    _description = 'Freight Receipt Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    receipt_id = fields.Many2one(
        'freight.receipts', 
        ondelete="cascade"
        )
    receiver_date = fields.Date(
        string='Date', 
        default=fields.Date.today(),
        )
    suppler_no = fields.Char(
        string="supplier No", 
        help="Description of the goods or shipment details"
        )
    product_id = fields.Many2one(
        'product.template',
        )
    model= fields.Char()
    item_image = fields.Binary("Photo")
    ctn = fields.Float(
        string="Ctn", 
        help="Number of cartons",
        )
    pcs = fields.Float(
        string="Qty/Ctn"
        )
    t_qty = fields.Float(
        string="T.Qty",
        compute="_compute_t_qty",
        store=True
        )
    size_ctn = fields.Char(
        string="Size/Ctn"
        )
    cbm = fields.Float(
        string="CBM",
        help="Cubic meters per carton",
        compute="_compute_cbm",
        store=True
        )
    t_cmb = fields.Float(
        string="T.Cbm",
        compute="_compute_t_cbm",
        store=True
        )
    weight_kg = fields.Float(
        string="Weight Kg"
        )
    t_weight = fields.Float(
        string="T.Weight",
        compute="_compute_t_weight",
        store=True,
        )
    ctn_delivered = fields.Float()
    remaining = fields.Float(
        string="Remaining CTN",
        compute="_compute_remaining_cbm",
        store=True
        )
    length = fields.Float()
    width = fields.Float()
    height = fields.Float()
    reference = fields.Char()

    @api.depends('length', 'width', 'height')
    def _compute_cbm(self):
        for record in self:
            if record.length and record.width and record.height:
                record.cbm = (record.length * record.width * record.height) / 1000000  
            else:
                record.cbm = 0.0
                
    @api.depends('ctn','ctn_delivered')
    def _compute_remaining_cbm(self):
        for line in self:
            line.remaining = line.ctn - line.ctn_delivered 
            
    @api.depends('ctn','pcs')
    def _compute_t_qty(self):
        for line in self:
            line.t_qty = line.ctn * line.pcs 
    
    @api.depends('ctn','cbm')
    def _compute_t_cbm(self):
        for line in self:
            line.t_cmb = line.ctn * line.cbm 
            
    @api.depends('ctn','weight_kg')
    def _compute_t_weight(self):
        for line in self:
         line.t_weight = line.ctn * line.weight_kg
         
    def unlink(self):
        for line in self:
            if line.ctn_delivered >= 1: 
                product_name = line.product_id.name
                raise UserError(_(
                    "You cannot delete the product '%s' because %s cartons have already been delivered."
                ) % (product_name, line.ctn_delivered))
        return super(FreightReceiptsLine, self).unlink()
