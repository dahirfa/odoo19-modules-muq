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
from odoo import models, fields, api, _
import calendar
from odoo.exceptions import UserError


class LateCheckIn(models.Model):
    _name = 'late.check_in'
    _description = 'Late Check-In'
    _rec_name = 'employee_id'

    name = fields.Char()
    absent = fields.Boolean(default=False)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    company_id = fields.Many2one('res.company', string='Company', related='employee_id.company_id', store=True)
    late_minutes = fields.Integer(string="Late Minutes")
    date = fields.Date(string="Date")
    amount = fields.Float(string="Amount", store=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved'), ('refused', 'Refused'), ('deducted', 'Deducted')],
        string="state", default="approved")
    attendance_id = fields.Many2one('hr.attendance', string='attendance')


    def get_penalty_amount(self, minutes, employee_id, date, absent=False):
        employee = employee_id
        late_penalty = employee.late_penalty_id
        if not late_penalty:
            return
        amount = 0.0
        diff = minutes
        to_deduct = 0.0
        daily_wage = (employee.wage / int(calendar.monthrange(date.year, date.month)[1]))
        if late_penalty.letency_type== 'wage':
            hours_per_day = employee.resource_calendar_id.hours_per_day
            amount = daily_wage / hours_per_day
            if absent:
                to_deduct = daily_wage
            else:
                diff -= late_penalty.minutes
                if diff > 0:
                    to_deduct = (minutes / 60) * amount
        elif late_penalty.letency_type== 'fixed':
            amount = late_penalty.fixed_amount
            diff -= late_penalty.minutes
            if absent:
                to_deduct = daily_wage
            else:
                if diff > 0:
                    to_deduct = (minutes / 60) * amount
        elif late_penalty.letency_type== 'custom':
            to_deduct = self._get_custom_amount(late_penalty, minutes)
        return round(to_deduct, 3)


    def _get_custom_amount(self, late_penalty, minutes):
        latency_rule = late_penalty.latency_rule_lines.search([('latency_rule_id.id', '=', late_penalty.id),
                                                        ('check_in', '>', minutes)], order='check_in', limit=1)
        return latency_rule.amount if latency_rule else 0.0
        
    def approve(self):
        self.state = 'approved'

    def reject(self):
        self.state = 'refused'
