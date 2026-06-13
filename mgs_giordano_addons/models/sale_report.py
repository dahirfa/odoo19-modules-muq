# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleReport(models.Model):
    _inherit = 'sale.report'

    product_barcode = fields.Char(string="Product Barcode", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['product_barcode'] = "COALESCE(p.barcode, '')"
        return res

    def _group_by_sale(self):
        return super()._group_by_sale() + ", p.barcode"