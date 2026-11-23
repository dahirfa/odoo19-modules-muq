from odoo import _, api, models
from odoo.exceptions import AccessError

SAFE_CONTEXT_KEYS = {'lang', 'tz', 'active_test', 'allowed_company_ids'}


def _check_public_name(name):
    if isinstance(name, str) and name.startswith('_'):
        raise AccessError(_("Access to private attribute %s is not allowed in MCP code.", name))


def safe_getattr(obj, name, *default):
    _check_public_name(name)
    return getattr(obj, name, *default)


def safe_hasattr(obj, name):
    _check_public_name(name)
    return hasattr(obj, name)


class MCPSandbox(models.AbstractModel):

    _inherit = 'muk_mcp.sandbox'

    @api.model
    def _mcp_allowed_context_keys(self):
        extra = self.env['ir.config_parameter'].sudo().get_param('muk_mcp.allowed_context_keys', '')
        return SAFE_CONTEXT_KEYS | {key.strip() for key in extra.split(',') if key.strip()}

    @api.model
    def _mcp_filter_context(self, context):
        if not isinstance(context, dict):
            return context
        allowed = self._mcp_allowed_context_keys()
        return {key: value for key, value in context.items() if key in allowed}

    @api.model
    def _mcp_filter_arguments(self, arguments):
        if isinstance(arguments, dict) and isinstance(arguments.get('context'), dict):
            arguments['context'] = self._mcp_filter_context(arguments['context'])
        return arguments

    def _get_eval_context(self, arguments, env):
        eval_context = super()._get_eval_context(arguments, env)
        eval_context.update({
            'getattr': safe_getattr,
            'hasattr': safe_hasattr,
        })
        return eval_context
