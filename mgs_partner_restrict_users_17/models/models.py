# -*- coding: utf-8 -*-

from odoo import models, fields


class PartnerTags(models.Model):
    _inherit = 'res.users'

    partner_tag_id = fields.Many2many('res.partner.category', string='Default Tags')