from odoo import models, fields, api
from datetime import date, datetime
from odoo.exceptions import ValidationError


class PropertyMaintenanceType(models.Model):
    _name = 'pm.maintenance.type'
    name = fields.Char('Maintenance Type')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

class PropertyMaintenanceLine(models.Model):
    _name = 'pm.maintenance.line'
    
    name = fields.Char('Brief Description')
    worker_id = fields.Many2one('res.partner', string="Assign To")
    type_id = fields.Many2one('pm.maintenance.type', 'Type',required=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    action = fields.Selection([('renew', 'Renew'),('replace', 'Replace'),('repair', 'Repair'),], default='repair', string='Action', store=True)
    maintenance_id = fields.Many2one('pm.maintenance')
    cost = fields.Monetary(required=1)
    currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True)
    description = fields.Html()
    
class PropertyMaintenance(models.Model):
    _name = 'pm.maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'code'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,tracking=True)
    code = fields.Char(string="maintenance ref.", required=True, copy=False, readonly=True, index=True, default='New',tracking=True)
    property_id = fields.Many2one('pm.property', string="Property", required=True,tracking=True)
    landlord_id = fields.Many2one('res.partner',store=True,related='property_id.landlord_id',compute='_get_info', string="Landlord", readonly=True,tracking=True)
    currency_id = fields.Many2one('res.currency', "Currency",default=lambda self: self.env.company.currency_id,readonly=True,tracking=True)
    tenant_id = fields.Many2one('res.partner',store=True,compute='_get_info',string="Tenant", readonly=True,tracking=True)
    # cost = fields.Monetary()
    available_deposit = fields.Monetary(compute='_get_info',store=True,tracking=True)
    date = fields.Date(default=fields.Date.today(),tracking=True)
    invoice_id=fields.Many2one('account.move',copy=False,domain=[('move_type', '=', 'out_invoice')],tracking=True)
    entry_id=fields.Many2one('account.move',copy=False,domain=[('move_type', '=', 'entry')],tracking=True)
    maintenance_line_ids=fields.One2many('pm.maintenance.line','maintenance_id',copy=False,tracking=True)

    expense_id=fields.Many2one('hr.expense',copy=False,tracking=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], default='draft', string='Status', store=True,tracking=True)

    mgmt_comm_amount = fields.Float(tracking=True)

    total_amount = fields.Float(compute='_total', store=True, readonly=True,tracking=True)
    cost = fields.Float(compute='_total', store=True, readonly=True,tracking=True)

    tenant_fault = fields.Boolean('Tenants Fault',tracking=True)
    subtract_from_deposit = fields.Boolean('Subtract From Deposit',tracking=True)


    

    
    

    def action_start(self):
        for r in self:
            r.state = 'in_progress'

    def action_done(self):
        for r in self:
            r.state = 'done'

    def action_draft(self):
        for r in self:
            r.state ='draft'

    def action_cancel(self):
        for r in self:
            r.state ='cancel'

    @api.depends('maintenance_line_ids','mgmt_comm_amount')
    def _total(self):
        for r in self:
            cost = 0.00
            for line in r.maintenance_line_ids:
                cost+=line.cost
            r.cost=cost
            r.total_amount=cost + r.mgmt_comm_amount



    @api.depends('property_id')
    def _get_info(self):
        query="""SELECT COALESCE(sum(aml.debit - aml.credit), 0.0)
                from account_move_line as aml 
                LEFT JOIN account_move am on aml.move_id=am.id 
                WHERE account_id= %s
                AND aml.partner_id=%s AND aml.analytic_distribution ? %s
                AND am.state='posted'"""
        account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.deposit_account_id')))]).id
        tenancy_obj=self.env['pm.tenancy']
        for rec in self:
            tenancy=tenancy_obj.search([('property_id','=',rec.property_id.id)])
            if tenancy:
                if len(tenancy) > 1:
                    rec.tenant_id=tenancy_obj.search([('property_id','=',rec.property_id.id),('state','=','in_progress')],limit=1).tenant_id.id or tenancy_obj.search([('property_id','=',rec.property_id.id)],order="id DESC",limit=1).tenant_id.id
                    self.env.cr.execute(query,(account_id,rec.tenant_id.id,str(rec.property_id.analytic_acc_id.id)))
                    result = self.env.cr.fetchone()
                    rec.available_deposit=abs(result[0]) if result[0] < 0.0 else -abs(result[0])
                if len(tenancy) ==1:
                    rec.tenant_id=tenancy.tenant_id.id
                    self.env.cr.execute(query,(account_id,rec.tenant_id.id,str(rec.property_id.analytic_acc_id.id)))
                    result = self.env.cr.fetchone()
                    rec.available_deposit=abs(result[0]) if result[0] < 0.0 else -abs(result[0])
    
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                seq_date = None
                vals['code'] = self.env['ir.sequence'].next_by_code('pm.maintenance') or 'New'
        result = super(PropertyMaintenance, self).create(vals_list)
        return result


    def get_invoice_journal(self):
        return self.env['account.move'].new({'move_type': 'out_invoice'})._search_default_journal()
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



    def action_view_entry(self):
        invoices = self.mapped('entry_id')
        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.id)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = self.entry_id.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action



    def create_journal_entry(self):
        entry = self.env['account.move']
        entry_lines_vals=[]
        account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.deposit_account_id')))]).id
        m_income_account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.maintenance_income_account_id')))]).id
        m_expense_account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.maintenance_expense_account_id')))]).id
        for r in self:
            if r.entry_id:
                return None
            if not r.subtract_from_deposit:
                raise ValidationError("you should create an invoice")
            if r.available_deposit < r.total_amount:
                raise ValidationError("insufficient deposit balance")
            partner_id = r.tenant_id.id
            name=" ".join(["Maintenance",r.code,'(',r.property_id.display_name,')'])
            inserted_entry = entry.create({
                'date': date.today(),
                'ref': r.code,
                'move_type': 'entry',
            })
            for line in r.maintenance_line_ids:
                entry_lines_vals.append((0, 0, {
                    'name': " ".join([line.type_id.name,":",line.name,'(',r.property_id.display_name,')']),
                    'partner_id': partner_id,
                    'account_id': account_id,
                    'analytic_distribution': {str(r.property_id.analytic_acc_id.id): 100},
                    'debit': line.cost}))
            if r.mgmt_comm_amount > 0.0:
                entry_lines_vals.append((0, 0, {
                    'name': "".join(["Service cost for maintenance #",r.code]),
                    'partner_id': partner_id,
                    'analytic_distribution': {str(r.property_id.analytic_acc_id.id): 100},
                    'account_id': account_id,
                    'debit': r.mgmt_comm_amount}))

                entry_lines_vals.append((0, 0, {
                    'name': name,
                    'account_id': m_income_account_id,
                    'credit': r.mgmt_comm_amount}))

            entry_lines_vals.append((0, 0, {
                'name': name,
                'account_id': m_expense_account_id,
                'credit': r.cost}))


            inserted_entry.line_ids = entry_lines_vals
            entry_lines_vals=None
            r.write({
                'entry_id': inserted_entry.id,
            })
            r.sudo().create_exp(m_expense_account_id)

        action = self.env.ref('account.action_move_journal_line').sudo().read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = inserted_entry.id
        return action



    def create_exp(self,account_id):
        expense_obj = self.env['hr.expense']
        context = self.env.context
        current_uid = self.env.uid
        user = self.env['res.users'].sudo().browse(current_uid).id
        employee_id = self.env['hr.employee'].sudo().search([('user_id','=',user)]).id
        # print(employee_id.name)
        # employee_id=employee_id.id

        expense_product_id = self.env['product.product'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.maintenance_expense_product_id')))]).id
        for r in self:
            name=r.code
            expense=expense_obj.create({
                'name':"".join(['Maintenance #',name,' for ',r.property_id.display_name]),
                'product_id':expense_product_id,
                'total_amount_currency':r.cost,
                'employee_id':employee_id,
                'account_id':account_id,
                'payment_mode':'company_account'})
            r.write({'expense_id': expense.id,})
            # r.expense_id.action_submit_expenses();
            # r.expense_id.sheet_id.employee_id=employee_id
            # r.expense_id.sheet_id.action_submit_sheet();


    def create_invoice(self):
        invoice = self.env['account.move']
        # tenancy = self.env['pm.tenancy'].search([('property_id','=',self.property_id),('state','!=','')])
        invoice_lines_vals = []
        account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.maintenance_income_account_id')))]).id
        journal_id = self.get_invoice_journal()
        m_expense_account_id = self.env['account.account'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('tis_property_managment.maintenance_expense_account_id')))]).id

        for r in self:
            if r.invoice_id:
                return None
            if r.tenant_fault == True:
                partner_id = r.tenant_id.id
            elif r.tenant_fault == False:
                partner_id = r.landlord_id.id
            # currency_id = r.currency_id.id
            code = r.code
            inserted_invoice = invoice.create({
                'partner_id': partner_id,
                'invoice_date': date.today(),
                'journal_id': journal_id.id,
                'currency_id': r.property_id.currency_id.id,
                'move_type': 'out_invoice',
                'invoice_origin': code,
                'narration': code,})
            for line in r.maintenance_line_ids:
                invoice_lines_vals.append((0, 0, {
                    'name': "".join([line.type_id.name,":",line.name,'(',r.property_id.display_name,')']),
                    'account_id': account_id,
                    'analytic_distribution': {str(r.property_id.analytic_acc_id.id): 100},
                    'price_unit': line.cost}))
            invoice_lines_vals.append((0, 0, {
                'name':"Service Cost",
                'account_id': account_id,
                'analytic_distribution': {str(r.property_id.analytic_acc_id.id): 100},
                'price_unit': r.mgmt_comm_amount}))
            inserted_invoice.invoice_line_ids = invoice_lines_vals
            invoice_lines_vals=None
            r.write({
                'invoice_id': inserted_invoice.id,
            })

            r.invoice_id.action_post();
            r.sudo().create_exp(m_expense_account_id)
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = inserted_invoice.id
        return action
