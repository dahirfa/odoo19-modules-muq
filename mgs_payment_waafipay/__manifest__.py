# -*- coding: utf-8 -*-
{
    'name': "Payment Provider: WaafiPay",
    'author': "Meisour GS",
    'website': "https://www.meisour.com",
    'version': '18.0',
    'depends': ['base','payment','account'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'data/payment_provider.xml',
    ],
    'category': 'Accounting/Payment Providers',
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
