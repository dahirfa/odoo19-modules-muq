# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AttendanceEmployee(models.Model):
    _inherit = "hr.employee"
    
    is_real_employee = fields.Boolean(string="Is Real Employee", default=True)
