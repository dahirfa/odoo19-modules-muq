# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import xlsxwriter
import base64
from io import BytesIO
_logger = logging.getLogger(__name__)


class Accounting_reportPartner_ledger(models.TransientModel):
    _name = "multicurrency.partnerledger"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.user.company_id,
    )
    currency_ids = fields.Many2many(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env["res.currency"].search([]),
    )
    date_from = fields.Date(string="Start Date")
    date_to = fields.Date(string="End Date")
    target_move = fields.Selection(
        [
            ("posted", "All Posted Entries"),
            ("all", "All Entries"),
        ],
        string="Target Moves",
        required=True,
        default="posted",
    )
    reconciled = fields.Boolean("Show Initial Balance", default=True)
    result_selection = fields.Selection(
        [
            ("customer", "Receivable Accounts"),
            ("supplier", "Payable Accounts"),
            ("customer_supplier", "Receivable and Payable Accounts"),
        ],
        string="Partner's Account",
        required=True,
        default="customer",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        "rel_multicurrency_partner",
        "multicurrency_id",
        "partner_id",
        string="Partner's",
    )

    category_id = fields.Many2many(
        "res.partner.category",
        column1="partner_id",
        column2="category_id",
        string="Tags",
    )
    
    
    display_zero_values = fields.Boolean(
        string='Display Zero Values?',
    )
    

    summary = fields.Boolean(
        string="Summary",
    )
    
    include_lines = fields.Boolean(
    string='Include Lines?'
    )
    
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)


    def get_data(self):
        data = {}
        used_context = {"currency_ids": [a.id for a in self.currency_ids]}
        data["move_state"] = ["draft", "posted"]
        if self.target_move == "posted":
            data["move_state"] = ["posted"]
        result_selection = self.result_selection
        if result_selection == "supplier":
            data["account_type"] = ["supplier"]
        elif result_selection == "customer":
            data["account_type"] = ["customer"]
        else:
            data["account_type"] = ["customer", "supplier"]

        data["date_from"] = self.date_from
        data["date_to"] = self.date_to

        return {
            "data": data,
            "docs": self.partner_ids.ids,
            "target_move": self.target_move,
            "account_type": self.result_selection,
            "reconciled": self.reconciled,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "summary": self.summary,
            'category_id':self.category_id.ids,
            'display_zero_values':self.display_zero_values
        }
    
   
           
    def print_excel_report(self):
        mc_partner_ledger_report = self.env['report.multi_currency_partner_ledger_app.report_partnerledger']
        lines = mc_partner_ledger_report._lines
        previous_balance = mc_partner_ledger_report._get_previous_balance
        get_invoice = mc_partner_ledger_report._get_invoice
        data = self.get_data().get('data')
        partner_domain = []
        
        if self.partner_ids.ids:
            partner_domain += [("id", "in", self.partner_ids.ids)]
        
        if self.category_id.ids:
            partner_domain += [('category_id', 'in', self.category_id.ids)]

        partner_ids = self.env["res.partner"].search(partner_domain)
        currency_ids = self.env["res.currency"].browse(self.currency_ids.ids)
        
        
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'Multicurrency_Partner_Ledger'
        worksheet = workbook.add_worksheet(filename)
        
        worksheet.set_column(0, 10, 20)
        
        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        
        sub_heading_format.set_bg_color('#F0ECE5') 
        
        totals_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        
        totals_format.set_underline()
        totals_format.set_bg_color('#F0ECE5') 
        
        
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': False, 'size': 12})
        
        header_cell_text = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        header_cell_text.set_bg_color('#F0ECE5') 
        header_cell_number = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        header_cell_number.set_bg_color('#F0ECE5') 
        
        partner_name_format = workbook.add_format({'align': 'center', 'bold': True, 'size': 12})
        partner_name_format.set_bg_color("BACD92")
        
        
        currency_cell_text = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'font_color': '#0E46A3'})
        
        
        previous_balance_cell_text = workbook.add_format(
            {'align': 'left', 'bold': False, 'size': 12, 'font_color': '#FC4100'})
        
        previous_balance_cell_text.set_italic()
        
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': False, 'size': 12})
        
        
        align_right = workbook.add_format({'align': 'right'})
        
        
        date_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format(
            {'align': 'left', 'num_format': 'd-m-yyyy'})
        
        
        
        # Heading
        row = 1
        worksheet.merge_range('A1:G1', f"Partner Ledger {'(Detailed Report)' if not self.summary else '(Summary Report)'}", heading_format)
        
        row += 1
        column = -1
        if self.date_from:
            row += 1
            worksheet.write(row, column+1, 'From Date', cell_text_format)
            worksheet.write(row, column+2, self.date_from or '', date_heading_format)
        column+2

        if self.date_to:
            row += 1
            worksheet.write(row, column+1, 'To Date', cell_text_format)
            worksheet.write(row, column+2, self.date_to or '', date_heading_format)
        column+2

        if self.target_move:
            row += 1
            worksheet.write(row, column+1, 'Target Move', cell_text_format)
            worksheet.write(row, column+2, self.target_move or '')
        column+2

        if self.result_selection:
            row += 1
            worksheet.write(row, column+1, 'Accounts', cell_text_format)
            worksheet.write(row, column+2, self.result_selection or '')
        column+2
        
        if self.reconciled:
            row += 1
            worksheet.write(row, column+1, 'Show Initial Balance', cell_text_format)
            worksheet.write(row, column+2, self.reconciled or '', cell_text_format)
        column+2
        
        
        # Sub headers
        row += 2
        column = -1
        if not self.summary:
            if self.include_lines:
                worksheet.write(row, column+1, 'Date', header_cell_text)
                worksheet.write(row, column+2, 'Description', header_cell_text)
                worksheet.write(row, column+3, 'Ref', header_cell_text)
                worksheet.write(row, column+4, 'Details', header_cell_text)
                worksheet.write(row, column+5, 'Debit', header_cell_number)
                worksheet.write(row, column+6, 'Credit', header_cell_number)
                worksheet.write(row, column+7, 'Balance', header_cell_number) if self.reconciled else None
            if not self.include_lines:
                worksheet.write(row, column+1, 'Date', header_cell_text)
                worksheet.write(row, column+2, 'Description', header_cell_text)
                worksheet.write(row, column+3, 'Ref', header_cell_text)
                worksheet.write(row, column+4, 'Debit', header_cell_number)
                worksheet.write(row, column+5, 'Credit', header_cell_number)
                worksheet.write(row, column+6, 'Balance', header_cell_number) if self.reconciled else None


        if self.summary:
            worksheet.write(row, column+1, 'Partner', header_cell_text)
            worksheet.write(row, column+2, 'Previous Balance', header_cell_number)
            worksheet.write(row, column+3, 'Debit', header_cell_number)
            worksheet.write(row, column+4, 'Credit', header_cell_number)
            worksheet.write(row, column+5, 'Balance', header_cell_number) if self.reconciled else None
        
        row += 2
        if not self.summary:
            for partner in partner_ids:
                    row += 1
                    if self.include_lines and self.reconciled:
                        worksheet.merge_range(f'A{row}:G{row}', partner.name, partner_name_format)
                        row += 1 
                    if not self.include_lines and self.reconciled:
                        worksheet.merge_range(f'A{row}:F{row}', partner.name, partner_name_format) 
                        row += 1
                    if not self.include_lines and not self.reconciled:
                        worksheet.merge_range(f'A{row}:E{row}', partner.name, partner_name_format) 
                        row += 1
                        
                    if self.include_lines and not self.reconciled:
                        worksheet.merge_range(f'A{row}:F{row}', partner.name, partner_name_format) 
                        row += 1
                        
                        
                    for currency in currency_ids:
                        if self.include_lines and self.reconciled:
                            worksheet.merge_range(f'A{row}:G{row}', currency.name, currency_cell_text)
                            row += 1 
                        if not self.include_lines and self.reconciled:
                            worksheet.merge_range(f'A{row}:F{row}', currency.name, currency_cell_text)
                            row += 1
                        if not self.include_lines and not self.reconciled:
                            worksheet.merge_range(f'A{row}:E{row}', currency.name, currency_cell_text) 
                            row += 1
                            
                        if self.include_lines and not self.reconciled:
                            worksheet.merge_range(f'A{row}:F{row}', currency.name, currency_cell_text) 
                            row += 1
                            
                            
                            
                        if previous_balance(data, partner, currency):
                            if self.include_lines and self.reconciled:
                                worksheet.merge_range(f'A{row}:F{row}', "Previous Balance", previous_balance_cell_text)
                                worksheet.write(row-1,column+7, f"{previous_balance(data, partner, currency).get('currency_id')}{'{:,.2f}'.format(previous_balance(data, partner, currency).get('previous_balance'))}", align_right)
                                row += 1 
                            if not self.include_lines and self.reconciled:
                                worksheet.merge_range(f'A{row}:E{row}', "Previous Balance", previous_balance_cell_text)
                                worksheet.write(row-1,column+6, f"{previous_balance(data, partner, currency).get('currency_id')}{'{:,.2f}'.format(previous_balance(data, partner, currency).get('previous_balance'))}", align_right)
                                row += 1 
                            if not self.include_lines and not self.reconciled:
                                worksheet.merge_range(f'A{row}:D{row}', "Previous Balance", previous_balance_cell_text)
                                worksheet.write(row-1,column+5, f"{previous_balance(data, partner, currency).get('currency_id')}{'{:,.2f}'.format(previous_balance(data, partner, currency).get('previous_balance'))}", align_right)
                                row += 1 
                                
                            if self.include_lines and not self.reconciled:
                                worksheet.merge_range(f'A{row}:E{row}', "Previous Balance", previous_balance_cell_text)
                                worksheet.write(row-1,column+6, f"{previous_balance(data, partner, currency).get('currency_id')}{'{:,.2f}'.format(previous_balance(data, partner, currency).get('previous_balance'))}", align_right)
                                row += 1 
                                
                                
                        total_balance = 0        
                        for line in lines(data, partner, currency):
                            if line['debit'] > 0 or line['credit'] > 0:
                                total_balance += line.get("progress", 0)
                                if self.include_lines:
                                    worksheet.write(row, column+1, line['date'], date_format)
                                    worksheet.write(row, column+2, f"{'' if not line['description'] else line['description']}", cell_text_format)
                                    worksheet.write(row, column+3, line['displayed_name'], cell_text_format)
                                    for invoice_line in get_invoice(line['move_name']):
                                        if invoice_line.move_type !='entry' and invoice_line.display_type == "product":
                                            worksheet.write(row, column+4, f"{invoice_line.name or ''}{invoice_line.quantity or ''} {invoice_line.product_uom_id.name or ''} * {'{0:,.2f}'.format(invoice_line.price_unit) or ''} = {invoice_line.currency_id.symbol or ''}{'{0:,.2f}'.format(invoice_line.price_subtotal) or ''}", cell_text_format)
                                    worksheet.write(row, column+5, f"{line['currency_id']} {'{:,.2f}'.format(line['debit']) or '0.00'}", cell_number_format)
                                    worksheet.write(row, column+6, f"{line['currency_id']} {'{:,.2f}'.format(line['credit']) or '0.00'}", cell_number_format)
                                    worksheet.write(row, column+7, f"{line['currency_id']} {'{:,.2f}'.format(total_balance) or '0.00'}", cell_number_format) if self.reconciled else None
                                    row += 1
                                if not self.include_lines:
                                    worksheet.write(row, column+1, line['date'], date_format)
                                    worksheet.write(row, column+2, f"{'' if not line['description'] else line['description']}", cell_text_format)
                                    worksheet.write(row, column+3, line['displayed_name'], cell_text_format)
                                    worksheet.write(row, column+4, f"{line['currency_id']} {'{:,.2f}'.format(line['debit']) or '0.00'}", cell_number_format)
                                    worksheet.write(row, column+5, f"{line['currency_id']} {'{:,.2f}'.format(line['credit']) or '0.00'}", cell_number_format)
                                    worksheet.write(row, column+6, f"{line['currency_id']} {'{:,.2f}'.format(total_balance) or '0.00'}", cell_number_format) if self.reconciled else None
                                    row += 1      
                        if lines(data, partner, currency):
                            if self.include_lines:
                                worksheet.merge_range(f'A{row+1}:D{row+1}', "TOTAL", sub_heading_format)
                                worksheet.write(row, column+5, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('debit_total'))}", totals_format)
                                worksheet.write(row, column+6, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('credit_total'))}", totals_format)
                                worksheet.write(row, column+7, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('balance_total'))}", totals_format) if self.reconciled else None
                                row += 1
                            if not self.include_lines:
                                worksheet.merge_range(f'A{row+1}:C{row+1}', "TOTAL", sub_heading_format)
                                worksheet.write(row, column+4, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('debit_total'))}", totals_format)
                                worksheet.write(row, column+5, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('credit_total'))}", totals_format)
                                worksheet.write(row, column+6, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('balance_total'))}", totals_format) if self.reconciled else None
                                row += 1
                            
                    
                            
        if self.summary:
            for currency in currency_ids:
                worksheet.merge_range(f'A{row}:G{row}', currency.name, currency_cell_text)
                row += 1
                for partner in partner_ids:
                    if self.display_zero_values:
                        worksheet.write(row, column+1, partner.name, cell_text_format)
                        worksheet.write(row, column+2, f"{previous_balance(data, partner, currency).get('currency_id')}{'{:,.2f}'.format(previous_balance(data, partner, currency).get('previous_balance'))}", cell_number_format)
                        
                        if lines(data, partner, currency):
                            worksheet.write(row, column+3, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('debit_total'))}", cell_number_format)
                        else:
                            worksheet.write(row, column+3, f"{previous_balance(data, partner, currency).get('currency_id')} {0.0}", cell_number_format)
                        
                        
                        if lines(data, partner, currency):
                            worksheet.write(row, column+4, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('credit_total'))}", cell_number_format)
                        else:
                            worksheet.write(row, column+4, f"{previous_balance(data, partner, currency).get('currency_id')} {0.0}", cell_number_format)
                            
                        if lines(data, partner, currency):
                            worksheet.write(row, column+5, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('balance_total'))}", cell_number_format)
                        else:
                            worksheet.write(row, column+5, f"{previous_balance(data, partner, currency).get('currency_id')} {0.0}", cell_number_format)
                        
                        row += 1
                    
                    if not self.display_zero_values:
                        if lines(data, partner, currency):
                            worksheet.write(row, column+1, partner.name, cell_text_format)
                            worksheet.write(row, column+2, f"{previous_balance(data, partner, currency).get('currency_id')}{'{:,.2f}'.format(previous_balance(data, partner, currency).get('previous_balance'))}", cell_number_format)
                            worksheet.write(row, column+3, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('debit_total'))}", cell_number_format)
                            worksheet.write(row, column+4, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('credit_total'))}", cell_number_format)
                            worksheet.write(row, column+5, f"{lines(data, partner, currency)[0].get('currency_id')} {'{:,.2f}'.format(lines(data, partner, currency)[0].get('balance_total'))}", cell_number_format)
                            row += 1

        
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out, 'datas_fname': filename})
        fp.close()
        filename += '%2Exlsx'
        
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            "url":f"web/content/?model={self._name}&id={self.id}&field=datas&download=true&filename={filename}",
        }
               

    def print_partner_ledger(self):
        data = {}
        used_context = {"currency_ids": [a.id for a in self.currency_ids]}
        data["move_state"] = ["draft", "posted"]
        if self.target_move == "posted":
            data["move_state"] = ["posted"]
        result_selection = self.result_selection
        if result_selection == "supplier":
            data["account_type"] = ["supplier"]
        elif result_selection == "customer":
            data["account_type"] = ["customer"]
        else:
            data["account_type"] = ["customer", "supplier"]

        data["date_from"] = self.date_from
        data["date_to"] = self.date_to

        final_dict = {
            "data": data,
            "used_context": used_context,
            "docs": self.partner_ids.ids,
            "target_move": self.target_move,
            "account_type": self.result_selection,
            "reconciled": self.reconciled,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "summary": self.summary,
            'category_id':self.category_id.ids,
            'display_zero_values':self.display_zero_values
        }

        return (
            self.env.ref(
                "multi_currency_partner_ledger_app.multi_currency_partner_ledger"
            )
            # .with_context(used_context)
            .report_action(self, data=final_dict)
        )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
