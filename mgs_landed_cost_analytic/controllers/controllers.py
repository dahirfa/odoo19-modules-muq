# -*- coding: utf-8 -*-
# from odoo import http


# class MgsLandedCostAnalytic(http.Controller):
#     @http.route('/mgs_landed_cost_analytic/mgs_landed_cost_analytic', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mgs_landed_cost_analytic/mgs_landed_cost_analytic/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mgs_landed_cost_analytic.listing', {
#             'root': '/mgs_landed_cost_analytic/mgs_landed_cost_analytic',
#             'objects': http.request.env['mgs_landed_cost_analytic.mgs_landed_cost_analytic'].search([]),
#         })

#     @http.route('/mgs_landed_cost_analytic/mgs_landed_cost_analytic/objects/<model("mgs_landed_cost_analytic.mgs_landed_cost_analytic"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mgs_landed_cost_analytic.object', {
#             'object': obj
#         })
