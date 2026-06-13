# -*- coding: utf-8 -*-
{
    "name": "MGS Purchase Reports",
    "summary": "Purchase report (qty, qty-billed, qty-ordered, qty-delivered, cost and other totals) by vendor and/or product",
    "description": "",
    "author": "Meisour Solutions",
    "website": "http://www.meisour.com",
    "category": "Reporting",
    "version": "2.0",
    "depends": ["purchase"],
    "license": "LGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "wizards/purchase_report.xml",
        "views/report_mgs_purchase.xml",
    ],
}  # type: ignore
