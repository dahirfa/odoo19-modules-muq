# -*- coding: utf-8 -*-

{
    'name': "Warehouse Restrictions",
    'summary': """Restrict users to specifec warehouses""",
    'description': """Restrict warehouses by user.""",
    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",
    'license': 'AGPL-3',
    'category': 'generic',
    'version': '19.0.1.0.0',
    'depends': ['account', 'base', 'stock'],
    'data': [
        'security/security.xml',
        'views/users.xml',
    ],
    "images": [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
