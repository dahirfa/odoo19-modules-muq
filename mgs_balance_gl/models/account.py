from odoo import models  # type: ignore

import logging

_logger = logging.getLogger(__name__)


class Journal(models.Model):
    _inherit = "account.journal"

    def _mgs_sum_open_balance(self, account_id):
        result = 0.0
        params = [account_id]
        query = """
            SELECT
                sum(aml.debit-aml.credit)
            FROM 
                account_move_line AS aml
                LEFT JOIN account_move AS am ON aml.move_id=am.id
            WHERE
                aml.account_id = %s and am.state = 'posted'"""

        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        _logger.info("Result: %s", result)
        return result

    def _mgs_sum_open_balance_fc(self, account_id):
        result = 0.0
        params = [account_id]
        query = """
            SELECT
                sum(aml.amount_currency)
            FROM 
                account_move_line AS aml
                LEFT JOIN account_move AS am ON aml.move_id=am.id
            WHERE
                aml.account_id = %s and am.state = 'posted'"""

        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        _logger.info("Result: %s", result)
        return result

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super(Journal, self)._fill_bank_cash_dashboard_data(dashboard_data)

        # Modify misc_operations_balance for each journal
        for journal in self.filtered(lambda j: j.type in ("bank", "cash")):
            if journal.id in dashboard_data:
                currency = (
                    journal.currency_id
                    if journal.currency_id
                    else self.env["res.currency"].browse(
                        journal.company_id.sudo().currency_id.id
                    )
                )

                # Check if the journal's currency matches the company currency
                if (
                    not journal.currency_id
                    or journal.currency_id.id == journal.company_id.currency_id.id
                ):
                    # Use current_balance in company currency
                    acc_balance = self._mgs_sum_open_balance(
                        journal.default_account_id.id
                    )
                else:
                    # Use function to calculate balance in foreign currency
                    acc_balance = self._mgs_sum_open_balance_fc(
                        journal.default_account_id.id
                    )

                # Format the misc_operations_balance to display in the correct currency format
                dashboard_data[journal.id]["acc_balance"] = currency.format(acc_balance)
