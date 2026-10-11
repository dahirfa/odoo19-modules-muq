from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        res = super().button_confirm()
        for order in self.filtered(lambda o: o.state == 'purchase'):
            company = order.company_id
            if company.is_receipt_set_to_done:
                order._auto_validate_receipts()

            if company.create_bill and not order.invoice_ids:
                order.action_create_invoice()

            if company.validate_bill:
                for invoice in order.invoice_ids.filtered(lambda m: m.state == 'draft'):
                    if not invoice.invoice_date:
                        invoice.invoice_date = fields.Date.context_today(invoice)
                    invoice.action_post()
        return res

    def _auto_validate_receipts(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        for picking in pickings:
            for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                move.quantity = move.product_uom_qty
                move.picked = True
        pickings.with_context(skip_backorder=True).button_validate()
