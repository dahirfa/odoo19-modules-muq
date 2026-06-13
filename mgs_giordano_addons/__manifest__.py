# -*- coding: utf-8 -*-
{
    'name': 'Giordano Addons',
    'version': '1.0.0',
    'summary': """ Mgs_giordano_addons Summary """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'category': '',
    'depends': ['base', 'account', 'account_reports','point_of_sale'],
    "data": [
        "views/report_pos_order_views.xml",
        "views/session_report.xml",
        "views/sale_report.xml",
    ],
   
   
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
