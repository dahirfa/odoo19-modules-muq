# -*- coding: utf-8 -*-
{
    'name': "POS Analytic Account",
    'summary': """
       Use analytic account defined on POS for anglo-saxon journal lines""",

    'description': """
        Use analytic account defined on POS for anglo-saxon journal lines
    """,
    'price': 15,
    'currency': 'EUR',
    'author': 'Meisour Solutions',
    'license': 'OPL-1',
    'category': 'Point Of Sale, Accounting',
    'website': 'https://meisour.com',
    'support': 'support@meisour.com',
    'version': '17.0',
    'depends': [
        'point_of_sale',
        'account',
        'analytic'
    ],
    'data': [
        'views/pos_config.xml',
        'views/pos_order.xml',
    ],
    'installable': True,
}
