# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "SoftAttendance",
    "version": "19.0.1.0",
    "category": "HR",
    "license": "OPL-1",
    'author':       "SOFT TECH LTD",
    "website":      "softatt.com",
    "depends": ["base", "resource", "mail", "hr", 'hr_attendance'],
    "demo": [],
    
    "data": [
        # Data
        "data/data.xml",
        
        # Security
        "security/ir.model.access.csv",
        "security/security.xml",
        
        # Odoo Views
        "views/device.xml",
        "views/hr_employee.xml",
        "views/shift.xml",
        "views/attendance_log.xml",
        "views/hr_attendance.xml",
        "views/dashboard.xml",
        "views/db_link.xml",
        "views/config.xml",
        "views/employee_code.xml",
        
        # Report Views
        "reports/Report_absence.xml",
        "reports/Report_daily.xml",
        "reports/Report_monthly.xml",
        "reports/Report_employee.xml",
        "reports/Report_att.xml",
        
        # Wizards
        "wizards/absence_wiz.xml",
        "wizards/daily_report_wiz.xml",
        "wizards/monthly_report_wiz.xml",
        "wizards/employee_attendance_wiz.xml",
        "wizards/att_report_wiz.xml",
        
        # Menu Items
        "views/menu_items.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "softatt_attendance/static/src/components/chart_renderer/bar_chart.js",
            "softatt_attendance/static/src/components/chart_renderer/bar_chart.xml",
            "softatt_attendance/static/src/components/logs/log.js",
            "softatt_attendance/static/src/components/logs/log.xml",
            "softatt_attendance/static/src/components/late/late.js",
            "softatt_attendance/static/src/components/late/late.xml",
            "softatt_attendance/static/src/components/dashboard/dashboard.js",
            "softatt_attendance/static/src/components/dashboard/dashboard.xml",
            "softatt_attendance/static/src/scss/**",
            
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
