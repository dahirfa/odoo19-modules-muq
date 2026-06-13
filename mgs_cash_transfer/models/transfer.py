from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CashTransfer(models.Model):
    _name = 'mgs_cash_transfer.transfer'
    _description = 'Cash Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', copy=False, default='New')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    memo = fields.Char(string='Memo')
    journal_id = fields.Many2one('account.journal', string='Source Journal (From)', required=True, domain=[('type', 'in', ['cash', 'bank'])])
    destination_journal_id = fields.Many2one('account.journal', string='Dest.Journal (To)', required=True, domain=[('type', 'in', ['cash', 'bank'])])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', copy=False)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', domain=[(
        'active', '=', True)], default=lambda self: self.env.company.currency_id.id, tracking=True)

    move_id = fields.Many2one('account.move', 'Journal Entry', index=True, copy=False)
    company_currency_id = fields.Many2one(string="Company Currency", related='company_id.currency_id')
    amount_company_currency_signed = fields.Monetary(
        currency_field='company_currency_id', compute='_compute_amount_company_currency_signed', store=True)
    currency_rate = fields.Float(string='Currency Rate', related='currency_id.rate')
    override_rate = fields.Boolean(string='Override Rate')
    custom_rate = fields.Float(string='Custom Rate')
    show_rate = fields.Boolean(string='Show Rate', compute='_compute_show_rate')
    
    @api.depends('currency_id', 'company_id') 
    def _compute_show_rate(self): 
        for payment in self: 
            payment.show_rate = payment.currency_id != payment.company_id.currency_id

    def _update_currency_rate(self):
        if self.override_rate and self.currency_id.rate == self.custom_rate:
            return True  # Don't create anything

        if self.override_rate and self.custom_rate:
            currency_rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', self.currency_id.id),
                ('company_id', '=', self.company_id.id),
                ('name', '=', fields.Date.today())
            ], limit=1, order='name desc')
            if currency_rate:
                currency_rate.rate = self.custom_rate
            else:
                self.env['res.currency.rate'].create({
                    'currency_id': self.currency_id.id,
                    'rate': self.custom_rate,
                    'name': fields.Date.today(),
                    'company_id': self.company_id.id,
                })

    
    @api.depends('move_id.amount_total_signed', 'amount', 'currency_id', 'date', 'company_id', 'company_currency_id')
    def _compute_amount_company_currency_signed(self):
        for payment in self:
            payment.amount_company_currency_signed = payment.currency_id._convert(
                from_amount=payment.amount,
                to_currency=payment.company_currency_id,
                company=payment.company_id,
                date=payment.date,
            )

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency_id.id if self.journal_id.currency_id.id and self.journal_id.currency_id.id != self.company_currency_id.id else self.env.company.currency_id.id

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        self.custom_rate = self.currency_id.rate

    def _prepare_move_vals(self):
        """
        Prepare the values for creating an account move.
        """
        current_company = self.env.company
        transer_journal = current_company.mgs_transfer_journal_id
        if not transer_journal:
            raise UserError(_( "You can't create a new trasfer without an default transfer journal set on the company"))
        
        ref = 'Internal Transfer'

        if self.memo:
            ref += ": %s" % self.memo
        
        return [{
            'move_type': 'entry',
            'date': self.date,
            'journal_id': transer_journal.id,  
            'ref': ref,
            'name': '/'
        }]
    
    def _prepare_move_line_vals(self):
        current_company = self.env.company
        currency_id = self.currency_id.id

        # Use custom rate if override_rate is True and currencies differ
        if self.override_rate and self.company_currency_id != self.currency_id and self.custom_rate > 0:
            liquidity_balance = self.amount / self.custom_rate
        else:
            liquidity_balance = self.currency_id._convert(
                self.amount,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )

        move_line_vals = [
            (0, 0, {
                'account_id': self.destination_journal_id.default_account_id.id,
                'partner_id': current_company.partner_id.id,
                'name': 'Transfer from %s' % self.journal_id.name,
                'amount_currency': self.amount,
                'debit': liquidity_balance,
                'credit': 0.0,
                'date_maturity': self.date,
                'date': self.date,
                'currency_id': currency_id,
            }),
            (0, 0, {
                'account_id': self.journal_id.default_account_id.id,
                'partner_id': current_company.partner_id.id,
                'name': 'Transfer to %s' % self.destination_journal_id.name,
                'amount_currency': -self.amount,
                'debit': 0.0,
                'credit': liquidity_balance,
                'date_maturity': self.date,
                'date': self.date,
                'currency_id': currency_id,
            })
        ]

        return move_line_vals

    # def _prepare_move_line_vals(self):
    #     current_company = self.env.company
    #     liquidity_amount_currency = self.amount
    #     liquidity_balance = self.currency_id._convert(
    #             liquidity_amount_currency,
    #             self.company_id.currency_id,
    #             self.company_id,
    #             self.date,
    #         )
    #     currency_id = self.currency_id.id

    #     move_line_vals = [
    #         (0, 0, {
    #             'account_id': self.destination_journal_id.default_account_id.id,  # Bank/Cash account
    #             'partner_id': current_company.partner_id.id,
    #             'name': 'Transfer from %s' % self.journal_id.name,
    #             'amount_currency': liquidity_amount_currency,
    #             'debit': liquidity_balance,
    #             'credit': 0.0,
    #             'date_maturity': self.date,
    #             'date': self.date,
    #             'currency_id': currency_id,
    #         }),
    #         (0, 0, {
    #             'account_id': self.journal_id.default_account_id.id,  # A/R account
    #             'partner_id': current_company.partner_id.id,
    #             'name': 'Transfer to %s' % self.destination_journal_id.name,
    #             'amount_currency': liquidity_amount_currency * -1,
    #             'debit': 0.0,
    #             'credit': liquidity_balance,
    #             'date_maturity': self.date,
    #             'date': self.date,
    #             'currency_id': currency_id,
    #         })
    #     ]

    #     return move_line_vals
    
    def action_post(self):
        for r in self:
            # if r.override_rate and not r.custom_rate:
            #     raise UserError(_("Please enter a custom rate to override the current rate."))
            # if r.override_rate and r.custom_rate:
            #     r._update_currency_rate()

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