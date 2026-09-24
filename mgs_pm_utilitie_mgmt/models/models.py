# -*- coding: utf-8 -*-

from odoo import models, fields, api

from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import calendar
class UtilityTypes(models.Model):
    _name = 'pm.utility.type'
    _description = 'Utility Types'

    name = fields.Char(required=True)
    enable_readings = fields.Boolean()
    uom_id = fields.Many2one('uom.uom', string='UOM')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    rate_per_uom = fields.Float()
    active = fields.Boolean(default=True)
    income_account_id = fields.Many2one('account.account', domain=[('account_type', '=', 'income')])
    expense_account_id = fields.Many2one('account.account', domain=[('account_type', '=', 'expense')])
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        result = super(UtilityTypes, self).create(vals_list)
        analytic_account_obj=self.env['account.analytic.account']
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        for rec in result:
            if rec.name:
                new_analytic_acc=analytic_account_obj.create({
                    'name':rec.name + " Utility",
                    'plan_id': project_plan.id,
                })
                rec.write({
                    'analytic_account_id': new_analytic_acc.id,
                })
        return result


class UtilityReadings(models.Model):
    _name = 'pm.utility.reading'
    _description = 'Utility Readings'
    _rec_name = 'sequence'
    _order='sequence desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.onchange('product_id','property_id')
    def get_last_reading_info(self):
        utility_info_obj=self.env['pm.utility.info']
        if self.enable_readings:
            prev_reading=utility_info_obj.search([('property_id.id','=',self.property_id.id),('product_id.id','=',self.product_id.id)])
            self.last_reading_date=prev_reading.last_read_date or None
            self.last_reading=prev_reading.last_read or prev_reading.opening_read
    
    @api.onchange('product_id','parent_property_id')
    def get_last_reading_info_pp(self):
        utility_info_obj=self.env['pm.utility.info']
        if self.enable_readings:
            prev_reading=utility_info_obj.search([('parent_property_id.id','=',self.parent_property_id.id),('product_id.id','=',self.product_id.id)])
            self.last_reading_date=prev_reading.last_read_date or None
            self.last_reading=prev_reading.last_read or prev_reading.opening_read
    
    
    sequence = fields.Char(string="Number", required=True, copy=False, readonly=True,tracking=True, index=True, default='New')
    date = fields.Date(default=fields.Date.today(),required=True,tracking=True)
    invoice_date_due = fields.Date(string='Due Date',default=fields.Date.today(),required=True,tracking=True)
    utility_id = fields.Many2one('pm.utility.type',tracking=True)
    uom_id = fields.Many2one('uom.uom',compute='get_info',store=True,string='Utility uom',tracking=True)
    rate_per_uom = fields.Float(compute='get_info',readonly=False,store=True,tracking=True)
    enable_readings = fields.Boolean(compute='get_info',store=True,tracking=True)
    last_reading_date=fields.Date(store=True,tracking=True)
    last_reading=fields.Float(store=True,tracking=True)
    current_reading=fields.Float(tracking=True)
    difference=fields.Float(compute='get_difference',tracking=True,store=True)
    amount=fields.Monetary(tracking=True)
    total_amount=fields.Monetary(store=True,compute='get_total_amount',tracking=True)
    parent_property_id= fields.Many2one('pm.property.parent',tracking=True)
    reading_type=fields.Selection([('in_invoice', 'in_invoice'), ('out_invoice', 'out_invoice')],string='State',default='out_invoice',readonly=True,tracking=True)
    product_id= fields.Many2one('product.product',domain=[('type','=','service')],tracking=True)
    readings_product_category=fields.Many2one('product.category',store=True,compute="get_with_date",tracking=True)
    property_id= fields.Many2one('pm.property',tracking=True,domain=[('active','in',[True,False])])
    currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True,tracking=True)
    tenant_id=fields.Many2one('res.partner',store=True,string="Current tenant",tracking=True)
    partner_id=fields.Many2one('res.partner',store=True,string="Partner",tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('cancel', 'Cancel')],
        string='State',
        default='draft',
        readonly=True,store=True,tracking=True)
    move_id = fields.Many2one('account.move',domain=[('move_type', 'in', ['out_invoice','in_invoice'])],copy=False,tracking=True)
    bill_on_date = fields.Float(compute="get_with_date")
    invices_on_date = fields.Float(compute="get_with_date")
    inv_state = fields.Selection(
        [('not_paid', 'Not Paid'), ('in_payment', 'In Payment'),('paid', 'Paid'),('partial', 'Partially Paid'),('reversed', 'Reversed'),('invoicing_legacy', 'Invoicing App Legacy')],
        related='move_id.payment_state',
        string='Payment State',
        copy=False,
        default='not_paid',store=True,
        readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence', 'New') == 'New':
                seq_date = None
                vals['sequence'] = self.env['ir.sequence'].next_by_code('pm.utility.reading') or 'New'
        result = super(UtilityReadings, self).create(vals_list)
        return result


    

    @api.depends('date')
    def get_with_date(self):
        config_obj=self.env['ir.config_parameter']
        categ_obj=self.env['product.category']
        utility_obj=self.env[self._name]
        for r in self:
            r.readings_product_category=categ_obj.sudo().search([('id','=',int(config_obj.sudo().get_param('mgs_pm_utilitie_mgmt.readings_product_category')))]).id
            date=r.date
            range=calendar.monthrange(date.year, date.month)
            r.bill_on_date=sum(utility_obj.search([('date','>=',date.replace(day=range[0]+1)),('date','<=',date.replace(day=range[1])),('reading_type','=','in_invoice'),('state','=','confirmed')]).mapped('difference')) * 80
            r.invices_on_date=sum(utility_obj.search([('date','>=',date.replace(day=range[0]+1)),('date','<=',date.replace(day=range[1])),('reading_type','=','out_invoice'),('state','=','confirmed')]).mapped('difference'))
    @api.depends('product_id')
    def get_info(self):
        for rec in self:
            if rec.product_id:
                rec.rate_per_uom= rec.product_id.list_price if rec.reading_type == "out_invoice" else rec.product_id.standard_price
            else:
                rec.rate_per_uom=0.0
            if rec.product_id.categ_id.id == rec.readings_product_category.id:
                rec.enable_readings=True
            rec.uom_id =rec.product_id.uom_id
                
    @api.depends('current_reading','last_reading')
    def get_difference(self):
        for rec in self:
            if rec.enable_readings:
                rec.difference=rec.current_reading - rec.last_reading

    @api.onchange('property_id')
    def get_tenant(self):
        tenancy_obj=self.env['pm.tenancy']
        for rec in self:
            if rec.property_id:
                rec.partner_id=tenancy_obj.search([('state','=','in_progress'),('property_id.id','=', rec.property_id.id)],limit=1).tenant_id.id or rec.property_id.tenant_id.id

    @api.depends('difference','rate_per_uom','amount')
    def get_total_amount(self):
        for rec in self:
            if rec.enable_readings:
                rec.total_amount=rec.difference * rec.rate_per_uom if rec.property_id else (rec.difference * 80) * rec.rate_per_uom
            else:
                rec.total_amount=rec.amount


    def get_invoice_journal(self):
        return self.env['account.move'].new({'move_type': 'out_invoice'})._search_default_journal()


    def action_view_move(self):
        invoices = self.mapped('move_id')
        move_type='action_move_out_invoice_type' if self.reading_type=='out_invoice' else 'action_move_in_invoice_type' 
        action = self.env.ref('account.%s'%move_type).sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.id)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = self.move_id.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    
    def create_move(self):
        move = self.env['account.move']
        for r in self:
            if r.move_id:
                return None
            elif r.total_amount==0.0:
                raise ValidationError("There's Nothing To Invoice")

            move_lines_vals = []
            partner_id = r.partner_id.id
            origin = r.sequence
            prop= " ".join((str(r.current_reading),'-',str(r.last_reading),'=',str(r.difference)))

            inserted_move = move.create({
                'partner_id': partner_id,
                'invoice_date': r.date,
                'date': r.date,
                'invoice_date_due': r.invoice_date_due,
                'move_type': 'out_invoice' if r.reading_type == 'out_invoice' else 'in_invoice',
                'currency_id': r.currency_id.id,
                'invoice_origin': origin,
                'narration': "<p>Previous reading: "+ str(r.last_reading) + " and current reading at "+ str(r.date)+" : "+ str(r.current_reading)+"</p>",
            })
            difference=None
            if r.enable_readings==True and r.property_id:
                difference=r.difference
            elif r.enable_readings==True and r.parent_property_id:
                difference=r.difference * 80
            else:
                difference=1
            move_lines_vals.append((0, 0, {
            'product_id': r.product_id.id,
            'name':  " ".join([r.product_id.name,"(%s)"%prop]),
            'quantity': difference,
            'price_unit': r.rate_per_uom if r.enable_readings else r.amount}))
            
            inserted_move.invoice_line_ids = move_lines_vals
            r.write({'move_id': inserted_move.id})
            r.move_id.action_post()

        move_type='action_move_out_invoice_type' if r.reading_type=='out_invoice' else 'action_move_in_invoice_type' 
        action = self.env.ref('account.%s'%move_type).sudo().read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = inserted_move.id
        return action



    def unlink(self):
        for rec in self:
            if rec.move_id:
                raise ValidationError("You can not delete an invoiced reading!!")
        return super(UtilityReadings, self).unlink()


    def action_confirm(self):
        utility_info_obj=self.env['pm.utility.info']
        utility_reading_obj=self.env['pm.utility.reading']
        for rec in self:
            duplicate_read=utility_reading_obj.search([('property_id.id','=',rec.property_id.id),('id','!=',rec.id),('product_id.id','=',rec.product_id.id),('date','=',rec.date)]) if rec.property_id else utility_reading_obj.search([('parent_property_id.id','=',rec.parent_property_id.id),('id','!=',rec.id),('product_id.id','=',rec.product_id.id),('date','=',rec.date)])
            if duplicate_read:
                raise ValidationError('There is another '+ rec.product_id.name +' reading with the same date!!')
            if not rec.partner_id:
                raise ValidationError("There's no Invoicing address")
            if rec.enable_readings and rec.current_reading <= rec.last_reading:
                raise ValidationError('Current reading can not be less then or equal to the previous reading!!')
            prev_reading=utility_info_obj.search([('property_id.id','=',rec.property_id.id),('product_id.id','=',rec.product_id.id)],limit=1) if rec.property_id else utility_info_obj.search([('parent_property_id.id','=',rec.parent_property_id.id),('product_id.id','=',rec.product_id.id)],limit=1)
            prev_reading.last_read_date = rec.date
            prev_reading.last_read = rec.current_reading
            rec.create_move()
            rec.write({'state': 'confirmed'})


    def action_cancel(self):
        reading_obj=self.env['pm.utility.reading']
        utility_info_obj=self.env['pm.utility.info']
        for rec in self:
            later_read=reading_obj.search([('product_id.id','=',rec.product_id.id),('property_id.id','=',rec.property_id.id),('state','=','confirmed'),('id','>',rec.id)],limit=1).sequence
            if later_read:
                raise ValidationError('Another reading '+rec.product_id.name+' for this property has been generated since this record.')
            if not rec.enable_readings:
                rec.move_id.button_draft()
                rec.move_id.name=None
                rec.move_id.unlink()
                return rec.write({'state': 'cancel'})
            if rec.state == 'draft':
                return rec.write({'state': 'cancel'})
            prev_reading=utility_info_obj.search([('property_id.id','=',rec.property_id.id),('product_id.id','=',rec.product_id.id)])
            prev_reading.last_read_date = rec.last_reading_date
            prev_reading.last_read = rec.last_reading
            rec.move_id.button_draft()
            rec.move_id.name=None
            rec.move_id.unlink()
            rec.write({'state': 'cancel'})

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})