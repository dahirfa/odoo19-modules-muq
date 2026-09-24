from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO


class ValuationSummary(models.TransientModel):
    _name = 'mgs_inventory.valuation_summary'
    _description = 'Valuation Summary'

    product_id = fields.Many2one('product.product', domain=[
                                 ('active', '=', True)])
    date = fields.Datetime('Inventory at', default=fields.Datetime.now)
    categ_id = fields.Many2one('product.category')
    location_id = fields.Many2one('stock.location', string='Location', domain=[
                                  ('usage', '=', 'internal')])
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    def confirm(self):
        location_obj = self.env['stock.location']
        domain = [('usage', '=', 'internal')]
        location_id = self.location_id.id
        location_ids = location_obj.sudo().search(
            [('id', '=', location_id)]).ids  # if location_id else location_obj.sudo().search(domain).ids
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date': self.date,
                'product_id': [self.product_id.id, self.product_id.name],
                'categ_id': [self.categ_id.id, self.categ_id.name],
                'company_id': [self.company_id.id, self.company_id.name],
                'location_ids': location_ids
            },
        }

        return self.env.ref('mgs_inventory.action_valuation_summary').report_action(self, data=data)

    def export_to_excel(self):
        valuation_report_obj = self.env['report.mgs_inventory.valuation_summary_report']
        lines = valuation_report_obj._lines
        get_avg_cost = valuation_report_obj._get_avg_cost
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        # wbf, workbook = self.add_workbook_format(workbook)
        filename = 'InventoryValuationSummaryReport'
        worksheet = workbook.add_worksheet(filename)
        # Formats
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

        # Heading
        row = 1
        worksheet.merge_range(
            'A1:I1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range(
            'A2:I3', 'Inventory Valuation Summary', heading_format)
        # Search criteria
        row += 2
        column = -1
        if self.product_id:
            row += 1
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')
            column+2

        if self.categ_id:
            worksheet.write(row, column+3, 'Category', cell_text_format)
            worksheet.write(row, column+4, self.categ_id.name or '')

        # if self.company_id:
        #     column = 0
        #     worksheet.write(row, column+1, 'Company', cell_text_format)
        #     worksheet.write(row, column+2, self.company_id.name or '')

        # Sub headers

        location_id = self.location_id.id
        location_ids = self.env['stock.location'].sudo().search(
            [('id', '=', location_id)]).ids
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Cateogry', cell_text_format)
        worksheet.write(row, column+2, 'Item Code', cell_text_format)
        worksheet.write(row, column+3, 'Item Description', cell_text_format)
        worksheet.write(row, column+4, 'On Hand', cell_number_format)
        worksheet.write(row, column+5, 'Avg Cost', cell_number_format)
        worksheet.write(row, column+6, 'Asset Value', cell_number_format)
        worksheet.write(row, column+7, 'Sales Price', cell_number_format)
        worksheet.write(row, column+8, 'Retail Value', cell_number_format)
        worksheet.write(row, column+9, 'Margin', cell_number_format)

        # data
        tot_qty = 0
        tot_asset_value = 0
        tot_retail_value = 0

        for category in lines(self.date, self.categ_id.id, self.product_id.id, self.company_id.id, location_ids, 'category'):
            row += 1
            column = -1
            worksheet.write(
                row, column+1, category['categ_name'], cell_text_format)

            tot_qty_category = 0
            tot_asset_value_category = 0
            tot_retail_value_category = 0

            for line in lines(self.date, self.categ_id.id, self.product_id.id, self.company_id.id, location_ids, 'product'):

                tot_qty += line['on_hand']
                tot_asset_value += line['product_value']
                retail_value = line['product_price'] * line['on_hand']
                tot_retail_value += retail_value

                tot_qty_category += line['on_hand']
                tot_asset_value_category += line['product_value']
                tot_retail_value_category += retail_value

                row += 1
                column = -1

                worksheet.write(row, column+2, line['default_code'])
                worksheet.write(row, column+3, line['product_name']['en_US'])
                worksheet.write(
                    row, column+4, '{:,.2f}'.format(line['on_hand']), align_right)
                worksheet.write(
                    row, column+5, get_avg_cost(line['product_id']), align_right)
                worksheet.write(
                    row, column+6, '{:,.2f}'.format(line['product_value']), align_right)
                worksheet.write(
                    row, column+7, '{:,.2f}'.format(line['product_price']), align_right)
                worksheet.write(
                    row, column+8, '{:,.2f}'.format(retail_value), align_right)
                worksheet.write(
                    row, column+9, '{:,.2f}'.format(retail_value-line['product_value']), align_right)

            row += 1
            column = -1
            worksheet.write(
                row, column+4, '{:,.2f}'.format(tot_qty_category), cell_number_format)
            worksheet.write(
                row, column+6, '{:,.2f}'.format(tot_asset_value_category), cell_number_format)
            worksheet.write(
                row, column+8, '{:,.2f}'.format(tot_retail_value_category), cell_number_format)
            worksheet.write(
                row, column+9, '{:,.2f}'.format(tot_retail_value_category-tot_asset_value_category), cell_number_format)

        row += 2
        column = -1
        worksheet.write(
            row, column+4, '{:,.2f}'.format(tot_qty), cell_number_format)
        worksheet.write(
            row, column+6, '{:,.2f}'.format(tot_asset_value), cell_number_format)
        worksheet.write(
            row, column+8, '{:,.2f}'.format(tot_retail_value), cell_number_format)
        worksheet.write(
            row, column+9, '{:,.2f}'.format(tot_retail_value-tot_asset_value), cell_number_format)

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


class ValuationSummaryReport(models.AbstractModel):
    _name = 'report.mgs_inventory.valuation_summary_report'
    _description = 'Valuation Summary Report'

    @api.model
    def _lines(self, date, categ_id, product_id, company_id, location_ids, group_by):
        if len(location_ids) < 1:
            return self._lines_without_location(date, categ_id, product_id, company_id, group_by)

        params = [company_id]
        select_query = """
        select pc.name as categ_name, pc.id as categ_id,
        COALESCE(sum(case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end * COALESCE((pp.standard_price ->> %s::text)::float, 0.0)), 0) * -1 as categ_value,
        COALESCE(sum(case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end), 0) * -1 as categ_on_hand
        """

        order_query = """
        group by pc.name, pc.id order by pc.name
        """
        if group_by == 'product':
            select_query = """
            select pt.name as product_name, pt.default_code as default_code, pt.list_price as product_price, pp.id as product_id, 
            COALESCE(sum(case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end * COALESCE((pp.standard_price ->> %s::text)::float, 0.0)), 0)  * -1 as product_value,
            COALESCE(sum(case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end), 0)  * -1 as on_hand
            """

            order_query = """
             group by pt.name, pt.list_price, pp.id, pt.default_code order by pt.default_code
            """

        from_query = """
        from stock_move_line as sml
        left join product_product as pp on sml.product_id=pp.id
        left join product_template as pt on pp.product_tmpl_id=pt.id
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join product_category as pc on pt.categ_id=pc.id
        left join stock_move as sm on sml.move_id=sm.id
        where pp.active = true
        """

        if date:
            params.append(date)
            from_query += " and sml.date <= %s"

        if categ_id:
            from_query += " and pt.categ_id = " + str(categ_id)

        if product_id:
            from_query += " and pp.id = " + str(product_id)

        if company_id:
            from_query += " and sml.company_id = " + str(company_id)

        if len(location_ids) > 0:
            from_query += """ and (sl.id in (""" + ','.join(map(str, location_ids)) + \
                """) or sld.id in (""" + ','.join(map(str,
                                                      location_ids)) + """))"""

        query = select_query + from_query + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    @api.model
    def _lines_without_location(self, date, categ_id, product_id, company_id, group_by):
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company
        domain = [('is_storable', '=', True)]

        if categ_id:
            domain.append(('categ_id', '=', categ_id))

        if product_id:
            domain.append(('id', '=', product_id))

        products = self.env['product.product'].with_company(company).with_context(
            allowed_company_ids=[company.id], to_date=date, lang='en_US').search(domain)

        product_lines = []
        for product in products:
            on_hand = product.qty_available
            value = product.total_value
            if not on_hand and not value:
                continue
            product_lines.append({
                'product_name': {'en_US': product.product_tmpl_id.name},
                'default_code': product.product_tmpl_id.default_code,
                'product_price': product.product_tmpl_id.list_price,
                'product_id': product.id,
                'product_value': value,
                'on_hand': on_hand,
                'categ_id': product.categ_id.id,
                'categ_name': product.categ_id.name,
            })

        if group_by == 'product':
            return sorted(product_lines, key=lambda l: (not l['default_code'], l['default_code'] or ''))

        categories = {}
        for line in product_lines:
            category = categories.setdefault(line['categ_id'], {
                'categ_name': line['categ_name'],
                'categ_id': line['categ_id'],
                'categ_value': 0.0,
                'categ_on_hand': 0.0,
            })
            category['categ_value'] += line['product_value']
            category['categ_on_hand'] += line['on_hand']
        return sorted(categories.values(), key=lambda c: c['categ_name'] or '')

    @api.model
    def _get_avg_cost(self, product_id):
        product_obj = self.env['product.product']
        return product_obj.search([('id', '=', product_id)]).standard_price

    @api.model
    def _sum_qty(self, product_id, company_id):
        params = ['done']
        location_ids = self.env['stock.location'].search(
            [('company_id', '=', company_id), ('usage', '=', 'internal')]).ids
        query = """
        select sum(case
        when sld.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end) as Balance
        from stock_move_line  as sml
        left join stock_picking as sp on sml.picking_id=sp.id
        left join stock_location as sl on sml.location_id=sl.id
        left join stock_location as sld on sml.location_dest_id=sld.id
        left join stock_move as sm on sml.move_id=sm.id
        left join res_partner as rp on sm.partner_id = rp.id
        left join product_product as pp on sml.product_id = pp.id
        left join product_template as pt on pt.id = pp.product_tmpl_id
        where sml.state = %s
        and (sml.location_id in (""" + ','.join(map(str, location_ids)) + """) or sml.location_dest_id in (""" + ','.join(map(str, location_ids)) + """))"""

        if product_id:
            query += """ and pp.id = """ + str(product_id)

        if company_id:
            query += """ and sm.company_id = """ + str(company_id)

        self.env.cr.execute(query, tuple(params))

        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    @api.model
    # def _get_report_values(self, docids, data=None):
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'date': data['form']['date'],
            'product_id': data['form']['product_id'],
            'categ_id': data['form']['categ_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            'lines': self._lines,
            'sum_qty': self._sum_qty,
            'get_avg_cost': self._get_avg_cost,
            'location_ids': data['form']['location_ids']
        }
