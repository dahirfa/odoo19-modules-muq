# -*- coding: utf-8 -*-
# from odoo import http


# class MgsProductCostReadonly(http.Controller):
#     @http.route('/mgs_product_cost_readonly/mgs_product_cost_readonly', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mgs_product_cost_readonly/mgs_product_cost_readonly/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mgs_product_cost_readonly.listing', {
#             'root': '/mgs_product_cost_readonly/mgs_product_cost_readonly',
#             'objects': http.request.env['mgs_product_cost_readonly.mgs_product_cost_readonly'].search([]),
#         })

#     @http.route('/mgs_product_cost_readonly/mgs_product_cost_readonly/objects/<model("mgs_product_cost_readonly.mgs_product_cost_readonly"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mgs_product_cost_readonly.object', {
#             'object': obj
#         })
