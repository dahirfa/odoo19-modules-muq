# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = "res.users"

    pos_allowed_payment_method_ids = fields.Many2many(
        'pos.payment.method',
        string="Allowed POS Payment Methods"
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super(ResUsers, self)._load_pos_data_fields(config_id)
        fields_list += ['pos_allowed_payment_method_ids']
        return fields_list
