# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from psycopg2.errors import CheckViolation

from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestResUsers(TransactionCase):

    def test_update_user_valid_idle_time(self):
        """A positive idle time is stored."""
        user = self.env.user
        user.write({'enable_idle': True, 'idle_time': 15})
        self.env.flush_all()
        self.assertEqual(user.idle_time, 15)
        self.assertTrue(user.enable_idle)

    @mute_logger('odoo.sql_db')
    def test_update_user_invalid_idle_time(self):
        """An idle time of 0 violates the constraint."""
        with self.assertRaises(CheckViolation):
            self.env.user.write({'enable_idle': True, 'idle_time': 0})
            self.env.flush_all()

    @mute_logger('odoo.sql_db')
    def test_update_user_negative_idle_time(self):
        """A negative idle time violates the constraint."""
        with self.assertRaises(CheckViolation):
            self.env.user.write({'enable_idle': True, 'idle_time': -5})
            self.env.flush_all()


@tagged('post_install', '-at_install')
class TestIdleTimeController(HttpCase):

    def _get_idle_time(self):
        return self.make_jsonrpc_request('/get_idle_time/timer', {})

    def test_returns_minutes_when_enabled(self):
        self.env.ref('base.user_admin').write({'enable_idle': True, 'idle_time': 7})
        self.authenticate('admin', 'admin')
        self.assertEqual(self._get_idle_time(), 7)

    def test_returns_false_when_disabled(self):
        self.env.ref('base.user_admin').write({'enable_idle': False})
        self.authenticate('admin', 'admin')
        self.assertIs(self._get_idle_time(), False)
