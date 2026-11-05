{
    'name': 'Invoice Attachment Optimization',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Stop storing an automatic PDF in the filestore for every POS invoice',
    'description': """
Invoice Attachment Optimization
===============================

Odoo renders, stores and emails a PDF for every invoice created from the Point of Sale.
This module keeps the invoice, its posting, payments and reconciliation, and skips that step:

* No automatic Send & Print while a POS order is invoiced, so no PDF attachment and no email
* The Send button is hidden on the invoice form, for every invoice
* Invoices that need an electronic document (EDI) keep the standard behaviour
    """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'license': 'LGPL-3',
    'depends': ['account', 'point_of_sale'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
