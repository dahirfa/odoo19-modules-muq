# -*- coding: utf-8 -*-
{
    "name": "Dispatching",
    "summary": """
        Dispatching
    """,
    "description": """Dispatching""",
    "author": "Meisour GS",
    "website": "https://www.meisour.com",
    "category": "Dispatching",
    "version": "19.0.1.0.0",
    "depends": ["base", "mail", "account", "hr_expense", "analytic"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/loads.xml",
        "views/views.xml",
        "views/trips.xml",
        "views/trips_report.xml",
        "views/res_config.xml",
        "views/templates.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
}
