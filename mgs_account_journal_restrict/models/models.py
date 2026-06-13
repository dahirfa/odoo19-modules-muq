# -*- coding: utf-8 -*-

from odoo import fields, models, api

class Users(models.Model):
    _inherit = 'res.users'

    journal_ids = fields.Many2many(
        'account.journal',
        'users_journals_restrict',
        'user_id',
        'journal_id',
        'Allowed Journals',
    )

    def write(self, vals):
        if 'journal_ids' in vals:
            self.env.registry.clear_cache()
        return super(Users, self).write(vals)
    

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _get_batch_available_journals(self, batch_result):
        """Override to apply journal restrictions for users in the journal restriction group."""
        # Check if the user is in the restricted group
        if self.env.user.has_group('mgs_account_journal_restrict.journal_restrict_group'):
            payment_type = batch_result['payment_values']['payment_type']
            company = batch_result['lines'].company_id
            # Fetch only the journals assigned to the current user
            journals = self.env['account.journal'].search([
                ('id', 'in', self.env.user.journal_ids.ids),
                *self.env['account.journal']._check_company_domain(company),
                ('type', 'in', ('bank', 'cash', 'credit')),
            ])
            # Apply the same filtering as the original method
            if payment_type == 'inbound':
                return journals.filtered('inbound_payment_method_line_ids')
            else:
                return journals.filtered('outbound_payment_method_line_ids')
        else:
            # If the user is not restricted, run the original method
            return super(AccountPaymentRegister, self)._get_batch_available_journals(batch_result)
        

    @api.model
    def _get_batch_journal(self, batch_result):
        """Override to apply journal restrictions for users in the restricted group.

        :param batch_result:    A batch computed by '_compute_batches'.
        :return:                An account.journal record.
        """
        payment_values = batch_result['payment_values']
        foreign_currency_id = payment_values['currency_id']
        partner_bank_id = payment_values['partner_bank_id']
        company = min(batch_result['lines'].company_id, key=lambda c: len(c.parent_ids))

        # Build default domain
        default_domain = [
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', ('bank', 'cash', 'credit')),
            ('id', 'in', self.available_journal_ids.ids),
        ]

        # Add journal restriction if the user is in the restricted group
        if self.env.user.has_group('mgs_account_journal_restrict.journal_restrict_group'):
            default_domain.append(('id', 'in', self.env.user.journal_ids.ids))

        # Define additional domains for currency and partner bank
        currency_domain = [('currency_id', '=', foreign_currency_id)]
        partner_bank_domain = [('bank_account_id', '=', partner_bank_id)]

        if partner_bank_id:
            extra_domains = (
                currency_domain + partner_bank_domain,
                partner_bank_domain,
                currency_domain,
                [],
            )
        else:
            extra_domains = (
                currency_domain,
                [],
            )

        # Search for a matching journal
        for extra_domain in extra_domains:
            journal = self.env['account.journal'].search(default_domain + extra_domain, limit=1)
            if journal:
                return journal

        # Return an empty journal record if no match is found
        return self.env['account.journal']
        

    @api.depends('available_journal_ids')
    def _compute_journal_id(self):
        for wizard in self:
            if self.env.user.has_group('mgs_account_journal_restrict.journal_restrict_group'):
                wizard.journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(wizard.company_id),
                        ('type', 'in', ('bank', 'cash', 'credit')),
                        ('id', 'in', self.env.user.journal_ids.ids)
                    ], limit=1)
            else:
                move_payment_method_lines = wizard.line_ids.move_id.preferred_payment_method_line_id
                if move_payment_method_lines and len(move_payment_method_lines) == 1:
                    wizard.journal_id = move_payment_method_lines.journal_id
                elif wizard.can_edit_wizard:
                    batch = wizard.batches[0]
                    wizard.journal_id = wizard._get_batch_journal(batch)
                else:
                    wizard.journal_id = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(wizard.company_id),
                        ('type', 'in', ('bank', 'cash', 'credit')),
                        ('id', 'in', self.available_journal_ids.ids)
                    ], limit=1)
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('company_id')
    def _compute_journal_id(self):
        for payment in self:
            company = self.company_id or self.env.company
            if not self.env.user.has_group('mgs_account_journal_restrict.journal_restrict_group'):
                payment.journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', 'in', ['bank', 'cash', 'credit']),
                ], limit=1)
            else:
                payment.journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', 'in', ['bank', 'cash', 'credit']), ('id', 'in', self.env.user.journal_ids.ids),
                ], limit=1)

    @api.depends('payment_type')
    def _compute_available_journal_ids(self):
        """
        Get all journals having at least one payment method for inbound/outbound depending on the payment_type.
        """
        if self.env.user.has_group('mgs_account_journal_restrict.journal_restrict_group'):
            journals = self.env['account.journal'].search([
                '|',
                ('company_id', 'parent_of', self.env.company.id),
                ('company_id', 'child_of', self.env.company.id),
                ('type', 'in', ('bank', 'cash')),
                ('id', 'in', self.env.user.journal_ids.ids)
            ])
        else:
            journals = self.env['account.journal'].search([
                '|',
                ('company_id', 'parent_of', self.env.company.id),
                ('company_id', 'child_of', self.env.company.id),
                ('type', 'in', ('bank', 'cash')),
            ])
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.available_journal_ids = journals.filtered('inbound_payment_method_line_ids')
            else:
                pay.available_journal_ids = journals.filtered('outbound_payment_method_line_ids')


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _get_action_dict(self):
        """Modify the Accounting Dashboard and other accounting-related actions dynamically"""
        action = super()._get_action_dict()
        user = self.env.user
        journal_restrict_group = user.has_group('mgs_account_journal_restrict.journal_restrict_group')

        # Define actions that need journal restrictions
        restricted_actions = {
            "account.open_account_journal_dashboard_kanban": ('id', user.journal_ids.ids),
            "account.action_move_out_invoice_type": ('journal_id', user.journal_ids.ids),
            "account.action_move_in_invoice_type": ('journal_id', user.journal_ids.ids),
            "account.action_move_journal_line": ('journal_id', user.journal_ids.ids),
        }

        # Check if the current action needs restriction
        for action_xml_id, (field_name, allowed_values) in restricted_actions.items():
            if action.get("id") == self.env.ref(action_xml_id).id and journal_restrict_group:
                action['domain'] = [(field_name, 'in', allowed_values)]

        # Ensure the Accounting Dashboard action has the correct context
        if action.get("id") == self.env.ref("account.open_account_journal_dashboard_kanban").id:
            action['context'] = {'search_default_dashboard': 1}
            

        return action

