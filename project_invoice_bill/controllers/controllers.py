# -*- coding: utf-8 -*-
from odoo import http

# class ProjectInvoiceBill(http.Controller):
#     @http.route('/project_invoice_bill/project_invoice_bill/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/project_invoice_bill/project_invoice_bill/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('project_invoice_bill.listing', {
#             'root': '/project_invoice_bill/project_invoice_bill',
#             'objects': http.request.env['project_invoice_bill.project_invoice_bill'].search([]),
#         })

#     @http.route('/project_invoice_bill/project_invoice_bill/objects/<model("project_invoice_bill.project_invoice_bill"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('project_invoice_bill.object', {
#             'object': obj
#         })