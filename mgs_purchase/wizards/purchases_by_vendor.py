from odoo import tools
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO
from itertools import groupby
from operator import itemgetter

import logging
_logger = logging.getLogger(__name__)




class PurchasesbyVendorDetail(models.TransientModel):
    _name = 'mgs_purchase.purchases_by_vendor'
    _description = 'Purchases by Vendor Detail'

    partner_id = fields.Many2one('res.partner', string="Partner")
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    report_by = fields.Selection(
        [('Summary', 'Summary'), ('Detail', 'Detail')], string='Report Type', default='Detail')
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError('''From Date should be less than To Date.''')

    def confirm(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'partner_id': [self.partner_id.id, self.partner_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
            },
        }

        return self.env.ref('mgs_purchase.action_purchases_by_vendor').report_action(self, data=data)

    def export_to_excel(self):
        purchases_by_vendor_report_obj = self.env['report.mgs_purchase.purchases_by_vendor_report']
        lines = purchases_by_vendor_report_obj._lines

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'PurchasesByVendor'
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
        worksheet.merge_range('A2:J3', 'Purchases by Vendor', heading_format)

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
            worksheet.write(row, column+1, 'Vendor', cell_text_format)
            worksheet.write(row, column+2, self.partner_id.name or '')
        column+2

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Vendor', cell_text_format)

        worksheet.write(row, column+2, 'Ordered Qty', cell_number_format)
        worksheet.write(row, column+3, 'Received Qty', cell_number_format)
        worksheet.write(row, column+4, 'Billed Qty', cell_number_format)
        worksheet.write(row, column+5, 'Amount', cell_number_format)

        if self.report_by == 'Detail':
            worksheet.write(row, column+2, 'Date', cell_text_format)
            worksheet.write(row, column+3, 'Order', cell_text_format)
            worksheet.write(row, column+4, 'Vendor', cell_text_format)

            worksheet.write(row, column+5, 'Ordered Qty', cell_number_format)
            worksheet.write(row, column+6, 'Received Qty', cell_number_format)
            worksheet.write(row, column+7, 'Billed Qty', cell_number_format)

            worksheet.write(row, column+8, 'Rate', cell_number_format)
            worksheet.write(row, column+9, 'Amount', cell_number_format)

        # Lines
        total_qty_ordered = 0
        total_qty_received = 0
        total_qty_billed = 0
        total_amount = 0

        for main in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, 'all'):
            # ------------------------------ Vendor ------------------------------

            for partner in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id.id, 'yes'):

                if self.report_by == 'Summary':
                    row += 1
                    column = -1
                    worksheet.write(row, column+1, partner['partner_name'])
                    worksheet.write(
                        row, column+2, int(partner['total_qty_ordered']), align_right)
                    worksheet.write(
                        row, column+3, int(partner['total_qty_received']), align_right)
                    worksheet.write(
                        row, column+4, int(partner['total_qty_billed']), align_right)
                    worksheet.write(
                        row, column+5, int(partner['total_amount']), align_right)

                if self.report_by == 'Detail':
                    row += 2
                    column = -1
                    row_number = 'A%s:K%s' % (row, row)
                    worksheet.merge_range(
                        row_number, partner['partner_name'], cell_text_format)

                    # ------------------------------ Lines ------------------------------
                    for line in lines(self.date_from, self.date_to, self.company_id.id, partner['partner_id'], 'no'):
                        row += 1
                        column = -1

                        worksheet.write(row, column+1, '')
                        worksheet.write(
                            row, column+2, line['date_order'], date_format)
                        worksheet.write(row, column+3, line['order_no'])
                        worksheet.write(
                            row, column+4, line['product']['en_US'])
                        worksheet.write(
                            row, column+5, int(line['qty_ordered']), align_right)
                        worksheet.write(
                            row, column+6, int(line['qty_received']), align_right)
                        worksheet.write(
                            row, column+7, int(line['qty_billed']), align_right)

                        worksheet.write(
                            row, column+8, line['price_total']/line['qty_ordered'], align_right)
                        worksheet.write(
                            row, column+9, int(line['price_total']), align_right)

                        # ---------------------------------------- END LINES ----------------------------------------

                    row += 2
                    column = -1
                    worksheet.write(row, column+1, 'TOTAL ' +
                                    partner['partner_name'], cell_text_format)
                    worksheet.write(row, column+2, '', cell_text_format)
                    worksheet.write(row, column+3, '', cell_text_format)
                    worksheet.write(row, column+4, '', cell_text_format)
                    worksheet.write(
                        row, column+5, int(partner['total_qty_ordered']), align_right_total)
                    worksheet.write(
                        row, column+6, int(partner['total_qty_received']), align_right_total)
                    worksheet.write(
                        row, column+7, int(partner['total_qty_billed']), align_right_total)
                    worksheet.write(row, column+8, '')
                    worksheet.write(
                        row, column+9, int(partner['total_amount']), align_right_total)

            # Main Totals
            row += 2
            column = -1
            worksheet.write(row, column+1, 'Total', cell_text_format)

            worksheet.write(
                row, column+2, int(main['total_qty_ordered_all']), align_right_total)
            worksheet.write(
                row, column+3, int(main['total_qty_received_all']), align_right_total)
            worksheet.write(
                row, column+4, int(main['total_qty_billed_all']), align_right_total)
            worksheet.write(
                row, column+5, int(main['total_amount_all']), align_right_total)

            if self.report_by == 'Detail':
                worksheet.write(row, column+2, '', cell_text_format)
                worksheet.write(row, column+3, '', cell_text_format)
                worksheet.write(row, column+4, '', cell_text_format)

                worksheet.write(
                    row, column+5, int(main['total_qty_ordered_all']), align_right_total)
                worksheet.write(
                    row, column+6, int(main['total_qty_received_all']), align_right_total)
                worksheet.write(
                    row, column+7, int(main['total_qty_billed_all']), align_right_total)
                worksheet.write(row, column+8, '', cell_number_format)
                worksheet.write(
                    row, column+9, int(main['total_amount_all']), align_right_total)

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


class PurchasesbyVendorDetailReport(models.AbstractModel):
    _name = 'report.mgs_purchase.purchases_by_vendor_report'
    _description = 'Purchases by Vendor Detail Report'

    
    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id):
        params = []

        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"
        unit_rates = [
            f"({company.id}, CAST(NULL AS VARCHAR), CAST(NULL AS DATE), CAST(NULL AS DATE), '{rate_type}', 1)"
            for company in self.env.companies
            for rate_type in (('historical', 'current', 'average') if False else ('current',))
        ]

        _select = """
            SELECT
                po.id as order_id,
                min(l.id) as id,
                po.date_order as date_order,
                po.state,
                po.date_approve,
                po.dest_address_id,
                po.partner_id as partner_id,
                po.user_id as user_id,
                po.company_id as company_id,
                po.fiscal_position_id as fiscal_position_id,
                l.product_id,
                p.product_tmpl_id,
                t.categ_id as category_id,
                c.currency_id,
                t.uom_id as product_uom,
                extract(epoch from age(po.date_approve,po.date_order))/(24*60*60)::decimal(16,2) as delay,
                extract(epoch from age(l.date_planned,po.date_order))/(24*60*60)::decimal(16,2) as delay_pass,
                count(*) as nbr_lines,
                sum(l.price_total / COALESCE(po.currency_rate, 1.0))::decimal(16,2) * account_currency_table.rate as price_total,
                (sum(l.product_qty * l.price_unit / COALESCE(po.currency_rate, 1.0))/NULLIF(sum(l.product_qty * line_uom.factor / product_uom.factor),0.0))::decimal(16,2) * account_currency_table.rate as price_average,
                partner.country_id as country_id,
                partner.commercial_partner_id as commercial_partner_id,
                sum(p.weight * l.product_qty * line_uom.factor / product_uom.factor) as weight,
                sum(p.volume * l.product_qty * line_uom.factor / product_uom.factor) as volume,
                sum(l.price_subtotal / COALESCE(po.currency_rate, 1.0))::decimal(16,2) * account_currency_table.rate as untaxed_total,
                sum(l.product_qty * line_uom.factor / product_uom.factor) as qty_ordered,
                sum(l.qty_received * line_uom.factor / product_uom.factor) as qty_received,
                sum(l.qty_invoiced * line_uom.factor / product_uom.factor) as qty_billed,
                case when t.purchase_method = 'purchase'
                    then sum(l.product_qty * line_uom.factor / product_uom.factor) - sum(l.qty_invoiced * line_uom.factor / product_uom.factor)
                    else sum(l.qty_received * line_uom.factor / product_uom.factor) - sum(l.qty_invoiced * line_uom.factor / product_uom.factor)
                end as qty_to_be_billed,
                partner.name AS partner_name, t.name AS product, po.name order_no, partner_ref
        """
        _from = """
            FROM
            purchase_order_line l
                join purchase_order po on (l.order_id=po.id)
                join res_partner partner on po.partner_id = partner.id
                    left join product_product p on (l.product_id=p.id)
                        left join product_template t on (p.product_tmpl_id=t.id)
                left join res_company C ON C.id = po.company_id
                left join uom_uom line_uom on (line_uom.id=l.product_uom_id)
                left join uom_uom product_uom on (product_uom.id=t.uom_id)
                left join (VALUES %s) AS account_currency_table(company_id, period_key, date_from, date_next, rate_type, rate) ON account_currency_table.company_id = po.company_id
        """ % ','.join(map(str, unit_rates))

        _where = """
            WHERE l.display_type IS NULL and po.state = 'purchase'
        """
        _group_by = """
            GROUP BY
                po.company_id,
                po.user_id,
                po.partner_id,
                line_uom.factor,
                c.currency_id,
                l.price_unit,
                po.date_approve,
                l.date_planned,
                l.product_uom_id,
                po.dest_address_id,
                po.fiscal_position_id,
                l.product_id,
                p.product_tmpl_id,
                t.categ_id,
                po.date_order,
                po.state,
                t.uom_id,
                t.purchase_method,
                line_uom.id,
                product_uom.factor,
                partner.country_id,
                partner.commercial_partner_id,
                po.id,
                account_currency_table.rate,
                partner.name, t.name, po.name, po.partner_ref
        """
        if date_from:
            _where += """ and po.date_order >= '%s' """ % f_date

        if date_to:
            _where += """ and po.date_order <= '%s' """ % t_date
            
        if partner_id:
            _where += """ and po.partner_id = """ + str(partner_id)

        if company_id:
            _where += """ and po.company_id = """ + str(company_id)

        query = f"""
            {_select}
            {_from}
            {_where}
            {_group_by}
        """

        self.env.cr.execute(query)
        key = itemgetter('partner_id', 'partner_name')
        res = sorted(self.env.cr.dictfetchall(), key=key)
        lines = []

        for key, value in groupby(res, key):

            sub_lines = []
            total_qty_ordered = 0
            total_qty_received = 0
            total_qty_billed = 0
            total_qty_to_be_billed = 0
            total_amount = 0

            for k in value:
                sub_lines.append(k)
                total_qty_ordered += k['qty_ordered']
                total_qty_received += k['qty_received']
                total_qty_billed += k['qty_billed']
                total_qty_to_be_billed += k['qty_to_be_billed']
                total_amount += k['price_total']

            lines.append({'name': key[1], 'lines': sub_lines, 'total_qty_ordered': total_qty_ordered,
                        'total_qty_received': total_qty_received, 'total_qty_billed': total_qty_billed,
                        'total_qty_to_be_billed': total_qty_to_be_billed, 'total_amount': total_amount})
        
        _logger.info("================= CHECK ====================")
        _logger.info(lines)
        
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
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'lines': self._lines,
        }
