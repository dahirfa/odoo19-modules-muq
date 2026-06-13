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
                                 default=lambda self: self.env.company.id)
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        if self.categ_id:
            return {'domain': {'product_id': [('categ_id.id', '=', self.categ_id.id)]}}

        return {'domain': {'product_id': []}}

    def confirm(self):
        location_obj = self.env['stock.location']
        domain = [('usage', '=', 'internal')]
        location_id = self.location_id.id
        location_ids = location_obj.sudo().search(
            # if location_id else location_obj.sudo().search(domain).ids
            [('id', '=', location_id)]).ids
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
            column += 2

        if self.categ_id:
            worksheet.write(row, column+3, 'Category', cell_text_format)
            worksheet.write(row, column+4, self.categ_id.name or '')

        # Locations
        location_id = self.location_id.id
        location_ids = self.env['stock.location'].sudo().search(
            [('id', '=', location_id)]).ids

        # Sub headers
        row += 2
        column = -1
        worksheet.write(row, column+1, 'Category', cell_text_format)
        worksheet.write(row, column+2, 'Item Code', cell_text_format)
        worksheet.write(row, column+3, 'Item Description', cell_text_format)
        worksheet.write(row, column+4, 'On Hand', cell_number_format)
        worksheet.write(row, column+5, 'Avg Cost', cell_number_format)
        worksheet.write(row, column+6, 'Asset Value', cell_number_format)
        worksheet.write(row, column+7, 'Sales Price', cell_number_format)
        worksheet.write(row, column+8, 'Retail Value', cell_number_format)
        worksheet.write(row, column+9, 'Margin', cell_number_format)

        # Totals
        tot_qty = 0.0
        tot_asset_value = 0.0
        tot_retail_value = 0.0

        for category in lines(self.date, self.categ_id.id, self.product_id.id, self.company_id.id, location_ids, 'category'):
            row += 1
            column = -1
            worksheet.write(
                row, column+1, category.get('categ_name', ''), cell_text_format)

            tot_qty_category = 0.0
            tot_asset_value_category = 0.0
            tot_retail_value_category = 0.0

            for line in lines(self.date, self.categ_id.id, self.product_id.id, self.company_id.id, location_ids, 'product'):

                # Safely extract numeric values (avoid NoneType errors)
                on_hand = line.get('on_hand') or 0.0
                product_value = line.get('product_value') or 0.0
                product_price = line.get('product_price') or 0.0
                default_code = line.get('default_code') or ''
                product_name = line.get(
                    'product_name', {}).get('en_US', '') or ''
                product_id = line.get('product_id')

                # Calculations
                retail_value = product_price * on_hand
                margin_value = retail_value - product_value

                # Update totals
                tot_qty += on_hand
                tot_asset_value += product_value
                tot_retail_value += retail_value

                tot_qty_category += on_hand
                tot_asset_value_category += product_value
                tot_retail_value_category += retail_value

                # Write row
                row += 1
                column = -1
                worksheet.write(row, column+2, default_code)
                worksheet.write(row, column+3, product_name)
                worksheet.write(
                    row, column+4, '{:,.2f}'.format(on_hand), align_right)
                worksheet.write(
                    row, column+5, '{:,.2f}'.format(get_avg_cost(product_id)), align_right)
                worksheet.write(
                    row, column+6, '{:,.2f}'.format(product_value), align_right)
                worksheet.write(
                    row, column+7, '{:,.2f}'.format(product_price), align_right)
                worksheet.write(
                    row, column+8, '{:,.2f}'.format(retail_value), align_right)
                worksheet.write(
                    row, column+9, '{:,.2f}'.format(margin_value), align_right)

            # Category totals
            row += 1
            column = -1
            worksheet.write(
                row, column+4, '{:,.2f}'.format(tot_qty_category), cell_number_format)
            worksheet.write(
                row, column+6, '{:,.2f}'.format(tot_asset_value_category), cell_number_format)
            worksheet.write(
                row, column+8, '{:,.2f}'.format(tot_retail_value_category), cell_number_format)
            worksheet.write(row, column+9, '{:,.2f}'.format(
                tot_retail_value_category - tot_asset_value_category), cell_number_format)

        # Final totals
        row += 2
        column = -1
        worksheet.write(
            row, column+4, '{:,.2f}'.format(tot_qty), cell_number_format)
        worksheet.write(
            row, column+6, '{:,.2f}'.format(tot_asset_value), cell_number_format)
        worksheet.write(
            row, column+8, '{:,.2f}'.format(tot_retail_value), cell_number_format)
        worksheet.write(
            row, column+9, '{:,.2f}'.format(tot_retail_value - tot_asset_value), cell_number_format)

        # Close and return
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out, 'datas_fname': filename})
        fp.close()
        filename += '%2Exlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f'web/content/?model={self._name}&id={self.id}&field=datas&download=true&filename={filename}',
        }

# comment
class ValuationSummaryReport(models.AbstractModel):
    _name = 'report.mgs_inventory.valuation_summary_report'
    _description = 'Valuation Summary Report'

    @api.model
    def _lines(self, date, categ_id, product_id, company_id, location_ids, group_by):
        if not location_ids:
            return self._lines_without_location(date, categ_id, product_id, company_id, group_by)

        params = [str(company_id)]
        loc_ids_str = ','.join(map(str, location_ids))

        # Base select for category grouping
        select_query = f"""
        SELECT 
            pc.name AS categ_name,
            pc.id AS categ_id,
            SUM(sq.quantity * (pp.standard_price ->> %s)::numeric) AS categ_value,
            SUM(sq.quantity) AS categ_on_hand
        """
        order_query = "GROUP BY pc.name, pc.id ORDER BY pc.name"

        # If grouping by product
        if group_by == 'product':
            select_query = f"""
            SELECT 
                pt.name AS product_name,
                pt.default_code AS default_code,
                pt.list_price AS product_price,
                pp.id AS product_id,
                SUM(sq.quantity * (pp.standard_price ->> %s)::numeric) AS product_value,
                SUM(sq.quantity) AS on_hand
            """
            order_query = """
            GROUP BY pt.name, pt.default_code, pt.list_price, pp.id
            ORDER BY pt.default_code
            """

        from_query = f"""
        FROM stock_quant AS sq
        LEFT JOIN product_product AS pp ON sq.product_id = pp.id
        LEFT JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
        LEFT JOIN product_category AS pc ON pt.categ_id = pc.id
        LEFT JOIN stock_location AS sl ON sq.location_id = sl.id
        WHERE pp.active = TRUE
        AND sl.id IN ({loc_ids_str})
        AND sl.usage = 'internal'
        """

        # Filters
        if product_id:
            from_query += " AND pp.id = %s"
            params.append(product_id)
        if categ_id:
            from_query += " AND pt.categ_id = %s"
            params.append(categ_id)
        if company_id:
            from_query += " AND sq.company_id = %s"
            params.append(company_id)
        if date:
            from_query += " AND sq.in_date <= %s"
            params.append(date)

        query = select_query + from_query + " " + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()

        # Optionally recalculate product_value using avg cost (for accuracy)
        if group_by == 'product' and categ_id:
            for r in res:
                avg_cost = self._get_avg_cost(r['product_id'])
                r['product_value'] = r['on_hand'] * avg_cost

        return res

    @api.model
    def _lines_without_location(self, date=None, categ_id=None, product_id=None, company_id=None, group_by='categ'):
        params = []

        # Base select for category grouping
        select_query = f"""
        SELECT 
            pc.name AS categ_name,
            pc.id AS categ_id,
            SUM(sq.quantity * (pp.standard_price ->> %s)::numeric) AS categ_value,
            SUM(sq.quantity) AS categ_on_hand
        """
        order_query = "GROUP BY pc.name, pc.id ORDER BY pc.name"

        # If grouping by product
        if group_by == 'product':
            select_query = f"""
            SELECT 
                pt.name AS product_name,
                pt.default_code AS default_code,
                pt.list_price AS product_price,
                pp.id AS product_id,
                SUM(sq.quantity * (pp.standard_price ->> %s)::numeric) AS product_value,
                SUM(sq.quantity) AS on_hand
            """
            order_query = """
            GROUP BY pt.name, pt.default_code, pt.list_price, pp.id
            ORDER BY pt.default_code
            """

        from_query = """
        FROM stock_quant AS sq
        LEFT JOIN product_product AS pp ON sq.product_id = pp.id
        LEFT JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
        LEFT JOIN product_category AS pc ON pt.categ_id = pc.id
        LEFT JOIN stock_location AS sl ON sq.location_id = sl.id
        WHERE pp.active = TRUE AND sl.usage = 'internal'
        """

        # Filters
        if product_id:
            from_query += " AND pp.id = %s"
            params.append(product_id)
        if categ_id:
            from_query += " AND pt.categ_id = %s"
            params.append(categ_id)
        if company_id:
            from_query += " AND sq.company_id = %s"
            params.append(company_id)

        # The company_id also needs to be passed for JSONB extraction
        params.insert(0, str(company_id))  # for ->> operator

        query = select_query + from_query + " " + order_query

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

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
