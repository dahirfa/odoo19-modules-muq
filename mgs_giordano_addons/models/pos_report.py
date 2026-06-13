# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PosOrderReport(models.Model):
    _inherit = "report.pos.order"

    product_barcode = fields.Char(string="Product (Barcode)", readonly=True)

    def _select(self):
        return super()._select() + """,
            COALESCE(p.barcode, '') AS product_barcode
        """

    def _group_by(self):
        return super()._group_by() + ", p.barcode"





class PosSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(
        self,
        date_start=False,
        date_stop=False,
        config_ids=False,
        session_ids=False,
        **kwargs
    ):
       
        result = super().get_sale_details(
            date_start=date_start,
            date_stop=date_stop,
            config_ids=config_ids,
            session_ids=session_ids,
            **kwargs
        )

        products = result.get('products', [])

       
        for category in products:
            for line in category.get('products', []):
                # store original qty for later restore
                line['_orig_qty'] = line.get('quantity', 0)

                if line.get('base_amount', 0) < 0:
                    line['quantity'] = 0

        
        config_id = False
        if config_ids:
            config_id = config_ids[0]
        elif session_ids:
            session = self.env['pos.session'].browse(session_ids[0])
            config_id = session.config_id.id

        products, products_info = self.with_context(
            config_id=config_id
        )._get_total_and_qty_per_category(products)

      
        for category in products:
            for line in category.get('products', []):
                if '_orig_qty' in line:
                    line['quantity'] = line['_orig_qty']
                    del line['_orig_qty']

      
        result['products'] = products
        result['products_info'] = products_info

        return result