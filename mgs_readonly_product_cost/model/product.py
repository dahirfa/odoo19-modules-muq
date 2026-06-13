from odoo import fields, models, api
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class Mgs_Product_Extension(models.Model):
    _inherit = 'product.template'
    
    hide_cost_group_condition = fields.Boolean(compute='_compute_hide_cost_group_condition')

    def _compute_hide_cost_group_condition(self):
        for record in self:                       
            record.hide_cost_group_condition = self.env.user.has_group('mgs_readonly_product_cost.hide_cost_group')
