
{
    'name': 'MGS Freight Management',
    'version': '19.0.1.0',
    'category': 'Industries',
    'summary': 'Module for Managing All Freight Operations',
    'description': 'Freight Operations and reports',
    'author': 'Meisour GLobal Solutions',
    'website': 'https://www.meisour.com',
    'company': 'Meisour GLobal Solutions',
    'depends': ['base','mail','account','product','analytic'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/freight_port.xml',
        'views/freight_receipts.xml',
        'views/res_config.xml',
        'views/freight_delivery.xml',
        'report/qweb_reports.xml',
        'wizard/freight_delivery_wizard_view.xml',
        'wizard/freight_receipt_wizard_view.xml',
        'wizard/freight_transfer.xml',
        'report/freight_delivery_report.xml',
        'report/freight_receipt_report.xml',
        
    ],
    
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
