# -*- coding: utf-8 -*-
{
    "name": "MGS Invoice Report",
    "summary": "Custom Invoice and Bill Reporting",
    "description": """
        Custom invoice and bill reports with Excel export capabilities.
        Supports grouping by partner or product with summary and detail views.
    """,
    "author": "Meisour Solutions",
    "website": "http://www.meisour.com",
    "category": "Accounting/Reporting",
    "version": "2.0.0",
    "depends": ["sale", "account"],
    "license": "LGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "wizard/invoice_report_wizard_view.xml",
        "wizard/gross_profit_wizard_view.xml",
        "wizard/account_statement_wizard_view.xml",
        "report/report_mgs_invoice.xml",
        "report/report_mgs_gross_profit.xml",
        "report/report_mgs_account_statement.xml",
    ],
    "demo": [],
    "application": False,
    "installable": True,
    "auto_install": False,
}  # type: ignore
