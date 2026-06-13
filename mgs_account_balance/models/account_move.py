from odoo import models, fields, api  # type: ignore


class AccountMove(models.Model):
    _inherit = "account.move"

    mgs_partner_balance = fields.Monetary(
        string="Partner Balance",
        default=0.0,
        compute="_compute_mgs_partner_balance",
        currency_field="currency_id",
    )

    @api.depends("partner_id", "move_type")
    def _compute_mgs_partner_balance(self):
        for move in self:
            move.mgs_partner_balance = 0
            if move.move_type in ["out_invoice", "out_refund"]:
                move.mgs_partner_balance = move.partner_id.mgs_credit
            elif move.move_type in ["in_invoice", "in_refund"]:
                move.mgs_partner_balance = move.partner_id.mgs_debit
