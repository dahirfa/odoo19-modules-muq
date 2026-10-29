{
    'name': 'Sahan Addons',
    'version': '19.0.1.1.0',
    'summary': 'Show the POS order reference on invoices',
    'description': """ Sahan Addons """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'category': 'Sales/Point of Sale',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_company_views.xml',
        'views/account_move_views.xml',
        'report/report_invoice.xml',
    ],
    'installable': True,
    'application': False,
}
