# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2020-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Ijaz Ahammed (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

from datetime import datetime, timedelta, date
import pytz
from odoo import models, fields

class HrAttendanceLatencyAbsence(models.TransientModel):
    _name = 'mgs.attendance.checker.wizard'
    _description = 'Attendance Checking'

    employee_ids = fields.Many2many('hr.employee',required=True)
    date_from  = fields.Date(default=fields.Date.today().replace(day=1), required=True)
    date_to  = fields.Date(default=fields.Date.today(),required=True)


    def check_attendance(self):
        start_date = self.date_from
        end_date = self.date_to
        obj= self.env['late.check_in']
        hr_obj= self.env['hr.attendance']

        for employee in self.employee_ids:
            employee_id = employee
            attendance_records = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id.id),
                ('check_in', '>=', start_date),
                ('check_out', '<=', end_date),
            ])
            for rec in attendance_records.filtered(lambda x:x.late_check_in > 0):
                obj.create({
                    'employee_id': employee_id.id,
                    'late_minutes': rec.late_check_in,
                    'date': rec.check_in.date(),
                    'attendance_id': rec.id,
                    'amount': obj.get_penalty_amount(rec.late_check_in, rec.employee_id, rec.check_in.date()),})
            working_schedule =  employee_id.resource_calendar_id.attendance_ids
            non_working_days = working_schedule.filtered(lambda x: x.dayofweek not in ('0','1','2','3','4','5','6')).mapped('dayofweek') or []
            recorded_dates = {attendance.check_in.date() for attendance in attendance_records}
            date_range = {
                start_date + timedelta(days=x) 
                for x in range((end_date - start_date).days + 1) 
                if (start_date + timedelta(days=x)).weekday() not in non_working_days
                } 
            missing_dates = date_range - recorded_dates
            if missing_dates:
                for md in missing_dates:
                    obj.create({
                        'employee_id': employee_id.id,
                        'absent': True,
                        'date': md,
                        'amount': obj.get_penalty_amount(99999, employee_id, md, absent=True)
                    })
            else:
                continue


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    late_check_in = fields.Integer(string="Late Check-in(Minutes)", compute="get_late_minutes")

    def get_late_minutes(self):
        for rec in self:
            rec.late_check_in = 0.0
            week_day = rec.sudo().check_in.weekday()
            employee =  rec.sudo().employee_id
            if employee:
                work_schedule = employee.resource_calendar_id
                for schedule in work_schedule.sudo().attendance_ids:
                    if schedule.dayofweek == str(week_day):
                        work_from = schedule.hour_from
                        result = '{0:02.0f}:{1:02.0f}'.format(*divmod(work_from * 60, 60))
                        user_tz = self.env.user.tz
                        dt = rec.check_in
                        if user_tz in pytz.all_timezones:
                            old_tz = pytz.timezone('UTC')
                            new_tz = pytz.timezone('Africa/Mogadishu')
                            dt = old_tz.localize(dt).astimezone(new_tz)
                        str_time = dt.strftime("%H:%M")
                        check_in_date = datetime.strptime(str_time, "%H:%M").time()
                        start_date = datetime.strptime(result, "%H:%M").time()
                        minutes=0
                        if employee.late_penalty_id:
                            minutes =  employee.late_penalty_id.minutes
                        t1 = timedelta(hours=check_in_date.hour, minutes=check_in_date.minute)
                        t2 = timedelta(hours=start_date.hour, minutes=start_date.minute + minutes)
                        if check_in_date > start_date:
                            final = t1 - t2
                            rec.sudo().late_check_in = final.total_seconds() / 60
