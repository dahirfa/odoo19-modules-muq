# # -*- coding: utf-8 -*-
# from datetime import datetime, timedelta, date
# from odoo import models, fields, api
# import xlsxwriter
# import base64
# from io import BytesIO


# class GrossProfit(models.TransientModel):
#     _name = 'mgs_account.gross_profit'
#     _description = 'Gross Profit Wizard'

#     product_id = fields.Many2one('product.product', string="Product")
#     partner_id = fields.Many2one('res.partner', string="Partner")
#     # , default=lambda self: fields.Date.today().replace(day=1)
#     date_from = fields.Date('From Date')
#     # , default=lambda self: fields.Date.today()
#     date_to = fields.Date('To Date')
#     company_id = fields.Many2one(
#         'res.company', string='Company', default=lambda self: self.env.company.id, required=True)
#     report_by = fields.Selection(
#         [('Product', 'Product'), ('Partner', 'Partner')], string='Group by', default='Product', required=True)
#     target_moves = fields.Selection(
#         [('all', 'All Entries'), ('posted', 'All Posted Entries')], string='Target Moves', default='all', required=True)
#     product_type = fields.Selection([('all', 'All Products'), ('product', '	Storable Products'), (
#         'service', 'Service Products')], string='Product Type', default='all', required=True)
#     datas = fields.Binary('File', readonly=True)
#     datas_fname = fields.Char('Filename', readonly=True)

#     def check_report(self):
#         data = {
#             'ids': self.ids,
#             'model': self._name,
#             'form': {
#                 'company_id': [self.company_id.id, self.company_id.name],
#                 'partner_id': [self.partner_id.id, self.partner_id.name],
#                 'product_id': [self.product_id.id, self.product_id.name],
#                 'date_from': self.date_from,
#                 'date_to': self.date_to,
#                 'report_by': self.report_by,
#                 'target_moves': self.target_moves,
#                 'product_type': self.product_type,
#             },
#         }

#         return self.env.ref('mgs_account.action_report_gross_profit').report_action(self, data=data)

#     def export_to_excel(self):
#         gross_profit_report_obj = self.env['report.mgs_account.gross_profit_report']
#         lines = gross_profit_report_obj._lines

#         fp = BytesIO()
#         workbook = xlsxwriter.Workbook(fp)
#         filename = 'GrossProfitReports'
#         worksheet = workbook.add_worksheet(filename)

#         # Styles
#         heading_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
#         sub_heading_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
#         cell_text_format = workbook.add_format({'align': 'left', 'bold': True, 'size': 12})
#         cell_number_format = workbook.add_format({'align': 'right', 'bold': True, 'size': 12})
#         align_right = workbook.add_format({'align': 'right'})
#         date_format = workbook.add_format({'align': 'left', 'num_format': 'd-m-yyyy'})

#         # Header
#         row = 1
#         worksheet.merge_range('A1:G1', self.company_id.name, sub_heading_format)
#         row += 1
#         worksheet.merge_range('A2:G3', 'Gross Profit Report', heading_format)

#         # Search Criteria
#         row += 2
#         column = -1

#         if self.date_from:
#             row += 1
#             worksheet.write(row, column+1, 'From Date', cell_text_format)
#             worksheet.write(row, column+2, self.date_from, date_format)

#         if self.date_to:
#             row += 1
#             worksheet.write(row, column+1, 'To Date', cell_text_format)
#             worksheet.write(row, column+2, self.date_to, date_format)

#         if self.product_id:
#             row += 1
#             worksheet.write(row, column+1, 'Product', cell_text_format)
#             worksheet.write(row, column+2, self.product_id.name)

#         if self.report_by:
#             row += 1
#             worksheet.write(row, column+1, 'Report by', cell_text_format)
#             worksheet.write(row, column+2, self.report_by)

#         if self.target_moves:
#             row += 1
#             worksheet.write(row, column+1, 'Target Moves', cell_text_format)
#             worksheet.write(row, column+2, self.target_moves)

#         if self.product_type:
#             row += 1
#             worksheet.write(row, column+1, 'Product Type', cell_text_format)
#             worksheet.write(row, column+2, self.product_type)

#         # Table headers
#         row += 2
#         column = -1
#         worksheet.write(row, column+1, 'No', cell_text_format)
#         worksheet.write(row, column+2, self.report_by, cell_text_format)
#         worksheet.write(row, column+3, 'Product Code', cell_text_format)
#         worksheet.write(row, column+4, 'Actual Revenue', cell_number_format)
#         worksheet.write(row, column+5, 'Actual Cost', cell_number_format)
#         worksheet.write(row, column+6, 'Gross Profit', cell_number_format)
#         worksheet.write(row, column+7, 'Gross Profit %', cell_number_format)

#         # Data lines
#         no = 0
#         for line in lines(
#             self.company_id.id,
#             self.date_from,
#             self.date_to,
#             self.partner_id.id,
#             self.product_id.id,
#             self.target_moves,
#             self.product_type,
#             self.report_by
#         ):
#             row += 2
#             column = -1
#             no += 1

#             group = line['group']
#             default_code = line.get('default_code', '')
#             act_revenue = line['act_revenue']
#             act_cost = line['act_cost']
#             balance = act_revenue - act_cost
#             balance_percentage = (balance / act_revenue) * 100 if act_revenue else 0

#             worksheet.write(row, column+1, no)
#             worksheet.write(row, column+2, group)
#             worksheet.write(row, column+3, default_code)
#             worksheet.write(row, column+4, '{:,.2f}'.format(act_revenue), align_right)
#             worksheet.write(row, column+5, '{:,.2f}'.format(act_cost), align_right)
#             worksheet.write(row, column+6, '{:,.2f}'.format(balance), align_right)
#             worksheet.write(row, column+7, '{:,.2f}'.format(balance_percentage), align_right)

#         # Finalize
#         workbook.close()
#         out = base64.encodebytes(fp.getvalue())
#         self.write({'datas': out, 'datas_fname': filename})
#         fp.close()
#         filename += '%2Exlsx'

#         return {
#             'type': 'ir.actions.act_url',
#             'target': 'new',
#             'url': f'web/content/?model={self._name}&id={self.id}&field=datas&download=true&filename={filename}',
#         }


# class GrossProfitReport(models.AbstractModel):
#     _name = 'report.mgs_account.gross_profit_report'
#     _description = 'Gross Profit Report'

    
#     def _lines(self, company_id, date_from, date_to, partner_id, product_id, target_moves, product_type, report_by):
#         params = []
#         states = "('posted','draft')"
#         if target_moves == 'posted':
#             states = "('posted')"

#         select_query = """SELECT pt.name['en_US'] AS group, pt.default_code AS default_code, pp.id AS product_id,
#                         COALESCE(SUM(aml.debit), 0) AS act_cost,
#                         COALESCE(SUM(aml.credit), 0) AS act_revenue """

#         order_query = " GROUP BY pt.name, pt.default_code, pp.id ORDER BY pt.name"

#         if report_by == 'Partner':
#             select_query = """SELECT rp.name AS group,
#                             COALESCE(SUM(aml.debit), 0) AS act_cost,
#                             COALESCE(SUM(aml.credit), 0) AS act_revenue """
#             order_query = " GROUP BY rp.name ORDER BY rp.name"

#         from_where_query = """
#             FROM account_move_line AS aml
#             LEFT JOIN account_account AS aa ON aml.account_id = aa.id
#             LEFT JOIN res_partner AS rp ON aml.partner_id = rp.id
#             LEFT JOIN product_product AS pp ON aml.product_id = pp.id
#             LEFT JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
#             WHERE aa.account_type IN ('expense_direct_cost', 'income')
#             AND aml.parent_state IN """ + states

#         if date_from:
#             params.append(date_from)
#             from_where_query += " AND aml.date >= %s"

#         if date_to:
#             params.append(date_to)
#             from_where_query += " AND aml.date <= %s"

#         if report_by == 'Product' and product_id:
#             from_where_query += f" AND aml.product_id = {product_id}"

#         if report_by == 'Partner' and partner_id:
#             from_where_query += f" AND aml.partner_id = {partner_id}"

#         if company_id:
#             from_where_query += f" AND aml.company_id = {company_id}"

#         # ✅ Ensure correct spacing
#         query = select_query + from_where_query + order_query

#         self.env.cr.execute(query, tuple(params))
#         return self.env.cr.dictfetchall()

#     @api.model
#     def _get_report_values(self, docids, data=None):
#         model = self.env.context.get('active_model')
#         docs = self.env[model].browse(self.env.context.get('active_id'))

#         return {
#             'doc_ids': self.ids,
#             'doc_model': model,
#             'docs': docs,
#             'date_from': data['form']['date_from'],
#             'date_to': data['form']['date_to'],
#             'product_id': data['form']['product_id'],
#             'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
#             'report_by': data['form']['report_by'],
#             'target_moves': data['form']['target_moves'],
#             'product_type': data['form']['product_type'],
#             'partner_id': data['form']['partner_id'],
#             'lines': self._lines,
#         }
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO
import logging
_logger = logging.getLogger(__name__)



class GrossProfit(models.TransientModel):
    _name = 'mgs_account.gross_profit'
    _description = 'Gross Profit Wizard'

    product_categ_id = fields.Many2many('product.category', string="Product Categories", domain=lambda self: [('id', 'in', self._get_categories_with_products())])
    product_id = fields.Many2many('product.product', string="Products", domain="[('categ_id', 'in', product_categ_id)]")
    journal_ids = fields.Many2many('account.journal', string="Journals", domain="[('type', '!=', ['bank', 'cash'])]")

    # product_id = fields.Many2one('product.product', string="Product")
    partner_id = fields.Many2one('res.partner', string="Partner")
    # , default=lambda self: fields.Date.today().replace(day=1)
    date_from = fields.Date('From Date', default=lambda self: date(date.today().year, 1, 1))
    # , default=lambda self: fields.Date.today()
    date_to = fields.Date('To Date', default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id, required=True)
    report_by = fields.Selection(
        [('Product', 'Product'), ('Partner', 'Partner'), ('Category', 'Product Category')], string='Group by', default='Product', required=True)
    target_moves = fields.Selection(
        [('all', 'All Entries'), ('posted', 'All Posted Entries')], string='Target Moves', default='all', required=True)
    product_type = fields.Selection([('all', 'All Products'), ('consu', '	Storable Products'), (
        'service', 'Service Products')], string='Product Type', default='consu', required=True)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)
    analytic_account_ids = fields.Many2many(
    'account.analytic.account', string="Analytic Accounts")

    @api.model
    def _get_categories_with_products(self):
        # Get categories that have at least one product assigned directly
        categories_with_products = self.env['product.product'].read_group(
            [('categ_id', '!=', False)],
            ['categ_id'],
            ['categ_id']
        )
        return [cat['categ_id'][0] for cat in categories_with_products if cat['categ_id']]

    def check_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'company_id': [self.company_id.id, self.company_id.name],
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'product_categ_ids': self.product_categ_id.ids,
                'product_id': self.product_id.ids,
                'journal_ids': self.journal_ids.ids,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'report_by': self.report_by,
                'target_moves': self.target_moves,
                'product_type': self.product_type,
                'analytic_account_ids': [(a.id, a.name) for a in self.analytic_account_ids],
            },
        }

        return self.env.ref('mgs_account.action_report_gross_profit').report_action(self, data=data)

    
    # def export_to_excel(self):

    #     gross_profit_report_obj = self.env['report.mgs_account.gross_profit_report']
    #     analytic_account_names = ', '.join([a.name for a in self.analytic_account_ids])
    #     analytic_ids = [a.id for a in self.analytic_account_ids]

    #     lines_data = gross_profit_report_obj._lines(
    #         self.company_id.id,
    #         self.date_from,
    #         self.date_to,
    #         self.partner_id.id,
    #         self.product_id.ids,
    #         self.target_moves,
    #         self.product_type,
    #         self.report_by,
    #         analytic_ids,
    #         self.product_categ_id.ids,
    #         self.journal_ids.ids
    #     )

    #     fp = BytesIO()
    #     workbook = xlsxwriter.Workbook(fp)
    #     filename = 'GrossProfitReports'
    #     worksheet = workbook.add_worksheet(filename)

    #     # Format definitions
    #     heading_format = workbook.add_format(
    #         {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
    #     sub_heading_format = workbook.add_format(
    #         {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
    #     cell_text_format = workbook.add_format(
    #         {'align': 'left', 'bold': True, 'size': 12})
    #     cell_number_format = workbook.add_format(
    #         {'align': 'right', 'bold': True, 'size': 12})
    #     align_right = workbook.add_format({'align': 'right'})
    #     align_right_total = workbook.add_format(
    #         {'align': 'right', 'bold': True})
    #     date_heading_format = workbook.add_format(
    #         {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
    #     date_format = workbook.add_format(
    #         {'align': 'left', 'num_format': 'd-m-yyyy'})
        
    #     # Additional formats for category hierarchy
    #     parent_header_format = workbook.add_format({
    #         'align': 'left', 'bold': True, 'size': 12, 
    #         'bg_color': '#f8f9fa', 'border': 1
    #     })
    #     child_header_format = workbook.add_format({
    #         'align': 'left', 'bold': True, 'size': 11, 
    #         'indent': 1
    #     })
    #     product_format = workbook.add_format({
    #         'align': 'left', 'size': 10, 
    #         'indent': 2
    #     })
    #     child_subtotal_format = workbook.add_format({
    #         'align': 'left', 'bold': True, 'italic': True, 'size': 11,
    #         'indent': 1
    #     })
    #     parent_subtotal_format = workbook.add_format({
    #         'align': 'left', 'bold': True, 'size': 12,
    #         'bg_color': '#e9ecef', 'border': 1
    #     })
    #     subtotal_number_format = workbook.add_format({
    #         'align': 'right', 'bold': True, 'size': 11
    #     })
    #     parent_subtotal_number_format = workbook.add_format({
    #         'align': 'right', 'bold': True, 'size': 12,
    #         'bg_color': '#e9ecef', 'border': 1
    #     })

    #     # Heading
    #     row = 1
    #     worksheet.merge_range(
    #         'A1:G1', self.company_id.name, sub_heading_format)
    #     row += 1
    #     worksheet.merge_range('A2:G3', 'Gross Profit Report', heading_format)

    #     # Search criteria
    #     row += 2
    #     column = -1
    #     if self.date_from:
    #         row += 1
    #         worksheet.write(row, column+1, 'From Date', cell_text_format)
    #         worksheet.write(row, column+2, self.date_from or '',
    #                         date_format)

    #     if self.date_to:
    #         row += 1
    #         column = -1
    #         worksheet.write(row, column+1, 'To Date', cell_text_format)
    #         worksheet.write(row, column+2, self.date_to or '',
    #                         date_format)

    #     if self.product_id:
    #         row += 1
    #         column = -1
    #         worksheet.write(row, column+1, 'Product', cell_text_format)
    #         worksheet.write(row, column+2, self.product_id.name or '')

    #     if self.report_by:
    #         row += 1
    #         column = -1
    #         worksheet.write(row, column+1, 'Report by', cell_text_format)
    #         worksheet.write(row, column+2, self.report_by or '')

    #     if self.target_moves:
    #         row += 1
    #         column = -1
    #         worksheet.write(row, column+1, 'Target Moves', cell_text_format)
    #         worksheet.write(row, column+2, self.target_moves or '')

    #     if self.product_type:
    #         row += 1
    #         column = -1
    #         worksheet.write(row, column+1, 'Product Type', cell_text_format)
    #         worksheet.write(row, column+2, self.product_type or '')

    #     if analytic_account_names:
    #         row += 1
    #         column = -1
    #         worksheet.write(row, column+1, 'Analytic Accounts', cell_text_format)
    #         worksheet.write(row, column+2, analytic_account_names)

    #     # Sub headers
    #     row += 2
    #     column = -1
    #     worksheet.write(row, column+1, 'No', cell_text_format)
        
    #     if self.report_by == 'Category':
    #         worksheet.write(row, column+2, 'Category', cell_text_format)
    #         worksheet.write(row, column+3, '', cell_text_format)  # Empty column for spacing
    #     else:
    #         worksheet.write(row, column+2, self.report_by, cell_text_format)
    #         worksheet.write(row, column+3, 'Product Code', cell_text_format)
        
    #     worksheet.write(row, column+4, 'Actual Revenue', cell_number_format)
    #     worksheet.write(row, column+5, 'Actual Cost', cell_number_format)
    #     worksheet.write(row, column+6, 'Gross Profit', cell_number_format)
    #     worksheet.write(row, column+7, 'Gross Profit %', cell_number_format)

    #     no = 0
    #     total_act_cost = 0
    #     total_act_revenue = 0

    #     if self.report_by == 'Category':
    #         # Handle category hierarchy
    #         for line in lines_data:
    #             row += 1
    #             column = -1
    #             line_type = line.get('type', 'product')

    #             if line_type == 'parent_header':
    #                 # Parent category header
    #                 worksheet.write(row, column+1, '', parent_header_format)
    #                 worksheet.write(row, column+2, line['group'], parent_header_format)
    #                 worksheet.write(row, column+3, '', parent_header_format)
    #                 worksheet.write(row, column+4, '', parent_header_format)
    #                 worksheet.write(row, column+5, '', parent_header_format)
    #                 worksheet.write(row, column+6, '', parent_header_format)
    #                 worksheet.write(row, column+7, '', parent_header_format)

    #             elif line_type == 'child_header':
    #                 # Child category header
    #                 worksheet.write(row, column+1, '', child_header_format)
    #                 worksheet.write(row, column+2, line['group'], child_header_format)
    #                 worksheet.write(row, column+3, '', child_header_format)
    #                 worksheet.write(row, column+4, '', child_header_format)
    #                 worksheet.write(row, column+5, '', child_header_format)
    #                 worksheet.write(row, column+6, '', child_header_format)
    #                 worksheet.write(row, column+7, '', child_header_format)

    #             elif line_type == 'product':
    #                 # Product line
    #                 no += 1
    #                 worksheet.write(row, column+1, no)
    #                 worksheet.write(row, column+2, line['group'], product_format)
    #                 worksheet.write(row, column+3, '', product_format)
    #                 worksheet.write(
    #                     row, column+4, '{:,.2f}'.format(line['act_revenue']), align_right)
    #                 worksheet.write(
    #                     row, column+5, '{:,.2f}'.format(line['act_cost']), align_right)

    #                 balance = line['act_revenue']-line['act_cost']
    #                 balance_percentage = (
    #                     balance/line['act_revenue']) * 100 if line['act_revenue'] else 0
    #                 worksheet.write(
    #                     row, column+6, '{:,.2f}'.format(balance), align_right)
    #                 worksheet.write(
    #                     row, column+7, '{:,.2f}'.format(balance_percentage), align_right)

    #                 total_act_cost += line['act_cost']
    #                 total_act_revenue += line['act_revenue']

    #             elif line_type == 'child_subtotal':
    #                 # Child category subtotal
    #                 worksheet.write(row, column+1, '', child_subtotal_format)
    #                 worksheet.write(row, column+2, line['group'], child_subtotal_format)
    #                 worksheet.write(row, column+3, '', child_subtotal_format)
    #                 worksheet.write(
    #                     row, column+4, '{:,.2f}'.format(line['act_revenue']), subtotal_number_format)
    #                 worksheet.write(
    #                     row, column+5, '{:,.2f}'.format(line['act_cost']), subtotal_number_format)

    #                 balance = line['act_revenue']-line['act_cost']
    #                 balance_percentage = (
    #                     balance/line['act_revenue']) * 100 if line['act_revenue'] else 0
    #                 worksheet.write(
    #                     row, column+6, '{:,.2f}'.format(balance), subtotal_number_format)
    #                 worksheet.write(
    #                     row, column+7, '{:,.2f}'.format(balance_percentage), subtotal_number_format)

    #             elif line_type == 'parent_subtotal':
    #                 # Parent category subtotal
    #                 worksheet.write(row, column+1, '', parent_subtotal_format)
    #                 worksheet.write(row, column+2, line['group'], parent_subtotal_format)
    #                 worksheet.write(row, column+3, '', parent_subtotal_format)
    #                 worksheet.write(
    #                     row, column+4, '{:,.2f}'.format(line['act_revenue']), parent_subtotal_number_format)
    #                 worksheet.write(
    #                     row, column+5, '{:,.2f}'.format(line['act_cost']), parent_subtotal_number_format)

    #                 balance = line['act_revenue']-line['act_cost']
    #                 balance_percentage = (
    #                     balance/line['act_revenue']) * 100 if line['act_revenue'] else 0
    #                 worksheet.write(
    #                     row, column+6, '{:,.2f}'.format(balance), parent_subtotal_number_format)
    #                 worksheet.write(
    #                     row, column+7, '{:,.2f}'.format(balance_percentage), parent_subtotal_number_format)

    #         # Grand Total for Category Report
    #         row += 2
    #         column = -1
    #         grand_total_format = workbook.add_format({
    #             'align': 'left', 'bold': True, 'size': 12,
    #             'bg_color': '#f8f9fa', 'border': 2
    #         })
    #         grand_total_number_format = workbook.add_format({
    #             'align': 'right', 'bold': True, 'size': 12,
    #             'bg_color': '#f8f9fa', 'border': 2
    #         })
            
    #         worksheet.write(row, column+1, '', grand_total_format)
    #         worksheet.write(row, column+2, 'GRAND TOTAL', grand_total_format)
    #         worksheet.write(row, column+3, '', grand_total_format)
    #         worksheet.write(
    #             row, column+4, '{:,.2f}'.format(total_act_revenue), grand_total_number_format)
    #         worksheet.write(
    #             row, column+5, '{:,.2f}'.format(total_act_cost), grand_total_number_format)
    #         worksheet.write(
    #             row, column+6, '{:,.2f}'.format(total_act_revenue-total_act_cost), grand_total_number_format)
    #         worksheet.write(row, column+7, '', grand_total_format)

    #     else:
    #         # Handle standard Product/Partner reports
    #         for line in lines_data:
    #             row += 1
    #             column = -1
    #             no += 1

    #             worksheet.write(row, column+1, no)
    #             group = line['group']
    #             worksheet.write(row, column+2, group)
    #             worksheet.write(row, column+3, line.get('default_code', ''))
    #             worksheet.write(
    #                 row, column+4, '{:,.2f}'.format(line['act_revenue']), align_right)
    #             worksheet.write(
    #                 row, column+5, '{:,.2f}'.format(line['act_cost']), align_right)

    #             balance = line['act_revenue']-line['act_cost']
    #             balance_percentage = (
    #                 balance/line['act_revenue']) * 100 if line['act_revenue'] else 0
    #             worksheet.write(
    #                 row, column+6, '{:,.2f}'.format(balance), align_right)
    #             worksheet.write(
    #                 row, column+7, '{:,.2f}'.format(balance_percentage), align_right)

    #             total_act_cost += line['act_cost']
    #             total_act_revenue += line['act_revenue']

    #         # Total for standard reports
    #         row += 2
    #         column = -1
    #         worksheet.write(
    #             row, column+4, '{:,.2f}'.format(total_act_revenue), cell_number_format)
    #         worksheet.write(
    #             row, column+5, '{:,.2f}'.format(total_act_cost), cell_number_format)
    #         worksheet.write(
    #             row, column+6, '{:,.2f}'.format(total_act_revenue-total_act_cost), cell_number_format)

    #     workbook.close()
    #     out = base64.encodebytes(fp.getvalue())
    #     self.write({'datas': out, 'datas_fname': filename})
    #     fp.close()
    #     filename += '%2Exlsx'

    #     return {
    #         'type': 'ir.actions.act_url',
    #         'target': 'new',
    #         'url': 'web/content/?model='+self._name+'&id='+str(self.id)+'&field=datas&download=true&filename='+filename,
    #     }

    def export_to_excel(self):
        gross_profit_report_obj = self.env['report.mgs_account.gross_profit_report']
        analytic_account_names = ', '.join([a.name for a in self.analytic_account_ids])
        analytic_ids = [a.id for a in self.analytic_account_ids]

        lines_data = gross_profit_report_obj._lines(
            self.company_id.id,
            self.date_from,
            self.date_to,
            self.partner_id.id,
            self.product_id.ids,
            self.target_moves,
            self.product_type,
            self.report_by,
            analytic_ids,
            self.product_categ_id.ids,
            self.journal_ids.ids
        )

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'GrossProfitReports'
        worksheet = workbook.add_worksheet(filename)

        # Format definitions
        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12, 'num_format': '0.000'})
        align_right = workbook.add_format({'align': 'right', 'num_format': '0.000'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True, 'num_format': '0.000'})
        date_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format(
            {'align': 'left', 'num_format': 'd-m-yyyy'})
        
        # Category hierarchy formats
        parent_header_format = workbook.add_format({
            'align': 'left', 'bold': True, 'size': 12, 
            'bg_color': '#f0f8ff', 'border': 1
        })
        child_header_format = workbook.add_format({
            'align': 'left', 'bold': True, 'size': 11, 
            'bg_color': '#ffffff'
        })
        product_format = workbook.add_format({
            'align': 'left', 'size': 10
        })
        child_subtotal_format = workbook.add_format({
            'align': 'left', 'bold': True, 'italic': True, 'size': 11,
            'bg_color': '#f8f8f8', 'top': 1
        })
        parent_subtotal_format = workbook.add_format({
            'align': 'left', 'bold': True, 'size': 12,
            'bg_color': '#e6f2ff', 'top': 2
        })
        subtotal_number_format = workbook.add_format({
            'align': 'right', 'bold': True, 'size': 11,
            'bg_color': '#f8f8f8', 'top': 1, 'num_format': '0.000'
        })
        parent_subtotal_number_format = workbook.add_format({
            'align': 'right', 'bold': True, 'size': 12,
            'bg_color': '#e6f2ff', 'top': 2, 'num_format': '0.000'
        })
        grand_total_format = workbook.add_format({
            'align': 'left', 'bold': True, 'size': 12,
            'bg_color': '#d9e6ff', 'top': 2, 'bottom': 2
        })
        grand_total_number_format = workbook.add_format({
            'align': 'right', 'bold': True, 'size': 12,
            'bg_color': '#d9e6ff', 'top': 2, 'bottom': 2, 'num_format': '0.000'
        })

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:H1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:H3', 'Gross Profit Report', heading_format)

        # Search criteria
        row += 2
        if self.date_from:
            row += 1
            worksheet.write(row, 0, 'From Date', cell_text_format)
            worksheet.write(row, 1, self.date_from or '', date_format)

        if self.date_to:
            row += 1
            worksheet.write(row, 0, 'To Date', cell_text_format)
            worksheet.write(row, 1, self.date_to or '', date_format)

        if self.product_id:
            row += 1
            worksheet.write(row, 0, 'Product', cell_text_format)
            worksheet.write(row, 1, self.product_id.name or '')

        if self.report_by:
            row += 1
            worksheet.write(row, 0, 'Report by', cell_text_format)
            worksheet.write(row, 1, self.report_by or '')

        if analytic_account_names:
            row += 1
            worksheet.write(row, 0, 'Analytic Accounts', cell_text_format)
            worksheet.write(row, 1, analytic_account_names)

        # Table headers
        row += 2
        headers = ['No', 'Parent Category', 'Child Category', 'Product']
        if self.report_by != 'Category':
            headers = ['No', self.report_by, 'Product Code', '']
        
        headers += ['Actual Revenue', 'Actual Cost', 'Gross Profit', 'Gross Profit %']
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, cell_text_format)

        no = 0
        total_act_cost = 0
        total_act_revenue = 0

        if self.report_by == 'Category':
            # Handle category hierarchy with 3 columns
            for line in lines_data:
                row += 1
                line_type = line.get('type', 'product')

                if line_type == 'parent_header':
                    # Parent category header
                    worksheet.write(row, 0, '', parent_header_format)
                    worksheet.write(row, 1, line['group'], parent_header_format)
                    worksheet.write(row, 2, '', parent_header_format)
                    worksheet.write(row, 3, '', parent_header_format)
                    worksheet.write(row, 4, '', parent_header_format)
                    worksheet.write(row, 5, '', parent_header_format)
                    worksheet.write(row, 6, '', parent_header_format)
                    worksheet.write(row, 7, '', parent_header_format)

                elif line_type == 'child_header':
                    # Child category header
                    worksheet.write(row, 0, '', child_header_format)
                    worksheet.write(row, 1, '', child_header_format)
                    worksheet.write(row, 2, line['group'], child_header_format)
                    worksheet.write(row, 3, '', child_header_format)
                    worksheet.write(row, 4, '', child_header_format)
                    worksheet.write(row, 5, '', child_header_format)
                    worksheet.write(row, 6, '', child_header_format)
                    worksheet.write(row, 7, '', child_header_format)

                elif line_type == 'product':
                    # Product line
                    no += 1
                    worksheet.write(row, 0, no)
                    worksheet.write(row, 1, '')
                    worksheet.write(row, 2, '')
                    worksheet.write(row, 3, line['group'], product_format)
                    worksheet.write(row, 4, line['act_revenue'], align_right)
                    worksheet.write(row, 5, line['act_cost'], align_right)

                    balance = line['act_revenue'] - line['act_cost']
                    balance_percentage = (balance/line['act_revenue'] * 100) if line['act_revenue'] else 0
                    worksheet.write(row, 6, balance, align_right)
                    worksheet.write(row, 7, balance_percentage, align_right)

                    total_act_cost += line['act_cost']
                    total_act_revenue += line['act_revenue']

                elif line_type == 'child_subtotal':
                    # Child category subtotal
                    worksheet.write(row, 0, '', child_subtotal_format)
                    worksheet.write(row, 1, '', child_subtotal_format)
                    worksheet.write(row, 2, line['group'], child_subtotal_format)
                    worksheet.write(row, 3, '', child_subtotal_format)
                    worksheet.write(row, 4, line['act_revenue'], subtotal_number_format)
                    worksheet.write(row, 5, line['act_cost'], subtotal_number_format)

                    balance = line['act_revenue'] - line['act_cost']
                    balance_percentage = (balance/line['act_revenue'] * 100) if line['act_revenue'] else 0
                    worksheet.write(row, 6, balance, subtotal_number_format)
                    worksheet.write(row, 7, balance_percentage, subtotal_number_format)

                elif line_type == 'parent_subtotal':
                    # Parent category subtotal
                    worksheet.write(row, 0, '', parent_subtotal_format)
                    worksheet.write(row, 1, line['group'], parent_subtotal_format)
                    worksheet.write(row, 2, '', parent_subtotal_format)
                    worksheet.write(row, 3, '', parent_subtotal_format)
                    worksheet.write(row, 4, line['act_revenue'], parent_subtotal_number_format)
                    worksheet.write(row, 5, line['act_cost'], parent_subtotal_number_format)

                    balance = line['act_revenue'] - line['act_cost']
                    balance_percentage = (balance/line['act_revenue'] * 100) if line['act_revenue'] else 0
                    worksheet.write(row, 6, balance, parent_subtotal_number_format)
                    worksheet.write(row, 7, balance_percentage, parent_subtotal_number_format)

            # Grand Total
            row += 1
            worksheet.write(row, 0, '', grand_total_format)
            worksheet.write(row, 1, 'GRAND TOTAL', grand_total_format)
            worksheet.write(row, 2, '', grand_total_format)
            worksheet.write(row, 3, '', grand_total_format)
            worksheet.write(row, 4, total_act_revenue, grand_total_number_format)
            worksheet.write(row, 5, total_act_cost, grand_total_number_format)
            
            balance = total_act_revenue - total_act_cost
            balance_percentage = (balance/total_act_revenue * 100) if total_act_revenue else 0
            worksheet.write(row, 6, balance, grand_total_number_format)
            worksheet.write(row, 7, balance_percentage, grand_total_number_format)

        else:
            # Handle standard Product/Partner reports
            for line in lines_data:
                row += 1
                no += 1

                worksheet.write(row, 0, no)
                worksheet.write(row, 1, line['group'])
                worksheet.write(row, 2, line.get('default_code', ''))
                worksheet.write(row, 3, '')
                worksheet.write(row, 4, line['act_revenue'], align_right)
                worksheet.write(row, 5, line['act_cost'], align_right)

                balance = line['act_revenue'] - line['act_cost']
                balance_percentage = (balance/line['act_revenue'] * 100) if line['act_revenue'] else 0
                worksheet.write(row, 6, balance, align_right)
                worksheet.write(row, 7, balance_percentage, align_right)

                total_act_cost += line['act_cost']
                total_act_revenue += line['act_revenue']

            # Total for standard reports
            row += 1
            worksheet.write(row, 3, 'TOTAL', cell_text_format)
            worksheet.write(row, 4, total_act_revenue, cell_number_format)
            worksheet.write(row, 5, total_act_cost, cell_number_format)
            
            balance = total_act_revenue - total_act_cost
            balance_percentage = (balance/total_act_revenue * 100) if total_act_revenue else 0
            worksheet.write(row, 6, balance, cell_number_format)
            worksheet.write(row, 7, balance_percentage, cell_number_format)

        # Set column widths
        worksheet.set_column('A:A', 5)   # No
        worksheet.set_column('B:B', 25)  # Parent Category/Report By
        worksheet.set_column('C:C', 25)  # Child Category/Product Code
        worksheet.set_column('D:D', 30)  # Product
        worksheet.set_column('E:H', 15)  # Numerical columns

        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out, 'datas_fname': filename})
        fp.close()
        filename += '%2Exlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model='+self._name+'&id='+str(self.id)+'&field=datas&download=true&filename='+filename,
        }
        
        
        
class GrossProfitReport(models.AbstractModel):
    _name = 'report.mgs_account.gross_profit_report'
    _description = 'Gross Profit Report'

   
    def _lines(self, company_id, date_from, date_to, partner_id, product_id, target_moves, product_type, report_by, analytic_account_ids=[], product_categ_ids=None, journal_ids=None):
        params = []
        states = "('posted','draft')"
        if target_moves == 'posted':
            states = "('posted')"

        if product_type == "all":
            product_type = ['consu', 'service']
        else:
            product_type = [product_type]

        select_query = """select pt.name['en_US'] as group, pt.default_code as default_code, pp.id as product_id,
        --COALESCE(sum(aml.balance), 0) as act_cost,
        --COALESCE(sum(aml.balance), 0) as act_revenue
        COALESCE(sum(CASE WHEN aa.account_type = 'expense_direct_cost' THEN aml.balance ELSE 0 END), 0) as act_cost,
        COALESCE(sum(CASE WHEN aa.account_type = 'income' THEN aml.balance * -1 ELSE 0 END), 0) as act_revenue        
        """
        

        order_query = "group by pt.name, pt.default_code, pp.id order by pt.name"

        if report_by == 'Partner':
            select_query = """select rp.name as group,
            --COALESCE(sum(aml.balance), 0) as act_cost,
            --COALESCE(sum(aml.balance), 0) as act_revenue
            COALESCE(sum(CASE WHEN aa.account_type = 'expense_direct_cost' THEN aml.balance ELSE 0 END), 0) as act_cost,
            COALESCE(sum(CASE WHEN aa.account_type = 'income' THEN aml.balance * -1 ELSE 0 END), 0) as act_revenue            
            """

            order_query = "group by rp.name order by rp.name"
        
        
        elif report_by == 'Category':
            # For category reporting, we need hierarchical data
            return self._get_category_lines(company_id, date_from, date_to, partner_id, product_id, target_moves, product_type, analytic_account_ids, product_categ_ids, params, states, journal_ids)

        from_where_query = """
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join res_partner as rp on aml.partner_id=rp.id
        left join product_product as pp on aml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        left join account_journal aj on aj.id = aml.journal_id
        where aa.account_type in ('expense_direct_cost', 'income') and aml.parent_state in """ + states 

        if analytic_account_ids:
            # Convert all to string, wrap in single quotes
            ids_str_list = [f"'{str(aid)}'" for aid in analytic_account_ids]
            array_str = ", ".join(ids_str_list)
            from_where_query += f"and aml.analytic_distribution ?| array[{array_str}] "

        if date_from:
            params.append(date_from)
            from_where_query += " and aml.date >= %s"

        if date_to:
            params.append(date_to)
            from_where_query += " and aml.date <= %s"
        
        if product_categ_ids:
            from_where_query += " and pt.categ_id IN %s"
            params.append(tuple(product_categ_ids))
            
        if journal_ids:
            from_where_query += " and aml.journal_id IN %s"
            params.append(tuple(journal_ids))
        
        if product_type:
            from_where_query += " and pt.type IN %s"
            params.append(tuple(product_type))
        
        if report_by == 'Product' and product_id:
            from_where_query += " and aml.product_id IN %s"
            params.append(tuple(product_id))

        if report_by == 'Partner' and partner_id:
            from_where_query += " and aml.partner_id = " + str(partner_id) + " "

        if company_id:
            from_where_query += " and aml.company_id = " + str(company_id) + " "

        query = select_query + from_where_query + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    
    def _get_category_lines(self, company_id, date_from, date_to, partner_id, product_id, target_moves, product_type, analytic_account_ids, product_categ_ids, params, states, journal_ids):
        """Get hierarchical category data with parent-child structure"""
        
        # Base query for getting data grouped by category and product
        base_query = """
        select 
            pc.id as category_id,
            pc.name as category_name,
            pc.parent_id as parent_category_id,
            parent_pc.name as parent_category_name,
            pt.name['en_US'] as product_name,
            pt.default_code as product_code,
            pp.id as product_id,
            --COALESCE(sum(aml.debit), 0) as act_cost,
            --COALESCE(sum(aml.credit), 0) as act_revenue
            COALESCE(sum(CASE WHEN aa.account_type = 'expense_direct_cost' THEN aml.balance ELSE 0 END), 0) as act_cost,
            COALESCE(sum(CASE WHEN aa.account_type = 'income' THEN aml.balance * -1 ELSE 0 END), 0) as act_revenue
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join product_product as pp on aml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        left join product_category as pc on pt.categ_id=pc.id
        left join product_category as parent_pc on pc.parent_id=parent_pc.id
        left join account_journal aj on aj.id = aml.journal_id
        where aa.account_type in ('expense_direct_cost', 'income')
        and aml.parent_state in """ + states

        # Add filters
        if analytic_account_ids:
            ids_str_list = [f"'{str(aid)}'" for aid in analytic_account_ids]
            array_str = ", ".join(ids_str_list)
            base_query += f" and aml.analytic_distribution ?| array[{array_str}]"

        if date_from:
            params.append(date_from)
            base_query += " and aml.date >= %s"

        if date_to:
            params.append(date_to)
            base_query += " and aml.date <= %s"
        
        if product_categ_ids:
            base_query += " and pt.categ_id IN %s"
            params.append(tuple(product_categ_ids))
            
        if journal_ids:
            base_query += " and aml.journal_id IN %s"
            params.append(tuple(journal_ids))
        
        if product_type:
            base_query += " and pt.type IN %s"
            params.append(tuple(product_type))
        
        if product_id:
            base_query += " and aml.product_id IN %s"
            params.append(tuple(product_id))

        if company_id:
            base_query += " and aml.company_id = " + str(company_id)

        base_query += """
        group by pc.id, pc.name, pc.parent_id, parent_pc.name, pt.name, pt.default_code, pp.id
        order by parent_pc.name NULLS FIRST, pc.name, pt.name
        """

        self.env.cr.execute(base_query, tuple(params))
        raw_data = self.env.cr.dictfetchall()
        
        # Structure the data hierarchically
        result = []
        current_parent = None
        current_child = None
        child_subtotal = {'act_cost': 0, 'act_revenue': 0}
        parent_subtotal = {'act_cost': 0, 'act_revenue': 0}
        
        for row in raw_data:
            parent_name = row['parent_category_name'] or row['category_name']
            child_name = row['category_name'] if row['parent_category_name'] else None

            # New parent category
            if current_parent != parent_name:
                # Append previous child subtotal if applicable
                if current_child and (child_subtotal['act_cost'] > 0 or child_subtotal['act_revenue'] > 0):
                    result.append({
                        'type': 'child_subtotal',
                        'group': f"{current_child} subtotal",
                        'act_cost': child_subtotal['act_cost'],
                        'act_revenue': child_subtotal['act_revenue']
                    })

                # Append previous parent subtotal if applicable
                if current_parent:
                    result.append({
                        'type': 'parent_subtotal',
                        'group': f"{current_parent} Subtotal",
                        'act_cost': parent_subtotal['act_cost'],
                        'act_revenue': parent_subtotal['act_revenue']
                    })

                # Start new parent
                current_parent = parent_name
                result.append({
                    'type': 'parent_header',
                    'group': parent_name,
                    'act_cost': 0,
                    'act_revenue': 0
                })
                parent_subtotal = {'act_cost': 0, 'act_revenue': 0}
                current_child = None
                child_subtotal = {'act_cost': 0, 'act_revenue': 0}

            # New child category
            if current_child != child_name:
                if current_child and (child_subtotal['act_cost'] > 0 or child_subtotal['act_revenue'] > 0):
                    result.append({
                        'type': 'child_subtotal',
                        'group': f"{current_child} subtotal",
                        'act_cost': child_subtotal['act_cost'],
                        'act_revenue': child_subtotal['act_revenue']
                    })

                current_child = child_name
                result.append({
                    'type': 'child_header',
                    'group': f"{child_name}",
                    'act_cost': 0,
                    'act_revenue': 0
                })
                child_subtotal = {'act_cost': 0, 'act_revenue': 0}

            # Add product line if product exists
            if row['product_name']:
                result.append({
                    'type': 'product',
                    'group': row['product_name'],
                    'default_code': row['product_code'],
                    'product_id': row['product_id'],
                    'act_cost': row['act_cost'],
                    'act_revenue': row['act_revenue']
                })

                # Update subtotals
                child_subtotal['act_cost'] += row['act_cost']
                child_subtotal['act_revenue'] += row['act_revenue']
                parent_subtotal['act_cost'] += row['act_cost']
                parent_subtotal['act_revenue'] += row['act_revenue']

        # Add final child subtotal if any
        if current_child and (child_subtotal['act_cost'] > 0 or child_subtotal['act_revenue'] > 0):
            result.append({
                'type': 'child_subtotal',
                'group': f"{current_child} subtotal",
                'act_cost': child_subtotal['act_cost'],
                'act_revenue': child_subtotal['act_revenue']
            })

        # Add final parent subtotal
        if current_parent:
            result.append({
                'type': 'parent_subtotal',
                'group': f"{current_parent} Subtotal",
                'act_cost': parent_subtotal['act_cost'],
                'act_revenue': parent_subtotal['act_revenue']
            })

        return result


   

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
            'product_id': data['form']['product_id'],
            'product_categ_ids': data['form']['product_categ_ids'],
            'journal_ids': data['form']['journal_ids'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'target_moves': data['form']['target_moves'],
            'product_type': data['form']['product_type'],
            'partner_id': data['form']['partner_id'],
            'lines': self._lines,
            'analytic_account_ids': [a[0] for a in data['form'].get('analytic_account_ids', [])],
            'analytic_account_names': [a[1] for a in data['form'].get('analytic_account_ids', [])],

        }
