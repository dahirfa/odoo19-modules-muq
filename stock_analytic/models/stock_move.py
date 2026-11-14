# Copyright 2013 Julius Network Solutions
# Copyright 2015 Clear Corp
# Copyright 2016 OpenSynergy Indonesia
# Copyright 2017 ForgeFlow S.L.
# Copyright 2018 Hibou Corp.
# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "analytic.mixin"]

    mgs_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        domain=[
            (
                "account_type",
                "in",
                [
                    "liability_current",
                    "liability_non_current",
                    "expense",
                    "expense_direct_cost",
                ],
            )
        ],
        index=True,
    )

    def _get_account_move_line_vals(self):
        """Put the move's analytic distribution (and the optional counterpart
        account override) on the non-valuation line of the stock journal entry.

        Since Odoo 19, a per-move journal entry is only created when the
        source or destination location has a valuation account
        (see `_should_create_account_move`).
        """
        res = super()._get_account_move_line_vals()
        if not self.analytic_distribution and not self.mgs_account_id:
            return res
        valuation_account = self.product_id._get_product_accounts()["stock_valuation"]
        for vals in res:
            if vals.get("account_id") == valuation_account.id:
                continue
            if self.analytic_distribution:
                vals["analytic_distribution"] = self.analytic_distribution
            if self.mgs_account_id:
                vals["account_id"] = self.mgs_account_id.id
        return res

    def _get_analytic_distribution(self):
        """Feed the move's distribution to Odoo's stock analytic lines.

        When a journal entry was created for the move, its counterpart line
        already carries the distribution and generates the analytic lines on
        posting, so we don't create a second set from the move.
        """
        if self.account_move_id:
            return super()._get_analytic_distribution()
        return self.analytic_distribution or super()._get_analytic_distribution()

    def _prepare_procurement_values(self):
        """
        Allows to transmit analytic account from moves to new
        moves through procurement.
        """
        res = super()._prepare_procurement_values()
        if self.analytic_distribution:
            res.update(
                {
                    "analytic_distribution": self.analytic_distribution,
                }
            )
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """
        We fill in the analytic account when creating the move line from
        the move
        """
        res = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res

    def _action_done(self, cancel_backorder=False):
        for move in self:
            # Validate analytic distribution only for outgoing moves.
            if move.location_id.usage not in (
                "internal",
                "transit",
            ) or move.location_dest_id.usage in ("internal", "transit"):
                continue
            move._validate_distribution(
                **{
                    "product": move.product_id.id,
                    "business_domain": "stock_move",
                    "company_id": move.company_id.id,
                }
            )
        return super()._action_done(cancel_backorder=cancel_backorder)


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "analytic.mixin"]

    def _prepare_stock_move_vals(self):
        """
        In the case move lines are created manually, we should fill in the
        new move created here with the analytic account if filled in.
        """
        res = super()._prepare_stock_move_vals()
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res
