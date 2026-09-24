import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LandlordSummary(models.TransientModel):
    _name = "pm.landlord.statement.wizard.report"


    landlord_id = fields.Many2one('res.partner',domain=[('is_landlord', '=', True)],required=True)
    parent_property_ids=fields.Many2many('pm.property.parent')
    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    def print_landlord_statement(self):
        start_date=self.read()[0].get('start_date')
        end_date=self.read()[0].get('end_date')
        landlord=self.read()[0].get('landlord_id')[0]
        parent_property_ids=self.read()[0].get('parent_property_ids')

        if start_date > end_date:
            raise ValidationError('Start Date Must Be Before End Date')
        else:
            domain=[('date','>=',str(start_date)),('date','<=',str(end_date)),('tenancy_id.state','=','in_progress'),('landlord_id','=',landlord)]
        if parent_property_ids:
            domain.append(('tenancy_id.property_id.parent_property_id.id','in',tuple(parent_property_ids)))
        if self.company_id:
            domain.append(('company_id.id','=',self.company_id.id))
        rent_schedule_obj=self.env['pm.rent.schedule'].search_read(domain)


        data = {
            'form': self.read()[0],
            'rent_schedule':rent_schedule_obj,
        }
        return self.env.ref('tis_property_managment.actiont_landlord_summary_report').with_context(landscape=False).report_action(self, data=data)
