
{
    'name': 'MGS Change password portal',
    'version': '19.0.1.0',
    'category': 'Industries',
    'summary': 'Module for Managing All Change password portal',
    'description': 'Change password portal',
    'author': 'Meisour GLobal Solutions',
    'website': 'https://www.meisour.com',
    'company': 'Meisour GLobal Solutions',
    'depends': ['base', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/mgs_partner_inherit.xml',
       
      
     
    ],
    # 'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}