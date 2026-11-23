from odoo.tools import SQL

from . import controllers
from . import models
from . import wizards


def post_init_hook(env):
    env.cr.execute(SQL(
        """
        UPDATE %s
           SET expiration_date = (NOW() AT TIME ZONE 'UTC') + make_interval(days => %s)
         WHERE expiration_date IS NULL
        """,
        SQL.identifier(env['muk_mcp.key']._table),
        env['muk_mcp.key']._mcp_key_max_days(),
    ))
