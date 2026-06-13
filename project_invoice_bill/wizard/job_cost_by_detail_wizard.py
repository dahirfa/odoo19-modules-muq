# -*- coding: utf-8 -*-

from odoo import models, fields, api


class JobCostByDetailWizard(models.TransientModel):
    _name = 'project_invoice_bill.job_cost_by_detail_wizard'


    project_id = fields.Many2one('project.project')
    partner_id = fields.Many2one('res.partner')
    date_from = fields.Date('From')
    date_to = fields.Date('To')
    debit_or_credit = fields.Selection([
        ('all', 'All'),
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ], default='all', string='Debit/Credit')

    summary_or_detail = fields.Selection([
        ('summary', 'Summary'),
        ('detail', 'Detail'),
    ], default='summary', string='Type')

    sort = fields.Selection([
        ('name', 'Name'),
        ('id', 'Id'),
    ], default='name', string='Sort by')






    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {

                'project_id': self.project_id.id,
                'project_name': self.project_id.name,
                'partner_id': self.partner_id.id,
                'partner_name': self.partner_id.name,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'debit_or_credit': self.debit_or_credit,
                'summary_or_detail': self.summary_or_detail,
                'sort': self.sort
            },
        }

        return self.env.ref('project_invoice_bill.action_job_cost_by_detail_wizard').report_action(self, data=data)






class InvoicesByAmountReport(models.AbstractModel):
    _name = "report.project_invoice_bill.job_cost_by_detail_wizard_report"


    @api.model
    def get_report_values(self, docids, data=None):

        project_id = data['form']['project_id']
        project_name = data['form']['project_name']
        partner_id = data['form']['partner_id']
        partner_name = data['form']['partner_name']
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        debit_or_credit = data['form']['debit_or_credit']
        summary_or_detail = data['form']['summary_or_detail']
        sort = data['form']['sort']


        docs = []

        project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ])
        total = sum(line.project_id.total_debit_credit for line in project)

        'Get id as an integer'
        if project_id:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('project_id', '=', project_id)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        if date_from:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('date_invoice', '>=', date_from)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        if date_to:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('date_invoice', '<=', date_to)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        if date_from and date_to:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('date_invoice', '>=', date_from),
                                                          ('date_invoice', '<=', date_to)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)


        if partner_id:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('project_id.partner_id', '=', partner_id)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        if partner_id and date_from:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('project_id.partner_id', '=', partner_id),
                                                          ('date_invoice', '>=', date_from)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        if partner_id and date_to:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('project_id.partner_id', '=', partner_id),
                                                          ('date_invoice', '<=', date_to)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        if partner_id and date_from and date_to:
            project = self.env['account.invoice'].search([('move_type', '=', 'out_invoice'), ('project_id.partner_id', '=', partner_id),
                                                          ('date_invoice', '>=', date_from),
                                                          ('date_invoice', '<=', date_to)], order=str(sort) + ' asc')
            total = sum(line.project_id.total_debit_credit for line in project)

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'project_id': project_id,
            'partner_id': partner_id,
            'project_name': project_name,
            'partner_name': partner_name,
            'date_from': date_from,
            'date_to': date_to,
            'debit_or_credit': debit_or_credit,
            'summary_or_detail': summary_or_detail,
            'total': total,
            'project':project,
        }
