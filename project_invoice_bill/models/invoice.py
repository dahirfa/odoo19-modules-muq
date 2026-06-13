# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'


    analytic_account_id = fields.Many2one("account.analytic.account")

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('analytic_distribution'):
                move_id = vals.get('move_id')

                if move_id:
                    move = self.env['account.move'].browse(move_id)
                    if move.analytic_account_id:
                        vals['analytic_distribution'] = {
                            move.analytic_account_id.id: 100
                        }

        return super().create(vals_list)