from odoo import models, fields, api
from odoo.exceptions import ValidationError
from itertools import groupby
from operator import itemgetter
import xlsxwriter
import base64
from io import BytesIO


class SalesByCustomerDetailReport(models.AbstractModel):
    _inherit = 'report.mgs_sale.sales_by_customer_report'

    @api.model
    def _lines(self, date_from, date_to, company_id, partner_id, user_id, product_ids, team_id):  # , company_branch_ids
        sale_report_obj = self.env['sale.report']
        lines = []
        _select_sale = sale_report_obj._select_sale()
        _from_sale = sale_report_obj._from_sale()
        _where_sale = sale_report_obj._where_sale()
        _group_by_sale = sale_report_obj._group_by_sale()

        with_ = sale_report_obj._with_sale()

        _select_sale += ', partner.name AS partner_name, t.name AS product, COALESCE(l.price_total-l.margin, 0) as cost, COALESCE(l.margin, 0), s.client_order_ref'
        _group_by_sale += ', partner.name, t.name, l.price_total, l.margin'

        # pos
        _select_pos = sale_report_obj._select_pos()
        _select_pos = _select_pos.replace("pos.partner_id", "COALESCE(pos.partner_id, -1)")

        _select_pos += ", COALESCE(partner.name, 'Undefined') AS partner_name, t.name AS product, COALESCE(l.price_subtotal-(l.price_subtotal - l.total_cost), 0) as cost, COALESCE(l.price_subtotal-(l.price_subtotal - l.total_cost), 0), pos.pos_reference"
        
        _group_by_pos = sale_report_obj._group_by_pos()
        _group_by_pos += ', partner.name, t.name, l.price_subtotal, l.price_subtotal - l.total_cost'
        _where_pos = sale_report_obj._where_pos()
        
        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if date_from:
            _where_sale += " and s.date_order >= '%s'" % f_date
            _where_pos += " and pos.date_order >= '%s'" % f_date

        if date_to:
            _where_sale += " and s.date_order <= '%s'" % t_date
            _where_pos += " and pos.date_order <= '%s'" % t_date

        if partner_id:
            _where_sale += ' and s.partner_id = %s' % partner_id
            _where_pos += ' and pos.partner_id = %s' % partner_id

        if user_id:
            _where_sale += ' and s.user_id = %s' % user_id
            _where_pos += ' and pos.user_id = %s' % user_id

        if company_id:
            _where_sale += ' and s.company_id = %s' % company_id
            _where_pos += ' and pos.company_id = %s' % company_id

        if product_ids:
            _where_sale += " and l.product_id in (" + \
                ','.join(map(str, product_ids)) + ")"
            _where_pos += " and l.product_id in (" + \
                ','.join(map(str, product_ids)) + ")"

        if team_id:
            _where_sale += ' and s.team_id = %s' % team_id
            _where_pos += ' and pos.crm_team_id = %s' % team_id

        _where_sale += " and s.state not in ('draft', 'cancel', 'sent')"

        
        query = f"""
            {"WITH " + with_ if with_ else ""}
            SELECT {_select_sale}
            FROM {_from_sale}
            WHERE {_where_sale}
            GROUP BY {_group_by_sale}
            {" " + with_ if with_ else ""}
            UNION ALL
            (
                SELECT {_select_pos}
                FROM {sale_report_obj._from_pos()}
                WHERE {_where_pos}
                GROUP BY {_group_by_pos}
            )
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
    

class SalesbyItemDetailReport(models.AbstractModel):
    _inherit = 'report.mgs_sale.sales_by_item_report'

    @api.model
    # def _lines(self, date_from, date_to, company_id, partner_id, user_id, product_ids, team_id):
    def _lines(self, date_from, date_to, company_id, user_id, product_ids, team_id, parent_categ_id, categ_id):  # , company_branch_ids
        sale_report_obj = self.env['sale.report']
        lines = []
        _select_sale = sale_report_obj._select_sale()
        _from_sale = sale_report_obj._from_sale()
        _where_sale = sale_report_obj._where_sale()
        _group_by_sale = sale_report_obj._group_by_sale()

        with_ = sale_report_obj._with_sale()

        _select_sale += ', partner.name AS partner_name, t.name AS product, COALESCE(l.price_total-l.margin, 0) as cost, COALESCE(l.margin, 0), s.client_order_ref'
        _group_by_sale += ', partner.name, t.name, l.price_total, l.margin'

        # pos
        _select_pos = sale_report_obj._select_pos()
        _select_pos = _select_pos.replace("l.product_id", "COALESCE(l.product_id, -1)")

        _select_pos += ", partner.name as partner_name, t.name AS product, COALESCE(l.price_subtotal-(l.price_subtotal - l.total_cost), 0) as cost, COALESCE(l.price_subtotal-(l.price_subtotal - l.total_cost), 0), pos.pos_reference"
        
        _group_by_pos = sale_report_obj._group_by_pos()
        _group_by_pos += ', partner.name, t.name, l.price_subtotal, l.price_subtotal - l.total_cost'
        _where_pos = sale_report_obj._where_pos()
        _from_pos = sale_report_obj._from_pos()

        _from_sale += """
        LEFT JOIN product_category as pc ON t.categ_id = pc.id 
        LEFT JOIN product_category as pc2 ON pc.parent_id = pc2.id"""

        _from_pos += """
        LEFT JOIN product_category as pc ON t.categ_id = pc.id 
        LEFT JOIN product_category as pc2 ON pc.parent_id = pc2.id"""
        
        f_date = str(date_from) + " 00:00:00"
        t_date = str(date_to) + " 23:59:59"

        if date_from:
            _where_sale += " and s.date_order >= '%s'" % f_date
            _where_pos += " and pos.date_order >= '%s'" % f_date

        if date_to:
            _where_sale += " and s.date_order <= '%s'" % t_date
            _where_pos += " and pos.date_order <= '%s'" % t_date

        if user_id:
            _where_sale += ' and s.user_id = %s' % user_id
            _where_pos += ' and pos.user_id = %s' % user_id

        if company_id:
            _where_sale += ' and s.company_id = %s' % company_id
            _where_pos += ' and pos.company_id = %s' % company_id

        if product_ids:
            _where_sale += " and l.product_id in (" + \
                ','.join(map(str, product_ids)) + ")"
            _where_pos += " and l.product_id in (" + \
                ','.join(map(str, product_ids)) + ")"

        if team_id:
            _where_sale += ' and s.team_id = %s' % team_id
            _where_pos += ' and pos.crm_team_id = %s' % team_id

        if parent_categ_id:
            _where_sale += """ and pc2.id = """ + str(parent_categ_id)
            _where_pos += """ and pc2.id = """ + str(parent_categ_id)

        if categ_id:
            _where_sale += """ and pc.id = """ + str(categ_id)
            _where_pos += """ and pc.id = """ + str(categ_id)

        _where_sale += " and s.state not in ('draft', 'cancel', 'sent')"

        
        query = f"""
            {"WITH " + with_ if with_ else ""}
            SELECT {_select_sale}
            FROM {_from_sale}
            WHERE {_where_sale}
            GROUP BY {_group_by_sale}
            {" " + with_ if with_ else ""}
            UNION ALL
            (
                SELECT {_select_pos}
                FROM {_from_pos}
                WHERE {_where_pos}
                GROUP BY {_group_by_pos}
            )
        """

        self.env.cr.execute(query)
        key = itemgetter('product_id', 'product')
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

            lines.append({'name': key[1]['en_US'], 'lines': sub_lines, 'total_qty_ordered': total_qty_ordered,
                          'total_qty_delivered': total_qty_delivered, 'total_qty_invoiced': total_qty_invoiced,
                          'total_qty_to_invoice': total_qty_to_invoice, 'total_amount': total_amount,
                          'total_margin': total_margin, 'total_cost': total_cost})
        return lines
    

class SalesbyRepDetailReport(models.AbstractModel):
    _inherit = 'report.mgs_sale.sales_by_rep_report'

    @api.model
    def _lines(self, date_from, date_to, company_id, product_ids, partner_id, team_id, user_id):  # , company_branch_ids
        sale_report_obj = self.env['sale.report']
        lines = []
        _select_sale = sale_report_obj._select_sale()
        _from_sale = sale_report_obj._from_sale()
        _where_sale = sale_report_obj._where_sale()
        _group_by_sale = sale_report_obj._group_by_sale()

        with_ = sale_report_obj._with_sale()

        _select_sale += ', partner.name AS partner_name, t.name AS product, COALESCE(l.price_total-l.margin, 0) as cost, COALESCE(l.margin, 0), s.client_order_ref'
        _group_by_sale += ', partner.name, t.name, l.price_total, l.margin'

        # pos
        _select_pos = sale_report_obj._select_pos()
        _select_pos = _select_pos.replace("pos.partner_id", "COALESCE(pos.partner_id, -1)")

        _select_pos += ", COALESCE(partner.name, 'Undefined') AS partner_name, t.name AS product, COALESCE(l.price_subtotal-(l.price_subtotal - l.total_cost), 0) as cost, COALESCE(l.price_subtotal-(l.price_subtotal - l.total_cost), 0), pos.pos_reference"
        
        _group_by_pos = sale_report_obj._group_by_pos()
        _group_by_pos += ', partner.name, t.name, l.price_subtotal, l.price_subtotal - l.total_cost'
        _where_pos = sale_report_obj._where_pos()

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

        _where_sale += " and s.state not in ('draft', 'cancel', 'sent')"

        query = f"""
            {"WITH " + with_ if with_ else ""}
            SELECT {_select_sale}
            FROM {_from_sale}
            WHERE {_where_sale}
            GROUP BY {_group_by_sale}
            {" " + with_ if with_ else ""}
            UNION ALL
            (
                SELECT {_select_pos}
                FROM {sale_report_obj._from_pos()}
                WHERE {_where_pos}
                GROUP BY {_group_by_pos}
            )
        """

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        return res