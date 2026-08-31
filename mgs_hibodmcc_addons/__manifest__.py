{
    'name': 'Mgs Hibo DMCC Addons ',
    'version': '1.0',
    'category': 'Generic',
    'description': """
        
    """,
    'author': 'Meisour Global Solutions',
    'website': 'https://meisour.com',
    'depends': ['base', 'stock', 'account','purchase','purchase_stock'],
    'data': [        
        'security/ir.model.access.csv',        
        'views/delivery.xml',        
        'views/delivery_report.xml',        
        'views/delivery_note_report.xml',        
        'views/proforma_invoice_report.xml',        
        'views/account_move.xml',                
             
    ],    
    'installable': True,
    'Application': True,    
}