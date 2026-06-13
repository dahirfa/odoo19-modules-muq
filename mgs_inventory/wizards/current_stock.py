from datetime import datetime, timedelta, date
from odoo import models, fields, api
import xlsxwriter
import base64
from io import BytesIO
from itertools import groupby
from operator import itemgetter


class CurrentStock(models.TransientModel):
    _name = 'mgs_inventory.current_stock'
    _description = 'Current Stock'

    stock_location_ids = fields.Many2many(
        'stock.location', domain=[('usage', '=', 'internal')])
    date = fields.Datetime(
        'Inventory at', default=fields.Datetime.now, required=True)
    # , domain = [('active', '=', True), ('type', '=', 'product')]
    product_id = fields.Many2one('product.product')
    categ_id = fields.Many2one('product.category')
    parent_categ_id = fields.Many2one(
        'product.category', string="Parent Category")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            return {'domain': {'stock_location_ids': [('company_id', '=', self.company_id.id)]}}

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        if self.categ_id:
            return {'domain': {'product_id': [('categ_id.id', '=', self.categ_id.id)]}}

        return {'domain': {'product_id': []}}

    def confirm(self):
        stock_location_ids = self.stock_location_ids.ids
        if not stock_location_ids:
            stock_location_ids = self.env['stock.location'].search(
                [('usage', '=', 'internal')]).ids

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date': self.date,
                'product_id': [self.product_id.id, self.product_id.name],
                'categ_id': [self.categ_id.id, self.categ_id.name],
                'parent_categ_id': [self.parent_categ_id.id, self.parent_categ_id.name],
                'stock_location_ids': stock_location_ids,
                'company_id': [self.company_id.id, self.company_id.name],

            },
        }

        return self.env.ref('mgs_inventory.action_current_stock').report_action(self, data=data)

    def export_to_excel(self):
        current_stock_report_obj = self.env['report.mgs_inventory.current_stock_report']
        lines = current_stock_report_obj._lines
        group_data_by_product = current_stock_report_obj._group_data_by_product

        location_ids = self.stock_location_ids
        if len(location_ids) == 0:
            location_ids = self.env['stock.location'].search(
                [('usage', '=', 'internal')])

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        # wbf, workbook = self.add_workbook_format(workbook)
        filename = 'QuantityOnHandByLocationReport'
        worksheet = workbook.add_worksheet(filename)
        # Formats
        heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 14})
        sub_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 13})
        # text_heading_format = workbook.add_format(
        #     {'bold': True, 'size': 12})
        # number_heading_format = workbook.add_format(
        #     {'align': 'right', 'bold': True, 'size': 12})
        date_heading_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 12, 'num_format': 'd-m-yyyy'})
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
            'A1:D1', self.company_id.name, sub_heading_format)
        row += 1
        worksheet.merge_range(
            'A2:D3', 'Quantity on Hand by Location', heading_format)
        row = 1
        worksheet.merge_range('A4:D4', self.date, date_heading_format)

        row += 1
        column = 0
        if self.product_id:
            worksheet.write(row, column+1, 'Product', cell_text_format)
            worksheet.write(row, column+2, self.product_id.name or '')

        if self.parent_categ_id:
            worksheet.write(row, column+3, 'Parent Category', cell_text_format)
            worksheet.write(row, column+4, self.parent_categ_id.name or '')

        if self.categ_id:
            worksheet.write(row, column+5, 'Category', cell_text_format)
            worksheet.write(row, column+6, self.categ_id.name or '')

        # Sub headers
        row += 1
        column = -1
        no = 1
        worksheet.write(row, column+no, 'Product', cell_text_format)

        for location in location_ids:
            no += 1
            worksheet.write(row, column+no, location.name, cell_text_format)

        no += 1
        worksheet.write(row, column+no, 'Total', cell_number_format)

        # data
        tot_qty_all = 0
        data = lines(self.date, self.categ_id.id, self.product_id.id,
                     location_ids.ids, self.company_id.id, self.parent_categ_id.id)

        # liens
        for line in group_data_by_product(data, location_ids):
            total_qty_product = 0
            row += 1
            column = -1
            no = 1
            worksheet.write(row, column+no, line['product'])

            for qty_location in line['qty']:
                no += 1
                worksheet.write(
                    row, column+no, "{:,}".format(int(qty_location)))
                total_qty_product += qty_location

            no += 1
            worksheet.write(
                row, column+no, "{:,}".format(int(total_qty_product)))

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


class CurrentStockReport(models.AbstractModel):
    _name = 'report.mgs_inventory.current_stock_report'
    _description = 'Current Stock Report'

    @api.model
    def _lines(self, date, categ_id, product_id, location_ids, company_id, parent_categ_id):
        params = ['done']
        if date:
            params.append(date)

        query = """
        SELECT 
            sml.product_id product_id, pt.name product_name,
            categ.id categ_id, categ.name categ_name,
            parent_categ.id parent_categ_id, parent_categ.name parent_categ_name,
            sl.id location_id, sl.name location_name,
            sld.id location_dest_id, sld.name location_dest_name,
            -- sml.quantity quantity
            COALESCE(sml.quantity / u.factor * u2.factor, 0) quantity
        FROM 
            stock_move_line sml
            LEFT JOIN stock_picking sp ON sml.picking_id=sp.id
            LEFT JOIN stock_location sl ON sml.location_id=sl.id
            LEFT JOIN stock_location sld ON sml.location_dest_id=sld.id
            LEFT JOIN stock_move sm ON sml.move_id=sm.id
            LEFT JOIN res_partner rp ON sm.partner_id = rp.id
            LEFT JOIN product_product pp ON sml.product_id = pp.id
            LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN uom_uom u ON u.id=sml.product_uom_id
            LEFT JOIN uom_uom u2 ON u2.id=pt.uom_id
            LEFT JOIN product_category categ ON pt.categ_id = categ.id
            LEFT JOIN product_category parent_categ ON categ.parent_id = parent_categ.id
        WHERE 
            NOT sl.id = sld.id AND sml.state = %s
        """

        if date:
            query += """ AND sml.date < %s"""

        if len(location_ids) > 0:
            query += """ and (sl.id in (""" + ','.join(map(str, location_ids)) + \
                """) or sld.id in (""" + ','.join(map(str,
                                                      location_ids)) + """))"""

        if categ_id:
            query += """ AND pt.categ_id = """ + str(categ_id)

        if parent_categ_id:
            query += """ AND parent_categ.id = """ + str(parent_categ_id)

        if product_id:
            query += """ AND pp.id = """ + str(product_id)

        if company_id:
            query += """ AND sm.company_id = """ + str(company_id)

        self.env.cr.execute(query, tuple(params))

        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        return res

    @api.model
    def _group_data_by_product(self, data, location_ids):
        key = itemgetter('product_id', 'product_name')
        res = sorted(data, key=key)
        lines = []
        for key, value in groupby(res, key=key):
            line = {'product': key[1]['en_US'], 'qty': []}

            for location in location_ids:
                product_location_qty = 0
                for move_line in [d for d in data if d['product_id'] == key[0] and (d['location_id'] == location.id or d['location_dest_id'] == location.id)]:
                    # product_location_qty += move_line.quantity if move_line.location_id == location.id else -= move_line.quantity
                    product_location_qty += move_line['quantity'] if move_line['location_dest_id'] == location.id else -move_line['quantity']

                    # if move_line['location_dest_id'] == location.id:
                    #     product_location_qty += move_line['quantity']
                    # else:
                    #     product_location_qty -= move_line['quantity']

                line['qty'].append(product_location_qty)

            lines.append(line)

        return lines

    @api.model
    # def _get_report_values(self, docids, data=None):
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': self.env[model].browse(self.env.context.get('active_id')),
            'date': data['form']['date'],
            'product_id': data['form']['product_id'],
            'categ_id': data['form']['categ_id'],
            'parent_categ_id': data['form']['parent_categ_id'],
            'company_id': self.env['res.company'].search([('id', '=', data['form']['company_id'][0])]),
            # 'stock_location_ids': stock_location_ids,
            'lines': self._lines,
            'group_data_by_product': self._group_data_by_product,
            'location_ids': self.env['stock.location'].search([('id', 'in', data['form']['stock_location_ids'])]),
        }

# class CurrentStockReport2(models.Model):
#     _name = 'report.mgs_inventory.current_stock_analysis'
#     _description = 'Current Stock Analysis'

#     location_id = fields.Many2one(
#         'stock.location', domain=[('usage', '=', 'internal')])
#     product_id = fields.Many2one('product.product')
#     parent_categ_id = fields.Many2one('product.category', string="Parent Category")
#     categ_id = fields.Many2one('product.category', string="Category")
#     company_id = fields.Many2one('res.company', string='Company',
#                                  default=lambda self: self.env.company)
#     quantity = fields.Float(string="On Hand")
#     value = fields.Float(string="Value")

#     @api.model
#     def _select(self, location_ids):
#         return """SELECT sml.product_id AS product_id, parent_categ.id AS parent_categ_id,
#         pt.categ_id AS categ_id, sml.company_id AS company_id,
#         case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.location_id else - sml.location_dest_id end), as location_id,
#         COALESCE(sum(case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end * prop.value_float), 0)  * -1 as value,
#         COALESCE(sum(case when sl.id in (""" + ','.join(map(str, location_ids)) + """) then sml.quantity else - sml.quantity end), 0)  * -1 as on_hand
#         """

#     @api.model
#     def _from(self, company_id=self.env.company.id):
#         return """
#         from stock_move_line as sml
#         left join product_product as pp on sml.product_id=pp.id
#         left join product_template as pt on pp.product_tmpl_id=pt.id
#         left join stock_location as sl on sml.location_id=sl.id
#         left join stock_location as sld on sml.location_dest_id=sld.id
#         left join ir_property prop on prop.res_id = 'product.product,' || pp.id and prop.company_id=%s
#         left join product_category as pc on pt.categ_id=pc.id
#         left join product_category as parent_categ on pc.parent_id = parent_categ.id
#         left join stock_move as sm on sml.move_id=sm.id
#         where pp.active = true
#             """ % str(company_id)

#     @api.model
#     def _where(self, date=fields.Date.today(), categ_id=None, product_id=None, location_ids=self.env['stock.location'].search([]).ids, company_id=self.env.company.id, parent_categ_id=None):
#         where_query = """WHERE pp.active = true AND sml.state NOT IN ('draft', 'cancel')"""

#         if date:
#             params.append(date)
#             where_query += " AND sml.date <= '%s'" % date

#         if categ_id:
#             where_query += " AND pt.categ_id = " + str(categ_id)

#         if product_id:
#             where_query += " AND pp.id = " + str(product_id)

#         if len(location_ids) > 0:
#             where_query += """ AND (sl.id in (""" + ','.join(map(str, location_ids)) + \
#                 """) OR sld.id IN (""" + ','.join(map(str, location_ids)) + """))"""

#         if company_id:
#             where_query += " AND sml.company_id = " + str(company_id)

#         if parent_categ_id:
#             where_query += """ AND parent_categ.id = """ + str(parent_categ_id)

#         return where_query

#     @api.model
#     def _group_by(self):
#         return " GROUP BY sml.product_id, parent_categ.id, pt.categ_id, sml.company_id"

#     def query_execute(self, date=fields.Date.today(), categ_id=None, product_id=None, location_ids=self.env['stock.location'].search([]).ids, company_id=self.env.company.id, parent_categ_id=None):
#         result = """
#         %s
#         %s
#         %s
#         %s

#         %s
#         """ % (self._select(location_ids), self._from(company_id), self._where(date, categ_id, product_id, location_ids, company_id, parent_categ_id), self._group_by())
#         # _logger.warning(
#         #     '#################################################')
#         # _logger.warning(result)
#         return result

#     def init(self):
#         tools.drop_view_if_exists(self._cr, self._table)
#         self._cr.execute('''CREATE OR REPLACE VIEW %s AS (%s)''' %
#                          (self._table, self.query_execute()))
