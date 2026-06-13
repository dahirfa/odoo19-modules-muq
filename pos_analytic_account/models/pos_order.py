# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        copy=False, string='Analytic Account')

    analytic_distribution = fields.Json()
    analytic_precision = fields.Integer()

    # def _prepare_invoice_lines(self):
    #     lines = super(PosOrder, self)._prepare_invoice_lines()
    #     # lines['analytic_distribution'] = order_id.analytic_distribution
    #     # sign = 1 if self.amount_total >= 0 else -1
    #     # line_values_list = self._prepare_tax_base_line_values(sign=sign)
    #     # invoice_lines  = []
    #     # for line_values in line_values_list:
    #     #     order_line = line_values['record']
            
    #     for line in lines:
    #         line[2]['analytic_distribution'] = self.analytic_distribution
    #     return lines


    def _prepare_invoice_lines(self, move_type):
        lines = super(PosOrder, self)._prepare_invoice_lines(move_type)

        for line in lines:
            # line format: (0, 0/None, values_dict)
            if isinstance(line, (list, tuple)) and len(line) >= 3 and isinstance(line[2], dict):
                line[2]['analytic_distribution'] = self.analytic_distribution

        return lines





    def write(self, vals):
        for order in self:
            if not order.account_analytic_id:
                vals['analytic_distribution'] = \
                    order.config_id.analytic_distribution
        return super(PosOrder, self).write(vals)
