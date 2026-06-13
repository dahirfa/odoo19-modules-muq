# -*- coding: utf-8 -*-
{
    'name': "Project Invoice & Bill",

    'summary': """
        Add Bills and invoices Associated with your project """,

    'description': """

    """,

    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'project',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'account', 'hr_timesheet'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/project.xml',
        'views/invoice.xml',
        'views/project_invoice_bill.xml',
        'views/job_cost_by_detail_report.xml',
        'views/job_cost_by_detail_wizard_report.xml',
        'wizard/job_cost_by_detail_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
