# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO
import json

class AccountStatement(models.TransientModel):
    _name = 'mgs_account.account_statement'
    _description = 'Account Statement Wizard'

    account_id = fields.Many2many('account.account', string="Accounts")
    partner_id = fields.Many2many('res.partner', string="Partner")
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account')
    date_from = fields.Date(
        'From  Date', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To  Date', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id)
    report_by = fields.Selection(
        [('detail', 'Detail'), ('summary', 'Summary')], string='Report Type', default='detail')
    target_moves = fields.Selection(
        [('all', 'All Entries'), ('posted', 'All Posted Entries')], string='Target Moves', default='all')
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    # @api.multi

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'company_id': [self.company_id.id, self.company_id.name],
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'account_id': self.account_id.ids,
                'analytic_account_id': [self.analytic_account_id.id, self.analytic_account_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_by': self.report_by,
                'target_moves': self.target_moves
            },
        }

        return self.env.ref('mgs_account.action_report_account_statement').report_action(self, data=data)

    def export_to_excel(self):
   

        def safe_str(value):
            if isinstance(value, dict):
                lang = self.env.lang or 'en_US'
                return value.get(lang) or next(iter(value.values()), '')
            elif value is None:
                return ''
            else:
                return str(value)

        account_statement_report_obj = self.env['report.mgs_account.account_statement_report']
        lines = account_statement_report_obj._lines
        sum_open_balance = account_statement_report_obj._sum_open_balance

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'AccountStatement.xlsx'
        worksheet = workbook.add_worksheet('Account Statement')

        # Formats
        heading_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'font_size': 14})
        sub_heading_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'font_size': 12})
        cell_text_format = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 12})
        cell_number_format = workbook.add_format({'align': 'right', 'bold': True, 'font_size': 12})
        align_right = workbook.add_format({'align': 'right'})
        align_right_total = workbook.add_format({'align': 'right', 'bold': True})
        date_heading_format = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 12, 'num_format': 'dd-mm-yyyy'})
        date_format = workbook.add_format({'align': 'left', 'num_format': 'dd-mm-yyyy'})
        number_fmt = workbook.add_format({
            'num_format': '#,##0.00',
            'align': 'right',
        })
        row = 1
        worksheet.merge_range('A1:I1', safe_str(self.company_id.name), sub_heading_format)
        row += 1
        worksheet.merge_range('A2:I3', 'Account Statement', heading_format)
        row += 3

        # Filter info
        if self.date_from:
            worksheet.write(row, 0, 'From Date', cell_text_format)
            worksheet.write(row, 1, self.date_from, date_heading_format)
            row += 1

        if self.date_to:
            worksheet.write(row, 0, 'To Date', cell_text_format)
            worksheet.write(row, 1, self.date_to, date_heading_format)
            row += 1

        
        if self.account_id:
            account_names = ', '.join(self.account_id.mapped('name'))
            worksheet.write(row, 0, 'Account(s)', cell_text_format)
            worksheet.write(row, 1, account_names)
            row += 1
        else:
            worksheet.write(row, 0, 'Account(s)', cell_text_format)
            worksheet.write(row, 1, 'All Accounts')
            row += 1

        if self.partner_id:
            partner_names = ', '.join(self.partner_id.mapped('name'))
            worksheet.write(row, 0, 'Partner(s)', cell_text_format)
            worksheet.write(row, 1, partner_names)
            row += 1

        if self.analytic_account_id:
            worksheet.write(row, 0, 'Analytic Account', cell_text_format)
            worksheet.write(row, 1, safe_str(self.analytic_account_id.name))
            row += 1

        if self.target_moves:
            worksheet.write(row, 0, 'Target Moves', cell_text_format)
            worksheet.write(row, 1, safe_str(self.target_moves))
            row += 2

        # Headers
        if self.report_by == 'summary':
            headers = ['Account', 'Initial Balance', 'Debit', 'Credit', 'Balance']
        else:
            headers = ['Account', 'Date', 'Reference', 'Partner', 'Label', 'Debit', 'Credit', 'Balance']

        for col, header in enumerate(headers):
            worksheet.write(row, col, header, cell_text_format)
        row += 1

        # Prepare filters
        partner_ids = self.partner_id.id if self.partner_id else False
        analytic_id = self.analytic_account_id.id if self.analytic_account_id else False
        account_ids = self.account_id.ids if self.account_id else False  

        
        accounts = lines(
            self.company_id.id, self.date_from, self.date_to,
            account_ids, partner_ids, analytic_id,
            self.target_moves, 'yes'
        )

        total_debit_all = total_credit_all = 0.0

        for account in accounts:
            initial_balance = 0.0
            if self.date_from:
                initial_balance = sum_open_balance(
                    self.company_id.id, self.date_from, [account['account_id']],
                    analytic_id, partner_ids, self.target_moves
                )

            total_balance = initial_balance + (account['total_debit'] - account['total_credit'])
            balance = initial_balance

            if self.report_by == 'summary':
                worksheet.write(row, 0, safe_str(account.get('group')), cell_text_format)
                worksheet.write(row, 1, initial_balance, align_right)
                worksheet.write_number(row, 2, float(account['total_debit'] or 0.0), number_fmt)
                worksheet.write_number(row, 3, float(account['total_credit'] or 0.0), number_fmt)

                worksheet.write(row, 4, total_balance, number_fmt)
                row += 1
            else:
                worksheet.write(row, 0, safe_str(account.get('group')), cell_text_format)
                worksheet.write(row, 7, initial_balance, number_fmt)
                row += 1

                details = lines(
                    self.company_id.id, self.date_from, self.date_to,
                    [account['account_id']], partner_ids,
                    analytic_id, self.target_moves, 'no'
                )

                for line in details:
                    worksheet.write(row, 1, line['date'], date_format)
                    worksheet.write(row, 2, safe_str(line.get('voucher_no')))
                    worksheet.write(row, 3, safe_str(line.get('partner_name')))
                    worksheet.write(row, 4, safe_str(line.get('label')))
                    worksheet.write_number(row, 5, float(line['debit']) or 0, number_fmt)
                    worksheet.write_number(row, 6,  float(line['credit']) or 0, number_fmt)

                    balance += line['debit'] - line['credit']
                    worksheet.write(row, 7, balance, number_fmt)
                    row += 1

                worksheet.write(row, 0, f"TOTAL {safe_str(account.get('group'))}", cell_text_format)
                worksheet.write(row, 5, account['total_debit'], number_fmt)
                worksheet.write(row, 6, account['total_credit'], number_fmt)
                worksheet.write(row, 7, total_balance, number_fmt)
                row += 1

           

        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        fp.close()

        self.write({'datas': out, 'datas_fname': filename})

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=datas&download=true&filename={filename}',
        }




class AccountStatementReport(models.AbstractModel):
    _name = 'report.mgs_account.account_statement_report'
    _description = 'Account Statement Report'

    def _lines(self, company_id, date_from, date_to, account_ids, partner_id, analytic_account_id, target_moves, is_it_group):
        params = []
        states = """('posted','draft')"""
        if target_moves == 'posted':
            states = """('posted')"""

        if is_it_group == 'yes':
            select_query = """
            select aa.name as group, aa.name as account_name, aa.id as account_id, sum(aml.debit) as total_debit, sum(aml.credit) total_credit
            """

            order_query = """
            group by aa.name, aa.id
            order by aa.code_store
            """

        if is_it_group == 'no':
            select_query = """
            select aml.id, aml.date as date, aml.move_id as move_id, aj.name as voucher_type,
            rp.name as partner_name, aml.name as label, aml.ref as ref, am.name as voucher_no,
            aml.partner_id, aml.account_id, aml.debit as debit, aml.credit as credit, am.ref as move_ref
            """

            order_query = """
            order by aml.date, aml.move_id
            """

        from_where_query = """
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join res_partner as rp on aml.partner_id=rp.id
        left join account_move as am on aml.move_id=am.id
        left join account_journal as aj on aml.journal_id=aj.id
        where am.state in """ + states

        if date_from:
            params.append(date_from)
            from_where_query += """ and aml.date >= %s"""

        if date_to:
            params.append(date_to)
            from_where_query += """ and aml.date <= %s"""

        # if account_id:
        #     from_where_query += """ and aml.account_id = """ + str(account_id)
            
        if account_ids:
            from_where_query += """ and aml.account_id in (""" + ','.join(map(str, account_ids)) + """)"""
        

        if analytic_account_id:
            from_where_query += ' and aml.analytic_distribution @> \'{"%s": 100}\'::jsonb' % str(
                analytic_account_id)

        if partner_id:
            from_where_query += """ and aml.partner_id = """ + str(partner_id)

        if company_id:
            from_where_query += """ and aml.company_id = """ + str(company_id)

        query = select_query + from_where_query + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res


    def _sum_open_balance(self, company_id, date_from, account_ids, analytic_account_id, partner_id, target_moves):
        states = """('posted','draft')"""
        if target_moves == 'posted':
            states = """('posted')"""

        total_balance = 0.0  

        for acc_id in account_ids:  
            params = [acc_id, date_from, company_id]
            query = f"""
                select sum(aml.debit - aml.credit)
                from account_move_line as aml
                left join account_move as am on aml.move_id = am.id
                where aml.account_id = %s and aml.date < %s 
                and am.state in {states}
                and aml.company_id = %s
            """

            if analytic_account_id:
                query += ' and aml.analytic_distribution @> \'{"%s": 100}\'::jsonb' % str(analytic_account_id)

            if partner_id:
                query += """ and aml.partner_id = """ + str(partner_id)

            self.env.cr.execute(query, tuple(params))
            contemp = self.env.cr.fetchone()
            if contemp and contemp[0]:
                total_balance += contemp[0]  
        return total_balance
    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to'],
            'account_ids': data['form']['account_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'target_moves': data['form']['target_moves'],
            'analytic_account_id': data['form']['analytic_account_id'],
            'partner_id': data['form']['partner_id'],
            'sum_open_balance': self._sum_open_balance,
            'lines': self._lines,
        }
