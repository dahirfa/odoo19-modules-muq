{
    'name': "MuK MCP Security Hardening",
    'summary': "Security fixes for the MuK MCP Server",
    'author': "Meisour Global Solutions",
    'website': "http://www.meisour.com",
    'category': 'Tools/API',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['muk_mcp'],
    'data': [
        'security/security.xml',
        'views/key.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
