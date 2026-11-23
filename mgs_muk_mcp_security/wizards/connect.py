from odoo import _, models

from odoo.addons.base.models.res_users import check_identity


class Connect(models.TransientModel):

    _inherit = 'muk_mcp.connect'
    _transient_max_hours = 0.1

    @check_identity
    def action_generate_key(self):
        self.ensure_one()
        result = self.env['muk_mcp.key'].generate_playground_key(
            name=_('Connect AI'), scope='read',
        )
        self.bearer_key = result['plaintext']
        return {
            'type': 'ir.actions.act_window',
            'name': _('Connect AI'),
            'res_model': self._name,
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
