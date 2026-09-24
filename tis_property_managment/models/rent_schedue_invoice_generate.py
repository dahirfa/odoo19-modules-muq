import datetime
from odoo.exceptions import ValidationError
from odoo import models, fields, api


class RentScheduleGenerateInvoice(models.TransientModel):
    _name = "pm.rent.schedule.generate.invoice.wizard"

    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def create_entries_(self):
        start_date=self.read()[0].get('start_date')
        end_date=self.read()[0].get('end_date')
        if start_date > end_date:
            raise ValidationError('Start Date Must Be Before End Date')
        else:
            domain=[('date','>=',str(start_date)),('date','<=',str(end_date)),('invoice_id','=',False),('tenancy_id.state','=','in_progress')]
        if self.company_id:
            domain.append(('company_id.id','=',self.company_id.id))
        rent_schedule_obj=self.env['pm.rent.schedule'].search(domain,limit=50)
        for line in rent_schedule_obj:
            line.create_entries()

    # def _generate_invoice(self):
    #     print("Button Invoice")
