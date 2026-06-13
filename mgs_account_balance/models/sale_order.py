from odoo import models, fields, api  # type: ignore


class SaleOrder(models.Model):
    _inherit = "sale.order"

    mgs_partner_balance = fields.Monetary(
        string="Partner Balance",
        default=0.0,
        compute="_compute_mgs_partner_balance",
        currency_field="currency_id",
    )

    @api.depends("partner_id")
    def _compute_mgs_partner_balance(self):
        for payment in self:
            payment.mgs_partner_balance = payment.partner_id.mgs_credit
