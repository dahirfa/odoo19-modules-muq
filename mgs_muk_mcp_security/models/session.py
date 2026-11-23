from odoo import _, models
from odoo.exceptions import AccessError


class MCPSession(models.Model):

    _inherit = 'muk_mcp.session'

    def write(self, vals):
        if not self.env.su and not (self.env.user._is_superuser() or self.env.user._is_system()):
            if set(vals) != {'active'} or vals['active']:
                raise AccessError(_("You can only revoke your MCP sessions."))
        return super().write(vals)
