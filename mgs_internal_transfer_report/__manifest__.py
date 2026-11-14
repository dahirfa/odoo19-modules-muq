# -*- coding: utf-8 -*-
{
    "name": "Internal Transfer Report",
    "version": "19.0.1.0.0",
    "summary": "Unit cost and total value on internal transfers",
    "description": """
Internal Transfer Report
========================

* Unit value (product cost) and total value on stock moves and move lines of internal transfers
* Transfer total and responsible employee on the transfers list
    """,
    "author": "Meisour Global Solutions",
    "website": "https://meisour.com",
    "license": "LGPL-3",
    "category": "Inventory/Inventory",
    "depends": ["stock", "hr"],
    "data": [
        "views/views.xml",
    ],
    "installable": True,
    "application": False,
}
