# -*- coding: utf-8 -*-

from odoo import api, models, fields
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MgsmultiCurrencyGL(models.AbstractModel):
    _name = "report.mgs_multicurrency_gl.gl_report_template"
    
    def _get_invoice(self, invoice_number):
        return self.env['account.move'].search([('name', '=', invoice_number)], limit=1).invoice_line_ids
    # Detailed Lines.
    # Since SQL cannot be used in this situation we have to use the orm
    def _lines(self, date_to, date_from, move_state, account, currency):
        domain = [
            ("currency_id", "=", currency),
        ]

        if account:
            domain += [
                ("account_id", "=", account),
            ]

        
        if move_state == "posted":
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", move_state)]


        if date_from and not date_to:
            domain += [("date", ">=",date_from)]
        elif date_to and not date_from:
            domain += [("date", "<=",date_to)]
        elif date_from and date_to:
            domain += [
                ("date", ">=",date_from),
                ("date", "<=",date_to),
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
            displayed_name = str(
                invoice.move_id.name or invoice.move_id.payment_reference 
            )

            amount_currency_amt_convert = invoice.amount_currency
            balance_amt_convert = invoice.balance
            accounted_balance = 0.0

            company_curr_debit = invoice.debit
            company_curr_credit = invoice.credit
            company_curr_balance = invoice.balance

            debit_amt_convert = 0.0
            credit_amt_convert = 0.0
            
            
            if amount_currency_amt_convert < 0:
                credit_amt_convert = abs(amount_currency_amt_convert)
            else:
                debit_amt_convert = amount_currency_amt_convert

            balance_amt_convert = debit_amt_convert - credit_amt_convert

           
                
            vals = {
                "company_curr_debit": company_curr_debit,
                "company_curr_credit": company_curr_credit,
                "company_curr_balance": company_curr_balance,
                "debit": debit_amt_convert,
                "credit": credit_amt_convert,
                "amount_currency": amount_currency_amt_convert,
                "balance": balance_amt_convert,
                "date": invoice.move_id.invoice_date
                or invoice.move_id.payment_ids.date
                or invoice.move_id.date,
                "date_due": invoice.move_id.invoice_date_due,
                "code": invoice.journal_id.code,
                "a_code": invoice.account_id.code,
                "displayed_name": displayed_name,
                "description": invoice.name or ", ".join(invoice.move_id.payment_ids.mapped("memo")) or invoice.move_id.ref or invoice.move_id.payment_reference,
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
        _logger.info('----------')
        _logger.info(full_account)
        return full_account

        
    def get_previous_balance(self, account_id, date_from, currency_id):

        if not date_from:
            return {'previous_balance': 0.0}

        where = ""

        if account_id:
            where += f" AND aml.account_id = {account_id} "

        if date_from:
            where += f"AND aml.date < '{date_from}'"
            

        query = f"""
            SELECT
            
            aa.id AS account_id,
            aa.name AS account_name,
            COALESCE(SUM(aml.amount_currency), 0) AS previous_balance
            
            FROM
            account_account aa
            JOIN account_move_line aml ON aa.id = aml.account_id
            
            WHERE
                aml.currency_id = {currency_id} 
                 
                and aml.parent_state = 'posted'
                {where}
            GROUP BY
            aa.id, aa.name;
        """

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchone()
        if not res:
            return {'previous_balance': 0.0}
            
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        
        if (data['date_from'] and data['date_to']) and data['date_from'] > data['date_to'] :
            raise ValidationError("Start Date cannot be Greater End Then")
        
        account_domain = []

        if data["account_id"][0] != False:
            account_domain += [("id", "=", data["account_id"][0])]
            
        if data['currency_id'][0] != False and data['currency_id'][0] != self.env.company.currency_id.id:
            account_domain += [("currency_id", "=", data['currency_id'][0])]
            
        
        accounts = self.env["account.account"].search(account_domain)
        
        
        return {
            "data": data,
            "accounts": accounts,
            "account_id": data["account_id"],
            "currency": data["currency_id"],
            "date_from": data["date_from"],
            "date_to": data["date_to"],
            "summary":data['summary'],
            "target_move":data['target_move'],
            "lines":self._lines,
            'reconciled': data['reconciled'],
            "previous_balance": self.get_previous_balance,
            "display_currency": data['display_currency']
        }
