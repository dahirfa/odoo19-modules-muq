# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
# from odoo.exceptions import Warning
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    restrict_locations = fields.Boolean('Restrict Location')

    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations')

    default_picking_type_ids = fields.Many2many(
        'stock.picking.type', 'stock_picking_type_users_rel',
        'user_id', 'picking_type_id', string='Default Warehouse Operations')

    default_warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Default Warehouses')

    allowed_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'user_allowed_warehouse_rel',
        'user_id',
        'warehouse_id',
        string='Allowed Warehouses')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for rec in self:

            user_locations = rec.env.user.stock_location_ids
            if rec.env.user.restrict_locations:
                message = _(
                    'Invalid Location. You cannot process this move since you do '
                    'not control the location "%s". '
                    'Please contact your Administrator.'
                    'LAGUUMA OGOLA TRANSFERKAN. LA XIDHIIDH INVENTORY MANAGERKA')
                if rec.location_id not in user_locations:
                    raise UserError(_(message % rec.location_id.name))
                elif rec.location_dest_id not in user_locations:
                    raise UserError(_(message % rec.location_dest_id.name))

        # Call the original button_validate method
        return super(StockPicking, self).button_validate()

# class stock_move(models.Model):
#     _inherit = 'stock.move'

    # @api.constrains('state', 'location_id', 'location_dest_id')
    # def check_user_location_rights(self):
    #     for rec in self:
    #         if rec.state == 'draft':
    #             return True

    #         user_locations = rec.env.user.stock_location_ids
    #         if rec.env.user.restrict_locations:
    #             message = _(
    #                 'Invalid Location. You cannot process this move since you do '
    #                 'not control the location "%s". '
    #                 'Please contact your Adminstrator.'
    #                 'LAGU0MA OGOLA TRANSFERKAN. LA XIDHIIDH INVENTORY MANAGERKA')
    #             if rec.location_id not in user_locations:
    #                 #raise Warning(message % rec.location_id.name)
    #                 raise UserError(_(message % rec.location_id.name))
    #             elif rec.location_dest_id not in user_locations:
    #                 # raise Warning(message % rec.location_dest_id.name)
    #                 raise UserError(_(message % rec.location_dest_id.name))
