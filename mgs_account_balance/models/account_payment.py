from odoo import models, fields, api  # type: ignore


class AccountPayment(models.Model):
    _inherit = "account.payment"

    mgs_partner_balance = fields.Monetary(
        string="Partner Balance",
        default=0.0,
        compute="_compute_mgs_partner_balance",
        currency_field="currency_id",
    )
    mgs_journal_balance = fields.Monetary(
        string="Journal Balance",
        default=0.0,
        compute="_compute_mgs_journal_balance",
        currency_field="currency_id",
    )

    @api.depends("partner_id", "payment_type")
    def _compute_mgs_partner_balance(self):
        for payment in self:
            payment.mgs_partner_balance = 0
            if payment.payment_type == "inbound":
                payment.mgs_partner_balance = payment.partner_id.mgs_credit
            elif payment.payment_type == "outbound":
                payment.mgs_partner_balance = payment.partner_id.mgs_debit

    @api.depends("journal_id")
    def _compute_mgs_journal_balance(self):
        for payment in self:
            payment.mgs_journal_balance = 0
            if payment.journal_id.currency_id == payment.company_id.currency_id:
                payment.mgs_journal_balance = (
                    payment.journal_id.default_account_id.current_balance
                )
            else:
                if payment.journal_id.default_account_id.id:
                    self.env.cr.execute(
                        """
                        SELECT SUM(amount_currency) 
                        FROM account_move_line 
                        WHERE account_id = %s AND parent_state = 'posted'
                    """,
                        (payment.journal_id.default_account_id.id,),
                    )
                    result = self.env.cr.fetchone()
                    payment.mgs_journal_balance = result[0] if result else 0.0
