# -*- coding: utf-8 -*-
{
    "name": "mgs account balance",
    "summary": """Show partner balance""",
    "description": """Show partner balance""",
    "author": "Meisour Solutions",
    "website": "http://www.meisour.com",
    "category": "Reporting",
    "version": "1.0",
    "depends": ["sale", "account"],
    "license": "LGPL-3",
    "data": [
        "views/account_move.xml",
        "views/account_payment.xml",
        "views/sale_order.xml",
        "views/partner.xml",
    ],
}  # type: ignore
