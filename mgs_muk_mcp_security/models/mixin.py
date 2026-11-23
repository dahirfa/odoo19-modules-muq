from odoo import api, models

from odoo.addons.muk_mcp.tools.parser import coerce_json_value


class MCPMixin(models.AbstractModel):

    _inherit = 'muk_mcp.mixin'

    @api.model
    def _mcp_call_method(self, model, method, ids=None, args=None, kwargs=None):
        keyword = coerce_json_value(kwargs)
        if isinstance(keyword, dict) and 'context' in keyword:
            keyword = {
                **keyword,
                'context': self.env['muk_mcp.tool']._mcp_filter_context(keyword['context']),
            }
            kwargs = keyword
        return super()._mcp_call_method(model, method, ids=ids, args=args, kwargs=kwargs)
