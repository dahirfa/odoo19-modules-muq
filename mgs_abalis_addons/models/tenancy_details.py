from odoo import models


class TenancyDetails(models.Model):
    _inherit = 'tenancy.details'

    def _get_rent_collection(self):
        """Return ``(invoiced, paid)`` rent amounts (tax included) of these contracts.

        Only the rent lines (the contract's installment item, i.e. Property Payment)
        are counted: deposit, maintenance, broker and any other line is ignored. An
        invoice mixing rent with other items is paid in proportion to its total, so
        the paid share of a rent line is ``line total * paid / invoice total``.
        """
        invoiced = paid = 0.0
        for contract in self:
            rent_product = contract.installment_item_id
            if not rent_product:
                continue
            moves = contract.rent_invoice_ids.rent_invoice_id.filtered(lambda m: m.state != 'cancel')
            for move in moves:
                rent_total = sum(move.invoice_line_ids.filtered(
                    lambda line: line.display_type == 'product' and line.product_id == rent_product
                ).mapped('price_total'))
                if not rent_total or not move.amount_total:
                    continue
                invoiced += rent_total
                paid += rent_total * (move.amount_total - move.amount_residual) / move.amount_total
        return invoiced, paid
