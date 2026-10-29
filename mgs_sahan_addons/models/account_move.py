from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_reference = fields.Char(
        string='POS Reference',
        readonly=True,
        copy=False,
        index=True,
        help="Receipt number of the POS order(s).",
    )
    show_pos_reference = fields.Boolean(related='company_id.show_pos_reference')
