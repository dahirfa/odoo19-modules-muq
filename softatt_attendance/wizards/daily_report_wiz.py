from datetime import datetime, time, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO
from odoo.tools import date_utils
import logging
_logger = logging.getLogger(__name__)



class SaDailyReportWiz(models.TransientModel):
    _name = 'sa.daily.report'
    _description = 'Daily Report Wizard'
    
    group_by        = fields.Selection([('date', 'Date'),
                                        ('location', 'Location'),
                                        ('department', 'Department'),
                                        ('shift', 'Shift')], default='date')
    date            = fields.Date(string="Date",default=lambda self: fields.Date.today(), required=True)
    location_ids      = fields.Many2many('hr.work.location')
    department_ids  = fields.Many2many('hr.department')
    resource_calendar_ids       = fields.Many2many('resource.calendar')
    employee_ids    = fields.Many2many('hr.employee')
    datas           = fields.Binary('File', readonly=True)
    
    def _get_dates(self, s, e):
        date_range = [[s + timedelta(days=x), date_utils._softatt_localize(s + timedelta(days=x), self.env.user.tz).date()] for x in range((e - s).days + 1)]
        return date_range

    def _dashboard(self):
        location_ids      = self.location_ids.read(['name'])
        department_ids  = self.department_ids.read(['name'])
        shift_ids       = self.resource_calendar_ids.read(['name'])
        employee_ids    = self.employee_ids.read(['name'])
        
        
        #!!
        dashboard                       = self.env['sa.attendance.dashboard'].with_user(self.env.user)
        date                            = self.date
        date_time                       = datetime.combine(date, time.min)
        
        # ----------------------------------------------------------------#
        #!!
        absent_domain                   = self.env['report.softatt_attendance.absence_report'].with_user(self.env.user)._prepare_domain(str(date_time), location_ids, department_ids, shift_ids, employee_ids)
        total_emps, attended, late      = dashboard._get_dashboard_summary(date_time, location_ids, department_ids, shift_ids, employee_ids)
        #!!
        absent_emps                     = self.env['hr.employee'].with_user(self.env.user).search_count(absent_domain)
        return [total_emps, attended, absent_emps, late]
    
    
    def action_confirm(self):
        s, e = date_utils._softatt_get_span_dates(self.date, self.date, self.env.user.tz)
        dashboard   = self._dashboard()
        _logger.error(dashboard)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                "group_by"          : self.group_by,
                "date_from"         : s,
                "date_to"           : e,
                "_from"             : self.date,
                "_to"               : self.date,
                "dashboard"         : dashboard,
                "dates"             : self._get_dates(s, e),
                "location_ids"      : self.location_ids.read(['name']),
                "department_ids"    : self.department_ids.read(['name']),
                "shift_ids"         : self.resource_calendar_ids.read(['name']),
                "employee_ids"      : self.employee_ids.read(['name']),
            },
        }
        return self.env.ref('softatt_attendance.action_daily_report').report_action(self, data=data)

class SaDailyReport(models.AbstractModel):
    _name = 'report.softatt_attendance.sa_daily_report'
    _description = 'Daily Report'



    
    def _absence_lines(self, date, location_ids, department_ids, shift_ids, employee_ids):
        absence_lines = self.env['report.softatt_attendance.absence_report']._lines(date, location_ids, department_ids, shift_ids, employee_ids)
        return absence_lines
    
    def _att_domain(self,  date_from, date_to, location_ids, department_ids, shift_ids, employee_ids):
        user = self.env.user
        user_tz         = user.tz
        if not user_tz:
            raise ValidationError("Please Set up Your Timezone")
        
        locations        =   [location_id['id'] for location_id in location_ids]
        departments     =   [department_id['id'] for department_id in department_ids]
        shifts          =   [shift_id['id'] for shift_id in shift_ids]
        employees       =   [employee_id['id'] for employee_id in employee_ids]
        
        # date            =   datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        # localized_date  =   date_utils._softatt_localize(date, user_tz)
        domain          = [
            ('employee_id'  , '!=', False),
            ('check_in'   , '>=', date_from), 
            ('check_in'   , '<=', date_to)]
        
        if locations:
            domain.append(('location_id.id','in',locations))
        if departments:
            domain.append(('department_id.id','in',departments))
        if shifts:
            domain.append(('resource_calendar_id.id','in',shifts))
        if employees:
            domain.append(('employee_id.id','in',employees))
        return domain
            
    def _att_lines(self, date_from, date_to, location_ids, department_ids, shift_ids, employee_ids):
        domain          =  self._att_domain(date_from, date_to, location_ids, department_ids, shift_ids, employee_ids)
        att_lines       =   self.env['hr.attendance'].search(domain)
        return att_lines
            
    @api.model
    def _get_report_values(self, docids, data=None):
        model   = self.env.context.get('active_model')
        docs    = self.env[model].browse(self.env.context.get('active_id'))
        user_tz = self.env.user.tz
        return {
            "doc_ids"           : self.ids,
            "doc_model"         : model,
            "docs"              : docs,
            "dates"             : data['form']['dates'],
            "group_by"          : data['form']['group_by'],
            "dashboard"         : data['form']['dashboard'],
            "date_from"         : data['form']['date_from'],
            "date_to"           : data['form']['date_to'],
            "_from"             : data['form']['_from'],
            "_to"               : data['form']['_to'],
            "location_ids"      : data['form']['location_ids'],
            "department_ids"    : data['form']['department_ids'],
            "shift_ids"         : data['form']['shift_ids'],
            "employee_ids"      : data['form']['employee_ids'],
            "absence_lines"     : self._absence_lines,
            "att_lines"         : self._att_lines,
            "tz"                : user_tz,
            "localize"          : date_utils._softatt_localize,
        }