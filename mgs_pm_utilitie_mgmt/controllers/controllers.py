# -*- coding: utf-8 -*-
# from odoo import http


# class MgsPmUtilitieMgmt(http.Controller):
#     @http.route('/mgs_pm_utilitie_mgmt/mgs_pm_utilitie_mgmt', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mgs_pm_utilitie_mgmt/mgs_pm_utilitie_mgmt/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mgs_pm_utilitie_mgmt.listing', {
#             'root': '/mgs_pm_utilitie_mgmt/mgs_pm_utilitie_mgmt',
#             'objects': http.request.env['mgs_pm_utilitie_mgmt.mgs_pm_utilitie_mgmt'].search([]),
#         })

#     @http.route('/mgs_pm_utilitie_mgmt/mgs_pm_utilitie_mgmt/objects/<model("mgs_pm_utilitie_mgmt.mgs_pm_utilitie_mgmt"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mgs_pm_utilitie_mgmt.object', {
#             'object': obj
#         })
