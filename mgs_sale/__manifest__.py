# -*- coding: utf-8 -*-
{
    'name': "MGS Sales Reports",
    'summary': "",
    'description': "",
    'author': "Meisour Solutions",
    'website': "http://www.meisour.com",
    'category': 'Reporting',
    'version': '2.0',
    'depends': ['sale', 'sale_margin'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/report_mgs_sale.xml',
        'wizards/sale_report.xml',
    ],
}