# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError


class SaAttendanceDashboardInherit(models.Model):
    _inherit = "sa.attendance.dashboard"

    def get_present_employee(self, _time=None):
        """Extend original method to count only real employees"""
        result = super().get_present_employee(_time)
        unique_employee, employee_ids, total = result

        total_real = self.env['hr.employee'].search_count([
            ('is_real_employee', '=', True)
        ])

        return (unique_employee, employee_ids, total_real)

    def get_absent_employee(self, _time=None):
        """Extend original method to exclude fake employees or users"""
        result = super().get_absent_employee(_time)
        _, absent_emp_ids = result

        real_absent_ids = self.env['hr.employee'].search([
            ('id', 'in', absent_emp_ids),
            ('is_real_employee', '=', True)
        ]).ids

        return (len(real_absent_ids), real_absent_ids)

