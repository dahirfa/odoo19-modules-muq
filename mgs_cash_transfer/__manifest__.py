# -*- coding: utf-8 -*-
{
    'name': 'MGS Cash Transfer',
    'version': '19.0.1.0',
    'summary': 'Module for internal cash transfers between company accounts',
    'description': 'Module for internal cash transfers between company accounts',
    'author': 'Meisour Solutions',
    'website': "http://www.meisour.com",
    'depends': ['base', 'account', 'mail'],
    'data': [
        'security/mgs_cash_transfer_security.xml', 
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/transfer_views.xml',
        'views/voucher_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'category': 'Accounting'
}

