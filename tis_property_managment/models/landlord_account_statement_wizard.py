import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LandlordAccountStatementWizard(models.TransientModel):
    _name = "pm.landlord.account.statement.wizard"

    landlord_id = fields.Many2one('res.partner',domain=[('is_landlord', '=', True)],required=True)
    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def print_landlord_account_statement(self):
        start_date=self.read()[0].get('start_date')
        end_date=self.read()[0].get('end_date')
        landlord=self.read()[0].get('landlord_id')[0]



        # landlord_obj=self.env['res.partner'].search([('id','=',landlord)])
        # landlord_receivable=landlord_obj.property_account_receivable_id.id
        # landlord_payable=landlord_obj.property_account_payable_id.id

        if start_date > end_date:
            raise ValidationError('Start-date must be before End-date')
        else:
            domain=[('date','>=',str(start_date)),('date','<=',str(end_date)),('display_type','in',('product','line_section','line_note')),('reconciled','=',False),('partner_id','=',landlord)]
        if self.company_id:
            domain.append(('company_id.id','=',self.company_id.id))
        account_move_line_obj=self.env['account.move.line'].search_read(domain, order="date")



        data = {'form': self.read()[0],'account_move_line':account_move_line_obj}
        
        return self.env.ref('tis_property_managment.actiont_landlord_account_statment_report').with_context(landscape=False).report_action(self, data=data)
