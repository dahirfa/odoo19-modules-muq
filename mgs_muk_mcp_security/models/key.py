import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import SQL


class MCPKey(models.Model):

    _inherit = 'muk_mcp.key'

    scope = fields.Selection(
        default='read',
    )

    expiration_date = fields.Datetime(
        string="Expires On",
        readonly=True,
    )

    def init(self):
        super().init()
        self.env.cr.execute(SQL(
            "ALTER TABLE %s ADD COLUMN IF NOT EXISTS expiration_date TIMESTAMP WITHOUT TIME ZONE",
            SQL.identifier(self._table),
        ))

    def _get_mcp_param(self, name, default):
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param(name, default))
        except (TypeError, ValueError):
            return default

    @api.model
    def _mcp_key_max_days(self):
        return max(self._get_mcp_param('muk_mcp.key_max_days', 90), 1)

    @api.model
    def _mcp_playground_key_hours(self):
        return max(self._get_mcp_param('muk_mcp.playground_key_hours', 24), 1)

    @api.model
    def _mcp_default_rate_limit(self):
        rate_limit = self._get_mcp_param('muk_mcp.rate_limit_requests', 60)
        return rate_limit if rate_limit > 0 else 60

    @api.model
    def _mcp_is_admin(self):
        return self.env.user._is_superuser() or self.env.user._is_system()

    @api.model
    def _mcp_check_recent_identity(self):
        minutes = max(self._get_mcp_param('muk_mcp.playground_identity_check', 10), 1)
        if not request or request.session.get('identity-check-last', 0) <= time.time() - minutes * 60:
            raise UserError(_(
                "For security reasons, confirm your password before creating an MCP key. "
                "Open your Preferences, go to Account Security, click \"Add MCP Key\" and "
                "enter your password, then try again within %s minutes.",
                minutes,
            ))

    @api.model
    def _authenticate_user_condition(self):
        return SQL(
            "%s AND u.share = false AND (k.expiration_date IS NULL OR k.expiration_date > NOW() AT TIME ZONE 'UTC')",
            super()._authenticate_user_condition(),
        )

    @api.model
    def generate_playground_key(self, name=None, scope='read'):
        self._mcp_check_recent_identity()
        result = super().generate_playground_key(name=name, scope=scope)
        key = self.sudo().browse(result['id'])
        key.write({
            'expiration_date': fields.Datetime.now() + timedelta(hours=self._mcp_playground_key_hours()),
        })
        result['expiration_date'] = fields.Datetime.to_string(key.expiration_date)
        return result

    @api.model
    def authenticate(self, token):
        self.env['res.users'].flush_model(['share'])
        self.flush_model(['expiration_date'])
        return super().authenticate(token)

    @api.model_create_multi
    def create(self, vals_list):
        is_admin = self._mcp_is_admin()
        if not self.env.su and not is_admin:
            raise AccessError(_("MCP keys can only be created with the key wizard."))
        max_date = fields.Datetime.now() + timedelta(days=self._mcp_key_max_days())
        for vals in vals_list:
            if is_admin:
                if 'expiration_date' not in vals:
                    vals['expiration_date'] = max_date
                continue
            vals['user_id'] = self.env.uid
            rate_limit = self._mcp_default_rate_limit()
            if not vals.get('rate_limit') or vals['rate_limit'] <= 0 or vals['rate_limit'] > rate_limit:
                vals['rate_limit'] = rate_limit
            expiration = fields.Datetime.to_datetime(vals.get('expiration_date'))
            vals['expiration_date'] = min(expiration, max_date) if expiration else max_date
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and not self._mcp_is_admin():
            if set(vals) - {'name', 'active', 'scope'}:
                raise AccessError(_("You can only rename, archive or restrict your MCP keys."))
            if vals.get('active'):
                raise AccessError(_("An archived MCP key cannot be reactivated. Create a new key instead."))
            if 'scope' in vals and vals['scope'] != 'read':
                raise AccessError(_("The scope of an MCP key can only be lowered to read only."))
        return super().write(vals)
