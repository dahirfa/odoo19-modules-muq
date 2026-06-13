# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfigInherit(models.Model):
    _inherit = 'pos.config'

    auto_invoice_on_payment = fields.Boolean(
        string="Auto Check Invoice on Payment?")


class ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_auto_invoice_on_payment = fields.Boolean(
        related="pos_config_id.auto_invoice_on_payment", readonly=False)
