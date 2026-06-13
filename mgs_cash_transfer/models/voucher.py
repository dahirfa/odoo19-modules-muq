from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MGSCashTransferVoucher(models.Model):
    _name = 'mgs_cash_transfer.voucher'
    _description = 'Cash Transfer Voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', default='/', copy=False)
    voucher_type = fields.Selection([('in', 'In'), ('out', 'Out')], string='Voucher Type', required=True)
    date = fields.Date(string='Pay Date', default=fields.Date.today)
    amount = fields.Float(string='Pay Amount', required=True)
    memo = fields.Char(string='Reference')
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancel')], string='State', default='draft')
    journal_id = fields.Many2one('account.journal', string='Journal', domain=[('type', 'in', ['bank', 'cash'])])
    move_id = fields.Many2one('account.move', string='Journal Entry')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    voucher_line_ids = fields.One2many('mgs_cash_transfer.voucher.line', 'voucher_id', string='Voucher Lines')
    memo = fields.Char(string="Memo")

    @api.constrains('amount', 'voucher_line_ids')
    def _check_amount(self):
        for record in self:
            total_line_amount = sum(line.amount for line in record.voucher_line_ids)
            if record.amount != total_line_amount:
                raise ValidationError('The total amount must be equal to the sum of the voucher line amounts.')

    def _prepare_move_vals(self):
        """
        Prepare the values for creating an account move.
        """
        ref = 'Payment Voucher' if self.voucher_type == 'in' else 'Receipt Voucher'

        if self.memo:
            ref += ": %s" % self.memo
        
        return [{
            'move_type': 'entry',
            'date': self.date,
            'journal_id': self.journal_id.id,  
            'ref': ref,
            'name': '/',
            'company_id': self.env.company.id
        }]
    
    def _prepare_move_line_vals(self):
        current_company = self.env.company
        liquidity_amount_currency = self.amount
        liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
        currency_id = self.currency_id.id
        move_line_vals = []
        journal_id = self.journal_id
        if self.voucher_type == 'in':
            move_line_vals.append((0, 0, {
                'account_id': journal_id.default_account_id.id,  # Bank/Cash account
                'name': self.memo,
                'amount_currency': liquidity_amount_currency,
                'debit': liquidity_balance,
                'credit': 0.0,
                'date_maturity': self.date,
                'date': self.date,
                'currency_id': currency_id,
                'company_id': current_company.id
            }))

        current_company = self.env.company
        for line in self.voucher_line_ids:
            line_amount_currency = line.amount
            line_balance = self.currency_id._convert(
                    liquidity_amount_currency,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
            
            rec = {
                'account_id': line.account_id.id,  # Bank/Cash account
                'partner_id': line.partner_id.id,
                'name': line.name,
                'date_maturity': self.date,
                'date': self.date,
                'currency_id': currency_id,
            }

            if line.analytic_distribution:
                rec.update ({'analytic_distribution': {str(line.analytic_distribution.id): 100},})

            if self.voucher_type == 'in':
                rec.update ({
                    'credit': line_balance,
                    'debit': 0,
                    'amount_currency': line_amount_currency * -1
                })
            else:
                rec.update ({
                    'debit': line_balance,
                    'credit': 0,
                    'amount_currency': line_amount_currency
                })

            move_line_vals.append((0, 0, rec))

        if self.voucher_type == 'out':
            move_line_vals.append((0, 0, {
                'account_id': journal_id.default_account_id.id,  # Bank/Cash account
                'name': self.memo,
                'amount_currency': liquidity_amount_currency * -1,
                'credit': liquidity_balance,
                'debit': 0.0,
                'date_maturity': self.date,
                'date': self.date,
                'currency_id': currency_id,
                'company_id': current_company.id
            }))
        
        return move_line_vals
    
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
    amount = fields.Float(string='Amount', required=True)

    @api.constrains('account_id', 'partner_id', 'analytic_distribution')
    def _check_account_partner_analytic(self):
        for record in self:
            if record.account_id.account_type in ['asset_receivable', 'liability_payable'] and not record.partner_id:
                raise ValidationError("Partner is required for accounts of type 'Receivable' or 'Payable'.")
            if record.account_id.account_type in ['income', 'income_other', 'expense_direct_cost', 'expense_depreciation', 'expense'] and not record.analytic_distribution:
                raise ValidationError("Analytic Distribution is required for accounts of type 'Income' 'Expense' accounts.")

