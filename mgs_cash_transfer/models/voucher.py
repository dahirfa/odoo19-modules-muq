from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MGSCashTransferVoucher(models.Model):
    _name = 'mgs_cash_transfer.voucher'
    _description = 'Cash Transfer Voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Name', default='/', copy=False)
    voucher_type = fields.Selection([('in', 'In'), ('out', 'Out')], string='Voucher Type', required=True)
    date = fields.Date(string='Pay Date', default=fields.Date.today)
    amount = fields.Monetary(string='Pay Amount', required=True, currency_field='currency_id')
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancel')], string='State', default='draft')
    journal_id = fields.Many2one('account.journal', string='Journal', check_company=True, domain=[('type', 'in', ['bank', 'cash'])])
    move_id = fields.Many2one('account.move', string='Journal Entry')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id',
                                  store=True, readonly=False, precompute=True)
    voucher_line_ids = fields.One2many('mgs_cash_transfer.voucher.line', 'voucher_id', string='Voucher Lines')
    memo = fields.Char(string="Memo")

    @api.depends('journal_id', 'company_id')
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.journal_id.currency_id or record.company_id.currency_id

    @api.constrains('amount', 'voucher_line_ids')
    def _check_amount(self):
        for record in self:
            total_line_amount = sum(line.amount for line in record.voucher_line_ids)
            if record.currency_id.compare_amounts(record.amount, total_line_amount) != 0:
                raise ValidationError(_('The total amount must be equal to the sum of the voucher line amounts.'))

    @api.constrains('currency_id', 'journal_id')
    def _check_currency(self):
        for record in self:
            if record.journal_id.currency_id and record.currency_id != record.journal_id.currency_id:
                raise ValidationError(_(
                    "The journal %(journal)s only accepts %(currency)s, the voucher currency must match it.",
                    journal=record.journal_id.display_name,
                    currency=record.journal_id.currency_id.name,
                ))

    def _prepare_move_vals(self):
        """
        Prepare the values for creating an account move.
        """
        ref = 'Receipt Voucher' if self.voucher_type == 'in' else 'Payment Voucher'

        if self.memo:
            ref += ": %s" % self.memo
        
        return [{
            'move_type': 'entry',
            'date': self.date,
            'journal_id': self.journal_id.id,  
            'ref': ref,
            'name': '/',
            'company_id': self.company_id.id
        }]
    
    def _prepare_move_line_vals(self):
        company_currency = self.company_id.currency_id
        date = self.date or fields.Date.context_today(self)
        currency_id = self.currency_id.id
        journal_id = self.journal_id
        sign = -1 if self.voucher_type == 'in' else 1

        # Convert every line on its own and balance the liquidity line with their sum, so the
        # entry stays balanced in company currency whatever the rounding of each conversion.
        counterpart_vals = []
        total_balance = 0.0
        for line in self.voucher_line_ids:
            line_balance = self.currency_id._convert(line.amount, company_currency, self.company_id, date)
            total_balance += line_balance

            rec = {
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'name': line.name,
                'date_maturity': self.date,
                'currency_id': currency_id,
                'amount_currency': sign * line.amount,
                'balance': sign * line_balance,
            }

            if line.analytic_distribution:
                rec.update ({'analytic_distribution': {str(line.analytic_distribution.id): 100},})

            counterpart_vals.append((0, 0, rec))

        liquidity_vals = (0, 0, {
            'account_id': journal_id.default_account_id.id,  # Bank/Cash account
            'name': self.memo,
            'date_maturity': self.date,
            'currency_id': currency_id,
            'amount_currency': -sign * self.amount,
            'balance': -sign * company_currency.round(total_balance),
        })

        if self.voucher_type == 'in':
            return [liquidity_vals] + counterpart_vals
        return counterpart_vals + [liquidity_vals]

    def action_post(self):
        for r in self:
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

class MGSCashTransferVoucherLine(models.Model):
    _name = 'mgs_cash_transfer.voucher.line'
    _description = 'Cash Transfer Voucher Line'

    name = fields.Char(string='Description')
    voucher_id = fields.Many2one('mgs_cash_transfer.voucher', string='Voucher', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    analytic_distribution = fields.Many2one('account.analytic.account', string='Analytic Distribution')
    analytic_precision = fields.Integer()
    currency_id = fields.Many2one(related='voucher_id.currency_id')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')

    @api.constrains('account_id', 'partner_id', 'analytic_distribution')
    def _check_account_partner_analytic(self):
        for record in self:
            if record.account_id.account_type in ['asset_receivable', 'liability_payable'] and not record.partner_id:
                raise ValidationError("Partner is required for accounts of type 'Receivable' or 'Payable'.")
            if record.account_id.account_type in ['income', 'income_other', 'expense_direct_cost', 'expense_depreciation', 'expense'] and not record.analytic_distribution:
                raise ValidationError("Analytic Distribution is required for accounts of type 'Income' 'Expense' accounts.")

