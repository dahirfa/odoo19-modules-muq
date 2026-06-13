from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO
from odoo.tools import date_utils

import logging
_logger = logging.getLogger(__name__)



class SaAbsenceReportWiz(models.TransientModel):
    _name = 'sa.absence'
    _description = 'Absence Report Wizard'
    
    group_by        = fields.Selection([('date', 'Date'),
                                        ('location', 'Location'),
                                        ('department', 'Department'),
                                        ('shift', 'Shift')], default='date')
    date_from       = fields.Date(string="From",default=lambda self: fields.Date.today(), required=True)
    date_to         = fields.Date(string="To",default=lambda self: fields.Date.today(), required=True)
    location_ids    = fields.Many2many('hr.work.location')
    department_ids  = fields.Many2many('hr.department')
    resource_calendar_ids       = fields.Many2many('resource.calendar') 
    employee_ids    = fields.Many2many('hr.employee')
    datas           = fields.Binary('File', readonly=True)
    
    def _get_dates(self, s, e):
        date_range = [[s + timedelta(days=x), 
                       date_utils._softatt_localize(s + timedelta(days=x), self.env.user.tz).date()] for x in range((e - s).days + 1)]
        return date_range

    def action_export_to_excel(self):
        fp = BytesIO()
        data = self.env['report.softatt_attendance.absence_report']
        s, e = date_utils._softatt_get_span_dates(self.date_from, self.date_to, self.env.user.tz)
        
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet("Report")
        headers = ['#', 'Employee', 'Location', 'Department']
        bold_format = workbook.add_format({'bold': True})  # Create a bold format
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, bold_format)
        row=1
        r=0
        for date in self._get_dates(s, e):
            worksheet.merge_range(row, 0, row, 3, str(date[1]))
            row+=1
            for record in data._lines(str(date[0]), self.location_ids.read(['name']), self.department_ids.read(['name']), self.resource_calendar_ids.read(['name']), self.employee_ids.read(['name'])):
                worksheet.write(row, 0, r+1)
                worksheet.write(row, 1, record.name)
                worksheet.write(row, 2, record.work_location_id.name)
                worksheet.write(row, 3, record.department_id.name)
                row+=1
                r+=1
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        self.write({'datas': out})
        fp.close()
        filename = 'Absence Report'
        filename += '%2Exlsx'
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model='+self._name+'&id='+str(self.id)+'&field=datas&download=true&filename='+filename,
        }

    def action_confirm(self):
        s, e = date_utils._softatt_get_span_dates(self.date_from, self.date_to, self.env.user.tz)
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                "group_by"          : self.group_by,
                "date_from"         : s,
                "date_to"           : e,
                "_from"             : self.date_from,
                "_to"               : self.date_to,
                "dates"             : self._get_dates(s, e),
                "location_ids"        : self.location_ids.read(['name']),
                "department_ids"    : self.department_ids.read(['name']),
                "shift_ids"         : self.resource_calendar_ids.read(['name']),
                "employee_ids"      : self.employee_ids.read(['name']),
            },
        }
        return self.env.ref('softatt_attendance.action_absence_report').report_action(self, data=data)
    
    
    




class SaAbsenceReport(models.AbstractModel):
    _name = 'report.softatt_attendance.absence_report'
    _description = 'Absence Report'

    
    
    def _prepare_domain(self, date, location_ids, department_ids, shift_ids, employee_ids):
        user = self.env.user
        user_tz         = user.tz
        if not user_tz:
            raise ValidationError("Please Set up Your Timezone")
        
        locations       =   [location_id['id'] for location_id in location_ids]
        departments     =   [department_id['id'] for department_id in department_ids]
        shifts          =   [shift_id['id'] for shift_id in shift_ids]
        employees       =   [employee_id['id'] for employee_id in employee_ids]

        date            = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        localized_date  = date_utils._softatt_localize(date, user_tz)
        domain          = [('dayofweek','=', localized_date.date().weekday())]
        shift_ids       = tuple(set(self.env['resource.calendar.attendance'].search(domain).mapped('calendar_id.id')))
        
        log             = set(self.env['hr.attendance'].search([
            ('employee_id'  , '!=', False),
            ('check_in'   , '>=', date), 
            ('check_in'   , '<=', date + timedelta(hours=24))]).mapped('employee_id.id'))
        
        emp_domain              = [('id','not in', tuple(log)), ('resource_calendar_id.id', 'in', shift_ids)]
        
        if locations:
            emp_domain.append(('work_location_id.id','in',locations))
        if departments:
            emp_domain.append(('department_id.id','in',departments))
        if shifts:
            emp_domain.append(('resource_calendar_id.id','in',shifts))
        if employees:
            emp_domain.append(('id','in',employees))
        return emp_domain
    
    
    def _lines(self, date, location_ids, department_ids, shift_ids, employee_ids):
        emp_domain              = self._prepare_domain(date, location_ids, department_ids, shift_ids, employee_ids)
        absent_emps             = self.env['hr.employee'].search(emp_domain)
        return absent_emps
    
    
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
            "date_from"         : data['form']['date_from'],
            "date_to"           : data['form']['date_to'],
            "_from"             : data['form']['_from'],
            "_to"               : data['form']['_to'],
            "location_ids"        : data['form']['location_ids'],
            "department_ids"    : data['form']['department_ids'],
            "shift_ids"         : data['form']['shift_ids'],
            "employee_ids"      : data['form']['employee_ids'],
            "lines"             : self._lines,
            "tz"                : user_tz,
            "localize"          : date_utils._softatt_localize,
        }