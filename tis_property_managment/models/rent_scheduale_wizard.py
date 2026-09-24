import datetime
from email.policy import default
from tracemalloc import DomainFilter

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class RentScheduleReport(models.TransientModel):
    _name = "pm.rent.scheduale.report.wizard"




    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    landlord_id = fields.Many2one('res.partner', string="Landlord", domain=[('is_landlord', '=', True)], store=True)
    parent_property_ids = fields.Many2many('pm.property.parent')
    property_ids = fields.Many2many('pm.property')
    info=fields.Selection([('detailed','Detailed'),
    ('regular','Regular')],default='regular')

    search_with=fields.Selection([('parent','By Parent'),
    ('property','By Property')],default='parent')
    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    contract_status = fields.Selection([('in_progress', 'In Progress'),('closed', 'Closed')], default='in_progress')

    def view_report(self):
        search_with=self.read()[0].get('search_with')
        landlord_id=self.read()[0].get('landlord_id')
        parent_property_ids=self.read()[0].get('parent_property_ids')
        property_ids=self.read()[0].get('property_ids')
        start_date=self.read()[0].get('start_date')
        end_date=self.read()[0].get('end_date')
        info=self.read()[0].get('info')

        # where=None
        # order_by=None
        # if start_date and end_date:
        #     where ="WHERE date BETWEEN " + start_date + " " + "AND" + " " + end_date
        # if parent_property_ids:
        #     where += " pmp.parent_property_id IN ("+ parent_property_ids +")"
        #     order_by="pmp.parent_property_id,"
        select="""
            SELECT	
            pmp.display_name property_name,
            rp_t.name tenant,
            pmt.end_date end_date,
            rp_t.phone phone,
            pmt.code tenancy,
            pmrs.date due_date,
            rp_l.name landlord,
            pmrs.amount rent_amount,
            pmrs.mgmt_comm mgmt_comm,
            pmrs.landlord_amount landlord_amount,
            pmrs.total_services_price _others,
            CASE
            WHEN am.payment_state = 'not_paid' THEN 'Not Paid'
            WHEN am.payment_state in ('paid','in_payment')THEN 'Paid'
            WHEN am.payment_state = 'partial' THEN 'Partially Paid'
            WHEN am.payment_state is NULL THEN 'Not Invoiced'
            END inv_status,
            am.amount_residual amount_residual,
            COALESCE(am.amount_total - am.amount_residual,0) as amount_paid"""
            
        From=""" 
            FROM pm_rent_schedule pmrs
            LEFT JOIN pm_tenancy pmt ON pmt.id= pmrs.tenancy_id
            LEFT JOIN pm_property pmp ON pmp.id=pmrs.property_id
            LEFT JOIN res_partner rp_t ON rp_t.id=pmrs.tenant_id
            LEFT JOIN res_partner rp_l ON rp_l.id=pmrs.landlord_id
            LEFT JOIN account_move am ON am.id=pmrs.invoice_id"""
        where=""
        order_by=""
        if start_date and end_date:
            where =" WHERE pmrs.active=True AND pmrs.date BETWEEN '" + str(start_date) + "' " + "AND" + " '" + str(end_date) + "' "
            order_by=" ORDER BY pmrs.date"
        if landlord_id:
            where += " AND rp_l.id = " + str(landlord_id[0])
        if parent_property_ids and len(parent_property_ids) > 1:
            where += " AND pmp.parent_property_id IN "+ str(tuple(parent_property_ids))
            order_by = " ORDER BY pmp.parent_property_id, pmrs.date"
        if parent_property_ids and len(parent_property_ids) == 1:
            where += " AND pmp.parent_property_id IN ("+ str(parent_property_ids[0])+")"
            order_by = " ORDER BY pmp.parent_property_id, pmrs.date"


        if property_ids and len(property_ids) > 1:
            where += " AND pmp.id IN "+ str(tuple(property_ids))
            order_by = " ORDER BY pmp.id, pmrs.date"
        if property_ids and len(property_ids) == 1:
            where += " AND pmp.id IN ("+ str(property_ids[0])+")"
            order_by = " ORDER BY pmp.id, pmrs.date"
        if self.contract_status == 'in_progress':
            where +=" AND pmt.state = 'in_progress'"
        if self.contract_status == 'closed':
            where +=" AND pmt.state = 'close'"
        where +=" AND pmrs.company_id = %s" % self.company_id.id if self.company_id else None
        query=select+ From + where + order_by
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()

        # if start_date > end_date:
        #     raise ValidationError('Start Date Must Be Before End Date')
        # else:
        #     domain=[('date','>=',str(start_date)),('date','<=',str(end_date)),('tenancy_id.state','=','in_progress'),('property_id.parent_property_id','in',parent_property_ids)]
        # rent_schedule_obj=self.env['pm.rent.schedule'].search_read(domain)
        data = {
            'form': self.read()[0],
            'rent_schedule':res
        }
        return self.env.ref('tis_property_managment.actiont_rent_scheduale_report').with_context(landscape=True).report_action(self, data=data)