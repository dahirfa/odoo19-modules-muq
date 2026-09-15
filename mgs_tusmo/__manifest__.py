# -*- coding: utf-8 -*-
{
    "name": "Mgs Tusmo",
    "version": "19.0.1.0",
    "summary": """ Mgs Tusmo Summary """,
    "author": "Meisour GS",
    "website": "https://www.meisour.com",
    "category": "Accounting",
    "depends": ["base", "account", "account_reports", "mgs_sms_marketing", "mgs_freight"],
    "data": [
        "views/account.xml",
        "views/invoice.xml",
        "views/config.xml",
        
        "views/aged_receivable.xml",
        "views/sms.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
