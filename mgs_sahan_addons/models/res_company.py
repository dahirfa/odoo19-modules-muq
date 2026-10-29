from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    show_pos_reference = fields.Boolean(
        string='Show POS Reference on Invoices',
        help="Copy the POS receipt number to invoices of this company and print it on the invoice report.",
    )
