# -*- coding: utf-8 -*-
# from odoo import http


# class MgsInventoryJournalRestrict(http.Controller):
#     @http.route('/mgs_inventory_journal_restrict/mgs_inventory_journal_restrict', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mgs_inventory_journal_restrict/mgs_inventory_journal_restrict/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mgs_inventory_journal_restrict.listing', {
#             'root': '/mgs_inventory_journal_restrict/mgs_inventory_journal_restrict',
#             'objects': http.request.env['mgs_inventory_journal_restrict.mgs_inventory_journal_restrict'].search([]),
#         })

#     @http.route('/mgs_inventory_journal_restrict/mgs_inventory_journal_restrict/objects/<model("mgs_inventory_journal_restrict.mgs_inventory_journal_restrict"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mgs_inventory_journal_restrict.object', {
#             'object': obj
#         })
