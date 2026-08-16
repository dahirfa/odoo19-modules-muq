from odoo import models, fields, api
from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    freight_product_id = fields.Many2one('product.product', string="Default Product")
    analytic_plan_id = fields.Many2one('account.analytic.plan')


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    freight_product_id = fields.Many2one(related="company_id.freight_product_id", readonly=False, string="Default Product")
    analytic_plan_id = fields.Many2one(related="company_id.analytic_plan_id", readonly=False, string="Default Analytic Plan")
