# -*- coding: utf-8 -*-

from odoo import models, fields


class PosSession(models.Model):
    _inherit = 'pos.session'

    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account', string='Analytic Account',
        copy=False)
    analytic_distribution = fields.Json()

    def _prepare_line(self, order_line):
        res = super(PosSession, self)._prepare_line(order_line)
        # res['analytic_distribution'] = order_line.order_id.account_analytic_id \
        #     or False
        analytic_account_id = order_line.order_id.account_analytic_id.id
        res['analytic_distribution'] = order_line.order_id.analytic_distribution
        return res

    def _get_sale_vals(self, key, sale_vals):
        res = super(PosSession, self)._get_sale_vals(key, sale_vals)
        analytic_account_id = self.account_analytic_id.id
        res['analytic_distribution'] = self.analytic_distribution
        return res

    def _get_stock_output_vals(self, out_account, amount, amount_converted):
        res = super(PosSession, self)._get_stock_output_vals(out_account,
                                                             amount,
                                                             amount_converted)
        if not self.company_id.anglo_saxon_accounting:
            # res['analytic_account_id'] = self.account_analytic_id.id \
            #     or False
            res['analytic_distribution'] = self.analytic_distribution
        return res

    def _get_stock_expense_vals(self, exp_account, amount, amount_converted):
        res = super(PosSession, self)._get_stock_expense_vals(exp_account,
                                                              amount,
                                                              amount_converted)
        if self.company_id.anglo_saxon_accounting:
            # res['analytic_account_id'] = self.account_analytic_id.id \
            #     or False
            res['analytic_distribution'] = self.analytic_distribution
        return res

    def write(self, vals):
        for session in self:
            if not session.account_analytic_id:
                # vals['account_analytic_id'] = \
                #     session.config_id.account_analytic_id.id or False
                vals['analytic_distribution'] = \
                    session.config_id.analytic_distribution or False
        return super(PosSession, self).write(vals)
