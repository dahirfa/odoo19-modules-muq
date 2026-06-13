# -*- coding: utf-8 -*-
{
    'name': 'POS Automate Invoice | POS auto Invoice Check ',
    'summary': "Allow to auto set invoice checkbox to create invoice auto ",
    'description': 'Allow to auto set invoice checkbox to create invoice auto and allow to restrict invoice download.',



    'category': 'Point of Sale',
    'version': '19.0.0.1'
    '',
    'depends': ['point_of_sale'],

    'data': [
        'views/res_config_views.xml'

    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'pos_auto_invoice_check/static/src/**/*',
        ],
    },

    'license': "OPL-1",

    'installable': True,
    'application': True,

}
