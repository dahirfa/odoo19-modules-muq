# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    unit_value = fields.Float(
        string='Unit Value', compute='_compute_unit_value', store=True, digits='Product Price')
    mgs_total_value = fields.Float(
        string='Total', compute='_compute_mgs_total_value', store=True)

    @api.depends('product_id', 'move_id', 'picking_type_id.code')
    def _compute_unit_value(self):
        for line in self:
            if line.picking_type_id.code == 'internal':
                line.unit_value = line.product_id.standard_price
            else:
                line.unit_value = line.unit_value or 0.0

    @api.depends('quantity', 'unit_value', 'picking_type_id.code')
    def _compute_mgs_total_value(self):
        for line in self:
            if line.picking_type_id.code == 'internal':
                line.mgs_total_value = line.quantity * line.unit_value
            else:
                line.mgs_total_value = 0.0


class StockMove(models.Model):
    _inherit = 'stock.move'

    unit_value = fields.Float(
        string='Unit Value', compute='_compute_unit_value', store=True, digits='Product Price')
    mgs_total_value = fields.Float(
        string='Total', compute='_compute_mgs_total_value', store=True)

    @api.depends('product_id', 'picking_type_id.code')
    def _compute_unit_value(self):
        for move in self:
            if move.picking_type_id.code == 'internal':
                move.unit_value = move.product_id.standard_price
            else:
                move.unit_value = move.unit_value or 0.0

    @api.depends('product_uom_qty', 'unit_value', 'picking_type_id.code')
    def _compute_mgs_total_value(self):
        for move in self:
            if move.picking_type_id.code == 'internal':
                move.mgs_total_value = move.product_uom_qty * move.unit_value
            else:
                move.mgs_total_value = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total = fields.Float(string='Total', compute='_compute_total', store=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')

    @api.depends('move_ids.mgs_total_value', 'picking_type_id.code')
    def _compute_total(self):
        for picking in self:
            if picking.picking_type_id.code == 'internal':
                picking.total = sum(picking.move_ids.mapped('mgs_total_value'))
            else:
                picking.total = 0.0
