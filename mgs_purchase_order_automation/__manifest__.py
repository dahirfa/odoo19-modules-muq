# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order Automation',
    'version': '19.0.1.0.0',
    'summary': 'Validate receipts and create/post vendor bills automatically on purchase order confirmation',
    'description': """
Purchase Order Automation
=========================

Company-level options, set in Settings, that run when a purchase order is confirmed:

* Validate the receipt(s) for the full ordered quantity
* Create the vendor bill
* Post the vendor bill
    """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': ['purchase_stock'],
    'data': [
        'views/res_config.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
