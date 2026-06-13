
from datetime import datetime, time, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)
from odoo.tools import date_utils

class SaAttendanceReportWiz(models.TransientModel):
    _name = 'sa.att.report'
    _description = 'Attendance Report Wizard'

    date_from = fields.Date(string="Start Date", required=True, default=lambda self: fields.Date.today() - timedelta(days=7))
    date_to = fields.Date(string="End Date", required=True, default=lambda self: fields.Date.today())
    location_ids = fields.Many2many('hr.work.location', string="Locations")
    department_ids = fields.Many2many('hr.department', string="Departments")
    resource_calendar_ids = fields.Many2many('resource.calendar', string="Shifts")
    employee_ids = fields.Many2many('hr.employee', string="Employees")
    datas = fields.Binary('File', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError("The start date must be earlier than the end date.")

    def action_confirm(self):
        """Prepare data for the report and trigger the report action."""
        s, e = self.date_from, self.date_to

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                "date_from": s,
                "date_to": e,
                "location_ids"      : self.location_ids.read(['name']),
                "department_ids"    : self.department_ids.read(['name']),
                "shift_ids"         : self.resource_calendar_ids.read(['name']),
                "employee_ids"      : self.employee_ids.read(['name']),
            },
        }
        return self.env.ref('softatt_attendance.action_att_report').report_action(self, data=data)

class SaAttendanceReport(models.AbstractModel):
    _name = 'report.softatt_attendance.sa_att_report'
    _description = 'Attendance Report'


    def _att_lines(self, date_from, date_to, location_ids, department_ids, shift_ids, employee_ids):
        daily_report = self.env['report.softatt_attendance.sa_daily_report']
        att_lines = daily_report._att_lines(date_from, date_to, location_ids, department_ids, shift_ids, employee_ids)
        return att_lines
        
    @api.model
    def _get_report_values(self, docids, data=None):

        # Reuse the `_att_lines` method from `sa.daily.report`
        model   = self.env.context.get('active_model')
        docs    = self.env[model].browse(self.env.context.get('active_id'))
        user_tz = self.env.user.tz
        
        form = data['form']
        date_from = form['date_from']
        date_to = form['date_to']
        location_ids = form['location_ids']
        department_ids = form['department_ids']
        shift_ids = form['shift_ids']
        employee_ids = form['employee_ids']

        return {
            "doc_ids"           : self.ids,
            "doc_model"         : model,
            "docs"              : docs,
            "date_from": date_from,
            "date_to": date_to,
            "location_ids": location_ids,
            "department_ids": department_ids,
            "shift_ids": shift_ids,
            "employee_ids": employee_ids,
            "att_lines" : self._att_lines,
            "tz"        : user_tz,
            "localize"  : date_utils._softatt_localize,

        }
