{
    'name': 'Container Control',
    'version': '19.0.1.1.0',
    'summary': 'Container discharge/loading tracking, delivery orders and demurrage invoicing',
    'description': """
Container Control
=================

* One Container Control record per container (discharge side, loading side, demurrage)
* Automatic total days out, demurrage days, dwell days and tiered demurrage amount
* Configurable Week 1 / Week 2 / Week 3 demurrage rates per container size/type
* Delivery Order with PDF report and Excel export (day calculations as live formulas)
* Manual demurrage invoice per Delivery Order: one line per container for its uninvoiced demurrage days
* Container Control Summary / Detail PDF reports per consignee
* Dedicated Delivery Order report logo on the company, shared by the PDF and Excel reports
    """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'license': 'LGPL-3',
    'depends': ['mail', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/container_size_type_data.xml',
        'report/container_delivery_order_reports.xml',
        'report/container_control_reports.xml',
        'views/res_company_views.xml',
        'views/container_size_type_views.xml',
        'views/container_control_views.xml',
        'views/container_delivery_order_views.xml',
        'wizard/container_control_report_wizard_views.xml',
        'views/mgs_container_control_menus.xml',
    ],
    'installable': True,
    'application': True,
}
