from xmlrpc.client import boolean
from odoo import models, fields, api
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class TenancyType(models.Model):
    _name = 'pm.tenancy.type'
    _rec_name='name'


    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    name=fields.Char(compute='name_',store=True)
    number = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),], default='1', string='Number', store=True)
    _type = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('weekly', 'Weekly'),])

    @api.depends('number','_type')
    def name_(self):
        for r in self:
            r.name=str(r.number) + " " + str(r._type)

class TenancyContract(models.Model):
    _name = 'pm.tenancy'
    
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name='code'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    code = fields.Char(string="Tenancy ref.", required=True, copy=False, readonly=True, index=True, default='New',tracking=True)
    # analytic_acc_id = fields.Many2one('account.analytic.account',
    #                               string='Analytic Account')
    property_id=fields.Many2one('pm.property',required=True,domain=[('state','=','available')],copy=False,tracking=True)
    tenant_id=fields.Many2one('res.partner',domain=[('is_tenant', '=', True)],required=True,tracking=True)
    landlord_id=fields.Many2one('res.partner',readonly=True,related='property_id.landlord_id',store=True,tracking=True)
    currency_id = fields.Many2one('res.currency', "Currency",readonly=True,related='property_id.currency_id',store=True,tracking=True)


    rent_price=fields.Monetary(related='property_id.rent_price',readonly=True,tracking=True)

    rent_price_per_period=fields.Monetary("Rent per period",compute="get_rent_price_per_period",store=True,readonly=False,tracking=True)


    date=fields.Date(default=fields.Date.today(),tracking=True)
    amount_deposit=fields.Monetary(tracking=True)
    deposit_payment_id = fields.Many2one('account.payment',string='Deposit Payment',tracking=True)
    return_deposit_payment_id = fields.Many2one('account.payment',string='Deposit return_Payment',tracking=True)

    agreement_charge=fields.Monetary(tracking=True)

    deposit_inv_id=fields.Integer(tracking=True)
    deposit_received=fields.Boolean(readonly=True,compute='_get_payment_state',tracking=True)
    deposit_returned=fields.Boolean(readonly=True,compute='_get_return_deposit_payment_state',tracking=True)
    amount_returned=fields.Monetary(readonly=True,tracking=True)
    active = fields.Boolean(default=True,tracking=True)
    start_date=fields.Date(default=fields.Date.today(),tracking=True,required=True)
    closing_date=fields.Date(tracking=True)

    remaning_days=fields.Integer(compute='_get_remaning',tracking=True)

    end_date=fields.Date(compute='_get_end_date',store=True,tracking=True)
    no_of_months=fields.Integer(default=12,string="Monthes",tracking=True)
    totall_amount=fields.Monetary(compute='calculate_totall_amount',store=True,tracking=True)

    rent_type_id=fields.Many2one('pm.tenancy.type',"Rent Type",required=True,tracking=True)
    rent_schedule_ids = fields.One2many('pm.rent.schedule', 'tenancy_id', string="Rent Schedule",tracking=True)
    service_lines = fields.One2many('pm.service.line', 'tenancy_id', string="Extra Services",tracking=True)
    rent_entry_chck=fields.Boolean(tracking=True)
    invoice_id=fields.Many2one('account.move',tracking=True,domain=[('move_type', '=', 'out_invoice')])

    agreement_charge_invoice_id=fields.Many2one('account.move',tracking=True,domain=[('move_type', '=', 'out_invoice')])

    bill_id=fields.Many2one('account.move',domain=[('move_type', '=', 'in_invoice')],tracking=True)
    
    enable_comm = fields.Boolean('Enable Commission',default=True,compute='get_commission',tracking=True,store=True)
    comm_type=fields.Selection([
        ('precentage','By Precentage'),
        ('fixed_cost','By Fixed Cost'),],compute='get_commission',store=True,tracking=True)
    mgmt_comm=fields.Monetary("Managment Amount",compute='calculate_commission',store=True,tracking=True)
    mgmt_precentage=fields.Float("Managment Comm",compute='get_commission',store=True,tracking=True)
    mgmt_fix_cost=fields.Float(compute='get_commission',store=True,tracking=True)
    landlord_amount=fields.Monetary(compute='calculate_landlord_commission',tracking=True,store=True)


    total_services_price=fields.Float(compute='calculate_total_services_price',store=True,tracking=True)
    total_services_amount_for_landlord=fields.Float(compute='calculate_total_services_amount_for_landlord',tracking=True,string="Total LL Amount",store=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('in_progress', 'In Progress'),
        ('close', 'Closed'),], default='draft', string='Status', store=True,tracking=True)
    note=fields.Text(tracking=True)


    
    @api.depends('end_date')
    def _get_remaning(self):
        current_date=date.today()
        for r in self:
            r.remaning_days=(r.end_date - current_date).days
    @api.depends('property_id')
    def get_commission(self):
        for r in self:
            r.enable_comm=r.property_id.enable_comm
            r.comm_type=r.property_id.comm_type
            r.mgmt_precentage=r.property_id.mgmt_precentage
            r.mgmt_fix_cost=r.property_id.mgmt_fix_cost

    def unlink(self):
        am_obj=self.env['account.move']
        rent_obj=self.env['pm.rent.schedule']
        for rec in self:
            existing_am=am_obj.search([('invoice_origin','=',rec.code)])
            existing_rent=rent_obj.search([('active','in',[True,False]),('tenancy_id.id','=',rec.id)])
            if existing_am or existing_rent:
                raise ValidationError("You can not delete this record !!")
            return super(TenancyContract, self).unlink()


    @api.depends('service_lines')
    def calculate_total_services_price(self):   
        total=0
             # for rec in self:
        for line in self.service_lines:
            total+= line.price
        self.total_services_price=total
    @api.depends('service_lines')
    def calculate_total_services_amount_for_landlord(self):
        total=0
        for line in self.service_lines:
            total+=line.landlord_comm_amount
        self.total_services_amount_for_landlord=total

    @api.depends('rent_type_id','rent_price')
    def get_rent_price_per_period(self):
        for rec in self:
            rec.rent_price_per_period= int(rec.rent_type_id.number)*rec.rent_price

    @api.depends('property_id')
    def get_rent_price(self):
        for rec in self:
            rec.rent_price= rec.property_id.rent_price


    @api.depends('no_of_months','rent_price')
    def calculate_totall_amount(self):
        for rec in self:
            rec.totall_amount= rec.no_of_months*rec.rent_price
    @api.depends('start_date','no_of_months')
    def _get_end_date(self):
        for r in self:
            if r.start_date:
                r.end_date=(datetime.strptime(str(r.start_date), '%Y-%m-%d')+relativedelta(months =+ r.no_of_months))
            else:
                r.end_date=None
                # r.start_date + relativedelta(months=r.no_of_months)


    @api.depends('comm_type', 'mgmt_precentage','rent_price_per_period', 'mgmt_fix_cost')
    def calculate_commission(self):
        """
        This method is used to calculate commistion
        -----------------------------------------------------------------
        @param self: The object pointer
        """
        for data in self:
            if data.comm_type == 'precentage':
                data.mgmt_comm = data.rent_price_per_period * data.mgmt_precentage
            if data.comm_type == 'fixed_cost':
                data.mgmt_comm = data.mgmt_fix_cost
    
    @api.depends('mgmt_comm')
    def calculate_landlord_commission(self):
        """
        This method is used to calculate mgmt as per commition type
        -----------------------------------------------------------------
        @param self: The object pointer
        """
        for rec in self:
            if rec.mgmt_comm!=0.00:
                rec.landlord_amount = rec.rent_price_per_period - rec.mgmt_comm
            else:
                rec.landlord_amount = rec.rent_price_per_period


    @api.depends('invoice_id')
    def _get_payment_state(self):
        for r in self:
            if r.deposit_payment_id.state in ('in_process', 'paid'):
                r.deposit_received=True
            else:
                r.deposit_received=False
    @api.depends('bill_id')
    def _get_return_deposit_payment_state(self):
        for r in self:
            if r.return_deposit_payment_id.state in ('in_process', 'paid'):
                r.deposit_returned=True
            else:
                r.deposit_returned=False



    def action_in_progress(self):
        for r in self:
            r.state = 'in_progress'
            r.create_rent_schedule()
            r.property_id.state='on_lease'
            r.property_id.tenant_id=r.tenant_id.id

    def action_draft(self):
        tenancy_obj=self.env['pm.tenancy'].search([('property_id','=',self.property_id.id),('state','=','in_progress')],limit=1)
        if tenancy_obj:
            raise ValidationError("This Property Is Already Onlease. See "+ tenancy_obj.code)
        else:
            self.state = 'draft'
        prop_obj=self.env['pm.property'].search([('id','=',self.property_id.id)])
        if self.property_id:
            prop_obj.state='booked'
            prop_obj.tenant_id=self.tenant_id.id


    def action_cancel(self):
        for r in self:
            r.state = 'close'
            r.closing_date = fields.Date.today()
            r.property_id.state='available'
            r.property_id.tenant_id = None
            for rent in r.rent_schedule_ids:
                if not rent.invoice_id or not rent.bill_id:
                    rent.active=False
    
    def closer_cron(self):
        current_date=date.today()
        self.env['pm.tenancy'].search([('state','=','in_progress'),('end_date', '<=', current_date)]).action_cancel()

    """Smart Button Functions Start"""
    # def action_view_invoice(self):
    #     invoices = self.mapped('invoice_id')
    #     action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
    #     if len(invoices) > 1:
    #         action['domain'] = [('id', 'in', invoices.id)]
    #     elif len(invoices) == 1:
    #         action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
    #         action['res_id'] = self.invoice_id.id
    #     else:
    #         action = {'type': 'ir.actions.act_window_close'}
    #     return action


    def action_view_agreement_charge_invoice(self):
        invoices = self.mapped('agreement_charge_invoice_id')
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.id)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = self.agreement_charge_invoice_id.id
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
    
    def action_view_rents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scheduled Rents',
            'view_mode': 'list,form',
            'res_model': 'pm.rent.schedule',
            'domain': [('tenancy_id', '=', self.id)],
            'context': "{'create': False,'order':'date'}"
        }

    def action_view_invoices(self):

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('invoice_origin', '=', self.code),('move_type','=','out_invoice')],
            'context': "{'create': False}"
        }

    def action_view_bills(self):

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('invoice_origin', '=', self.code),('move_type','=','in_invoice')],
            'context': "{'create': False}"
        }

    """Smart Button Functions End"""




    """Add Tenancey Sequance To On Create Method"""
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                seq_date = None
                vals['code'] = self.env['ir.sequence'].next_by_code('pm.tenancy') or 'New'
        results = super(TenancyContract, self).create(vals_list)
        for result in results:
            prop_obj=self.env['pm.property'].search([('id','=',result.property_id.id)])
            if result.property_id:
                prop_obj.state='booked'
        return results



    """Create Rent Schedule"""
    def create_rent_schedule(self):

        """
        This button method is used to create rent schedule Lines.
        """
        rent_obj = self.env['pm.rent.schedule']
        for tenancy_rec in self:
            service_lines_vals=tenancy_rec.service_lines or False
            if tenancy_rec.rent_type_id._type == 'weekly':
                d1 = datetime.strptime(str(tenancy_rec.start_date), str(DEFAULT_SERVER_DATE_FORMAT))
                d2 = datetime.strptime(str(tenancy_rec.end_date), str(DEFAULT_SERVER_DATE_FORMAT))
                interval = int(tenancy_rec.rent_type_id.number)
                if d2 < d1:
                    raise UserError(_('End Date Must Be After The Start Date.'))
                wek_diff = (d2 - d1)
                wek_tot1 = (wek_diff.days) / (interval * 7)
                wek_tot = (wek_diff.days) % (interval * 7)
                if wek_diff.days == 0:
                    wek_tot = 1
                if wek_tot1 > 0:
                    for wek_rec in range(int(wek_tot1)):
                        rent_obj.create(
                            {
                                'date': d1.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                'amount': tenancy_rec.rent_price_per_period or 0.0,
                                'property_id': tenancy_rec.property_id.id or False,
                                'tenancy_id': tenancy_rec.id,
                                'landlord_id': tenancy_rec.landlord_id.id or False,
                                'tenant_id': tenancy_rec.tenant_id.id,
                                'landlord_amount': tenancy_rec.landlord_amount,
                                'total_services_price': tenancy_rec.total_services_price,
                                'total_services_amount_for_landlord': tenancy_rec.total_services_amount_for_landlord,
                                # 'service_lines':tenancy_rec.service_lines,

                            })
                        d1 = d1 + relativedelta(days=(7 * interval))
                if wek_tot > 0 and tenancy_rec.rent_type_id.number!="2":
                    one_day_rent = 0.0
                    if tenancy_rec.rent_price:
                        one_day_rent = (tenancy_rec.rent_price) / (7 * interval)
                    rent_obj.create(
                        {
                            'date': d1.strftime(DEFAULT_SERVER_DATE_FORMAT),
                            'amount': (one_day_rent * (wek_tot)) or 0.0,
                            'property_id': tenancy_rec.property_id.id or False,
                            'tenancy_id': tenancy_rec.id,
                            'landlord_id': tenancy_rec.landlord_id.id or False,
                            'tenant_id': tenancy_rec.tenant_id.id,
                            'landlord_amount': tenancy_rec.landlord_amount,
                            'total_services_price': tenancy_rec.total_services_price,
                            'total_services_amount_for_landlord': tenancy_rec.total_services_amount_for_landlord,
                            # 'service_lines':tenancy_rec.service_lines,

                        })
            elif tenancy_rec.rent_type_id._type != 'weekly':
                if tenancy_rec.rent_type_id._type == 'monthly':
                    interval = int(tenancy_rec.rent_type_id.number)
                if tenancy_rec.rent_type_id._type == 'yearly':
                    interval = int(tenancy_rec.rent_type_id.number) * 12
                d1 = datetime.strptime(str(tenancy_rec.start_date), DEFAULT_SERVER_DATE_FORMAT)
                d2 = datetime.strptime(str(tenancy_rec.end_date), DEFAULT_SERVER_DATE_FORMAT)
                diff = abs((d1.year - d2.year) * 12 + (d1.month - d2.month))
                tot_rec = diff / interval
                tot_rec2 = diff % interval
                if abs(d1.month - d2.month) >= 0 and d1.day < d2.day:
                    tot_rec2 += 1
                if diff == 0:
                    tot_rec2 = 1
                if tot_rec > 0:
                    for rec in range(int(tot_rec)):
                        rent_obj.create(
                            {
                            
                            'date': d1.strftime(DEFAULT_SERVER_DATE_FORMAT),
                            'amount': tenancy_rec.rent_price_per_period or 0.0,
                            'property_id': tenancy_rec.property_id.id or False,
                            'tenancy_id': tenancy_rec.id,
                            'landlord_id': tenancy_rec.landlord_id.id or False,
                            'tenant_id': tenancy_rec.tenant_id.id,
                            'landlord_amount': tenancy_rec.landlord_amount,
                            'total_services_price': tenancy_rec.total_services_price,
                            'total_services_amount_for_landlord': tenancy_rec.total_services_amount_for_landlord,
                            # 'service_lines':tenancy_rec.service_lines,
 
                            })
                        d1 = d1 + relativedelta(months=interval)
                if tot_rec2 > 0:
                    rent_obj.create({
                        'date': d1.strftime(DEFAULT_SERVER_DATE_FORMAT),
                        'amount': tenancy_rec.rent_price_per_period * tot_rec2 or 0.0,
                        'property_id': tenancy_rec.property_id.id or False,
                        'tenancy_id': tenancy_rec.id,
                        'landlord_id': tenancy_rec.landlord_id.id or False,
                        'tenant_id': tenancy_rec.tenant_id.id,
                        'landlord_amount': tenancy_rec.landlord_amount,
                        'total_services_price': tenancy_rec.total_services_price,
                        'total_services_amount_for_landlord': tenancy_rec.total_services_amount_for_landlord,
                        # 'service_lines':service_lines_vals,

                    })
        return True
    
    




    """Deposit Receive Invoice And Deposit Return Bill"""
    def get_invoice_journal(self):
        return self.env['account.move'].new({'move_type': 'out_invoice'})._search_default_journal()
    def get_bill_journal(self):
        return self.env['account.move'].new({'move_type': 'in_invoice'})._search_default_journal()

# Return Deposit
    # def receive_deposit(self):
    def action_receive_deposit_wizard(self):
        action= self.env.ref('tis_property_managment.action_receive_deposit_wizard').sudo().read()[0]
        action['context']={}
        action['context']['default_partner_id'] = int(self.tenant_id.id)
        action['context']['default_tenancy_id'] = int(self.id)
        action['context']['default_payment_type'] = 'inbound'
        action['context']['default_amount'] = self.amount_deposit
        return action

    def action_view_receive_deposit_payment(self):
        self.ensure_one()
        return {
			'type': 'ir.actions.act_window',
			'name': 'Payment',
			'view_mode': 'form',
			'res_model': 'account.payment',
			'view_id':self.env.ref('account.view_account_payment_form').id,
			'context': "{'create': False}",
			'res_id': self.deposit_payment_id.id}
    
    



    


    # def receive_deposit(self):
        # invoice = self.env['account.move']
        # invoice_lines_vals = []
        # journal_id = self.get_invoice_journal()
        # account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.deposit_account_id')))]).id
        # for r in self:
        #     if r.invoice_id:
        #         return None
        #     elif r.amount_deposit==0.0:
        #         raise ValidationError("There's Nothing To Deposit")
        #     origin = r.code
        #     inserted_invoice = invoice.create({
        #         'partner_id': r.tenant_id.id,
        #         'journal_id': journal_id.id,
        #         'currency_id': r.property_id.currency_id.id,
        #         'move_type': 'out_invoice',
        #         'invoice_origin': origin,
        #         'narration': origin,
        #     })

        #     invoice_lines_vals.append((0, 0, {
        #     'name':" ".join(["Tenancy Deposit For",r.code]),
        #     'account_id': account_id,
        #     'analytic_account_id': r.property_id.analytic_acc_id.id,
        #     'price_unit': r.amount_deposit,}))
            
        #     inserted_invoice.invoice_line_ids = invoice_lines_vals
        #     invoice_lines_vals=None
        #     r.write({
        #         'invoice_id': inserted_invoice.id,
        #     })

        #     r.invoice_id.action_post();

        # action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        # action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        # action['res_id'] = inserted_invoice.id
        # return action
# Return Deposit




    def action_return_deposit_wizard(self):
        invoice = self.env['account.move']
        query="""
               SELECT COALESCE(sum(aml.debit - aml.credit), 0.0)
                from account_move_line as aml 
                LEFT JOIN account_move am on aml.move_id=am.id 
                WHERE account_id= %s
                AND aml.partner_id=%s AND aml.analytic_distribution ? %s
                AND am.state='posted'
                
                """
        account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.deposit_account_id')))]).id
        for r in self:
            partner_id=r.tenant_id.id
            analytic_account_id = r.property_id.analytic_acc_id.id
            self.env.cr.execute(query,(account_id,partner_id,str(analytic_account_id)))
            result = self.env.cr.fetchone()
            available_deposit=abs(result[0]) if result[0] < 0.0 else -abs(result[0])
            action= self.env.ref('tis_property_managment.action_receive_deposit_wizard').sudo().read()[0]
            action['context']={}
            action['context']['default_partner_id'] = partner_id
            action['context']['default_tenancy_id'] = int(self.id)
            action['context']['default_payment_type'] = 'outbound'
            action['context']['default_amount'] = available_deposit
            return action

    def action_view_return_deposit_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'view_id':self.env.ref('account.view_account_payment_form').id,
            'context': "{'create': False}",
            'res_id': self.return_deposit_payment_id.id}

    def create_agreement_charge_invoice(self):
        invoice = self.env['account.move']
        # tenancy = self.env['pm.tenancy'].search([('property_id','=',self.property_id),('state','!=','')])
        invoice_lines_vals = []
        account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.agreement_income_account_id')))]).id
        for r in self:
            if r.agreement_charge_invoice_id:
                return True
            elif r.agreement_charge==0.0:
                raise ValidationError("There's Nothing To Deposit")
            origin = r.code
            journal_id = r.get_invoice_journal()
            inserted_invoice = invoice.create({
                'partner_id': r.tenant_id.id,
                'journal_id': journal_id.id,
                'currency_id': r.property_id.currency_id.id,
                'move_type': 'out_invoice',
                'invoice_origin': origin,
                'narration': origin,
            })

            invoice_lines_vals.append((0, 0, {
            'name':" ".join(["Agreement charge for contract",origin]),
            'account_id': account_id,
            'analytic_distribution': {str(r.property_id.analytic_acc_id.id): 100},
            'price_unit': r.agreement_charge,}))
            
            inserted_invoice.invoice_line_ids = invoice_lines_vals
            r.write({
                'agreement_charge_invoice_id': inserted_invoice.id,
            })

            r.agreement_charge_invoice_id.action_post()
            invoice_lines_vals = None
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = inserted_invoice.id
        return action




class ReceiveDeposit(models.TransientModel):
    _name = 'pm.tenancy.rceceive.deposit.wizard'
    _description = 'Receive Deposit Wizard'

    partner_id = fields.Many2one('res.partner', string='Tenant')
    date=fields.Date(default=fields.Date.today())
    currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True)
    amount=fields.Monetary()
    journal_id = fields.Many2one('account.journal',string='Journal',domain=[('type','in',('bank','cash'))])
    payment_id = fields.Many2one('account.payment',string='Payment')
    tenancy_id=fields.Many2one('pm.tenancy')
    payment_type=fields.Selection([('inbound', 'inbound'),('outbound', 'outbound')])
    def create_payment(self):
        account_id = self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.deposit_account_id')
        account_payment_obj=self.env['account.payment']
        if self.payment_id:
            return None
        if not self.journal_id:
            raise ValidationError("Please sellect a journal")
        if self.partner_id:
            payment=account_payment_obj.create({
                'partner_id':self.partner_id.id,
                'partner_type':'supplier',
                'payment_type':self.payment_type,
                'journal_id':self.journal_id.id,
                'date':self.date,
                'memo':self.tenancy_id.code or None,
                'amount':float(self.amount),
            })
            self.payment_id=payment.id
            if self.payment_type=='inbound':
                self.tenancy_id.deposit_payment_id=payment.id
            else:
                self.tenancy_id.return_deposit_payment_id=payment.id
            self.payment_id.action_post()
            move_id=payment.move_id
            payable_line=move_id.line_ids.search([('account_id.id','=',int(account_id)),('move_id','=',move_id.id)])
            payable_line.analytic_distribution={str(self.tenancy_id.property_id.analytic_acc_id.id): 100}
        else:
            raise ValidationError(('You can not create a payment without selecting a partner.'))