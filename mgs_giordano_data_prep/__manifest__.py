{
    'name': 'Giordano Data Preparation',
    'version': '19.0.1.0.0',
    'summary': """ Giordano Data Preparation is module that prepares products so that they work properly with the rfid feature """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'category': 'Supply Chain',
    'depends': ['base', 'stock', "product" ],
    "data": [
        "security/ir.model.access.csv",
        "views/product.xml",
        "views/adjustment_retracking.xml",
    ],
   
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
