# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta 
import logging
_logger = logging.getLogger(__name__)



class truck(models.Model):
    _name = 'truck.dispatch'
    _description = 'Trucks'
    _inherit = ['mail.thread']

    @api.onchange('vendor_pays_for_expenses')
    def onchange_vendor_pays_for_expenses(self):
        if self.vendor_pays_for_expenses:
            self.commission=0.05
        else:
            self.commission=0.1

    

    company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='Unit No.',tracking=True)
    eld = fields.Char(string='Eld-ID No.')
    make_id = fields.Many2one('make.dispatch', string='Make')
    plate = fields.Char(string='Plate No.',tracking=True)
    trailer_id = fields.Many2one('trailer.dispatch', string='Trailer',tracking=True)
    type_id = fields.Many2one('truck_type.dispatch', string='Type',tracking=True)
    trucking_no = fields.Char(string='Trucking No.',tracking=True)
    country = fields.Char(string='Country')
    state = fields.Char(string='State')
    vin = fields.Char(string='Vin No.')
    driver_id = fields.Many2one('res.partner',tracking=True, string='Driver', domain=[('is_driver','=', True)])
    ifta_id = fields.Many2one('ifta.dispatch', string='IFTA group')


    truck_owner = fields.Selection([ ('type1', 'Company Truck'),('type2', "Third Party Truck"),],'Truck Owner', default='type1',tracking=True)
    partner_id = fields.Many2one('res.partner', string='Vendor',tracking=True)
    commission = fields.Float(default=0.1,tracking=True)
    vendor_pays_for_expenses = fields.Boolean('Vendor Pays For Expenses',tracking=True)


    rpm_loaded = fields.Float(string='Rate/Mile (Loaded)')
    rpm_empty = fields.Float(string='Rate/Mile (Empty)')
    rph = fields.Char(string='Rate/Hour')
    Weight = fields.Char(string='Weight (Lbs)')
    is_working = fields.Boolean('Still Working',default=True,tracking=True)
    note = fields.Text('Note')

 

class Trailer(models.Model):
    _name = 'trailer.dispatch'
    _description = 'Trailers'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name = fields.Char(string='Unit No.')
    trucking_no = fields.Char(string='Trucking No.')
    make_id = fields.Many2one('make.dispatch', string='Make')
    plate = fields.Char(string='Plate No.')
    vin = fields.Char(string='Vin No.')
    country = fields.Char(string='Country')
    state = fields.Char(string='State')
    type_id = fields.Many2one('trailer_type.dispatch', string='Type')
    equipment = fields.Char(string='Equipment')
    Weight = fields.Char(string='Weight (Lbs)')
    is_working = fields.Boolean('Still Working')
    is_third_party_trailer = fields.Boolean('Is a Third Party Trailer')
    note = fields.Text('Note')



class Driver(models.Model):
    _inherit = "res.partner"
    is_driver = fields.Boolean(string='Driver', help="Check this box if this contact is a Driver.")

# Account.move inherit
class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    truck_id = fields.Many2one('truck.dispatch',related='trip_id.truck_id',store=True)
    billed = fields.Boolean(string='billed',related='move_line_id.trip_bill_line',store=True)
    load_id=fields.Many2one('load.dispatch',related='move_line_id.load_id',store=True)
    trip_id=fields.Many2one('load.line.dispatch',related='move_line_id.trip_id',store=True)
    mgs_bill_line_id = fields.Many2one("account.move.line")
    expense_charged = fields.Boolean( string='Expense Charged', related='mgs_bill_line_id.expense_charged', store=True)
    


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    load_id=fields.Many2one('load.dispatch')
    analytic_account_id = fields.Many2one("account.analytic.account",
    related='load_id.analytic_acc_id',
    readonly=True,
    store=True
    )
    
    trip_id = fields.Many2one(
        string='Trip',
        comodel_name='load.line.dispatch',
        ondelete='restrict',
    )
    
    trip_ids=fields.Many2many('load.line.dispatch',compute='_compute_trips',store=True)
    @api.depends('line_ids.trip_id')
    def _compute_trips(self):
        for r in self:
            r.trip_ids  = [(6, 0, r.line_ids.mapped('trip_id.id'))]
            
            
    def button_draft(self):
        for r in self:
            if r.trip_id and 'allow_action' not in self.env.context:
                raise UserError("Invoices can be modified from the 'Trips' module only!")
        return super(AccountMove, self).button_draft()

    def button_cancel(self):
        for r in self:
            if r.trip_id and 'allow_action' not in self.env.context:
                raise UserError("Invoices can be modified from the 'Trips' module only!")
        return super(AccountMove, self).button_cancel()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for r in self:
            if r.trip_id and 'allow_action' not in self.env.context:
                raise UserError("Invoices can be modified from the 'Trips' module only!")
        return res


class HEXP(models.Model):
    _inherit = 'hr.expense'

    load_id=fields.Many2one('load.dispatch')
    trip_id=fields.Many2one('load.line.dispatch')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    exp_trip_id = fields.Many2one('load.line.dispatch',readonly=False,related='expense_id.trip_id')
    trip_bill_line = fields.Boolean(string='billed',default=False)
    load_id=fields.Many2one('load.dispatch',related='move_id.load_id',readonly=True,store=True)
    trip_id=fields.Many2one('load.line.dispatch',readonly=False,compute='get_exp_trip_id',store=True)
    
    
    expense_charged = fields.Boolean(string='Expense Charged', default=False)
    

    
    @api.depends('exp_trip_id')
    def get_exp_trip_id(self):
        for r in self:
            if r.exp_trip_id and not r.trip_id:
                r.trip_id=r.exp_trip_id.id
            else:
                r.trip_id=None


    @api.onchange('analytic_distribution')
    def _onchange_analytic_account_id(self):
        for r in self:
            if r.move_id.move_type != 'entry' and r.move_id.analytic_account_id:
                r.analytic_distribution = {str(r.move_id.analytic_account_id.id) :100.0}




class Load(models.Model):
    _name = 'load.dispatch'
    _description = 'Batch'
    _order="id DESC"
    _inherit = ['mail.thread']

    name = fields.Char(string='Batch No.',tracking=True, copy=False)
    date = fields.Date(default=fields.Date.today(),tracking=True, copy=False)
    reference = fields.Char(string='Reference',tracking=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company',tracking=True, default=lambda self: self.env.company)
    customer_id = fields.Many2one('res.partner',string='Customer', required=True,tracking=True)
    goods = fields.Text(string='Goods',tracking=True)
    bill_count = fields.Integer(compute='_compute_invoice',tracking=True, string='# of Bills', copy=False, default=0)
    
    expense_count = fields.Integer(compute='_compute_expenses',tracking=True, string='# of Expenses', copy=False, default=0)
    invoice_count = fields.Integer(compute="_compute_invoice",tracking=True, string='# of Invoices', copy=False, default=0)
    rbill_count = fields.Integer(compute="_compute_invoice",tracking=True, string='# of rBills', copy=False, default=0)
    load_line_ids = fields.One2many('load.line.dispatch','load_id', copy=False)
    analytic_acc_id = fields.Many2one('account.analytic.account', string='Analytic Account',tracking=True,copy=False)
    state = fields.Selection([('new', 'New'), ('running', 'Running'), ('closed', 'Closed'), ('canceled', 'Canceled')], string='Status', readonly=True , default='new',tracking=True)
    trip_count= fields.Integer(compute='compute_trips', string='Trips', default=0,tracking=True)
    invoice_id = fields.Many2one('account.move',string='Customer Invoice' ,domain=[('move_type','=','out_invoice')], copy=False)
    billed = fields.Boolean(default=False)
    currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True)
    rate=fields.Monetary()


    
    @api.depends('load_line_ids')
    def compute_trips(self):
        for r in self:
            r.trip_count=len(r.load_line_ids)

    def start_load(self):
        return self.write({'state': 'running'})

    def cancel_load(self):
        return self.write({'state': 'canceled'})

    def close_load(self):
        return self.write({'state': 'closed'})

    def reset_to_new(self):
        return self.write({'state': 'new'})

     #Vendor Bills smart button

    def bill_create(self):
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.sudo().read()[0]
        result['context'] = {}
        result['context']['default_move_type'] = 'in_invoice'
        result['context']['default_analytic_account_id'] = self.analytic_acc_id.id
        result['context']['default_load_id'] = self.id

        journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id)
         ]
        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)

        if default_journal_id:
            result['context']['default_journal_id'] = default_journal_id.id

        result['context']['default_invoice_origin'] = self.name


        result['domain'] = [('analytic_account_id', '=', self.analytic_acc_id.id), ('move_type', '=', 'in_invoice'), ('trip_id', '=', False)]
        return result
    #Customer
    def invoice_create(self):
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.sudo().read()[0]

        result['context'] = {}
        result['context']['default_move_type'] = 'out_invoice'
        result['context']['default_analytic_account_id'] = self.analytic_acc_id.id
        result['context']['default_load_id'] = self.id
        journal_domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ]
        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
        if default_journal_id:
            result['context']['default_journal_id'] = default_journal_id.id

        result['context']['default_invoice_origin'] = self.name
        if self.customer_id:
            result['context']['default_partner_id'] = self.customer_id.id
        result['domain'] = "[('analytic_account_id', '=', " + str(self.analytic_acc_id.id) + "), ('move_type', '=', 'out_invoice')]"
        return result


    def expense_create(self):
        action = self.env.ref('hr_expense.hr_expense_actions_my_all')
        result = action.sudo().read()[0]

        result['context'] = {}
        result['context']['default_payment_mode'] = 'company_account'
        result['context']['default_analytic_distribution'] = {str(self.analytic_acc_id.id):100.0}
        result['context']['default_load_id'] = self.id
        result['domain'] = "[('load_id.id', '=', '%s')]"%self.id
        return result

    def trip_create(self):
        action = self.env.ref('mgs_dispatch.trip_list_action')
        result = action.sudo().read()[0]
        result['context'] = {}
        result['context']['default_load_id'] = self.id
        result['domain'] = "[('load_id', '=', " + str(self.id) + ")]"
        result['context']['create']=False if self.state in ('closed','canceled') else True
        return result

    def cost_and_revenue(self):
        action = self.env.ref('analytic.account_analytic_line_action')
        result = action.sudo().read()[0]
        result['context'] = {}
        result['context']['default_account_id'] = self.analytic_acc_id.id
        result['domain'] = "[('account_id', '=', " + str(self.analytic_acc_id.id) +")]"
        return result
    
    @api.depends('analytic_acc_id')
    def _compute_invoice(self):
        for r in self:
            r.bill_count = self.env['account.move'].sudo().search_count([('analytic_account_id', '=', r.analytic_acc_id.id), ('move_type', '=', 'in_invoice'), ('trip_id', '=', False)])
            r.invoice_count = self.env["account.move"].sudo().search_count([('analytic_account_id', '=', r.analytic_acc_id.id), ('move_type', '=', 'out_invoice')])
            r.rbill_count = self.env["account.move"].sudo().search_count([('analytic_account_id', '=', r.analytic_acc_id.id), ('move_type', '=', 'in_refund')])
    
    # @api.depends('analytic_acc_id')
    def _compute_expenses(self):
        obj=self.env['hr.expense']
        for r in self:
            r.expense_count = obj.search_count([('load_id.id','=',r.id)])
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']

        # Fix: vals_list is a list of dicts
        for vals in vals_list:
            vals['name'] = seq.next_by_code('load.dispatch') or 'New'

        records = super().create(vals_list)

        analytic_account_obj = self.env['account.analytic.account']
        plan_id = self.env.company.transport_analytic_plan_id.id

        for rec in records:
            if rec.name and plan_id:
                analytic = analytic_account_obj.create({
                    'name': rec.name,
                    'plan_id': plan_id,
                })
                rec.analytic_acc_id = analytic.id

        return records


    def create_vendor_bills(self):
        account_move_obj=self.env['account.move']
        for r in self:
            for trip in r.load_line_ids.filtered(lambda x: x.state in ('completed','invoiced') and not x.bill_id  and x.truck_id.truck_owner =='type2'):
                # raise ValidationError("test")
                new_bill=account_move_obj.create(r._prepare_bill(trip))
                trip.bill_id=new_bill.id

    def _prepare_bill(self,trip):
        bill = self._prepare_bill_data(trip)
        bill['invoice_line_ids']=self._prepare_lines(trip)
        return bill
    
    def _prepare_bill_data(self,trip):
        name = trip.name
        return {
            'move_type': 'in_invoice',
            'load_id': self.id,
            'partner_id': trip.truck_id.partner_id.id,
            'currency_id': trip.company_id.currency_id.id,
            'invoice_origin': name ,
            'narration': " / ".join((trip.load_id.name,name)),
        }
        
    def _prepare_lines(self,trip):
        product_id=self.env.company.transport_product_id
        commision_product_id = self.env.company.commision_product_id
        account_analytic_line_obj=self.env['account.analytic.line']
        product__id=product_id.id
        product_name=product_id.name
        commision_product__id=commision_product_id.id
        commision_product_account_id = commision_product_id.property_account_income_id.id or commision_product_id.categ_id.property_account_income_categ_id.id
        commision_product_name = commision_product_id.name
        lst_price=self.rate
        analytic_account_id=self.analytic_acc_id.id
        aml_ids=[]

        truck_id=trip.truck_id
        trip_id=trip.id
        ref=str(trip.date)
        tons=trip.tons
        date=trip.date
        sequence=int("".join([str(date.month),str(date.day)]))
        bill_lines =[
            (
                0,0,{
                'trip_bill_line': True,
                'sequence': sequence,
                'product_id': product__id,
                'name': " ".join([product_name,"|",truck_id.name,"|",ref]),
                'analytic_distribution': {str(analytic_account_id) : 100.0},
                'quantity': tons,
                'trip_id': trip_id,
                'price_unit':lst_price}
            ),
            (
                0,0,{
                'trip_bill_line': True,
                'sequence': sequence,
                'product_id': commision_product__id,
                'account_id': commision_product_account_id,
                'name': " ".join([commision_product_name,"|",truck_id.name,"|",ref]),
                'analytic_distribution':  {str(analytic_account_id) : 100.0},
                'trip_id': trip_id,
                'quantity': 1,
                'price_unit': -abs(truck_id.commission * (lst_price * tons))}
            )]
        for line in account_analytic_line_obj.search([('account_id.id','=',analytic_account_id),('billed','=',False),('amount','<',0.0),('category','!=','invoice'),('trip_id.id','=',trip.id)],order='date'):
            if line.id not in aml_ids:
                date=line.date
                sequence=int("".join([str(date.month),str(date.day)]))
                aml_ids.append(line.id)
                line_product_id= line.product_id
                bill_lines.append((0,0,{
                    'trip_bill_line': True,
                    'sequence'              : sequence,
                    'product_id'            : line_product_id.id or None,
                    'account_id'            : line.move_line_id.account_id.id,
                    'name'                  : "".join([line.name or line_product_id.name or line.move_line_id.move_id.name,"|",truck_id.name,"|",str(date)]) if line.category != 'other' else "".join([line.name.split(': ')[1] if ': ' in line.name else line.name or line_product_id.name or line.move_line_id.move_id.name," | ",truck_id.name," | ",str(date)]),
                    'analytic_distribution' :  {str(analytic_account_id) : 100.0},
                    'trip_id'               : trip_id,
                    'quantity'              :  1.0,
                    'price_unit'            :   -abs(line.amount)
                    }))
        return bill_lines


    

    # def create_invoice(self):
    #     product_id=self.env.company.transport_product_id
    #     if not product_id:
    #         raise ValidationError("Configure Products")
    #     account_move_obj=self.env['account.move']
    #     account_move_line_obj=self.env['account.move.line']
    #     for record in self:
    #         analytic_account_id=record.analytic_acc_id.id
    #         invoice_lines=[]
    #         origin=record.name
    #         created_invoice=None
    #         if (record.load_line_ids and record.load_line_ids.filtered(lambda trip: trip.state=='completed' and not trip.invoice_line_id) ):
    #             created_invoice=account_move_obj.create({
    #                 'partner_id': record.customer_id.id,
    #                 'load_id': record.id,
    #                 'invoice_date': fields.Date.today(),
    #                 'move_type': 'out_invoice',
    #                 'invoice_origin': origin,
    #                 'narration': origin,})            
    #             for trip in record.load_line_ids.filtered(lambda t: t.state=='completed' and not t.invoice_line_id):
    #                 name = " ".join([product_id.name,"|",trip.truck_id.name,"|",str(trip.date)])
    #                 truck_id=trip.truck_id
    #                 invoice_line_id=account_move_line_obj.create({
    #                     'product_id': product_id.id,
    #                     'name': name,
    #                     'analytic_distribution':  {str(analytic_account_id) : 100.0},
    #                     'trip_id': trip.id,
    #                     'quantity': trip.tons,
    #                     'move_id': created_invoice.id,
    #                     'price_unit':record.rate})
    #                 trip.write({'invoice_line_id':invoice_line_id.id,'state':'invoiced'})
    #             created_invoice.action_post()
    #             record.invoice_id=created_invoice.id


    def create_vendor_bills(self):
        account_move_obj=self.env['account.move']
        for r in self:
            for trip in r.load_line_ids.filtered(lambda x: x.state in ('completed','invoiced') and not x.bill_id  and x.truck_id.truck_owner =='type2'):
                # raise ValidationError("test")
                new_bill=account_move_obj.create(r._prepare_bill(trip))
                trip.bill_id=new_bill.id


    def create_expense_invoices(self):
        expensing_type =self.env.company.transport_expenseing_type
        account_analytic_line_obj=self.env['account.analytic.line']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        
        bill_lines=[]
        if expensing_type == 'per_vendor':
            for rec in self:
                vendor_ids = set (rec.load_line_ids.filtered(lambda x: x.vendor_id and x.truck_id.truck_owner =='type2').mapped('vendor_id.id'))
                
                _logger.info(vendor_ids)
                aml_ids=[]
                
                
                analytic_account_id = rec.analytic_acc_id.id
                for vendor in vendor_ids: 
                    lines=account_analytic_line_obj.search([('account_id.id','=',analytic_account_id),('billed','=',False), ('expense_charged','=',False), ('amount','<',0.0),('category','!=','invoice'),('trip_id.vendor_id.id','=',vendor)],order='date')
                    if lines:
                        bill = move_obj.create(
                            {
                                'move_type': 'in_refund',
                                'load_id': self.id,
                                'partner_id': vendor,
                                'currency_id': self.company_id.currency_id.id,
                                'invoice_origin': self.name ,
                                'narration': self.name,
                                })
                        
                        for line in lines:
                            if line.id not in aml_ids:
                                date=line.date
                                sequence=int("".join([str(date.month),str(date.day)]))
                                aml_ids.append(line.id)
                                line_product_id= line.product_id
                                bill_line=move_line_obj.create({
                                    'move_id': bill.id,
                                    'trip_bill_line': True,
                                    'expense_charged': True ,
                                    'sequence'              : sequence,
                                    'product_id'            : line_product_id.id or None,
                                    'account_id'            : line.move_line_id.account_id.id,
                                    'name'                  : "".join([line.name or line_product_id.name or line.move_line_id.move_id.name,"|",line.truck_id.name,"|",str(date)]) if line.category != 'other' else "".join([line.name.split(': ')[1] if ': ' in line.name else line.name or line_product_id.name or line.move_line_id.move_id.name," | ",line.truck_id.name," | ",str(date)]),
                                    'analytic_distribution' :  {str(analytic_account_id) : 100.0},
                                    'trip_id'               : line.trip_id.id,
                                    'quantity'              :  1.0,
                                    'price_unit'            :  abs(line.amount)
                                    })
                            line.mgs_bill_line_id = bill_line.id

        else:
            for rec in self:
                analytic_account_id = rec.analytic_acc_id.id
                for trip in rec.load_line_ids.filtered(lambda x: x.vendor_id and x.truck_id.truck_owner =='type2'):
                    lines=account_analytic_line_obj.search([('account_id.id','=',analytic_account_id),('billed','=',False) ,('expense_charged','=',False),('amount','<',0.0),('category','!=','invoice'),('trip_id.id','=',trip.id)],order='date')
                    if lines:
                        bill = move_obj.create(
                            {'move_type': 'in_refund',
                                'load_id': self.id,
                                'partner_id': trip.vendor_id.id,
                                'currency_id': self.company_id.currency_id.id,
                                'invoice_origin': self.name ,
                                'narration': self.name,
                                }) 
                        aml_ids=[]
                        for line in lines:
                            if line.id not in aml_ids:
                                date=line.date
                                sequence=int("".join([str(date.month),str(date.day)]))
                                aml_ids.append(line.id)
                                line_product_id= line.product_id
                                bill_line=move_line_obj.create({
                                    'move_id': bill.id,
                                    'trip_bill_line': True,
                                    'expense_charged': True ,
                                    'sequence'              : sequence,
                                    'product_id'            : line_product_id.id or None,
                                    'account_id'            : line.move_line_id.account_id.id,
                                    'name'                  : "".join([line.name or line_product_id.name or line.move_line_id.move_id.name,"|",line.truck_id.name,"|",str(date)]) if line.category != 'other' else "".join([line.name.split(': ')[1] if ': ' in line.name else line.name or line_product_id.name or line.move_line_id.move_id.name," | ",line.truck_id.name," | ",str(date)]),
                                    'analytic_distribution' :  {str(analytic_account_id) : 100.0},
                                    'trip_id'               : line.trip_id.id,
                                    'quantity'              :  1.0,
                                    'price_unit'            : abs(line.amount)
                                    })
                            line.mgs_bill_line_id = bill_line.id
                 
    
    def  open_inrefund_bills(self):
        return {
            'name': 'SC Deductions',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('load_id', '=', self.id), ('move_type', '=', 'in_refund')],
        }
    
        
        
        
        


class LoadLines(models.Model):
    _name = 'load.line.dispatch'
    _description = 'Trips'
    _inherit = ['mail.thread']
    _rec_names_search = ['name', 'truck_id.name', 'vendor_id.name']

    active = fields.Boolean(default=True)
    name = fields.Char(string='No.',tracking=True)
    company_id = fields.Many2one('res.company',readonly=True, string='Company', default=lambda self: self.env.company,tracking=True)
    load_id = fields.Many2one('load.dispatch', string='Batch',tracking=True)
    pickup_state = fields.Many2one('res.country.state', string='Pick-up State',tracking=True, required=True)
    pickup_city = fields.Many2one('city.dispatch', string='Pick-up City', required=True,tracking=True)
    pickup_address = fields.Char(string='Pick-up address', required=True,tracking=True)
    pickup_address2 = fields.Char(string='Pick-up address 2',tracking=True)
    pickup_contact_Name = fields.Char(string='Contact Name(Pick-up)',tracking=True)
    pickup_contact_Phone = fields.Char(string='Contatct Phone(Pick-up)',tracking=True)
    truck_id = fields.Many2one('truck.dispatch', string='Truck',tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver',tracking=True)
    trailer_id = fields.Many2one('trailer.dispatch', string='Trailer',tracking=True)
    notes_for_pickup = fields.Text(string='Pick-up Notes',tracking=True)
    pickup_master_Note = fields.Text(string='Pick-up Master Notes',tracking=True)
    pickup_start_time = fields.Datetime(string='Start Time',tracking=True)
    pickup_end_time = fields.Datetime(string='End Time',tracking=True)

    tons = fields.Float(string='Tons',tracking=True, digits='Product Price')
    currency_id = fields.Many2one('res.currency', "Currency",related='load_id.currency_id',readonly=True)
    vendor_id = fields.Many2one('res.partner', "Sub-contractor",related='truck_id.partner_id',readonly=True,store=True)
    partner_id = fields.Many2one('res.partner', "Customer",related='load_id.customer_id',readonly=True,store=True)
    amount_total=fields.Monetary(string='Total',compute='compute_amount_total',store=True)
    amount_commission=fields.Monetary(string='Total Commission',compute='compute_amount_total',store=True)
    rate = fields.Monetary(string='Rate',related='load_id.rate',readonly=True,store=True,tracking=True)
    date = fields.Date(tracking=True,default=fields.Date.today(), copy=False)
    
    bill_id = fields.Many2one('account.move',domain=['move_type','=','in_invoice'],string='Bill', copy=False,tracking=True)
    bill_count = fields.Integer(compute='_compute_account_move_count',tracking=True, string='# of Bills', copy=False, default=0)

    invoice_line_id= fields.Many2one('account.move.line',domain=['move_id.move_type','=','out_invoice'],string='Invoice Line', copy=False)
    invoice_id = fields.Many2one('account.move',string='Customer Invoice' ,domain=[('move_type','=','out_invoice')], copy=False)
    invoice_count = fields.Integer(compute="_compute_account_move_count",tracking=True, string='# of Invoices', copy=False, default=0)


    delivery_state = fields.Many2one('res.country.state', string='D-State', required=True,tracking=True)
    delivery_city = fields.Many2one('city.dispatch', string='D-City', required=True,tracking=True)
    delivery_address = fields.Char(string='Delivery address', required=True,tracking=True)
    delivery_address2 = fields.Char(string='Delivery address 2',tracking=True)
    delivery_contact_Name = fields.Char(string='Contact Name(Delivery)',tracking=True)
    delivery_contact_Phone = fields.Char(string='Contact Phone(Delivery)',tracking=True)
    notes_for_delivery = fields.Text(string='Delivery Notes',tracking=True)
    delivery_master_Note = fields.Text(string='Delivery Master Notes',tracking=True)
    delivery_start_time = fields.Datetime(string='D Start Time',tracking=True)
    delivery_end_time = fields.Datetime(string='D End Time',tracking=True)

    commission = fields.Float(default=0.1,tracking=True,  compute='compute_trip_commission', readonly=False, store=True)
    

    dispatched_time = fields.Datetime(string='Dispatched On',tracking=True)
    loaded_on_time = fields.Datetime(string='Loaded On',tracking=True)
    
    arrived_on_time = fields.Datetime(string='Arrived On',tracking=True)
    finished_on_time = fields.Datetime(string='Offloaded On',tracking=True)
    analytic_line_ids = fields.One2many('account.analytic.line', 'trip_id')
    state = fields.Selection([('new', 'New'),
                              ('dispatched','Dispatched'),
                              ('loaded','Loaded'),
                              ('on_road', 'On Road'),
                              ('arrived','Arrived'), 
                              ('cancel', 'Canceled'), 
                              ('finished', 'Offloaded'),
                              ('completed', 'Completed'),
                              ('invoiced', 'Invoiced'),
                              ], string='Status', readonly=True, default='new',tracking=True)
    
    @api.depends('truck_id')
    def compute_trip_commission(self):
        for record in self:
            record.commission = 0
            if record.truck_id.truck_owner == "type2":
                record.commission = record.truck_id.commission
    
    
    def _compute_account_move_count(self):
        for r in self:
            r.bill_count = self.env['account.move'].sudo().search_count([('move_type', '=', 'in_invoice'), ('trip_id', '=', r.id)])
            r.invoice_count = self.env["account.move"].sudo().search_count([('move_type', '=', 'out_invoice'), ('trip_id', '=', r.id)])
    
    
    
    def view_trip_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.sudo().read()[0]
        result['domain'] = [('trip_id', '=', self.id), ('move_type', '=' ,'out_invoice')]
        return result
    
    
    
    def view_trip_bill(self):
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.sudo().read()[0]
        result['domain'] = [('trip_id', '=', self.id), ('move_type', '=' ,'in_invoice')]
        return result
    
    
    def create_trip_invoice(self):
        product_id=self.env.company.transport_product_id
        analytic_account_id=self.load_id.analytic_acc_id.id
        invoice_lines = []
        
        for record in self: 
            name = " ".join([product_id.name,"|",record.truck_id.name,"|",str(record.date)])
            invoice_lines.append((0, 0, {
                'product_id': product_id.id,
                'name': name,
                'trip_id': self.id,
                'analytic_distribution':  {str(analytic_account_id) : 100.0},
                'quantity': record.tons,
                'price_unit': record.rate,
            }))
            
            vals = {
                'partner_id': record.partner_id.id if record.partner_id else None,
                'trip_id': record.id,
                'load_id': record.load_id.id if record.load_id else None,
                'invoice_date': self.date,
                'move_type': 'out_invoice',
                'invoice_line_ids': invoice_lines,
                'narration': record.load_id.name,
            }            
    
    
            return vals
           
           
           
           
    def _prepare_lines(self):
        product_id=self.env.company.transport_product_id
        commision_product_id = self.env.company.commision_product_id
        
        product__id=product_id.id
        product_name=product_id.name
        commision_product__id=commision_product_id.id
        commision_product_account_id = commision_product_id.property_account_income_id.id or commision_product_id.categ_id.property_account_income_categ_id.id
        commision_product_name = commision_product_id.name
        lst_price=self.rate
        analytic_account_id=self.load_id.analytic_acc_id.id

        truck_id=self.truck_id
        trip_id=self.id
        ref=str(self.date)
        tons=self.tons
        date=self.date
        sequence=int("".join([str(date.month),str(date.day)]))
        bill_lines =[
            (
                0,0,{
                'trip_bill_line': True,
                'sequence': sequence,
                'product_id': product__id,
                'name': " ".join([product_name,"|",truck_id.name,"|",ref]),
                'analytic_distribution': {str(analytic_account_id) : 100.0},
                'quantity': tons,
                'trip_id': trip_id,
                'price_unit':lst_price}
            ),
            (
                0,0,{
                'trip_bill_line': True,
                'sequence': sequence,
                'product_id': commision_product__id,
                'account_id': commision_product_account_id,
                'name': " ".join([commision_product_name,"|",truck_id.name,"|",ref]),
                'analytic_distribution':  {str(analytic_account_id) : 100.0},
                'trip_id': trip_id,
                'quantity': 1,
                'price_unit': -abs(truck_id.commission * (lst_price * tons))}
            )]
        return bill_lines


    def _prepare_bill_data(self):
            trip_id=self.id
            return {
                'move_type': 'in_invoice',
                'load_id': self.load_id.id if self.load_id else None,
                'trip_id':trip_id,
                'invoice_date': self.date,
                'partner_id': self.truck_id.partner_id.id,
                'currency_id': self.company_id.currency_id.id,
                'invoice_origin': self.name ,
                'narration': " / ".join((self.load_id.name, self.name)),
            }
        
    def create_trip_bill(self): 
        for rec in self:
            bill = rec._prepare_bill_data()
            bill['invoice_line_ids'] = rec._prepare_lines()
            return bill
        
        
        
    def check_if_invoice_or_bill_is_created(self):
        account_move = self.env['account.move']
        for rec in self:
            if not rec.invoice_id or rec.invoice_id.state == 'cancel':
                invoice = rec.create_trip_invoice()
                move = account_move.create(invoice)
                move.with_context(allow_action=True).action_post()
                rec.write({'invoice_id': move.id})
            
                
            if rec.vendor_id and (not rec.bill_id or rec.bill_id.state == 'cancel'):
                bill = rec.create_trip_bill()
                move = account_move.create(bill)            
                move.with_context(allow_action=True).action_post()
                rec.write({'bill_id': move.id})
            
            
            
    def cancel_moves(self):
        for rec in self:
            if rec.invoice_id:
                rec.invoice_id.with_context(allow_action = True).button_cancel()
            
            if rec.bill_id:
                rec.bill_id.with_context(allow_action = True).button_cancel()
            
            
    
    def get_analytic_line_ids(self):
        # try:
        result = self.analytic_line_ids.search([('account_id.id','=',self.load_id.analytic_acc_id.id),('billed','=',False),('amount','<',0.0),('category','!=','invoice'),('trip_id.id','=',self.id)],order='date')
        return result
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']

        for vals in vals_list:
            vals['name'] = seq.next_by_code('load.dispatch.line') or 'New'

        records = super().create(vals_list)
        return records
    
    @api.depends('name', 'truck_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.truck_id.name}|{rec.name}"
                if rec.truck_id else (rec.name or "")
            )
    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     args = args or []
    #     recs = self.browse()
    #     if name:
    #         recs = self.search((args + ['|', ('name', 'ilike', name),('truck_id.name', 'ilike', name)]), limit=limit)
    #     if not recs:
    #         recs = self.search([('name', operator, name)] + args, limit=limit)
    #     return recs.name_get()
    
    @api.depends('rate','tons')
    def compute_amount_total(self):
        for r in self:
            r.amount_total=r.rate * r.tons
            r.amount_commission= -abs(r.amount_total * r.truck_id.commission)
            
    def dispatch_trip(self):
        self.check_if_invoice_or_bill_is_created()
        for rec in self:
            if not rec.dispatched_time:
                rec.write({'dispatched_time':fields.Datetime.now()})
            rec.write({'state': 'dispatched'})

    def mark_as_loaded(self):
        self.check_if_invoice_or_bill_is_created()
        return self.write({'state': 'loaded','loaded_on_time':fields.Datetime.now()})

    def mark_as_arrived(self):
        self.check_if_invoice_or_bill_is_created()
        for rec in self:
            if not rec.arrived_on_time:
                rec.write({'arrived_on_time':fields.Datetime.now()})
            rec.write({'state': 'arrived'})
    
    def start_trip(self):
        self.check_if_invoice_or_bill_is_created()
        return self.write({'state': 'on_road'})

    def mark_as_finished(self):
        self.check_if_invoice_or_bill_is_created()
        for rec in self:
            if not rec.finished_on_time:
                rec.write({'finished_on_time':fields.Datetime.now()})
            rec.write({'state': 'finished',})

    def cancel_load(self):
        self.cancel_moves()
        return self.write({'state': 'cancel'})
    
    
    
    def complete_load(self):
        self.check_if_invoice_or_bill_is_created()
        return self.write({'state': 'completed'})
    
    
    def reset_to_new(self):
        self.cancel_moves()
        return self.write({'state': 'new'})



    @api.onchange('truck_id')
    def onchange_driver(self):
        for r in self:
            r.driver_id = r.truck_id.driver_id
            r.trailer_id = r.truck_id.trailer_id




class City(models.Model):
    _name = 'city.dispatch'
    _description = 'Citties'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Name")
    code = fields.Char( string='Code')
    company_id = fields.Many2one('res.company',readonly=True, string='Company', default=lambda self: self.env.company)
    state_id = fields.Many2one('res.country.state', string='State')




class Make(models.Model):
    _name = 'make.dispatch'
    _description = 'Makers'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', readonly=True,string='Company', default=lambda self: self.env.company)
    name = fields.Char(required=True, string="Maker ")
    code = fields.Char( string='Code')


class TurckType(models.Model):
    _name = 'truck_type.dispatch'
    _description = 'Truck Type'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Type")
    code = fields.Char( string='Code')
    company_id = fields.Many2one('res.company', readonly=True,string='Company', default=lambda self: self.env.company)



class TrailerType(models.Model):
    _name = 'trailer_type.dispatch'
    _description = 'Trailer Type'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Type")
    code = fields.Char( string='Code')
    company_id = fields.Many2one('res.company',readonly=True, string='Company', default=lambda self: self.env.company)



class IFTA(models.Model):
    _name = 'ifta.dispatch'
    _description = 'IFTA Group'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Group Name")
    code = fields.Char( string='Code')
    company_id = fields.Many2one('res.company', readonly=True, string='Company', default=lambda self: self.env.company)
