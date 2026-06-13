# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class Accounting_report_General_ledger(models.TransientModel):
    _name = "mgs.multicurrency.gl.wizard"

    account_id = fields.Many2one(comodel_name="account.account", string="Account")
    
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.user.company_id,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env["res.currency"].search([]),
    )
    
    target_move = fields.Selection(
        [
            ("posted", "All Posted Entries"),
            ("all", "All Entries"),
        ],
        string="Target Moves",
        required=True,
        default="posted",
    )
    
    reconciled = fields.Boolean("Show Initial Balance?", default=True)
    
    
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    
    
    summary = fields.Boolean(
        string="Summary",
    )
    

    
    @api.onchange('account_id')
    def _onchange_account_id(self):
        for rec in self:
            if rec.account_id.currency_id.id:
                rec.currency_id = rec.account_id.currency_id.id
            else:
                rec.currency_id = rec.company_id.currency_id.id
                
    
    


    def print_general_ledger(self):
        
        move_state = ["draft", "posted"]
        if self.target_move == "posted":
            move_state = "posted"
        
    
        wizard_dict = {
            "account_id": [self.account_id.id, self.account_id.name],
            'move_state':move_state,
            "currency_id": [self.currency_id.id, self.currency_id.name],
            "date_from": self.date_from,
            "date_to": self.date_to,
            "reconciled": self.reconciled,
            "summary":self.summary,
            "target_move":self.target_move,
            "display_currency": self.currency_id.symbol
        }

        action = self.env.ref(
            "mgs_multicurrency_gl.mgs_multicurrency_gl_report_action"
        ).report_action(self, data=wizard_dict)

        return action


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
