# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ServiceLine(models.Model):
	_name = 'pm.service.line'


	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	rent_schedule_id=fields.Many2one('pm.rent.schedule',ondelete='cascade')
	product_id=fields.Many2one('product.product',string="Product",required=True)
	tenancy_id=fields.Many2one('pm.tenancy',string="Tenancy")
	description=fields.Char()
	currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True)
	price=fields.Monetary(required=True)
	mgmt_comm=fields.Float("Mgmt %",required=True,default=100.0)
	landlord_comm=fields.Float("LL %",compute='_calculate_landlord_comm',store=True)
	landlord_comm_amount=fields.Monetary("LL Amount",readonly=True,compute='_calculate_landlord_comm_amount',store=True)
	mgmt_comm_amount=fields.Monetary("Mgmt Amount",readonly=True,compute='_calculate_mgmt_comm_amount',store=True)

	@api.depends('price')
	def _calculate_landlord_comm(self):
		for r in self:
			if r.mgmt_comm != 0.00:
				r.landlord_comm= 100.00 - r.mgmt_comm
			else:
				r.landlord_comm=100.00 - 0.00
	@api.depends('price','mgmt_comm')
	def _calculate_mgmt_comm_amount(self):
		for r in self:
			if r.mgmt_comm != 0.00:
				r.mgmt_comm_amount=r.price * r.mgmt_comm
			else:
				r.mgmt_comm_amount=0.00
	@api.depends('mgmt_comm_amount')
	def _calculate_landlord_comm_amount(self):
		for r in self:
			if r.mgmt_comm_amount:
				r.landlord_comm_amount=r.price - r.mgmt_comm_amount
			else:
				r.landlord_comm_amount=r.price - 0.00

		
class RentSchedule(models.Model):
	_name = 'pm.rent.schedule'
	_order = 'date'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	@api.onchange('letting_comm')
	def _onchange_letting_comm(self):
		if self.letting_comm == False:
			self.letting_comm_precentage=None
			self.letting_comm_Amount=None
			self.new_landlord_amount=None

	#RENT SCHEDULE

	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,tracking=True)
	name=fields.Char(compute='_get_name',tracking=True)
	tenancy_id=fields.Many2one('pm.tenancy',tracking=True,string="Tenancy",ondelete='cascade',required=True)
	property_id=fields.Many2one('pm.property',related='tenancy_id.property_id',store=True,tracking=True)
	currency_id = fields.Many2one('res.currency', "Currency",readonly=True,related='tenancy_id.currency_id',tracking=True,store=True)
	date=fields.Date(store=True,tracking=True)
	landlord_id=fields.Many2one('res.partner',readonly=True,related='tenancy_id.landlord_id',store=True,tracking=True)
	tenant_id=fields.Many2one('res.partner',related='tenancy_id.tenant_id',store=True,tracking=True)
	amount=fields.Monetary(compute="get_amount",store=True,tracking=True)
	landlord_amount=fields.Monetary(related='tenancy_id.landlord_amount',tracking=True,store=True)
	mgmt_comm=fields.Monetary(related='tenancy_id.mgmt_comm',store=True,tracking=True)
	service_lines=fields.One2many('pm.service.line','rent_schedule_id',readonly=False,tracking=True)
	cheque_detail=fields.Char(tracking=True)
	note=fields.Text(tracking=True)
	invoice_id = fields.Many2one("account.move", domain=[('move_type', '=', 'out_invoice')],tracking=True)
	bill_id = fields.Many2one("account.move", domain=[('move_type', '=', 'in_invoice')],tracking=True)
	enable_comm=fields.Boolean(related='tenancy_id.enable_comm',tracking=True)
	inv_posted=fields.Boolean(tracking=True)
	inv_status=fields.Selection([
		('Paid','Paid'),
		('Partially Paid','Partially Paid'),
		('Not Paid','Not Paid'),
	],compute='_get_payment_state',tracking=True)

	letting_comm=fields.Boolean(tracking=True)
	letting_comm_precentage=fields.Float("Letting Commission %",tracking=True)
	
	letting_comm_Amount=fields.Monetary("Letting Commission Amount",compute='calculate_letting_comm',store=True,tracking=True)

	new_landlord_amount= fields.Monetary("Landlord Amount",compute='calculate_letting_comm_landlord',store=True,tracking=True)
	# broker_id=fields.Many2one('res.partner')


	amount_residual=fields.Monetary(compute='_get_amount_residual',tracking=True)
	bill_posted=fields.Boolean(tracking=True)
	bill_paid=fields.Boolean(tracking=True)
	total_services_price=fields.Float(compute='calculate_total_services_price',tracking=True,string="Total Services  Price",store=True,related='tenancy_id.total_services_price')
	total_services_amount_for_landlord=fields.Float(compute='calculate_total_services_amount_for_landlord',tracking=True,string="Total LL Amount",store=True,related='tenancy_id.total_services_amount_for_landlord')
	active=fields.Boolean(default=True,tracking=True)

	@api.depends('tenancy_id')
	def get_amount(self):
		for rec in self:
			rec.amount= rec.tenancy_id.rent_price_per_period



	@api.depends('letting_comm_precentage')
	def calculate_letting_comm(self):  

		for data in self:
			if data.letting_comm_precentage != 0.00:
				data.letting_comm_Amount = data.amount * data.letting_comm_precentage
			else:
				data.letting_comm_Amount=0.00
	@api.depends('letting_comm_Amount','letting_comm_precentage')
	def calculate_letting_comm_landlord(self):  

		for data in self:
			if data.letting_comm_precentage != 0.00:
				data.new_landlord_amount=data.amount - data.letting_comm_Amount
			else:
				data.new_landlord_amount=data.amount

	@api.depends('tenancy_id','property_id','date')
	def _get_name(self):
		for r in self:
			r.name=(r.tenancy_id.code or '')+" | "+ (r.property_id.code or '')+" | "+ str(r.date)
	

	@api.depends('invoice_id')
	def _get_payment_state(self):
		for r in self:
			if r.invoice_id.payment_state=='paid' or r.invoice_id.payment_state=='in_payment':
				r.inv_status='Paid'
			elif r.invoice_id.payment_state=='partial':
				r.inv_status='Partially Paid'
			else:
				r.inv_status='Not Paid'
	@api.depends('invoice_id')
	def _get_amount_residual(self):
		for r in self:
			if r.invoice_id.amount_residual != 0.0:
				r.amount_residual=r.invoice_id.amount_residual
			else:
				r.amount_residual=0.0




	"""Smart Buttons"""
	def action_view_invoice(self):
		invoices = self.mapped('invoice_id')
		action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
		if len(invoices) > 1:
			action['domain'] = [('id', 'in', invoices.id)]
		elif len(invoices) == 1:
			action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
			action['res_id'] = self.invoice_id.id
		else:
			action = {'type': 'ir.actions.act_window_close'}
		return action

	def action_view_bill(self):
		invoices = self.mapped('bill_id')
		action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
		if len(invoices) > 1:
			action['domain'] = [('id', 'in', invoices.id)]
		elif len(invoices) == 1:
			action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
			action['res_id'] = self.bill_id.id
		else:
			action = {'type': 'ir.actions.act_window_close'}
		return action

	# def action_view_broker_bill(self):
	# 	invoices = self.mapped('broker_bill_id')
	# 	action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
	# 	if len(invoices) > 1:
	# 		action['domain'] = [('id', 'in', invoices.id)]
	# 	elif len(invoices) == 1:
	# 		action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
	# 		action['res_id'] = self.broker_bill_id.id
	# 	else:
	# 		action = {'type': 'ir.actions.act_window_close'}
	# 	return action
	# def action_view_bill(self):
	# 	self.sudo()
	# 	self.sudo()._action_view_bill()
	"""Smart Buttons"""


	"""Create Bill And Invoice"""

	def get_invoice_journal(self):
		return self.env['account.move'].new({'move_type': 'out_invoice'})._search_default_journal()
	def get_bill_journal(self):
		return self.env['account.move'].new({'move_type': 'in_invoice'})._search_default_journal()

	

	def create_bill(self):
		if self.tenancy_id.enable_comm==False:
			return True
		if self.bill_id:
			return True
		if self.new_landlord_amount<=0.0 and self.letting_comm:
			return True


		service_lines_vals = []
		invoice = self.env['account.move']
		bill_lines_vals = []
		account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.expense_account_id')))]).id

		for r in self:
			partner_id = r.landlord_id.id
			currency_id = r.currency_id.id
			user_id = r.create_uid.id
			origin = r.tenancy_id.code
			tenancy = r.tenancy_id.code
			tenancy_id = r.tenancy_id
			property = r.tenancy_id.property_id.display_name
			journal_id = r.get_bill_journal()
			analytic_account_id = r.property_id.analytic_acc_id.id
			date = r.date
			ref = tenancy+"|"+ str(date)

			landlord_amount=0.0
			des=None
			if r.new_landlord_amount > 0.0 and r.letting_comm:
				landlord_amount=r.new_landlord_amount
				des="Letting Commission"
			else:
				landlord_amount=r.landlord_amount
				des="Rent From ("+ property+")"


			inserted_bill = invoice.create({
				'partner_id': partner_id,
				'invoice_date': date,
				'journal_id': journal_id.id,
				'user_id': user_id,
				'ref':ref,
				'currency_id': currency_id,
				'move_type': 'in_invoice',
				'invoice_origin': origin,
				'narration': origin,
			})
			
			bill_lines_vals.append((0, 0, {
				'name': des,
				'account_id': account_id,
				'analytic_distribution': {str(analytic_account_id): 100},
				'price_unit': landlord_amount,}))
			for line in tenancy_id.service_lines:
				if line.landlord_comm_amount != 0.00:
					bill_lines_vals.append((0, 0, {
						'product_id': line.product_id.id,
						'name':  line.product_id.name+" ("+property+")" or line.description,
						'account_id': line.product_id.property_account_expense_id.id or  line.product_id.categ_id.		property_account_expense_categ_id.id or account_id,
						'analytic_distribution': {str(analytic_account_id): 100},
						'price_unit': line.landlord_comm_amount,}))
			inserted_bill.invoice_line_ids = bill_lines_vals
			# inserted_bill.invoice_line_ids = service_lines_vals
			self.write({
				'bill_id': inserted_bill.id,
			})

			r.bill_id.action_post();
		action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
		action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
		action['res_id'] = inserted_bill.id
		# return action


	def create_entries(self):
		self.create_bill()

		if self.invoice_id:
			return True
		service_lines_vals = []
		invoice = self.env['account.move']
		invoice_lines_vals = []
		account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.income_account_id')))]).id
		service_account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.services_income_account_id')))]).id
		for r in self:
			partner_id = r.tenant_id.id
			currency_id = r.currency_id.id
			user_id = r.create_uid.id
			origin = r.tenancy_id.code
			tenancy = r.tenancy_id.code
			tenancy_id = r.tenancy_id
			property = r.tenancy_id.property_id.display_name
			journal_id = r.get_invoice_journal()
			analytic_account_id = r.property_id.analytic_acc_id.id
			date = r.date
			ref = tenancy+"|"+str(date)
			inserted_invoice = invoice.create({
				'partner_id': partner_id,
				'invoice_date': date,
				'journal_id': journal_id.id,
				'user_id': user_id,
				'ref':ref,
				'currency_id': currency_id,
				'move_type': 'out_invoice',
				'invoice_origin': origin,
				'narration': origin,
			})

			invoice_lines_vals.append((0, 0, {
				'name': "Rent Cost For ("+ property+")",
				'analytic_distribution': {str(analytic_account_id): 100},
				'account_id': account_id,
				'price_unit': r.amount,}))
			for line in tenancy_id.service_lines:
				invoice_lines_vals.append((0, 0, {
					'product_id': line.product_id.id,
					'name': line.product_id.name +"("+ property +")" or line.description,
					'account_id':line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id  or service_account_id,
					'analytic_distribution': {str(analytic_account_id): 100},
					'price_unit': line.price,}))
			inserted_invoice.invoice_line_ids = invoice_lines_vals

			self.write({
				'invoice_id': inserted_invoice.id,
			})

			r.invoice_id.action_post();
		action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
		action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
		action['res_id'] = inserted_invoice.id
		return action 