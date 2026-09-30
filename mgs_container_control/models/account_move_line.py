from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    container_control_id = fields.Many2one(
        comodel_name='container.control',
        string='Container',
        index='btree_not_null',
        ondelete='restrict',
        help="Container whose demurrage days are billed on this line. "
             "The line quantity is the number of demurrage days it invoices.",
    )
