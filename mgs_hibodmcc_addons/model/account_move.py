from odoo import api, fields, models, _, http
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class Mgs_Account_Move_Extension(models.Model):
    _inherit = 'account.move'
    
    truck_num = fields.Char(string="Truck", tracking=True)
    bill_to = fields.Many2one(string="Bill To", comodel_name="res.country.state")
    deliver_to = fields.Many2one(string="Deliver To", comodel_name="res.country.state")
    
