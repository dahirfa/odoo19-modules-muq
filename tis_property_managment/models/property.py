# -*- coding: utf-8 -*-

from pyclbr import readmodule
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ParentProperty(models.Model):
    _name='pm.property.feature'
    _description="Property Feature"

    name = fields.Char()
    color = fields.Integer()

class ParentProperty(models.Model):
    _name='pm.property.parent'

    
    image_1920 = fields.Binary("Image",tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,tracking=True)
    name = fields.Char(required=True,tracking=True)
    landlord_id=fields.Many2one('res.partner',tracking=True, string="Landlord", domain=[('is_landlord', '=', True)],required=True)
    country_id = fields.Many2one('res.country',string='Country',tracking=True, ondelete='restrict')
    street = fields.Char(required=True,tracking=True)
    street2 = fields.Char(tracking=True)
    city = fields.Char(tracking=True)
    property_ids=fields.One2many('pm.property','parent_property_id')
    active = fields.Boolean(default=True,tracking=True)


    _unique_name = models.Constraint('unique(Name)', 'Name already exists!')



class PropertyType(models.Model):
    _name = 'pm.property.type'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char('Type')



class Property(models.Model):
    _name = 'pm.property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _rec_name='display_name'

    image_1920 = fields.Binary("Image",tracking=True)
    company_id = fields.Many2one('res.company',tracking=True, string='Company', default=lambda self: self.env.company)
    display_name=fields.Char(compute='set_rec_name',store=True,tracking=True)
    code = fields.Char(string="Property Reference", required=True, copy=False,tracking=True, readonly=True, index=True, default='New')
    name = fields.Char(required=True,tracking=True)
    parent_property_id=fields.Many2one('pm.property.parent',tracking=True)

# THESE FIELDS WILL TAKE VALUE FROM PARENT_PROPERTY IF THERE"S

# START

    country_id = fields.Many2one('res.country',
                                 string='Country',
                                 ondelete='restrict',readonly=False,
                                 compute='get_country_id', store=True,tracking=True)
    street = fields.Char(readonly=False, compute='get_street', store=True,tracking=True)
    street2 = fields.Char(readonly=False, compute='get_street2', store=True,tracking=True)
    city = fields.Char(readonly=False, compute='get_city', store=True,tracking=True)
    landlord_id = fields.Many2one('res.partner', string="Landlord", domain=[('is_landlord', '=', True)],
                                compute='get_landlord_id',readonly=False, store=True,tracking=True)

    date = fields.Date(default=fields.Date.today(),tracking=True)
    currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True,tracking=True)
    rent_price = fields.Monetary('Rent Price',tracking=True)
    active = fields.Boolean(default=True,tracking=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('available', 'Available'),
        ('on_lease', 'On Lease'),
        ('booked', 'Booked'),
        ('close', 'Close')
    ], default='draft', string='Status', store=True,tracking=True)
    type_id = fields.Many2one('pm.property.type', "Type",tracking=True)
    furnishing = fields.Selection(
        [('none', 'None'),
         ('semi_furnished', 'Semi Furnished'),
         ('full_furnished', 'Full Furnished')],
        default='none', string='Furnishing',tracking=True)
    facing = fields.Selection(
        [('north', 'North'), ('south', 'South'),
         ('east', 'East'), ('west', 'West')],
        string='Facing',tracking=True)
    bedrooms = fields.Char("Bedrooms",default="1",tracking=True)
    bathrooms = fields.Char("Bathrooms",default="1",tracking=True)
    feature_ids = fields.Many2many('pm.property.feature')
    analytic_acc_id = fields.Many2one('account.analytic.account',
                                      string='Analytic Account',tracking=True)


    enable_comm = fields.Boolean('Enable Commission',tracking=True)
    comm_type=fields.Selection([
        ('precentage','By Precentage'),
        ('fixed_cost','By Fixed Cost'),],tracking=True)
    mgmt_comm=fields.Monetary("Managment Amount",compute='calculate_commission',store=True,tracking=True)
    mgmt_precentage=fields.Float("Managment Comm %",tracking=True)
    mgmt_fix_cost=fields.Float(tracking=True)
    landlord_amount=fields.Monetary(compute='calculate_landlord_commission',store=True,tracking=True)



    tenant_id=fields.Many2one('res.partner',copy=False,string="Current tenant",tracking=True)
    tenancy_ids=fields.One2many('pm.tenancy','property_id')
    maintenance_ids=fields.One2many('pm.maintenance','property_id')
    note = fields.Text(tracking=True)


    _unique_display_name = models.Constraint('unique(display_name)', 'Name already exists!')
    
    def unlink(self):
        tenancy_obj=self.env['pm.tenancy']
        maintenance_obj=self.env['pm.maintenance']
        rent_sch_obj=self.env['pm.rent.schedule']
        for rec in self:
            existing_tenancy=tenancy_obj.search([('active','in',[True,False]),('property_id.id','=',rec.id)])
            existing_maintenance=maintenance_obj.search([('property_id.id','=',rec.id)])
            existing_rent=rent_sch_obj.search([('active','in',[True,False]),('property_id.id','=',rec.id)])
            if existing_tenancy or existing_maintenance or existing_rent:
                raise ValidationError("You can not delete this record !!")
            return super(Property, self).unlink()
        

        
    @api.depends('comm_type', 'mgmt_precentage','rent_price', 'mgmt_fix_cost')
    def calculate_commission(self):
        for data in self:
            if data.comm_type == 'precentage':
                data.mgmt_comm = data.rent_price * data.mgmt_precentage
            if data.comm_type == 'fixed_cost':
                data.mgmt_comm = data.mgmt_fix_cost

    @api.depends('mgmt_comm')
    def calculate_landlord_commission(self):
        for rec in self:
            if rec.mgmt_comm!=0.00:
                rec.landlord_amount = rec.rent_price - rec.mgmt_comm
            else:
                rec.landlord_amount = rec.rent_price


    @api.depends('parent_property_id')
    def get_country_id(self):
        for rec in self:
            if rec.parent_property_id:
                rec.country_id = rec.parent_property_id.country_id.id
            else:
                rec.country_id=rec.country_id
    @api.depends('parent_property_id')
    def get_street(self):
        for rec in self:
            if rec.parent_property_id:
                rec.street = rec.parent_property_id.street
            else:
                rec.street = rec.street

    @api.depends('parent_property_id')
    def get_street2(self):
        for rec in self:
            if rec.parent_property_id:
                rec.street2 = rec.parent_property_id.street2
            else:
                rec.street2 = rec.street2

    @api.depends('parent_property_id')
    def get_city(self):
        for rec in self:
            if rec.parent_property_id:
                rec.city = rec.parent_property_id.city
            else:
                rec.city = rec.city


    @api.depends('parent_property_id')
    def get_landlord_id(self):
        for rec in self:
            if rec.parent_property_id:
                rec.landlord_id = rec.parent_property_id.landlord_id
            else:
                rec.landlord_id = rec.landlord_id




    @api.depends('code','name','parent_property_id')
    def set_rec_name(self):
        for rec in self:
            if rec.parent_property_id:
                rec.display_name=(rec.parent_property_id.name or '')+" / " + (rec.name or '')
            elif not rec.parent_property_id:
                rec.display_name=(rec.code or '')+" / " + (rec.name or '')
    def action_open(self):
        self.state = 'available'

    def action_draft(self):
        self.state = 'draft'

    def action_close(self):
        tenancy_obj=self.env['pm.tenancy'].search([('property_id','=',self.id),('state','=','in_progress')],limit=1)
        if tenancy_obj:
            raise ValidationError("This Property Is Currently Onlease. See Tenancy : "+ tenancy_obj.code)
        else:
            self.state = 'close'
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                seq_date = None
                # if 'date' in vals:
                # 	seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                vals['code'] = self.env['ir.sequence'].next_by_code('pm.property') or 'New'
        result = super(Property, self).create(vals_list)

        analytic_account_obj=self.env['account.analytic.account']
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        for rec in result:
            if rec.parent_property_id:
                new_analytic_acc=analytic_account_obj.create({
                    'name':rec.parent_property_id.name+" / " + rec.code,
                    'plan_id': project_plan.id,
                })
            elif not rec.parent_property_id:
                new_analytic_acc=analytic_account_obj.create({
                'name':rec.code,
                'plan_id': project_plan.id,
                })
            rec.write({
                'analytic_acc_id': new_analytic_acc.id,
            })
        return result

