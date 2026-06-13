# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
    )

    analytic_distribution = fields.Json()
    analytic_precision = fields.Integer()
