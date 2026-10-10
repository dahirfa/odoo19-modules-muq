from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class CashTransfer(models.Model):
    _name = 'mgs_cash_transfer.transfer'
    _description = 'Cash Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Reference', copy=False, default='New')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    memo = fields.Char(string='Memo')
    journal_id = fields.Many2one('account.journal', string='Source Journal (From)', required=True, check_company=True, domain=[('type', 'in', ['cash', 'bank'])])
    destination_journal_id = fields.Many2one('account.journal', string='Dest.Journal (To)', required=True, check_company=True, domain=[('type', 'in', ['cash', 'bank'])])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    # The amount is always expressed in the currency of the source journal and the
    # destination amount in the currency of the destination journal.
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id',
                                  store=True, precompute=True, tracking=True)
    destination_currency_id = fields.Many2one('res.currency', string='Destination Currency',
                                              compute='_compute_destination_currency_id', store=True, precompute=True)
    destination_amount = fields.Monetary(
        string='Destination Amount', currency_field='destination_currency_id',
        compute='_compute_destination_amount', store=True, readonly=False, precompute=True, tracking=True,
        help="Amount received in the destination journal currency. Computed from the exchange rate "
             "of the transfer date, it can be adjusted to the rate actually applied.")
    is_cross_currency = fields.Boolean(compute='_compute_is_cross_currency')
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 6), compute='_compute_exchange_rate',
                                 help="Destination currency units received for one unit of the source currency.")

    move_id = fields.Many2one('account.move', 'Journal Entry', index=True, copy=False)
    company_currency_id = fields.Many2one(string="Company Currency", related='company_id.currency_id')
    amount_company_currency_signed = fields.Monetary(
        string='Amount (Company Currency)', currency_field='company_currency_id',
        compute='_compute_amount_company_currency_signed', store=True)

    @api.depends('journal_id', 'company_id')
    def _compute_currency_id(self):
        for transfer in self:
            transfer.currency_id = transfer.journal_id.currency_id or transfer.company_id.currency_id

    @api.depends('destination_journal_id', 'company_id')
    def _compute_destination_currency_id(self):
        for transfer in self:
            transfer.destination_currency_id = transfer.destination_journal_id.currency_id or transfer.company_id.currency_id

    @api.depends('currency_id', 'destination_currency_id')
    def _compute_is_cross_currency(self):
        for transfer in self:
            transfer.is_cross_currency = transfer.currency_id != transfer.destination_currency_id

    @api.depends('amount', 'currency_id', 'destination_currency_id', 'date', 'company_id')
    def _compute_destination_amount(self):
        for transfer in self:
            if not transfer.currency_id or not transfer.destination_currency_id:
                transfer.destination_amount = transfer.amount
            else:
                transfer.destination_amount = transfer.currency_id._convert(
                    transfer.amount,
                    transfer.destination_currency_id,
                    transfer.company_id,
                    transfer.date or fields.Date.context_today(transfer),
                )

    @api.depends('amount', 'destination_amount')
    def _compute_exchange_rate(self):
        for transfer in self:
            transfer.exchange_rate = transfer.destination_amount / transfer.amount if transfer.amount else 0.0

    @api.depends('amount', 'destination_amount', 'currency_id', 'destination_currency_id', 'date', 'company_id')
    def _compute_amount_company_currency_signed(self):
        for transfer in self:
            transfer.amount_company_currency_signed = transfer._get_company_currency_balance()

    def _get_company_currency_balance(self):
        """ Value of the transfer in company currency. When one side of the transfer is in company
        currency its amount is the exact value, which keeps any manually negotiated rate. """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if not self.currency_id or self.currency_id == company_currency:
            return self.amount
        if self.destination_currency_id == company_currency:
            return self.destination_amount
        return self.currency_id._convert(
            self.amount,
            company_currency,
            self.company_id,
            self.date or fields.Date.context_today(self),
        )

    @api.constrains('journal_id', 'destination_journal_id')
    def _check_journals(self):
        for transfer in self:
            if transfer.journal_id == transfer.destination_journal_id:
                raise ValidationError(_("The source and destination journals must be different."))

  

    def _prepare_move_vals(self):
        """
        Prepare the values for creating an account move.
        """
        transer_journal = self.company_id.mgs_transfer_journal_id
        if not transer_journal:
            raise UserError(_("You can't create a new trasfer without an default transfer journal set on the company"))

        ref = 'Internal Transfer'

        if self.memo:
            ref += ": %s" % self.memo

        return [{
            'move_type': 'entry',
            'date': self.date,
            'journal_id': transer_journal.id,
            'company_id': self.company_id.id,
            'ref': ref,
            'name': '/'
        }]

    def _prepare_move_line_vals(self):
        for journal in (self.journal_id, self.destination_journal_id):
            if not journal.default_account_id:
                raise UserError(_("Please define a default account on the journal %s.", journal.display_name))

        balance = self.company_id.currency_id.round(self._get_company_currency_balance())
        destination_amount = self.destination_amount if self.is_cross_currency else self.amount
        partner_id = self.company_id.partner_id.id

        return [
            (0, 0, {
                'account_id': self.destination_journal_id.default_account_id.id,
                'partner_id': partner_id,
                'name': 'Transfer from %s' % self.journal_id.name,
                'currency_id': self.destination_currency_id.id,
                'amount_currency': destination_amount,
                'balance': balance,
                'date_maturity': self.date,
            }),
            (0, 0, {
                'account_id': self.journal_id.default_account_id.id,
                'partner_id': partner_id,
                'name': 'Transfer to %s' % self.destination_journal_id.name,
                'currency_id': self.currency_id.id,
                'amount_currency': -self.amount,
                'balance': -balance,
                'date_maturity': self.date,
            })
        ]

    def action_post(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("Only draft transfers can be posted."))
            if float_is_zero(r.amount_company_currency_signed, precision_rounding=r.company_id.currency_id.rounding):
                raise UserError(_("The transfer amount is too small to be recorded in the company currency."))

            if r.move_id:
                # Override the existing move
                move_id = r.move_id
                move_vals = r._prepare_move_vals()[0]
                move_vals['line_ids'] = r._prepare_move_line_vals()
                r.move_id.line_ids.unlink()
                r.move_id.write(move_vals)
                r.move_id.action_post()
            else:
                # Create a new move
                move_vals = r._prepare_move_vals()[0]
                move_vals['line_ids'] = r._prepare_move_line_vals()
                move_id = self.env['account.move'].sudo().create(move_vals)
                move_id.action_post()
                r.move_id = move_id.id

            r.write({
                'state': 'posted',
                'name': move_id.name
            })
        return True

    def action_cancel(self):
        for r in self:
            r.write({
                'state': 'cancel',
            })
            r.move_id.button_cancel()

    def action_reset_to_draft(self):
        for r in self:
            r.write({
                'state': 'draft',
            })
            r.move_id.button_draft()

    def button_open_journal_entry(self):
        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.move_id.id
        return action
