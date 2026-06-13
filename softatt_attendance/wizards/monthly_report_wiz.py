from datetime import datetime, time, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO
from odoo.tools import date_utils
import logging
_logger = logging.getLogger(__name__)



class SaMonthlyReportWiz(models.TransientModel):
    _name = 'sa.monthly.report'
    _description = 'Monthly Report Wizard'
    
    group_by        = fields.Selection([('date', 'Date'),
                                        ('location', 'Location'),
                                        ('department', 'Department'),
                                        ('shift', 'Shift')], default='date')
    date_from       = fields.Date(string="From",default=lambda self: fields.Date.today().replace(day=1), required=True)
    date_to         = fields.Date(string="To",default=lambda self: fields.Date.today(), required=True)
    location_ids            = fields.Many2many('hr.work.location')
    department_ids          = fields.Many2many('hr.department')
    resource_calendar_ids   = fields.Many2many('resource.calendar')
    employee_ids            = fields.Many2many('hr.employee')
    
    include_absence         = fields.Boolean(default=True)
    include_deductions      = fields.Boolean(default=False)
    include_late_minutes    = fields.Boolean(default=True)
    
    datas                   = fields.Binary('File', readonly=True)
    
    def action_confirm(self):
        s, e = date_utils._softatt_get_span_dates(self.date_from, self.date_to, self.env.user.tz)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                "group_by"              : self.group_by,
                
                "date_from"             : s,
                "date_to"               : e,
                
                "include_absence"       : self.include_absence,
                "include_deductions"    : self.include_deductions,
                "include_late_minutes"  : self.include_late_minutes,
                
                "_from"                 : self.date_from,
                "_to"                   : self.date_to,
                       
                "location_ids"          : self.location_ids.read(['name']),
                "department_ids"        : self.department_ids.read(['name']),
                "shift_ids"             : self.resource_calendar_ids.read(['name']),
                "employee_ids"          : self.employee_ids.read(['name']),
            },
        }
        return self.env.ref('softatt_attendance.action_monthly_report').report_action(self, data=data)

class SaDailyReport(models.AbstractModel):
    _name = 'report.softatt_attendance.sa_monthly_report'
    _description = 'Monthly Report'

    def _emp_domain(self, location_ids, department_ids, shift_ids, employee_ids):
        locations       =   [location_id['id'] for location_id in location_ids]
        departments     =   [department_id['id'] for department_id in department_ids]
        shifts          =   [shift_id['id'] for shift_id in shift_ids]
        employees       =   [employee_id['id'] for employee_id in employee_ids]
        domain          = []
        if locations:
            domain.append(('location_id.id','in',locations))
        if departments:
            domain.append(('department_id.id','in',departments))
        if shifts:
            domain.append(('resource_calendar_id.id','in',shifts))
        if employees:
            domain.append(('id','in',employees))
        return domain
    
    def _get_dates(self, s, e):
        date_range = [[s + timedelta(days=x), 
                       date_utils._softatt_localize(s + timedelta(days=x), self.env.user.tz).date()] for x in range((e - s).days + 1)]
        return date_range

    def _emp_vals(self, employee_id, data):
        domain          = [('employee_id','=', employee_id),
                           ('check_in'   , '>=', data['form']['date_from']),
                           ('check_in'   , '<=', data['form']['date_to'])]
        att_lines       =   self.env['hr.attendance'].search(domain)
        result = {'worked_hours': sum(att_lines.mapped('worked_hours'))}
        
        if data['form']['include_absence']:
            absence     = 0
            report      = self.env['report.softatt_attendance.absence_report']
            date_from   = datetime.strptime(data['form']['_from'], '%Y-%m-%d')
            date_to     = datetime.strptime(data['form']['_to'], '%Y-%m-%d')
            
            for date in self._get_dates(date_from, date_to):                
                absence += len(report._lines(str(date[0]), [], [], [], [{'id':employee_id}]).ids)
            result.update({'absence': int(absence)})
            
        if data['form']['include_deductions']:
            result.update({'deductions': sum(att_lines.filtered(lambda x: x.waved==False).mapped('penalty_amount'))})
            
        if data['form']['include_late_minutes']:
            result.update({'late_minutes': sum(att_lines.mapped('late_minutes'))})
        return result
    
    
    def _emp_lines(self, location_ids, department_ids, shift_ids, employee_ids):
        domain          =  self._emp_domain(location_ids, department_ids, shift_ids, employee_ids)
        emp_lines       =   self.env['hr.employee'].search(domain)
        return emp_lines
            
    @api.model
    def _get_report_values(self, docids, data=None):
        model   = self.env.context.get('active_model')
        docs    = self.env[model].browse(self.env.context.get('active_id'))
        user_tz = self.env.user.tz
        return {
            "doc_ids"           : self.ids,
            "doc_model"         : model,
            "docs"              : docs,
            "data"              : data,
            "group_by"          : data['form']['group_by'],
            "date_from"         : data['form']['date_from'],
            "date_to"           : data['form']['date_to'],
            "_from"             : data['form']['_from'],
            "_to"               : data['form']['_to'],
            "location_ids"      : data['form']['location_ids'],
            "department_ids"    : data['form']['department_ids'],
            "shift_ids"         : data['form']['shift_ids'],
            "include_absence"       : data['form']['include_absence'],
            "include_deductions"    : data['form']['include_deductions'],
            "include_late_minutes"  : data['form']['include_late_minutes'],
            "employee_ids"          : data['form']['employee_ids'],
            "emp_lines"             : self._emp_lines,
            "emp_vals"              : self._emp_vals,
            "tz"                    : user_tz,
        }