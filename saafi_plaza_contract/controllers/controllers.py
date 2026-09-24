# -*- coding: utf-8 -*-
# from odoo import http


# class SafariPlazaContract(http.Controller):
#     @http.route('/safari_plaza_contract/safari_plaza_contract', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/safari_plaza_contract/safari_plaza_contract/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('safari_plaza_contract.listing', {
#             'root': '/safari_plaza_contract/safari_plaza_contract',
#             'objects': http.request.env['safari_plaza_contract.safari_plaza_contract'].search([]),
#         })

#     @http.route('/safari_plaza_contract/safari_plaza_contract/objects/<model("safari_plaza_contract.safari_plaza_contract"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('safari_plaza_contract.object', {
#             'object': obj
#         })
