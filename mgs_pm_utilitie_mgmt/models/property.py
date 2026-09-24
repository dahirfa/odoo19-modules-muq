from odoo import models, fields, api

from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class UtilityInfo(models.Model):
    _name = 'pm.utility.info'

    parent_property_id=fields.Many2one('pm.property.parent')
    property_id=fields.Many2one('pm.property')
    utility_id=fields.Many2one('pm.utility.type')
    product_id=fields.Many2one('product.product',domain=[('type','=','service')])
    opening_read=fields.Float()
    last_read=fields.Float()
    last_read_date=fields.Date()
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)


class ParentProperty(models.Model):
    _inherit ='pm.property.parent'
    utility_info_ids = fields.One2many('pm.utility.info', 'parent_property_id')
    @api.model_create_multi
    def create(self, vals_list):
        result = super(ParentProperty, self).create(vals_list)
        
        readings_product_category = self.env['ir.config_parameter'].sudo().get_param('mgs_pm_utilitie_mgmt.readings_product_category')
        products_obj=self.env['product.product']
        for rec in result:
            utilities_list=[]
            utilities=products_obj.search([('categ_id.id','=',int(readings_product_category))])
            for utility in utilities:
                utilities_list.append((0, 0, {
                                                'product_id':utility.id,
                                                'opening_read':0.0,
                                                'last_read_date':None,
                                                'last_read':0.0}))
            rec.write({'utility_info_ids':utilities_list,})
        return result
class Property(models.Model):
    _inherit = 'pm.property'

    utility_info_ids = fields.One2many('pm.utility.info', 'property_id')
    @api.model_create_multi
    def create(self, vals_list):
        result = super(Property, self).create(vals_list)
        
        readings_product_category = self.env['ir.config_parameter'].sudo().get_param('mgs_pm_utilitie_mgmt.readings_product_category')
        products_obj=self.env['product.product']
        for rec in result:
            utilities_list=[]
            utilities=products_obj.search([('categ_id.id','=',int(readings_product_category))])
            for utility in utilities:
                utilities_list.append((0, 0, {
                                                'product_id':utility.id,
                                                'opening_read':0.0,
                                                'last_read_date':None,
                                                'last_read':0.0}))
            rec.write({'utility_info_ids':utilities_list,})
        return result


