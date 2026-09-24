from odoo import models, fields, api



class InheritPartner(models.Model):
	_inherit = 'res.partner'
	
	is_landlord = fields.Boolean(compute='check_for_parent_id',readonly=False ,store=True)
	is_tenant = fields.Boolean(compute='check_for_parent_id',store=True)

	@api.depends('parent_id')
	def check_for_parent_id(self):
		for r in self:
			if r.is_landlord==True and r.parent_id:
				r.is_landlord=False
			if r.is_tenant==True and r.parent_id:
				r.is_tenant=False