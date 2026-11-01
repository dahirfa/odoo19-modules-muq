{
    'name': 'Rental Management Dashboard - Landlord Filter',
    'version': '19.0.1.0.0',
    'summary': 'Filter the Rental Management dashboard by one or more landlords',
    'description': """
Rental Management Dashboard - Landlord Filter
=============================================

* Adds a multi-select Landlord filter to the Rental Management dashboard
* Every card, chart and the property map follow the selected landlords
* Opening a card shows the matching records for the selected landlords only
* With no landlord selected the dashboard shows all data, exactly as before
    """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'category': 'Services',
    'license': 'LGPL-3',
    'depends': ['rental_management'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'mgs_rental_management_dashboard/static/src/js/rental_dashboard_patch.js',
            'mgs_rental_management_dashboard/static/src/xml/rental_dashboard.xml',
            'mgs_rental_management_dashboard/static/src/scss/rental_dashboard.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
