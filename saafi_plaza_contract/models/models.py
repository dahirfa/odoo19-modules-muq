# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class safari_plaza_contract(models.Model):
#     _name = 'safari_plaza_contract.safari_plaza_contract'
#     _description = 'safari_plaza_contract.safari_plaza_contract'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
