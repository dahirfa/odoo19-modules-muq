from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO
import logging
_logger = logging.getLogger(__name__)


class MGSInvoiceDetail(models.TransientModel):
    _name = 'mgs_account.invoice_detail'
    _description = 'MGS Invoice Detail'

    partner_id = fields.Many2one('res.partner', string="Partner")
    product_id = fields.Many2one('product.product', string="Product")
    team_id = fields.Many2one('crm.team', string="Salesteam")
    user_id = fields.Many2one('res.users', string='Salesperson')
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term')
    date_from = fields.Date(
        'From', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To', default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company.id)
    invoices_bills = fields.Selection([('Invoices', 'Invoices'), (
        'Bills', 'Bills')], string='Invoices/Bills', default='Invoices', required=True)
    report_by = fields.Selection([('Summary', 'Summary'), ('Detail', 'Detail')],
                                 string='Report Type', default='Detail', required=True)
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
                'product_id': [self.product_id.id, self.product_id.name],
                'team_id': [self.team_id.id, self.team_id.name],
                'user_id': [self.user_id.id, self.user_id.name],
                'payment_term_id': [self.payment_term_id.id, self.payment_term_id.name],
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': [self.company_id.id, self.company_id.name],
                'report_by': self.report_by,
                'invoices_bills': self.invoices_bills,
            },
        }

        return self.env.ref('mgs_account.action_invoice_detail').report_action(self, data=data)

    def export_to_excel(self):
        invoice_detail_report_obj = self.env['report.mgs_account.invoice_detail_report']
        lines = invoice_detail_report_obj._lines
        # self, self.date_from, self.date_to, self.company_id.id, self.partner_id.id, self.user_id.id, is_group

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        filename = 'MGSInvoiceReport'
        worksheet = workbook.add_worksheet(filename)

        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12})
        cell_text_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12})
        cell_number_format = workbook.add_format(
            {'align': 'right', 'bold': True, 'size': 12})
        align_right = workbook.add_format({'align': 'right'})
        align_right_total = workbook.add_format(
            {'align': 'right', 'bold': True})
        date_heading_format = workbook.add_format(
            {'align': 'left', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
        date_format = workbook.add_format(
            {'align': 'left', 'num_format': 'd-m-yyyy'})

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:G1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range('A2:G3', 'MGS Invoice Report', heading_format)

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

        if self.team_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Salesteam', cell_text_format)
            worksheet.write(row, column+2, self.team_id.name or '')

        if self.payment_term_id:
            row += 1
            column = -1
            worksheet.write(row, column+1, 'Payment Term', cell_text_format)
            worksheet.write(row, column+2, self.payment_term_id.name or '')

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Date', cell_text_format)
        worksheet.write(row, column+2, 'Number', cell_text_format)
        worksheet.write(row, column+3, 'Partner', cell_text_format)
        worksheet.write(row, column+4, 'Item', cell_text_format)
        worksheet.write(row, column+5, 'Quantity', cell_number_format)
        worksheet.write(row, column+6, 'Rate', cell_number_format)
        worksheet.write(row, column+7, 'Amount', cell_number_format)

        total_qty = 0
        total_amount = 0

        for line in lines(self.date_from, self.date_to, self.company_id.id, self.partner_id, self.product_id.id, self.team_id.id, self.user_id.id, self.payment_term_id.id, self.invoices_bills):

            _logger.info("==================================")
            _logger.info(line)
            _logger.info(line['partner'])
            
            
            row += 2
            column = -1
            worksheet.write(row, column+1, line['date'], date_format)
            worksheet.write(row, column+2, line['ref'])
            worksheet.write(row, column+3, line['partner'])
            worksheet.write(row, column+4, line['product']['en_US'])
            worksheet.write(
                row, column+5, '{:,.2f}'.format(line['quantity']), align_right)

            rate = line['amount_total'] / \
                line['quantity'] if line['amount_total'] and line['quantity'] else 0
            worksheet.write(row, column+6, '{:,.2f}'.format(rate), align_right)
            worksheet.write(
                row, column+7, '{:,.2f}'.format(line['amount_total']), align_right)

            total_qty += line['quantity']
            total_amount += line['amount_total']

        row += 2
        column = -1
        worksheet.write(
            row, column+5, '{:,.2f}'.format(total_qty), cell_number_format)

        worksheet.write(
            row, column+7, '{:,.2f}'.format(total_amount), cell_number_format)

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


class MGSInvoiceDetailReport(models.AbstractModel):
    _name = 'report.mgs_account.invoice_detail_report'
    _description = 'MGS Invoice Detail Report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, product_id, team_id, user_id, payment_term_id, invoices_bills):
        types = "('out_invoice', 'out_refund')"

        if invoices_bills == 'Bills':
            types = "('in_invoice', 'in_refund')"

        # Prepare unit rates as a list of tuples
        unit_rates = [
            (company.id, None, None, None, rate_type, 1)
            for company in self.env.companies
            for rate_type in (('historical', 'current', 'average') if False else ('current',))
        ]

        # Convert unit rates to a VALUES clause string
        values_str = ", ".join(
            "({})".format(", ".join(["%s"] * len(row))) for row in unit_rates
        )
        
        # Flatten the unit_rates list for parameterized query
        flat_unit_rates = [item for sublist in unit_rates for item in sublist]

        query = f"""
            SELECT
                line.id,
                concat(move.ref, ' - ', move.name) as ref,
                template.name as product,
                partner.name as partner,
                line.move_id,
                line.product_id,
                line.account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id,
                line.partner_id AS commercial_partner_id,
                account.account_type AS user_type,
                move.state,
                move.move_type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.payment_state,
                move.invoice_date AS date,
                move.invoice_date_due,
                uom_template.id AS product_uom_id,
                template.categ_id AS product_categ_id,
                line.quantity * COALESCE(uom_line.factor, 1) / NULLIF(COALESCE(uom_template.factor, 1), 0.0) * 
                (CASE WHEN move.move_type IN ('in_invoice', 'out_refund', 'in_receipt') THEN -1 ELSE 1 END) AS quantity,
                line.price_subtotal * 
                (CASE WHEN move.move_type IN ('in_invoice', 'out_refund', 'in_receipt') THEN -1 ELSE 1 END) AS price_subtotal_currency,
                -line.balance * account_currency_table.rate AS price_subtotal,
                line.price_total * 
                (CASE WHEN move.move_type IN ('in_invoice', 'out_refund', 'in_receipt') THEN -1 ELSE 1 END) AS amount_total
            FROM account_move_line line
                LEFT JOIN res_partner partner ON partner.id = line.partner_id
                LEFT JOIN product_product product ON product.id = line.product_id
                LEFT JOIN account_account account ON account.id = line.account_id
                LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
                LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
                INNER JOIN account_move move ON move.id = line.move_id
                LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id
                JOIN (VALUES {values_str}) AS account_currency_table(company_id, period_key, date_from, date_next, rate_type, rate)
                    ON account_currency_table.company_id = line.company_id
            WHERE
                move.state = 'posted' AND line.quantity != 0
                AND move.move_type IN {types}
        """

        params = flat_unit_rates

        if date_from:
            params.append(date_from)
            query += " AND move.invoice_date >= %s"

        if date_to:
            params.append(date_to)
            query += " AND move.invoice_date <= %s"

        if partner_id:
            params.append(partner_id)
            query += " AND move.partner_id = %s"

        if product_id:
            params.append(product_id)
            query += " AND line.product_id = %s"

        if team_id:
            params.append(team_id)
            query += " AND move.team_id = %s"

        if user_id:
            params.append(user_id)
            query += " AND move.invoice_user_id = %s"

        if payment_term_id:
            params.append(payment_term_id)
            query += " AND move.invoice_payment_term_id = %s"

        if company_id:
            params.append(company_id)
            query += " AND move.company_id = %s"

        query += " ORDER BY move.invoice_date"

        # Execute the query with parameters
        self.env.cr.execute(query, tuple(params))
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
            'partner_id': data['form']['partner_id'],
            'product_id': data['form']['product_id'],
            'team_id': data['form']['team_id'],
            'user_id': data['form']['user_id'],
            'payment_term_id': data['form']['payment_term_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'report_by': data['form']['report_by'],
            'invoices_bills': data['form']['invoices_bills'],
            'lines': self._lines,
        }
