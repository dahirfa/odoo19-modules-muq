# -*- coding: utf-8 -*-

from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class MultiReportPartnerLedger(models.AbstractModel):
    _name = "report.multi_currency_partner_ledger_app.report_partnerledger"
    def _get_invoice(self, invoice_number):
        return self.env['account.move'].search([('name', '=', invoice_number)], limit=1).invoice_line_ids
    
    
    def _lines(self, data, partner, currency):
        domain = [
            ("currency_id", "=", currency.id),
        ]

        if partner:
            domain += [
                ("partner_id", "=", partner.id),
            ]

        move_state = data["move_state"]
        if move_state == ["posted"]:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["draft", "posted"])]

        account_type = data["account_type"]
        if account_type == ["supplier"]:
            domain += [("account_id.account_type", "=", "liability_payable")]
        elif account_type == ["customer"]:
            domain += [("account_id.account_type", "=", "asset_receivable")]
        else:
            domain += [
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            ]

        if data["date_from"] and not data["date_to"]:
            domain += [("date", ">=", data["date_from"])]
        elif data["date_to"] and not data["date_from"]:
            domain += [("date", "<=", data["date_to"])]
        elif data["date_from"] and data["date_to"]:
            domain += [
                ("date", ">=", data["date_from"]),
                ("date", "<=", data["date_to"]),
            ]
        else:
            domain += []

        invoice_ids = self.env["account.move.line"].search(domain, order="date asc")

        full_account = []
        debit_currecny_amount_total = 0.0
        credit_currecny_amount_total = 0.0
        balance_currecny_amount_total = 0.0

        for invoice in invoice_ids:
            company_id = self.env.user.company_id
            # displayed_name = str(invoice.move_id.name or '') + '-' + str(invoice.move_id.payment_reference or '')
            displayed_name = str(
                invoice.move_id.name or invoice.move_id.payment_reference
            )

            # debit_amt_convert = invoice.debit
            # credit_amt_convert = invoice.credit
            amount_currency_amt_convert = invoice.amount_currency
            balance_amt_convert = invoice.balance
            accounted_balance = 0.0

            company_curr_debit = invoice.debit
            company_curr_credit = invoice.credit
            company_curr_balance = invoice.balance
            # company_curr_balance = company_id.currency_id._convert(invoice.balance, invoice.currency_id, company_id, invoice.move_id.date)

            debit_amt_convert = 0.0
            credit_amt_convert = 0.0
            # if company_id.currency_id != invoice.currency_id:
            # debit_amt_convert = company_id.currency_id._convert(invoice.debit, invoice.currency_id, company_id, invoice.move_id.date)
            # credit_amt_convert = company_id.currency_id._convert(invoice.credit, invoice.currency_id, company_id, invoice.move_id.date)
            # balance_amt_convert = company_id.currency_id._convert(invoice.balance, invoice.currency_id, company_id, invoice.move_id.date)
            if amount_currency_amt_convert < 0:
                credit_amt_convert = abs(amount_currency_amt_convert)
            else:
                debit_amt_convert = amount_currency_amt_convert
            
            if account_type == ["supplier"]:
                balance_amt_convert = credit_amt_convert -  debit_amt_convert
            elif account_type == ["customer"]:
                balance_amt_convert = debit_amt_convert - credit_amt_convert
            else:
                balance_amt_convert = debit_amt_convert - credit_amt_convert
                
           
                
            vals = {
                "company_curr_debit": company_curr_debit,
                "company_curr_credit": company_curr_credit,
                "company_curr_balance": company_curr_balance,
                "debit": debit_amt_convert,
                "credit": credit_amt_convert,
                "amount_currency": amount_currency_amt_convert,
                "progress": balance_amt_convert,
                "date": invoice.move_id.date or invoice.move_id.date,
                "date_due": invoice.move_id.invoice_date_due,
                "code": invoice.journal_id.code,
                "a_code": invoice.account_id.code,
                "displayed_name": displayed_name,
                "description": invoice.move_id.ref,
                "currency_id": invoice.currency_id.symbol
                or company_id.currency_id.symbol,
                "invoice_id": invoice.move_id.id,
            }

            debit_currecny_amount_total += debit_amt_convert
            credit_currecny_amount_total += credit_amt_convert
            balance_currecny_amount_total += balance_amt_convert

            full_account.append(vals)

        if full_account:
            full_account[0].update(
                {
                    "debit_total": debit_currecny_amount_total,
                    "credit_total": credit_currecny_amount_total,
                    "balance_total": balance_currecny_amount_total,
                }
            )

        return full_account

    def _get_previous_balance(self, data, partner, currencies):
        previous_balance = 0.0

        domain = [
            ("currency_id", "=", currencies.id),
            ("date", "<", data["date_from"]),
        ]

        if partner:
            domain += [
                ("partner_id", "=", partner.id),
            ]

        move_state = data["move_state"]
        if move_state == ["posted"]:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["draft", "posted"])]

        account_type = data["account_type"]
        if account_type == ["supplier"]:
            domain += [("account_id.account_type", "=", "liability_payable")]
        elif account_type == ["customer"]:
            domain += [("account_id.account_type", "=", "asset_receivable")]
        else:
            domain += [
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            ]

        previous_balance_lines = self.env["account.move.line"].search(domain)
        
        debit_currecny_amount_total = 0.0
        credit_currecny_amount_total = 0.0
        balance_currecny_amount_total = 0.0
        for line in previous_balance_lines:
            
            amount_currency_amt_convert = line.amount_currency
            balance_amt_convert = line.balance
            debit_amt_convert = 0.0
            credit_amt_convert = 0.0
            
            if amount_currency_amt_convert < 0:
                credit_amt_convert = abs(amount_currency_amt_convert)
            else:
                debit_amt_convert = amount_currency_amt_convert
            
            if account_type == ["supplier"]:
                balance_amt_convert = credit_amt_convert -  debit_amt_convert
            elif account_type == ["customer"]:
                balance_amt_convert = debit_amt_convert - credit_amt_convert
            else:
                balance_amt_convert = debit_amt_convert - credit_amt_convert
                
            debit_currecny_amount_total += debit_amt_convert
            credit_currecny_amount_total += credit_amt_convert
            balance_currecny_amount_total += balance_amt_convert
            
            
            previous_balance += line.amount_currency

        _logger.info(balance_currecny_amount_total)
        return {"currency_id": currencies.symbol, "previous_balance": balance_currecny_amount_total}



    @api.model
    def _get_report_values(self, docids, data=None):
        context = data.get("used_context")
        currency_ids = self.env["res.currency"].browse(context.get("currency_ids"))

        partner_domain = []

        if data.get("docs"):
            partner_domain += [("id", "in", data.get("docs"))]
        
        if data.get('category_id'):
            partner_domain += [('category_id', 'in', data.get('category_id'))]

        partner_ids = self.env["res.partner"].search(partner_domain)

        return {
            "currency_ids": currency_ids,
            "doc_model": self.env["res.partner"],
            "docs": partner_ids,
            "lines": self._lines,
            "extra": data,
            # "sum_partner": self._sum_partner,
            "previous_balance": self._get_previous_balance,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
