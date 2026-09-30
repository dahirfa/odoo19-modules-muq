from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    container_delivery_order_id = fields.Many2one(
        comodel_name='container.delivery.order',
        string='Delivery Order',
        index='btree_not_null',
        ondelete='set null',
        copy=False,
        readonly=True,
        help="Delivery Order whose containers are billed for demurrage on this invoice.",
    )
