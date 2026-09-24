# -*- coding: utf-8 -*-

from odoo import fields, models, api

class Users(models.Model):
    _inherit = 'res.users'

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'users_warehouses_restrict',
        'user_id',
        'warehouse_id',
        'Allowed Warehouses',
    )

    @api.constrains('warehouse_ids')
    def update_warehouse_restrict(self):
        restrict_group = self.env.ref('mgs_warehouse_restriction.warehouse_restrict_group')
        for user in self:
            if user.warehouse_ids:
                # add users to restriction group
                # Due to strange behavior, we must remove the user from the group then
                # re-add him again to get restrictions applied
                restrict_group.write({'user_ids': [(3, user.id)]})
                user.group_ids = [(3, restrict_group.id)]
                ## re-add
                restrict_group.write({'user_ids': [(4, user.id)]})
                user.group_ids = [(4, restrict_group.id)]
            else:
                restrict_group.write({'user_ids': [(3, user.id)]})
                user.group_ids = [(3, restrict_group.id)]

            # Clear cache to ensure restrictions are applied immediately
            self.env.registry.clear_cache()