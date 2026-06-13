# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    invoice_selection_ids = fields.One2many(
        'account.payment.invoice.line', 'payment_id',
        string='Select Invoices',
    )

    def _load_invoices(self):
        """Utility method to reload invoice selection lines"""
        for rec in self:
            rec.invoice_selection_ids = [(5, 0, 0)]  # Clear existing lines

            if not rec.partner_id or rec.state != 'draft':
                continue

            domain = [
                ('partner_id', 'child_of', rec.partner_id.id),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ]

            if rec.partner_type == 'customer':
                domain.append(('move_type', '=', 'out_invoice'))
            elif rec.partner_type == 'supplier':
                domain.append(('move_type', '=', 'in_invoice'))
            else:
                continue

            invoices = self.env['account.move'].search(domain, order='invoice_date asc')
            lines = [(0, 0, {'invoice_id': inv.id}) for inv in invoices]
            rec.invoice_selection_ids = lines

    @api.onchange('partner_id', 'partner_type')
    def _onchange_partner_invoice_selection(self):
        self._load_invoices()

    def action_post(self):
        for payment in self:
            is_require = self.env.company.require_reconciliation_on_payment
            if payment.invoice_selection_ids and not payment.invoice_selection_ids.filtered('selected') and is_require:
                raise ValidationError("Please select at least one invoice or bill before posting the payment.")
        res = super().action_post()

        for payment in self:
            if payment.invoice_selection_ids:
                selected_lines = payment.invoice_selection_ids.filtered(
                    lambda l: l.selected and l.invoice_id.state == 'posted'
                )

                for line in selected_lines:
                    invoice = line.invoice_id

                    # Find the invoice's payable/receivable lines
                    target_lines = invoice.line_ids.filtered(
                        lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable']
                        and not l.reconciled
                    )

                    # Find the payment's matching lines
                    payment_lines = payment.move_id.line_ids.filtered(
                        lambda l: l.account_id == target_lines[0].account_id and not l.reconciled
                    )

                    if payment_lines and target_lines:
                        (target_lines + payment_lines).reconcile()

                        # Set the payment reference
                        invoice.payment_reference = payment.name

            # Clear the invoice selector after post
            payment.invoice_selection_ids.unlink()

        return res
    def action_draft(self):
        res = super().action_draft()
        self._load_invoices()
        return res


class AccountPaymentInvoiceLine(models.Model):
    _name = 'account.payment.invoice.line'
    _description = 'Selectable Invoice for Payment'

    payment_id = fields.Many2one('account.payment')
    invoice_id = fields.Many2one('account.move', string='Invoice or Bill')
    selected = fields.Boolean('Select')
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    invoice_date = fields.Date(related='invoice_id.invoice_date', string='Invoice Date')
    amount_total = fields.Monetary(related='invoice_id.amount_total_in_currency_signed', string='Total Amount')
    state = fields.Selection(related='invoice_id.payment_state', string='Status')
    amount_due = fields.Monetary(related="invoice_id.amount_residual_signed")