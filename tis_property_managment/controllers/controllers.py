# -*- coding: utf-8 -*-
# from odoo import http


# class TisPropertyManagment(http.Controller):
#     @http.route('/tis_property_managment/tis_property_managment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tis_property_managment/tis_property_managment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tis_property_managment.listing', {
#             'root': '/tis_property_managment/tis_property_managment',
#             'objects': http.request.env['tis_property_managment.tis_property_managment'].search([]),
#         })

#     @http.route('/tis_property_managment/tis_property_managment/objects/<model("tis_property_managment.tis_property_managment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tis_property_managment.object', {
#             'object': obj
#         })
