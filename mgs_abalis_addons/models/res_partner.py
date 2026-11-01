from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    document_ids = fields.One2many(
        comodel_name='res.partner.document',
        inverse_name='partner_id',
        string='Documents',
    )

    user_type = fields.Selection(
        selection_add=[('owner', 'Owner')],
        ondelete={'owner': 'set null'},
    )

