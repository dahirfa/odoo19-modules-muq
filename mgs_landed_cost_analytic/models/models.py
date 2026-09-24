# -*- coding: utf-8 -*-

from odoo import models, fields, api



class MgsLandedCostAnalytic(models.Model):
    _inherit = 'stock.landed.cost.lines'
    
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

class InheritStockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        res = super(InheritStockLandedCost, self).button_validate()

        for cost in self:
            for line in cost.cost_lines:
                analytic_account = line.analytic_account_id
                if analytic_account:
                    for move_line in line.cost_id.account_move_id.line_ids:
                        if move_line.account_id == line.account_id:
                            move_line.analytic_distribution =  {str(analytic_account.id) : 100.0}

        return res
   
