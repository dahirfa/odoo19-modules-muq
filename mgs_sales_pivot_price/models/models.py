from odoo import models, fields, api

class SalesPivotPrice(models.Model):
    _inherit = "sale.report"
    
    qty_price = fields.Float(string="Qty Price", readonly=True) 
    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['qty_price'] = f"""SUM(l.price_unit
            / {self._case_value_or_one('s.currency_rate')}
            * {self._case_value_or_one('account_currency_table.rate')})
        """
        return res

    



    