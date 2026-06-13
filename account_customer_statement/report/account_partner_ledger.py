# -*- coding: utf-8 -*-

import time
# from openerp import api, models
from odoo import api, models
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ReportPartnerLedger_statement(models.AbstractModel):
    _name = 'report.account_customer_statement.report_partnerledger_custom'
    _description = 'Report Partner Ledger Statement'

    def _get_invoice(self, invoice_number):
        return self.env['account.move'].search([('name', '=', invoice_number)], limit=1).invoice_line_ids\


    def _lines(self, data, partner):
        full_account = []
        currency = self.env['res.currency']

        # Call _query_get to get tables, where clause, and parameters
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        reconcile_clause = "" if data['form']['reconciled'] else ' AND aml.full_reconcile_id IS NULL '

        # Build the params for the query
        params = [partner.id, data['computed']['move_state'],
                  data['computed']['account_ids']] + query_get_data[2]

        # Ensure the `tables` part from _query_get includes "account_move_line"
        tables = query_get_data[0]
        if "account_move_line" not in tables:
            tables = f"account_move_line aml {tables}"

        # SQL Query
        query = f"""
            SELECT 
                aml.id, 
                aml.date, 
                j.code AS journal_code, 
                acc.code_store AS a_code, 
                acc.name AS account_name, 
                aml.ref, 
                m.name AS move_name, 
                aml.name, 
                aml.debit, 
                aml.credit, 
                aml.amount_currency, 
                aml.currency_id, 
                c.symbol AS currency_code
            FROM {tables}
            LEFT JOIN account_journal j ON (aml.journal_id = j.id)
            LEFT JOIN account_account acc ON (aml.account_id = acc.id)
            LEFT JOIN res_currency c ON (aml.currency_id = c.id)
            LEFT JOIN account_move m ON (m.id = aml.move_id)
            WHERE aml.partner_id = %s
                AND m.state IN %s
                AND aml.account_id = ANY(%s)
                AND {query_get_data[1]} {reconcile_clause}
            ORDER BY aml.date
        """

        # Execute the query
        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()

        # Process results
        sum = 0.0
        lang_code = self.env.context.get('lang') or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format

        for r in res:
            # Format the date
            r['date'] = datetime.strptime(
                str(r['date']), DEFAULT_SERVER_DATE_FORMAT
            ).strftime(date_format)

            # Combine name fields for display
            r['displayed_name'] = '-'.join(
                r[field_name] for field_name in ('move_name', 'ref', 'name')
                if r[field_name] not in (None, '', '/')
            )

            # SAFE EXTRACTION OF ACCOUNT CODE
            # 1. Get the current company ID as a string (keys in code_store are usually strings)
            company_key = str(self.env.company.id)
            
            # 2. Check if a_code is actually a dictionary (it might be None or empty)
            if isinstance(r['a_code'], dict):
                # Try getting code for current company, fallback to '1', fallback to empty string
                r['a_code'] = r['a_code'].get(company_key) or r['a_code'].get('1') or ''
            else:
                # If it's not a dict, ensure it's a string or handle gracefully
                r['a_code'] = str(r['a_code']) if r['a_code'] else ''

            # Calculate cumulative progress
            sum += r['debit'] - r['credit']
            r['progress'] = sum

            # Attach currency object
            r['currency_id'] = currency.browse(r.get('currency_id'))

            full_account.append(r)

        return full_account

    def _sum_open_balance(self, data, partner, field):
        if field not in ['debit', 'credit', 'debit - credit']:
            return
        result = 0.0
        context = {}
        context['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        context['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        context['date_from'] = False
        context['date_to'] = False if not data['form']['date_from'] else datetime.strptime(
            data['form']['date_from'], "%Y-%m-%d") + relativedelta(days=-1)
        context['strict_range'] = False
        query_get_data = self.env['account.move.line'].with_context(
            context)._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND aml.reconciled = false '

        params = [partner.id, tuple(data['computed']['move_state']), tuple(
            data['computed']['account_ids'])] + query_get_data[2]
        query = """SELECT sum(""" + field + """)
				FROM """ + query_get_data[0] + """, account_move AS m
				WHERE aml.partner_id = %s
					AND m.id = aml.move_id
					AND m.state IN %s
					AND account_id IN %s
					AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))

        contempp = self.env.cr.fetchone()
        if contempp is not None:
            resultt = contempp[0] or 0.0
        return resultt

    def _sum_partner(self, data, partner, field):
        if field not in ['debit', 'credit', 'debit - credit']:
            return
        result = 0.0
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND aml.reconciled = false '

        params = [partner.id, tuple(data['computed']['move_state']), tuple(
            data['computed']['account_ids'])] + query_get_data[2]
        query = """SELECT sum(""" + field + """)
				FROM """ + query_get_data[0] + """, account_move AS m
				WHERE aml.partner_id = %s
					AND m.id = aml.move_id
					AND m.state IN %s
					AND account_id IN %s
					AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))

        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

#     @api.multi
#     def render_html(self, doc_ids, data):
    @api.model
    def _get_report_values(self, docids, data=None):
        data['computed'] = {}

        obj_partner = self.env['res.partner']

        # Fetch query data with context
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {})
        )._query_get()

        # Determine move states
        data['computed']['move_state'] = ('draft', 'posted')
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ('posted',)

        # Determine account types based on result selection
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            data['computed']['ACCOUNT_TYPE'] = ('liability_payable',)
        elif result_selection == 'customer':
            data['computed']['ACCOUNT_TYPE'] = ('asset_receivable',)
        else:
            data['computed']['ACCOUNT_TYPE'] = (
                'asset_receivable', 'liability_payable')

        # Query account IDs based on account types
        # Use `active` instead of the removed `deprecated` column (older Odoo used `deprecated` boolean)
        # Keep the same semantics: we want accounts that are active (i.e. not deprecated)
        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.account_type IN %s
            AND a.active
        """, (data['computed']['ACCOUNT_TYPE'],))
        data['computed']['account_ids'] = [
            a for (a,) in self.env.cr.fetchall()]

        # Prepare query parameters
        reconcile_clause = "" if data['form'].get(
            'reconciled', False) else ' AND aml.reconciled = false '
        account_clause = "aml.account_id IN %s" if data['computed']['account_ids'] else "1=0"
        params = [data['computed']['move_state']]
        if data['computed']['account_ids']:
            params.append(tuple(data['computed']['account_ids']))
        params += query_get_data[2]

        # SQL query
        query = f"""
            SELECT DISTINCT aml.partner_id
            FROM {query_get_data[0]}, account_account AS account, account_move AS am
            WHERE aml.partner_id IS NOT NULL
                AND aml.account_id = account.id
                AND am.id = aml.move_id
                AND am.state IN %s
                AND {account_clause}
                AND account.active
                AND {query_get_data[1]} {reconcile_clause}
        """
        self.env.cr.execute(query, tuple(params))

        # Get partner IDs from the query
        partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]

        # Override partner_ids if provided via custom form input
        if data['form'].get('custom_partner_ids'):
            partner_ids = data['form']['custom_partner_ids']

        # Fetch partner records and sort them
        partners = obj_partner.browse(partner_ids)
        partners = sorted(partners, key=lambda x: (x.ref, x.name))

        # Prepare document arguments
        docargs = {
            'doc_ids': partner_ids,
            'doc_model': 'res.partner',
            'data': data,
            'docs': partners,
            'time': time,
            'lines': self._lines,
            'get_invoice': self._get_invoice,
            'sum_partner': self._sum_partner,
            'sum_open_balance': self._sum_open_balance
        }
        return docargs
