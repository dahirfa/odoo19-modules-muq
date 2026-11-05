from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _generate_pos_order_invoice(self):
        # A 'generate_pdf' already in the context is a localization's explicit decision.
        if 'generate_pdf' in self.env.context:
            return super()._generate_pos_order_invoice()
        return super(
            PosOrder, self.with_context(mgs_pos_skip_invoice_documents=True)
        )._generate_pos_order_invoice()
