# -*- coding: utf-8 -*-
{
    "name": "Multi Currency General Ledger Report",
    "version": "19.0.0",
    "description": """
        This app helps user to print multi currency general ledger report with filter options like date, target moves, and general accounts
     """,
    'license': 'LGPL-3',
    "author": "Meisour Global Solutions",
    "website": "https://meisour.com",
    "depends": ["base", "account","account_reports"],
    "data": [
        "security/ir.model.access.csv",
        "reports/report_gl_template.xml",
        "wizard/mgs_multicurrency_gl_wizard_view.xml",
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
