from odoo import _, api, fields, models

from odoo.exceptions import ValidationError

class Mgs_Approval_Category_Extension(models.Model):
    _inherit = "approval.category"

    approval_type = fields.Selection(selection_add=[('request_items', 'Request Items')])   
    
    
class ApprovalsInherit(models.Model):
    _inherit = "approval.request"
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', readonly=True)
    picking_count = fields.Integer(compute='_compute_picking_count')
    source_location_id = fields.Many2one('stock.location', required=True)
    destination_location_id = fields.Many2one('stock.location', required=True)
    operation_type_id = fields.Many2one('stock.picking.type', string='Operation Type', domain=[('code', '=', 'internal')], required=True)
    
    @api.depends('picking_id')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = 1 if rec.picking_id else 0
    
    def action_view_picking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }
    
    
    def action_approve(self, approver=None):
        
        res = super(ApprovalsInherit, self).action_approve(approver=approver)
        
        sequence = self.operation_type_id.sequence_id
        name = sequence.next_by_id() if sequence else '/'
        picking = self.env['stock.picking'].create({
            'name': name,
            'picking_type_id': self.operation_type_id.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name
        })
        
        for line in self.product_line_ids:
            if line.product_id:
                self.env['stock.move'].create({
                    # 'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                })
        
        picking.action_confirm()
        picking.button_validate()
        
        self.picking_id = picking.id
        
        
        return res
    
    
    
    