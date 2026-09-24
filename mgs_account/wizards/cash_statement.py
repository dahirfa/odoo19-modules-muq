# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO
import json

class AccountStatement(models.TransientModel):
    _name = 'mgs_account.cash_statement'
    _description = 'Cash/Bank Statement Wizard'

    journal_id = fields.Many2one('account.journal', string="Cash Account", domain=[('type', 'in', ['cash', 'bank'])], required=True)
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
                'account_id': [self.journal_id.default_account_id.id, self.journal_id.default_account_id.name],
                'analytic_account_id': [self.analytic_account_id.id, self.analytic_account_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_by': self.report_by,
                'target_moves': self.target_moves
            },
        }

        return self.env.ref('mgs_account.action_report_cash_statement').report_action(self, data=data)

    def export_to_excel(self):
   

        def safe_str(value):
            if isinstance(value, dict):
                lang = self.env.lang or 'en_US'
                return value.get(lang) or next(iter(value.values()), '')
            elif value is None:
                return ''
            return str(value)

        account_statement_report_obj = self.env['report.mgs_account.account_statement_report']
        lines = account_statement_report_obj._lines
        sum_open_balance = account_statement_report_obj._sum_open_balance

        fp = BytesIO()
        filename = 'CashBankStatement.xlsx'
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('CashBankStatement')

        heading_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'font_size': 14})
        sub_heading_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'font_size': 12})
        cell_text_format = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 12})
        cell_number_format = workbook.add_format({'align': 'right', 'bold': True, 'font_size': 12})
        align_right = workbook.add_format({'align': 'right'})
        align_right_total = workbook.add_format({'align': 'right', 'bold': True})
        date_heading_format = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 12, 'num_format': 'dd-mm-yyyy'})
        date_format = workbook.add_format({'align': 'left', 'num_format': 'dd-mm-yyyy'})

        row = 1
        worksheet.merge_range('A1:I1', safe_str(self.company_id.name), sub_heading_format)
        row += 1
        worksheet.merge_range('A2:I3', 'Cash/Bank Statement', heading_format)

        row += 2
        column = -1
        if self.date_from:
            row += 1
            worksheet.write(row, column+1, 'From Date', cell_text_format)
            worksheet.write(row, column+2, self.date_from, date_heading_format)

        if self.date_to:
            row += 1
            worksheet.write(row, column+1, 'To Date', cell_text_format)
            worksheet.write(row, column+2, self.date_to, date_heading_format)

        if self.target_moves:
            row += 1
            worksheet.write(row, column+1, 'Target Moves', cell_text_format)
            worksheet.write(row, column+2, safe_str(self.target_moves))

        # Table Headers
        row += 2
        column = -1

        if self.report_by == 'summary':
            worksheet.write(row, column+1, 'Account', cell_text_format)
            worksheet.write(row, column+2, 'Initial Balance', cell_number_format)
            worksheet.write(row, column+3, 'Debit', cell_number_format)
            worksheet.write(row, column+4, 'Credit', cell_number_format)
            worksheet.write(row, column+5, 'Balance', cell_number_format)
        else:
            worksheet.write(row, column+1, 'Account', cell_text_format)
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'JV#', cell_text_format)
            worksheet.write(row, column+4, 'Partner', cell_text_format)
            worksheet.write(row, column+5, 'Label', cell_text_format)
            worksheet.write(row, column+6, 'Debit', align_right_total)
            worksheet.write(row, column+7, 'Credit', align_right_total)
            worksheet.write(row, column+8, 'Balance', align_right_total)

        accounts = lines(
            self.company_id.id,
            self.date_from,
            self.date_to,
            self.journal_id.default_account_id.id,
            self.partner_id.id,
            self.analytic_account_id.id,
            self.target_moves,
            'yes'
        )

        for account in accounts:
            initial_balance = 0
            if self.date_from:
                initial_balance = sum_open_balance(
                    self.company_id.id,
                    self.date_from,
                    account['account_id'],
                    self.analytic_account_id.id,
                    self.partner_id.id,
                    self.target_moves
                )

            total_balance = initial_balance + (account['total_debit'] - account['total_credit'])
            balance = initial_balance

            if self.report_by == 'summary':
                row += 1
                column = -1
                worksheet.write(row, column+1, safe_str(account.get('group')), cell_text_format)
                worksheet.write(row, column+2, int(initial_balance), align_right)
                worksheet.write(row, column+3, int(account['total_debit']), align_right)
                worksheet.write(row, column+4, int(account['total_credit']), align_right)
                worksheet.write(row, column+5, int(total_balance), align_right)

            if self.report_by == 'detail':
                row += 2
                column = -1
                worksheet.write(row, column+1, safe_str(account.get('group')), cell_text_format)
                worksheet.write(row, column+8, int(initial_balance), align_right_total)

                details = lines(
                    self.company_id.id,
                    self.date_from,
                    self.date_to,
                    account['account_id'],
                    self.partner_id.id,
                    self.analytic_account_id.id,
                    self.target_moves,
                    'no'
                )

                for line in details:
                    row += 1
                    column = -1
                    worksheet.write(row, column+2, line['date'], date_format)
                    worksheet.write(row, column+3, safe_str(line.get('voucher_no')))
                    worksheet.write(row, column+4, safe_str(line.get('partner_name')))
                    worksheet.write(row, column+5, safe_str(line.get('label')))
                    worksheet.write(row, column+6, float(line['debit']), align_right)
                    worksheet.write(row, column+7, float(line['credit']), align_right)
                    balance += line['debit'] - line['credit']
                    worksheet.write(row, column+8, int(balance), align_right)

                row += 1
                worksheet.write(row, column+1, 'TOTAL ' + safe_str(account.get('group')), cell_text_format)
                worksheet.write(row, column+6, int(account['total_debit']), align_right_total)
                worksheet.write(row, column+7, int(account['total_credit']), align_right_total)
                worksheet.write(row, column+8, int(total_balance), align_right_total)


        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out, 'datas_fname': filename})
        fp.close()

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=datas&download=true&filename={filename}',
        }




class AccountStatementReport(models.AbstractModel):
    _name = 'report.mgs_account.cash_statement_report'
    _description = 'Account Statement Report'



    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        report_obj = self.env['report.mgs_account.account_statement_report']

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date_from': data['form']['date_from'],
            'date_to': data['form']['date_to'],
            'account_id': data['form']['account_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'target_moves': data['form']['target_moves'],
            'analytic_account_id': data['form']['analytic_account_id'],
            'partner_id': data['form']['partner_id'],
            'sum_open_balance': report_obj._sum_open_balance,
            'lines': report_obj._lines,
        }
