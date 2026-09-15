from odoo import models, fields, api
from odoo.exceptions import ValidationError
from itertools import groupby
from operator import itemgetter
import xlsxwriter
import base64
from io import BytesIO


class SalesByCustomerDetail(models.TransientModel):
    _name = 'mgs_sale.sales_by_customer'
    _description = 'Sales by Customer Detail'

    partner_id = fields.Many2one('res.partner', string="Partner")
    product_tag_id = fields.Many2one('product.tag', string="Tag")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id)
    report_by = fields.Selection(
        [('Summary', 'Summary'), ('Detail', 'Detail')], string='Report Type', default='Detail')
    # filter_sales = fields.Selection(
    #     [('all', 'All'), ('sale_orders', 'Sale Orders'), ('quotations', 'Quotations')], string='Filter', default='sale_orders')
    team_id = fields.Many2one('crm.team', string='Salesteam')
    user_id = fields.Many2one('res.users', string='Salesperson')
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError('''From Date should be less than To Date.''')

    def confirm(self):
        product_ids = []
        if self.product_tag_id:
            product_ids = self.env['product.product'].search(
                [('product_tag_ids', 'in', [self.product_tag_id.id])]
            ).ids

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'product_tag_id': [self.product_tag_id.id, self.product_tag_id.name],
                'product_ids': product_ids,
                'user_id': [self.user_id.id, self.user_id.name],
                'team_id': [self.team_id.id, self.team_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
                # 'filter': self.filter_sales
            },
        }

        return self.env.ref('mgs_sale.action_sales_by_customer').report_action(self, data=data)

    def export_to_excel(self):
        sales_by_customer_report_obj = self.env['report.mgs_sale.sales_by_customer_report']
        lines = sales_by_customer_report_obj._lines
        # self, self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, is_group

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'SalesByCustomer'
        worksheet = workbook.add_worksheet(filename)

        product_obj = self.env['product.product']
        domain = []
        if self.product_tag_id:
            domain.append(('product_tag_ids', 'in', [self.product_tag_id.id]))
        product_ids = product_obj.search(domain).ids

        # Totals
        total_qty_ordered = 0
        total_qty_delivered = 0
        total_qty_invoiced = 0
        total_amount = 0
        total_cost = 0
        total_margin = 0

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
            'A1:K1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:K3', 'Sales by Customer', heading_format)

        # Search criteria
        row += 2
        column = -1
        if self.date_from:
            row += 1
            worksheet.write(row, column+1, 'From Date', cell_text_format)
            worksheet.write(row, column+2, self.date_from or '',
                            date_heading_format)
        column+2

        if self.date_to:
            row += 1
            worksheet.write(row, column+1, 'To Date', cell_text_format)
            worksheet.write(row, column+2, self.date_to or '',
                            date_heading_format)
        column+2

        if self.partner_id:
            row += 1
            worksheet.write(row, column+1, 'Partner', cell_text_format)
            worksheet.write(row, column+2, self.partner_id.name or '')
        column+2

        if self.user_id:
            row += 1
            worksheet.write(row, column+1, 'Salesperson', cell_text_format)
            worksheet.write(row, column+2, self.user_id.name or '')
        column+2

        if self.team_id:
            row += 1
            worksheet.write(row, column+1, 'Salesteam', cell_text_format)
            worksheet.write(row, column+2, self.team_id.name or '')
        column+2

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Customer', cell_text_format)

        worksheet.write(row, column+2, 'Ordered Qty', cell_number_format)
        worksheet.write(row, column+3, 'Delivered Qty', cell_number_format)
        worksheet.write(row, column+4, 'Invoiced Qty', cell_number_format)
        worksheet.write(row, column+5, 'Amount', cell_number_format)

        if self.env.user.has_group('account.group_account_manager'):
            worksheet.write(row, column+6, 'T.Cost', cell_number_format)
            worksheet.write(row, column+7, 'Gross Profit', cell_number_format)

        if self.report_by == 'Detail':
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'Order', cell_text_format)
            worksheet.write(row, column+4, 'Item', cell_text_format)

            worksheet.write(row, column+5, 'Ordered Qty', cell_number_format)
            worksheet.write(row, column+6, 'Delivered Qty', cell_number_format)
            worksheet.write(row, column+7, 'Invoiced Qty', cell_number_format)

            worksheet.write(row, column+8, 'Rate', cell_number_format)
            worksheet.write(row, column+9, 'Amount', cell_number_format)

            if self.env.user.has_group('account.group_account_manager'):
                worksheet.write(row, column+10, 'T.Cost', cell_number_format)
                worksheet.write(row, column+11, 'Gross Profit',
                                cell_number_format)

        # ------------------------------ Customer ------------------------------
        for group in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, product_ids, self.team_id.id):

            # Totals
            total_qty_ordered += group['total_qty_ordered']
            total_qty_delivered += group['total_qty_delivered']
            total_qty_invoiced += group['total_qty_invoiced']
            total_amount += group['total_amount']
            total_cost += group['total_cost']
            total_margin += group['total_margin']

            if self.report_by == 'Summary':
                row += 1
                column = -1
                worksheet.write(row, column+1, group['name'])
                worksheet.write(
                    row, column+2, int(group['total_qty_ordered']), align_right)
                worksheet.write(
                    row, column+3, int(group['total_qty_delivered']), align_right)
                worksheet.write(
                    row, column+4, int(group['total_qty_invoiced']), align_right)
                worksheet.write(
                    row, column+5, int(group['total_amount']), align_right_money)
                if self.env.user.has_group('account.group_account_manager'):
                    worksheet.write(
                        row, column+6, int(group['total_cost']), align_right_money)
                    worksheet.write(
                        row, column+7, int(group['total_margin']), align_right_money)

            if self.report_by == 'Detail':
                row += 2
                column = -1
                row_number = 'A%s:K%s' % (row, row)
                worksheet.merge_range(
                    row_number, group['name'], cell_text_format)

                # ------------------------------ Lines ------------------------------
                for line in group['lines']:
                    row += 1
                    column = -1

                    worksheet.write(row, column+1, '')
                    worksheet.write(
                        row, column+2, line['date'], date_format)
                    name = line['name']
                    if line['client_order_ref']:
                        name += '(%s)' % line['client_order_ref']
                    worksheet.write(row, column+3, name)
                    worksheet.write(
                        row, column+4, line['product']['en_US'])
                    worksheet.write(
                        row, column+5, int(line['product_uom_qty']), align_right)
                    worksheet.write(
                        row, column+6, int(line['qty_delivered']), align_right)
                    worksheet.write(
                        row, column+7, int(line['qty_invoiced']), align_right)

                    rate = 0
                    if line['product_uom_qty'] > 0:
                        rate = line['price_total']/line['product_uom_qty']

                    worksheet.write(
                        row, column+8, rate, align_right)
                    worksheet.write(
                        row, column+9, int(line['price_total']), align_right_money)

                    if self.env.user.has_group('account.group_account_manager'):
                        worksheet.write(
                            row, column+10, int(line['cost']), align_right_money)
                        worksheet.write(
                            row, column+11, int(line['margin']), align_right_money)

                    # ---------------------------------------- END LINES ----------------------------------------

                row += 2
                column = -1
                worksheet.write(row, column+1, 'TOTAL ' +
                                group['name'], cell_text_format)
                worksheet.write(row, column+2, '', cell_text_format)
                worksheet.write(row, column+3, '', cell_text_format)
                worksheet.write(row, column+4, '', cell_text_format)
                worksheet.write(
                    row, column+5, int(group['total_qty_ordered']), align_right_total)
                worksheet.write(
                    row, column+6, int(group['total_qty_delivered']), align_right_total)
                worksheet.write(
                    row, column+7, int(group['total_qty_invoiced']), align_right_total)
                worksheet.write(row, column+8, '')
                worksheet.write(
                    row, column+9, int(group['total_amount']), align_right_money_total)

                if self.env.user.has_group('account.group_account_manager'):
                    worksheet.write(
                        row, column+10, int(group['total_cost']), align_right_money_total)
                    worksheet.write(
                        row, column+11, int(group['total_margin']), align_right_money_total)

        # Main Totals
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Total', cell_text_format)

        worksheet.write(
            row, column+2, int(total_qty_ordered), align_right_total)
        worksheet.write(
            row, column+3, int(total_qty_delivered), align_right_total)
        worksheet.write(
            row, column+4, int(total_qty_invoiced), align_right_total)
        worksheet.write(
            row, column+5, int(total_amount), align_right_money_total)

        if self.env.user.has_group('account.group_account_manager'):
            worksheet.write(
                row, column+6, int(total_cost), align_right_money_total)
            worksheet.write(
                row, column+7, int(total_margin), align_right_money_total)

        if self.report_by == 'Detail':
            worksheet.write(row, column+2, '', cell_text_format)
            worksheet.write(row, column+3, '', cell_text_format)
            worksheet.write(row, column+4, '', cell_text_format)

            worksheet.write(
                row, column+5, int(total_qty_ordered), align_right_total)
            worksheet.write(
                row, column+6, int(total_qty_delivered), align_right_total)
            worksheet.write(
                row, column+7, int(total_qty_invoiced), align_right_total)
            worksheet.write(row, column+8, '', cell_number_format)
            worksheet.write(
                row, column+9, int(total_amount), align_right_money_total)

            if self.env.user.has_group('account.group_account_manager'):
                worksheet.write(
                    row, column+10, int(total_cost), align_right_money_total)
                worksheet.write(
                    row, column+11, int(total_margin), align_right_money_total)

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


class SalesByCustomerDetailReport(models.AbstractModel):
    _name = 'report.mgs_sale.sales_by_customer_report'
    _description = 'Sales by Customer Detail Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, user_id, product_ids, team_id):  # , company_branch_ids
        sale_report_obj = self.env['sale.report']
        lines = []
        _select_sale = sale_report_obj._select_sale()
        _from_sale = sale_report_obj._from_sale()
        _where_sale = sale_report_obj._where_sale()
        _group_by_sale = sale_report_obj._group_by_sale()

        with_ = sale_report_obj._with_sale()
        # sale.report shows amounts in company currency by default.
        # Added price_total and margin again from sale lines to access values tied to the order currency in a multicurrency context.

        _select_sale += ', partner.name AS partner_name, t.name AS product, COALESCE(l.price_total-l.margin, 0) as cost, COALESCE(l.margin, 0), s.client_order_ref, l.price_total as price_total, l.margin as margin'
        _group_by_sale += ', partner.name, t.name, l.price_total, l.margin'

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if date_from:
            _where_sale += " and s.date_order >= '%s'" % f_date

        if date_to:
            _where_sale += " and s.date_order <= '%s'" % t_date

        if partner_id:
            _where_sale += ' and s.partner_id = %s' % partner_id

        if user_id:
            _where_sale += ' and s.user_id = %s' % user_id

        if company_id:
            _where_sale += ' and s.company_id = %s' % company_id

        if product_ids:
            _where_sale += " and l.product_id in (" + \
                ','.join(map(str, product_ids)) + ")"

        if team_id:
            _where_sale += ' and s.team_id = %s' % team_id

        _where_sale += " and s.state not in ('draft', 'cancel', 'sent')"

        query = f"""
            {"WITH" + with_ + "(" if with_ else ""}
            SELECT {_select_sale}
            FROM {_from_sale}
            WHERE {_where_sale}
            GROUP BY {_group_by_sale}
            {")" if with_ else ""}
        """

        self.env.cr.execute(query)
        key = itemgetter('partner_id', 'partner_name')
        res = sorted(self.env.cr.dictfetchall(), key=key)

        for key, value in groupby(res, key):

            sub_lines = []
            total_qty_ordered = 0
            total_qty_delivered = 0
            total_qty_invoiced = 0
            total_qty_to_invoice = 0
            total_amount = 0
            total_margin = 0
            total_cost = 0
            total_amount = 0


            for k in value:
                sub_lines.append(k)
                total_qty_ordered += k['product_uom_qty']
                total_qty_delivered += k['qty_delivered']
                total_qty_invoiced += k['qty_invoiced']
                total_qty_to_invoice += k['qty_to_invoice']
                total_amount += k['price_total']
                total_margin += k['margin']
                total_cost += k['cost']

            lines.append({'name': key[1], 'lines': sub_lines, 'total_qty_ordered': total_qty_ordered,
                          'total_qty_delivered': total_qty_delivered, 'total_qty_invoiced': total_qty_invoiced,
                          'total_qty_to_invoice': total_qty_to_invoice, 'total_amount': total_amount,
                          'total_margin': total_margin, 'total_cost': total_cost})
        return lines

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
            'partner_id': data['form']['partner_id'],
            'user_id': data['form']['user_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'product_ids': data['form']['product_ids'],
            'team_id': data['form']['team_id'],
            'product_tag_id': data['form']['product_tag_id'],
            'lines': self._lines,
        }
