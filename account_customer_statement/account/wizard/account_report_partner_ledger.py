# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountPartnerLedger(models.TransientModel):
	_inherit = "account.common.partner.report"
	_name = "account.report.partner.ledger"
	_description = "Account Partner Ledger"

	amount_currency = fields.Boolean("With Currency", help="It adds the currency column on report if the currency differs from the company currency.")
	reconciled = fields.Boolean('Reconciled Entries')
	report_type = fields.Selection([('summary', 'Summary'), ('detail', 'Detail')],string="Report Type", default='summary')

	def _print_report(self, data):
		data = self.pre_print_report(data)
		data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency, 'report_type': self.report_type})
		print ("data------------------------------------",data)
		return self.env.ref('account_customer_statement.action_report_partnerledger').report_action(self, data=data)
#        return self.env.ref('account_customer_statement.action_report_partnerledgercustomer').report_action(self, data=data)
