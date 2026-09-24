# -*- coding: utf-8 -*-
{
    'name': "MGS Sales Reports",
    'summary': """""",
    'description': """""",
    'author': "Meisour Solutions",
    'website': "http://www.meisour.com",
    'category': 'Reporting',
    'version': '19.0.1.0.0',
    'depends': ['sale', 'sale_margin'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/paperformat.xml',
        'views/report_sales_by_customer.xml',
        'views/report_sales_by_item.xml',
        'views/report_sales_by_rep.xml',
        'wizards/sales_by_customer.xml',
        'wizards/sales_by_item.xml',
        'wizards/sales_by_rep.xml',
    ],
}
