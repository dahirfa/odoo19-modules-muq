from odoo import api, models


class MCPPrompt(models.Model):

    _inherit = 'muk_mcp.prompt'

    @api.model
    def get_prompt(self, name, arguments=None):
        return super().get_prompt(name, self._mcp_filter_arguments(dict(arguments or {})))
