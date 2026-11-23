from odoo import fields, models

from odoo.addons.base.models.res_users import check_identity


class MCPKeyWizard(models.TransientModel):

    _inherit = 'muk_mcp.generate_key'

    scope = fields.Selection(
        default='read',
    )

    @check_identity
    def action_make_key(self):
        return super().action_make_key()
