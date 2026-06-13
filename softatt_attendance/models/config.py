from odoo import models, fields, api
import requests
import json
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class IrConfigSettings(models.Model):
    _inherit = 'ir.config_parameter'
    
    
    def _softatt_authenticate(self):
        username    = self.sudo().get_param('softatt_attendance.att_username')
        url         = self.sudo().get_param('softatt_attendance.att_server_url')
        db          = self.sudo().get_param('softatt_attendance.att_db')
        password    = self.sudo().get_param('softatt_attendance.att_password')
        full_url    = "%s/web/session/authenticate"%url
        payload     = json.dumps({
        "params": {
            "db"        : db,
            "login"     : username,
            "password"  : password
        }})
        request = requests.request("GET", full_url, headers={'Content-Type': 'application/json'}, data=payload)
        response=json.loads(request.text)
        if not response.get('result', False):
            _logger.error("Invalid Credentials or Error in the authentication")
            raise ValidationError("Invalid credentials")
        session_id=request.cookies.get('session_id')
        return session_id

MODES = [
    ('api','API'),
    ('dblink','DB-Link')
]
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    softatt_comm_mode= fields.Selection(MODES, default='api', required=True,  string='Attendance Communication Mode', 
                                        config_parameter='softatt_attendance.softatt_comm_mode')
    att_server_url  = fields.Char(string='Url', 
                                  config_parameter='softatt_attendance.att_server_url')
    att_username    = fields.Char(string='Username',
                                  config_parameter='softatt_attendance.att_username')
    att_password    = fields.Char(string='Password',
                                  config_parameter='softatt_attendance.att_password')
    att_db          = fields.Char(string='Database',
                                  config_parameter='softatt_attendance.att_db')
    att_limit       = fields.Integer(string='Request Limit', 
                                     config_parameter='softatt_attendance.att_limit')
    module_softatt_lateness_deductions       = fields.Boolean(string='Use Lateness Deductions')

    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        config_param = self.env['ir.config_parameter'].sudo()
        config_param.set_param('softatt_attendance.softatt_comm_mode',   self.softatt_comm_mode)
        config_param.set_param('softatt_attendance.att_server_url',   self.att_server_url)
        config_param.set_param('softatt_attendance.att_username',     self.att_username)
        config_param.set_param('softatt_attendance.att_password',     self.att_password)
        config_param.set_param('softatt_attendance.att_db',           self.att_db)
        config_param.set_param('softatt_attendance.att_limit',        self.att_limit)