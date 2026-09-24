from odoo import models, fields, api
from odoo.exceptions import ValidationError
from itertools import groupby
from operator import itemgetter
import xlsxwriter
import base64
from io import BytesIO


class SalesbyRepDetail(models.TransientModel):
    _name = 'mgs_sale.sales_by_rep'
    _description = 'Sales by Rep'

    product_id = fields.Many2one('product.product', string="Product")
    product_tag_id = fields.Many2one('product.tag', string="Tag")
    partner_id = fields.Many2one('res.partner', string="Partner")
    team_id = fields.Many2one('crm.team', string="Salesteam")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id)
    user_id = fields.Many2one('res.users', string='Salesperson')
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError('''From Date should be less than To Date.''')

    def confirm(self):
        product_obj = self.env['product.product']
        domain = []
        if self.product_tag_id:
            domain.append(('product_tag_ids', 'in', [self.product_tag_id.id]))

        if self.product_id:
            domain.append(('id', '=', self.product_id.id))

        product_ids = product_obj.search(domain).ids

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'product_id': [self.product_id.id, self.product_id.name],
                'product_ids': product_ids,
                'product_tag_id': [self.product_tag_id.id, self.product_tag_id.name],
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'team_id': [self.team_id.id, self.team_id.name],
                'user_id': [self.user_id.id, self.user_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
            },
        }

        return self.env.ref('mgs_sale_fatah.action_sales_by_rep').report_action(self, data=data)

    def export_to_excel(self):
        sales_by_rep_report_obj = self.env['report.mgs_sale_fatah.sales_by_rep_report']
        lines = sales_by_rep_report_obj._lines

        product_obj = self.env['product.product']
        domain = []
        if self.product_tag_id:
            domain.append(('product_tag_ids', 'in', [self.product_tag_id.id]))

        if self.product_id:
            domain.append(('id', '=', self.product_id.id))

        product_ids = product_obj.search(domain).ids

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'MGSSalesReports'
        worksheet = workbook.add_worksheet(filename)

        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        align_right = workbook.add_format(
            {'align': 'right', 'num_format': '#,##0.00'})
        align_right_money = workbook.add_format(
            {'align': 'right', 'num_format': '$#,##0.00'})
        align_right_money_total = workbook.add_format(
            {'align': 'right', 'bold': True, 'num_format': '$#,##0.00'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True, 'num_format': '#,##0.00'})
        date_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format(
            {'align': 'left', 'num_format': 'd-m-yyyy'})

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:J1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:J3', 'MGS Sale Report', heading_format)

        # Search criteria
        row += 2
        column = -1
        if self.date_from:
            row += 1
            worksheet.write(row, column+1, 'From Date', cell_text_format)
            worksheet.write(row, column+2, self.date_from or '',
                            date_heading_format)

        if self.date_to:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'To Date', cell_text_format)
            worksheet.write(row, column+2, self.date_to or '',
                            date_heading_format)

        if self.partner_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Partner', cell_text_format)
            worksheet.write(row, column+2, self.partner_id.name or '')

        if self.product_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')

        if self.user_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Salesperson', cell_text_format)
            worksheet.write(row, column+2, self.user_id.name or '')

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Date', cell_text_format)
        worksheet.write(row, column+2, 'Order', cell_text_format)
        worksheet.write(row, column+3, 'Partner', cell_text_format)
        worksheet.write(row, column+4, 'Item', cell_text_format)
        worksheet.write(row, column+5, 'Ordered Qty', cell_number_format)
        worksheet.write(row, column+6, 'Delivered Qty', cell_number_format)
        worksheet.write(row, column+7, 'Invoiced Qty', cell_number_format)
        worksheet.write(row, column+8, 'To Invoice Qty', cell_number_format)
        worksheet.write(row, column+9, 'Rate', cell_number_format)
        worksheet.write(row, column+10, 'Amount', cell_number_format)

        total_product_uom_qty = 0
        total_qty_delivered = 0
        total_qty_invoiced = 0
        total_qty_to_invoice = 0
        total_amount = 0

        for line in lines(self.date_from, self.date_to, self.company_id.id, product_ids, self.partner_id.id, self.team_id.id, self.user_id.id):
            row += 2
            column = -1
            worksheet.write(row, column+1, line['date'], date_format)
            worksheet.write(row, column+2, line['name'])
            worksheet.write(row, column+3, line['partner_name'])
            worksheet.write(row, column+4, line['product']['en_US'])
            worksheet.write(
                row, column+5, '{:,.2f}'.format(line['product_uom_qty']), align_right)
            worksheet.write(
                row, column+6, '{:,.2f}'.format(line['qty_delivered']), align_right)
            worksheet.write(
                row, column+7, '{:,.2f}'.format(line['qty_invoiced']), align_right)
            worksheet.write(
                row, column+8, '{:,.2f}'.format(line['qty_to_invoice']), align_right)

            rate = line['price_total'] / \
                line['product_uom_qty'] if line['price_total'] and line['product_uom_qty'] else 0
            worksheet.write(row, column+9, '{:,.2f}'.format(rate), align_right)
            worksheet.write(
                row, column+10, '{:,.2f}'.format(line['price_total']), align_right_money)

            total_product_uom_qty += line['product_uom_qty']
            total_qty_delivered += line['qty_delivered']
            total_qty_invoiced += line['qty_invoiced']
            total_qty_to_invoice += line['qty_to_invoice']
            total_amount += line['price_total']

        row += 2
        column = -1
        worksheet.write(
            row, column+5, '{:,.2f}'.format(total_product_uom_qty), cell_number_format)
        worksheet.write(
            row, column+6, '{:,.2f}'.format(total_qty_delivered), cell_number_format)
        worksheet.write(
            row, column+7, '{:,.2f}'.format(total_qty_invoiced), cell_number_format)
        worksheet.write(
            row, column+8, '{:,.2f}'.format(total_qty_to_invoice), cell_number_format)
        worksheet.write(
            row, column+10, '{:,.2f}'.format(total_amount), align_right_money_total)

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


class SalesbyRepDetailReport(models.AbstractModel):
    _name = 'report.mgs_sale_fatah.sales_by_rep_report'
    _description = 'Sales by Rep Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_ids, partner_id, team_id, user_id):  # , company_branch_ids
        sale_report_obj = self.env['sale.report']
        lines = []
        # _select_sale = sale_report_obj._select_sale()
        _select_sale = f""" s.date_order AS date, s.name AS name,
        partner.name AS partner_name, t.name AS product, l.product_id,
        s.partner_id, s.state,
        
        CASE WHEN l.product_id IS NOT NULL THEN SUM(l.product_uom_qty * u.factor / u2.factor) ELSE 0 END AS product_uom_qty,
        CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_delivered * u.factor / u2.factor) ELSE 0 END AS qty_delivered,
        CASE WHEN l.product_id IS NOT NULL THEN SUM((l.product_uom_qty - l.qty_delivered) * u.factor / u2.factor) ELSE 0 END AS qty_to_deliver,
        CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_invoiced * u.factor / u2.factor) ELSE 0 END AS qty_invoiced,
        CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_to_invoice * u.factor / u2.factor) ELSE 0 END AS qty_to_invoice,
        CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total) ELSE 0
        END AS price_total,
        CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal
            / {sale_report_obj._case_value_or_one('s.currency_rate')}
            / {sale_report_obj._case_value_or_one('account_currency_table.rate')}
            ) ELSE 0
        END AS price_subtotal
        """
        
        _from_sale = sale_report_obj._from_sale()
        _where_sale = sale_report_obj._where_sale()
       
        _group_by_sale = """
        s.date_order, s.name, partner.name, t.name, l.product_id,
        s.partner_id, s.state, partner.name
        """

        with_ = sale_report_obj._with_sale()

        

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if date_from:
            _where_sale += " and s.date_order >= '%s'" % f_date

        if date_to:
            _where_sale += " and s.date_order <= '%s'" % t_date

        if user_id:
            _where_sale += ' and s.user_id = %s' % user_id

        if company_id:
            _where_sale += ' and s.company_id = %s' % company_id

        if product_ids:
            _where_sale += " and l.product_id in (" + \
                ','.join(map(str, product_ids)) + ")"

        if partner_id:
            _where_sale += ' and s.partner_id = %s' % partner_id

        if team_id:
            _where_sale += ' and s.team_id = %s' % team_id

        query = f"""
            {"WITH" + with_ + "(" if with_ else ""}
            SELECT {_select_sale}
            FROM {_from_sale}
            WHERE {_where_sale}
            GROUP BY {_group_by_sale}
            {")" if with_ else ""}
        """

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        return res

    @api.model
    # def _get_report_values(self, docids, data=None):
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
            'product_ids': data['form']['product_ids'],
            'partner_id': data['form']['partner_id'],
            'team_id': data['form']['team_id'],
            'user_id': data['form']['user_id'],
            'product_tag_id': data['form']['product_tag_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'lines': self._lines,
        }
