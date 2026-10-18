{
    'name': 'MGS Document Designs',
    'version': '19.0.1.0.0',
    'summary': 'Custom designs for the invoice, payment receipt and picking operations reports',
    'description': """
MGS Document Designs
====================

* Customer invoice / credit note / vendor bill layout
* Receipt / payment voucher layout for payments
* Picking operations layout for transfers

The designs are separate templates plugged into the standard report actions, so
the core templates (and every module extending them) are left untouched.
    """,
    'category': 'Accounting/Accounting',
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'license': 'LGPL-3',
    'depends': ['account', 'stock'],
    'data': [
        'views/invoice.xml',
        'views/picking.xml',
        'views/payment.xml',
    ],
    'installable': True,
    'application': False,
}
