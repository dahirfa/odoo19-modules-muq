# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, string="Currency")
    
    bill_count = fields.Integer(compute='_compute_invoice', string='# of Bills', copy=False, default=0)
    journal_count = fields.Integer(compute='_compute_invoice', string='# of Journals', copy=False, default=0)
    total_bills = fields.Float('Total Bills',compute='_get_total_bills')#

    
    proj_date = fields.Date('Proj Date')
    debit_total = fields.Float()
    credit_total = fields.Float()
    total_debit_credit = fields.Float()

    invoice_count = fields.Integer(compute="_compute_invoice", string='# of Invoices', copy=False, default=0)

    total_qty = fields.Float('Total Quantities')
    total_price_unit = fields.Float('Total Unitts')

    total_invoices = fields.Float('Total Invoices',compute='_get_total_invoices')


    @api.depends('company_id')
    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id or self.env.user.company_id.currency_id
    

    def action_view_bills(self):
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.sudo().read()[0]
        result['context'] = {}
        result['context']['default_move_type'] = 'in_invoice'
        result['context']['default_analytic_account_id'] = self.account_id.id
        journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id)
         ]
        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)

        if default_journal_id:
            result['context']['default_journal_id'] = default_journal_id.id

        result['context']['default_invoice_origin'] = self.name
        result['context']['invoice_date'] = self.proj_date
        result['domain'] = "[('analytic_account_id', '=', " + str(self.account_id.id) + "), ('move_type', '=', 'in_invoice')]"
        return result

   

    def action_view_invoices(self):
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.sudo().read()[0]

        result['context'] = {}
        result['context']['default_move_type'] = 'out_invoice'
        result['context']['default_analytic_account_id'] = self.account_id.id
        journal_domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ]
        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
        if default_journal_id:
            result['context']['default_journal_id'] = default_journal_id.id

        result['context']['default_invoice_origin'] = self.name
        if self.partner_id:
            result['context']['default_partner_id'] = self.partner_id.id
        result['context']['invoice_date'] = self.proj_date
        result['domain'] = "[('analytic_account_id', '=', " + str(self.account_id.id) + "), ('move_type', '=', 'out_invoice')]"
        return result

    def action_view_journals(self):
        action = self.env.ref('account.action_move_journal_line')
        result = action.sudo().read()[0]

        result['context'] = {}
        result['context']['default_analytic_account_id'] = self.account_id.id
        result['context']['default_invoice_origin'] = self.name
       
        result['domain'] = "[('analytic_account_id', '=', " + str(self.account_id.id) + "), ('move_type', '=', 'entry')]"
        return result
    def cost_and_revenue(self):
        action = self.env.ref('analytic.account_analytic_line_action')
        result = action.sudo().read()[0]
        result['context'] = {}
        result['context']['default_account_id'] = self.account_id.id
        result['domain'] = "[('account_id', '=', " + str(self.account_id.id) +")]"
        return result

    def compute_invoice(self):
        for r in self:
            r.bill_count = self.env['account.move'].search_count([('analytic_account_id', '=', r.account_id.id), ('move_type', '=', 'in_invoice')])
            r.invoice_count = self.env["account.move"].search_count([('analytic_account_id', '=', r.account_id.id), ('move_type', '=', 'out_invoice')])
            r.journal_count = self.env["account.move"].search_count([('analytic_account_id', '=', r.account_id.id),('move_type', '=', 'entry')])
    @api.depends('account_id')
    def _compute_invoice(self):
        self.sudo()
        self.sudo().compute_invoice()

    def get_total_invoices(self):
        for r in self:
            invoices_obj = self.env['account.move']
            
            for r in self:
                inv=invoices_obj.search([('analytic_account_id', '=', r.account_id.id), ('move_type', '=', 'out_invoice')])
                r.total_invoices = 0.0
                total_invoices = 0
                if inv:
                    for invoice in inv:
                        if invoice.state != 'draft':
                            total_invoices += invoice.amount_total
                            r.total_invoices = total_invoices
    @api.depends('account_id')
    def _get_total_invoices(self):
        self.sudo()
        self.sudo().get_total_invoices()

    def get_total_bills(self):
        for r in self:
            invoices_obj = self.env['account.move']
            
            for r in self:
                inv=invoices_obj.search([('analytic_account_id', '=', r.account_id.id), ('move_type', '=', 'in_invoice')])
                r.total_bills = 0.0
                total_bills = 0
                if inv:
                    for bill in inv:
                        if bill.state != 'draft':
                            total_bills += bill.amount_total
                            r.total_bills = total_bills
    @api.depends('account_id')
    def _get_total_bills(self):
        self.sudo()
        self.sudo().get_total_bills()