# -*- coding: utf-8 -*-
{
    'name': 'POS User Allowed Payment Methods',
    'version': '1.0',
    'summary': 'Restrict POS payment methods visibility per user',
    'category': 'Point of Sale',
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_users_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'mgs_pos_user_payment_methods/static/src/js/payment_methods.js',
        ],
    },
    'installable': True,
}

