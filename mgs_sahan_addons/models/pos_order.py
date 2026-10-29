from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
     
        vals = super()._prepare_invoice_vals()
        if not self.company_id.show_pos_reference:
            return vals
        refs = self.filtered('pos_reference').mapped('pos_reference')
        if refs:
            vals['pos_reference'] = ', '.join(refs)
        return vals
