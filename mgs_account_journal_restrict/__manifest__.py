# -*- coding: utf-8 -*-

{
    'name': "Journal Restrictions",
    'summary': """Restrict users to specifec journals""",
    'description': """Restrict journals by user.""",
    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",
    'license': 'AGPL-3',
    'category': 'account',
    'version': '13.0',
    'depends': ['account', 'point_of_sale', 'sale'],
    'data': [
        'views/users.xml',
        'security/security.xml',
    ],
    "images": [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
