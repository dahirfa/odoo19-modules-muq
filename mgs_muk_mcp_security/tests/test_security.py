import json
import secrets
import time
from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from werkzeug.exceptions import NotFound

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.muk_mcp.models.tool import MCPTool as BaseTool
from odoo.addons.mgs_muk_mcp_security import post_init_hook
from odoo.addons.mgs_muk_mcp_security.controllers.transfer import MCPTransferControllerSecure

KEY_REQUEST = 'odoo.addons.mgs_muk_mcp_security.models.key.request'
IDENTITY_REQUEST = 'odoo.addons.base.models.res_users.request'
TRANSFER_REQUEST = 'odoo.addons.mgs_muk_mcp_security.controllers.transfer.request'


def _identity_request(checked_at):
    return SimpleNamespace(session={'identity-check-last': checked_at})


@tagged('post_install', '-at_install')
class TestMcpSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Key = cls.env['muk_mcp.key']
        cls.admin = cls.env.ref('base.user_admin')
        cls.employee = new_test_user(cls.env, login='mgs_sec_employee', groups='base.group_user')
        cls.other = new_test_user(cls.env, login='mgs_sec_other', groups='base.group_user')
        cls.emp_token, cls.emp_key = cls._make_key(cls.employee)
        cls.other_token, cls.other_key = cls._make_key(cls.other)

    @classmethod
    def _make_key(cls, user, **extra):
        token = secrets.token_urlsafe(32)
        key = cls.Key.sudo().create({
            'name': 'Security Test',
            'user_id': user.id,
            'key_hash': cls.Key._hash_key(token),
            'key_prefix': token[:8],
            'scope': 'write',
            **extra,
        })
        return token, key

    @contextmanager
    def _as_rpc_user(self, user):
        transaction = self.env.transaction
        previous = transaction.default_env
        transaction.default_env = self.env(user=user)
        try:
            yield transaction.default_env
        finally:
            transaction.default_env = previous

    def _call_tool(self, code, arguments, user=None):
        name = f'mgs_sec_tool_{secrets.token_hex(4)}'
        self.env['muk_mcp.tool'].create({
            'name': name,
            'description': name,
            'category': 'read',
            'code': code,
        })
        env = self.env(user=user or self.employee)
        text, _info = env['muk_mcp.tool']._call(name, arguments, env)
        return json.loads(text)

    def test_user_cannot_reassign_own_key(self):
        with self.assertRaises(AccessError):
            self.emp_key.with_user(self.employee).write({'user_id': self.admin.id})
        self.assertEqual(self.emp_key.user_id, self.employee)

    def test_self_write_cannot_touch_keys(self):
        new_hash = self.Key._hash_key(secrets.token_urlsafe(32))
        for command in (
            (1, self.other_key.id, {'key_hash': new_hash}),
            (1, self.emp_key.id, {'key_hash': new_hash}),
            (4, self.other_key.id),
            (0, 0, {'name': 'Injected', 'key_hash': new_hash}),
        ):
            with self.subTest(command=command), self._as_rpc_user(self.employee) as env, self.assertRaises(AccessError):
                env.user.write({'mcp_key_ids': [command]})
        self.assertFalse(self.Key.sudo().search([('key_hash', '=', new_hash)]))

    def test_self_write_cannot_touch_other_sessions(self):
        session = self.env['muk_mcp.session'].sudo().create({'user_id': self.other.id})
        with self._as_rpc_user(self.employee) as env, self.assertRaises(AccessError):
            env.user.write({
                'mcp_session_ids': [(1, session.id, {'active': False})],
            })
        self.assertTrue(session.active)

    def test_user_allowed_key_changes(self):
        key = self.emp_key.with_user(self.employee)
        key.write({'name': 'Renamed'})
        key.write({'scope': 'read'})
        with self.assertRaises(AccessError):
            key.write({'scope': 'write'})
        with self.assertRaises(AccessError):
            key.write({'rate_limit': 0})
        key.write({'active': False})
        with self.assertRaises(AccessError):
            key.write({'active': True})
        self.assertEqual((self.emp_key.name, self.emp_key.scope, self.emp_key.active), ('Renamed', 'read', False))

    def test_user_can_delete_own_key_only(self):
        with self.assertRaises(AccessError):
            self.other_key.with_user(self.employee).unlink()
        self.emp_key.with_user(self.employee).unlink()
        self.assertFalse(self.emp_key.exists())

    def test_user_direct_create_refused(self):
        with self.assertRaises(AccessError):
            self.Key.with_user(self.employee).create({
                'name': 'Direct', 'key_hash': 'x' * 64, 'user_id': self.employee.id,
            })

    def test_sudo_create_by_user_is_bound_and_capped(self):
        far = fields.Datetime.now() + timedelta(days=3650)
        key = self.Key.with_user(self.employee).sudo().create({
            'name': 'Wizard', 'key_hash': 'y' * 64, 'user_id': self.admin.id,
            'rate_limit': 0, 'expiration_date': far,
        })
        self.assertEqual(key.user_id, self.employee)
        self.assertEqual(key.rate_limit, self.Key._mcp_default_rate_limit())
        self.assertLessEqual(key.expiration_date, fields.Datetime.now() + timedelta(days=90, minutes=1))

    def test_rate_limit_cap_follows_system_default(self):
        self.env['ir.config_parameter'].sudo().set_param('muk_mcp.rate_limit_requests', 30)
        key = self.Key.with_user(self.employee).sudo().create({
            'name': 'Wizard', 'key_hash': 'z' * 64, 'rate_limit': 500,
        })
        self.assertEqual(key.rate_limit, 30)

    def test_admin_unrestricted(self):
        key = self.other_key.with_user(self.admin)
        key.write({'user_id': self.employee.id, 'scope': 'write', 'rate_limit': 0})
        self.assertEqual(self.other_key.user_id, self.employee)
        created = self.Key.with_user(self.admin).create({
            'name': 'Admin', 'key_hash': 'a' * 64, 'user_id': self.other.id, 'rate_limit': 0,
        })
        self.assertEqual((created.user_id, created.rate_limit), (self.other, 0))

    def test_session_user_can_only_revoke(self):
        session = self.env['muk_mcp.session'].sudo().create({'user_id': self.employee.id})
        own = session.with_user(self.employee)
        with self.assertRaises(AccessError):
            own.write({'user_id': self.admin.id})
        with self.assertRaises(AccessError):
            own.write({'initialized': True})
        own.action_revoke()
        self.assertFalse(session.active)
        with self.assertRaises(AccessError):
            own.write({'active': True})

    def test_tool_getattr_refuses_private_names(self):
        for code in (
            "result = getattr(env.cr.execute, '__glo' + 'bals__')",
            "result = getattr(env, '_cr')",
            "result = hasattr(env.user, '_name')",
        ):
            with self.subTest(code=code), self.assertRaises(AccessError):
                self._call_tool(code, {})

    def test_tool_public_getattr_works(self):
        result = self._call_tool(
            "result = [getattr(env.user, 'login'), getattr(env.user, 'missing', 'dflt'), hasattr(env.user, 'login')]",
            {},
        )
        self.assertEqual(result, [self.employee.login, 'dflt', True])

    def test_tool_context_is_filtered(self):
        code = "result = sorted(env.context.keys())"
        injected = {'tracking_disable': True, 'mail_notrack': True, 'mcp_name': 'spoofed', 'lang': 'en_US', 'tz': 'UTC'}
        keys = self._call_tool(code, {'context': injected})
        self.assertIn('lang', keys)
        self.assertIn('tz', keys)
        for key in ('tracking_disable', 'mail_notrack', 'mcp_name'):
            self.assertNotIn(key, keys)
        self.env['ir.config_parameter'].sudo().set_param('muk_mcp.allowed_context_keys', 'mail_notrack, default_type')
        keys = self._call_tool(code, {'context': injected})
        self.assertIn('mail_notrack', keys)
        self.assertNotIn('tracking_disable', keys)

    def test_tool_context_filtered_for_method_tools(self):
        partner = self.env['res.partner'].create({'name': 'MGS Archived', 'active': False})
        user = new_test_user(self.env, login='mgs_sec_partner', groups='base.group_user,base.group_partner_manager')
        env = self.env(user=user)
        seen = {}
        original = BaseTool._execute

        def spy(model, name, arguments, call_env, enforce_scope):
            seen.update(arguments.get('context') or {})
            return original(model, name, arguments, call_env, enforce_scope)

        with patch.object(BaseTool, '_execute', spy):
            text, _info = env['muk_mcp.tool']._call('search_read', {
                'model': 'res.partner',
                'domain': [['id', '=', partner.id]],
                'fields': ['id'],
                'context': {'active_test': False, 'tracking_disable': True},
            }, env)
        self.assertEqual(seen, {'active_test': False})
        self.assertEqual([row['id'] for row in json.loads(text)], [partner.id])

    def _get_prompt(self, body, arguments, user=None):
        name = f'mgs_sec_prompt_{secrets.token_hex(4)}'
        self.env['muk_mcp.prompt'].create({
            'name': name,
            'title': name,
            'description': name,
            'body': body,
        })
        result = self.env['muk_mcp.prompt'].with_user(user or self.employee).get_prompt(name, arguments)
        return result['messages'][0]['content']['text']

    def test_prompt_getattr_refuses_private_names(self):
        with self.assertRaises(AccessError):
            self._get_prompt("result = str(getattr(env.cr.execute, '__glo' + 'bals__'))", {})
        self.assertEqual(self._get_prompt("result = getattr(env.user, 'login')", {}), self.employee.login)

    def test_prompt_context_is_filtered(self):
        text = self._get_prompt("result = json.dumps(sorted(env.context.keys()))", {
            'context': {'tracking_disable': True, 'mcp_name': 'spoofed', 'lang': 'en_US'},
        })
        keys = json.loads(text)
        self.assertIn('lang', keys)
        self.assertNotIn('tracking_disable', keys)
        self.assertNotIn('mcp_name', keys)

    def test_call_method_context_is_filtered(self):
        user = new_test_user(self.env, login='mgs_sec_caller', groups='base.group_user,base.group_partner_manager')
        partner = self.env['res.partner'].create({'name': 'MGS Context'})
        env = self.env(user=user)
        seen = {}
        original = type(self.env['res.partner']).write

        def spy(records, vals):
            seen.update(records.env.context)
            return original(records, vals)

        with patch.object(type(self.env['res.partner']), 'write', spy):
            env['muk_mcp.tool']._call('call_method', {
                'model': 'res.partner',
                'method': 'write',
                'ids': [partner.id],
                'args': json.dumps([{'ref': 'via mcp'}]),
                'kwargs': {'context': {'tracking_disable': True, 'mcp_name': 'spoofed', 'lang': 'en_US'}},
            }, env)
        self.assertEqual(seen.get('lang'), 'en_US')
        self.assertNotIn('tracking_disable', seen)
        self.assertNotEqual(seen.get('mcp_name'), 'spoofed')
        self.assertEqual(partner.ref, 'via mcp')

    def test_authenticate_rejects_inactive_share_expired(self):
        self.assertEqual(self.Key.authenticate(self.emp_token), self.emp_key)
        portal = new_test_user(self.env, login='mgs_sec_portal', groups='base.group_portal')
        portal_token, _key = self._make_key(portal)
        self.assertFalse(self.Key.authenticate(portal_token))
        expired_token, _key = self._make_key(
            self.employee, expiration_date=fields.Datetime.now() - timedelta(minutes=1),
        )
        self.assertFalse(self.Key.authenticate(expired_token))
        self.employee.active = False
        self.assertFalse(self.Key.authenticate(self.emp_token))

    def test_scope_defaults_read_and_expiry_set(self):
        wizard = self.env['muk_mcp.generate_key'].with_user(self.employee).create({'name': 'Default'})
        self.assertEqual(wizard.scope, 'read')
        with patch(IDENTITY_REQUEST, _identity_request(time.time())):
            wizard.action_make_key()
        key = self.Key.sudo().search([('name', '=', 'Default'), ('user_id', '=', self.employee.id)])
        self.assertEqual(key.scope, 'read')
        self.assertTrue(key.expiration_date)
        self.assertLessEqual(key.expiration_date, fields.Datetime.now() + timedelta(days=90, minutes=1))
        self.assertEqual(self.Key.sudo().create({'name': 'Plain', 'key_hash': 'b' * 64}).scope, 'read')

    def test_playground_requires_identity_check(self):
        key_model = self.Key.with_user(self.employee)
        with self.assertRaises(UserError):
            key_model.generate_playground_key(name='No request')
        with patch(KEY_REQUEST, _identity_request(time.time() - 11 * 60)), self.assertRaises(UserError):
            key_model.generate_playground_key(name='Stale')
        with patch(KEY_REQUEST, _identity_request(time.time() - 60)):
            result = key_model.generate_playground_key(name='Fresh')
        key = self.Key.sudo().browse(result['id'])
        self.assertEqual((key.user_id, key.scope), (self.employee, 'read'))
        self.assertLessEqual(key.expiration_date, fields.Datetime.now() + timedelta(hours=24, minutes=1))

    def test_connect_wizard_identity_and_read_only(self):
        wizard = self.env['muk_mcp.connect'].with_user(self.employee).create({})
        with patch(IDENTITY_REQUEST, _identity_request(0)):
            action = wizard.action_generate_key()
        self.assertEqual(action['res_model'], 'res.users.identitycheck')
        self.assertFalse(wizard.bearer_key)
        recent = _identity_request(time.time())
        with patch(IDENTITY_REQUEST, recent), patch(KEY_REQUEST, recent):
            wizard.action_generate_key()
        self.assertTrue(wizard.bearer_key)
        key = self.Key.authenticate(wizard.bearer_key)
        self.assertEqual((key.user_id, key.scope), (self.employee, 'read'))

    def test_key_wizard_requires_identity_check(self):
        Wizard = self.env['muk_mcp.generate_key'].with_user(self.employee)
        wizard = Wizard.create({'name': 'Wizard RPC', 'scope': 'write'})
        with self.assertRaises(UserError):
            wizard.action_make_key()
        with patch(IDENTITY_REQUEST, _identity_request(time.time() - 11 * 60)):
            action = wizard.action_make_key()
        self.assertEqual(action['res_model'], 'res.users.identitycheck')
        self.assertFalse(self.Key.sudo().search([('name', '=', 'Wizard RPC')]))
        with patch(IDENTITY_REQUEST, _identity_request(time.time())):
            action = wizard.action_make_key()
        self.assertEqual(action['res_model'], 'muk_mcp.key.show')
        key = self.Key.sudo().search([('name', '=', 'Wizard RPC')])
        self.assertEqual((key.user_id, key.scope), (self.employee, 'write'))
        self.assertEqual(self.Key._hash_key(action['context']['default_key']), key.key_hash)

    def test_connect_wizard_hidden_from_other_users(self):
        wizard = self.env['muk_mcp.connect'].with_user(self.employee).create({})
        wizard.bearer_key = 'secret-test-value'
        Connect = self.env['muk_mcp.connect'].with_user(self.other)
        self.assertFalse(Connect.search([('id', '=', wizard.id)]))
        with self.assertRaises(AccessError):
            Connect.browse(wizard.id).read(['bearer_key'])
        self.assertEqual(type(self.env['muk_mcp.connect'])._transient_max_hours, 0.1)

    def test_log_open_record_uses_user_rights(self):
        param = self.env['ir.config_parameter'].sudo().search([], limit=1)
        log = self.env['muk_mcp.log'].sudo().create({
            'user_id': self.employee.id, 'method': 'tools/call',
            'model_name': 'ir.config_parameter', 'res_id': param.id,
        })
        action = log.with_user(self.employee).action_open_record()
        self.assertEqual(action['tag'], 'display_notification')
        partner = self.env['res.partner'].create({'name': 'MGS Visible'})
        log.sudo().write({'model_name': 'res.partner', 'res_id': partner.id})
        action = log.with_user(self.employee).action_open_record()
        self.assertEqual((action['res_model'], action['res_id']), ('res.partner', partner.id))

    def test_transfer_checks_token_before_body(self):
        httprequest = MagicMock(method='PUT')
        type(httprequest).files = property(lambda _self: self.fail('files read before token check'))
        httprequest.get_data.side_effect = lambda *a, **k: self.fail('body read before token check')
        fake_request = MagicMock(httprequest=httprequest)
        fake_request.env = {'muk_mcp.transfer': MagicMock(_redeem=MagicMock(return_value=self.env['muk_mcp.transfer']))}
        with patch(TRANSFER_REQUEST, fake_request), self.assertRaises(NotFound):
            MCPTransferControllerSecure().transfer('invalid-token')

    def test_post_init_hook_backfills_expiry(self):
        _token, key = self._make_key(self.employee, expiration_date=False)
        self.assertFalse(key.expiration_date)
        post_init_hook(self.env)
        key.invalidate_recordset(['expiration_date'])
        self.assertTrue(key.expiration_date)
        self.assertGreater(key.expiration_date, fields.Datetime.now() + timedelta(days=89))
