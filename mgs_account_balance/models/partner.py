from odoo import models, fields, api  # type: ignore


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _credit_search(self, operator, operand):
        return self._asset_difference_search("asset_receivable", operator, operand)

    @api.model
    def _debit_search(self, operator, operand):
        return self._asset_difference_search("liability_payable", operator, operand)

    mgs_credit = fields.Monetary(
        compute="_mgs_credit_debit_get",
        search=_credit_search,
        string="AR_Balance",
        help="Total amount this customer owes you (mgs).",
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    mgs_debit = fields.Monetary(
        compute="_mgs_credit_debit_get",
        search=_debit_search,
        string="AP_Balance",
        help="Total amount you have to pay to this vendor.",
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    mgs_total_due = fields.Monetary(
        compute="_mgs_credit_debit_get",
        string="Total Due",
        help="Total amount due",
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    def get_partner_balance(self, account_type, id, debit_credit):
        result = 0.0
        partner_balance = (
            """
            SELECT 
                COALESCE(SUM(%s"""
            % debit_credit
            + """), 0)
            FROM
                account_move_line as aml
            LEFT JOIN account_account AS aa ON aml.account_id=aa.id
            WHERE 
                aml.partner_id = %s"""
            % str(id)
            + """
                AND aa.account_type IN %s"""
            % account_type
            + """
                AND parent_state in ('posted') 
                AND aml.company_id = %s"""
            % str(self.env.company.id)
            + """
            """
        )
        self.env.cr.execute(partner_balance)
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    @api.depends_context("company")
    def _mgs_credit_debit_get(self):
        if not self.ids:
            self.mgs_debit = False
            self.mgs_credit = False
            return

        for r in self:
            r.mgs_debit = r.get_partner_balance(
                "('liability_payable')", r.id, "aml.credit - aml.debit"
            )
            r.mgs_credit = r.get_partner_balance(
                "('asset_receivable')", r.id, "aml.debit - aml.credit"
            )
            r.mgs_total_due = r.get_partner_balance(
                "('liability_payable', 'asset_receivable')",
                r.id,
                "aml.debit - aml.credit",
            )
