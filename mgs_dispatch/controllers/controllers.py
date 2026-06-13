# -*- coding: utf-8 -*-
# from odoo import http


# class Dispatch(http.Controller):
#     @http.route('/dispatch/dispatch', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dispatch/dispatch/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dispatch.listing', {
#             'root': '/dispatch/dispatch',
#             'objects': http.request.env['dispatch.dispatch'].search([]),
#         })

#     @http.route('/dispatch/dispatch/objects/<model("dispatch.dispatch"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dispatch.object', {
#             'object': obj
#         })
