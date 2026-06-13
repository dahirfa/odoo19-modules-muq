# -*- coding: utf-8 -*-
{
    'name': "Mgs Payment Reconcillation",

    'summary': """ """,

    'description': """
        This module allows users to select multiple posted invoices or bills and reconcile them automatically with a payment.
        It supports both customer and vendor payments, ensuring accurate matching and clearing of open balances.
    """,

    'author': "Meisour GS",
    'website': "https://meisour.com", 
    'category': '',
    'version': '18.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/view.xml',
        'views/config_view.xml',

    ]
}
