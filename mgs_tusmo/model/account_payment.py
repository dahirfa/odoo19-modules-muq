from odoo import api, fields, models, _
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_payment_discount = fields.Boolean(copy=False)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    has_discount = fields.Boolean(string="Discount", default=False)
    discount_amount = fields.Monetary(
        string="Discount Amount", currency_field="currency_id", default=0.0
    )
    discount_account_id = fields.Many2one(
        "account.account",
        string="Discount Account",
        check_company=True,
        domain=[("account_type", "in", ("expense", "expense_direct_cost"))],
    )

    @api.constrains("has_discount", "discount_amount", "discount_account_id")
    def _check_discount(self):
        for pay in self.filtered(lambda p: p.has_discount and p.payment_type == "inbound"):
            if not pay.discount_account_id:
                raise ValidationError(_("Please select the Discount Account!"))
            if pay.discount_amount <= 0:
                raise ValidationError(_("Discount Amount must be greater than zero."))

    def _is_discount_payment(self):
        self.ensure_one()
        return (
            self.has_discount
            and self.payment_type == "inbound"
            and self.discount_account_id
            and self.discount_amount > 0
        )

    def _prepare_discount_line_vals(self):
        """ Write-off line debiting the discount account. The core computes the
        receivable counterpart as -(liquidity + write-offs), so the receivable is
        credited with paid amount + discount.
        """
        self.ensure_one()
        company = self.company_id
        return {
            "name": _("Discount"),
            "account_id": self.discount_account_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "amount_currency": self.discount_amount,
            "balance": self.currency_id._convert(
                self.discount_amount, company.currency_id, company, self.date
            ),
            "is_payment_discount": True,
        }

    def _prepare_move_lines_per_type(self, write_off_line_vals=None, force_balance=None):
        
        if self._is_discount_payment():
            write_off_line_vals = [
                vals for vals in (write_off_line_vals or [])
                if not vals.get("is_payment_discount")
            ] + [self._prepare_discount_line_vals()]
        return super()._prepare_move_lines_per_type(
            write_off_line_vals=write_off_line_vals, force_balance=force_balance
        )

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return super()._get_trigger_fields_to_synchronize() + (
            "has_discount", "discount_amount", "discount_account_id",
        )

    def _synchronize_to_moves(self, changed_fields):
        # The core merges all existing write-off lines into a single one when
        # rebuilding a draft entry. Drop the old discount line first so the
        # current discount values are applied instead of being added twice.
        if any(f in changed_fields for f in self._get_trigger_fields_to_synchronize()):
            for pay in self:
                discount_lines = pay.move_id.line_ids.filtered("is_payment_discount")
                if pay.move_id.state == "draft" and discount_lines:
                    pay.move_id.with_context(
                        check_move_validity=False, skip_invoice_sync=True
                    ).write({"line_ids": [Command.delete(line.id) for line in discount_lines]})
        return super()._synchronize_to_moves(changed_fields)

    def action_post(self):
        for pay in self.filtered(
            lambda p: p.state == "draft" and p.payment_type == "inbound" and p.has_discount
        ):
            pay._check_discount()
            if not pay.outstanding_account_id:
                raise UserError(_(
                    "A discount can only be booked on a payment that creates a journal entry. "
                    "Set an Outstanding Receipts account on the '%(method)s' payment method "
                    "of the %(journal)s journal.",
                    method=pay.payment_method_line_id.name,
                    journal=pay.journal_id.display_name,
                ))
        return super().action_post()
