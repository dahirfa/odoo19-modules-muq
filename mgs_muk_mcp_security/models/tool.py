from odoo import api, models


class MCPTool(models.Model):

    _inherit = 'muk_mcp.tool'

    @api.model
    def _execute(self, name, arguments, env, enforce_scope):
        return super()._execute(name, self._mcp_filter_arguments(arguments), env, enforce_scope)
