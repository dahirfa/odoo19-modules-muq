# -*- coding: utf-8 -*-
{
    'name': "tis_property_managment",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Meisour GS",
    'website': "https://www.meisour.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '19.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail','account','hr_expense'],

    # always loaded
    'data': [
        'data/seq.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/property.xml',
        'views/parent_property.xml',
        'views/tenancy.xml',
        'views/maintenance.xml',
        'views/rent_schedule.xml',

        'views/rent_schedule_report_wizard.xml',
        'views/rent_schedule_invoice_generate.xml',
        'views/landlord_summary_wizard.xml',
        'views/landlord_account_statement_wizard.xml',

        'views/Report_rent_schedule.xml',
        'views/Report_landlord_summary.xml',
        'views/Report_landlord_account_statment.xml',
        
        'views/configuration.xml',
        'views/res_partner.xml',
        'views/res_config.xml',


    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
