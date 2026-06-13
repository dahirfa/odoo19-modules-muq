# -*- coding: utf-8 -*-
{
    'name': "POS Receipt Design",

    'summary': """
        Change default pos receipt design to table design.""",

    'description': """
        Change default pos receipt design to table design to be more readable and easy to get quantities and price,
        Show customer name on receipt,
        Show receipt number on the top to be more readable.
    """,

    'author': "Meisour Global Solutions",
    'website': "https://meisour.com",

    'category': 'Point of Sale',
    'version': '18.0',

    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            
            'mgs_pos_receipt_design_giordano/static/src/xml/OrderReceipt.xml',
        ],
    },
    
    # 'images': ['static/description/images/banner.gif'],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
