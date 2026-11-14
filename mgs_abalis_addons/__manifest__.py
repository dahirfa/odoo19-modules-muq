{
    'name': 'MGS Abalis Addons',
    'version': '19.0.1.1.0',
    'summary': 'Abalis customizations: link inventory transfers to properties',
    'description': """
MGS Abalis Addons
=================

* Adds a Property Details field on inventory transfers (stock.picking)
* Shows the field on the transfer form and list views
    """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'license': 'LGPL-3',
    'depends': ['stock', 'rental_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/property_details.xml',
        'views/property_project_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
}
