from odoo import _, models
from odoo.exceptions import AccessError


class MCPLog(models.Model):

    _inherit = 'muk_mcp.log'

    def action_open_record(self):
        self.ensure_one()
        if not self.model_name or not self.res_id:
            return
        try:
            exists = (
                self.model_name in self.env
                and self.env[self.model_name].search_count([('id', '=', self.res_id)], limit=1)
            )
        except AccessError:
            exists = False
        if not exists:
            return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
                'title': _("Record not available"),
                'message': _("%(model)s(%(id)s) no longer exists or you cannot access it.", model=self.model_name, id=self.res_id),
                'type': 'warning',
            }}
        return super().action_open_record()
