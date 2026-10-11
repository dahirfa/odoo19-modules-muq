from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    is_receipt_set_to_done = fields.Boolean(string="Validate Receipt on Confirmation")
    create_bill = fields.Boolean(string="Create Bill on Confirmation")
    validate_bill = fields.Boolean(string="Post Bill on Confirmation")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_receipt_set_to_done = fields.Boolean(related="company_id.is_receipt_set_to_done", readonly=False)
    create_bill = fields.Boolean(related="company_id.create_bill", readonly=False)
    validate_bill = fields.Boolean(related="company_id.validate_bill", readonly=False)
