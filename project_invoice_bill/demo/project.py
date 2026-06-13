# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    @api.one
    @api.depends('bill_ids')
    def _compute_bill(self):
        self.bill_count = len(self.env["account.invoice"].search(
            [("id",
              "in",
              [c.id for c in self.bill_ids])]))



    # invoice_count = fields.Integer(compute="_compute_invoice", string='# of Invoices', copy=False, default=0, store=True)
    # invoice_ids = fields.One2many('account.invoice', 'project_id', compute="_compute_invoice", string='Bills', copy=False, store=True)

    bill_count = fields.Integer(compute="_compute_bill", string='# of Bills', copy=False, default=0, store=True)
    bill_ids = fields.Many2many('account.invoice', compute="_compute_bill", string='Bills', copy=False, store=True)



    @api.multi
    def bill_create(self):
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]

        result['context'] = {'type': 'in_invoice'}

        journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
         ]

        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)

        if default_journal_id:
            result['context']['default_journal_id'] = default_journal_id.id

        result['context']['default_origin'] = self.name
        result['context']['default_partner_id'] = self.partner_id.id
        result['context']['default_project_id'] = self.id

        result['domain'] = "[('project_id', '=', " + str(self.id) + ")]"

        print('--------------')
        print(self.bill_ids)

        return result




