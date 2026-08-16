from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FreightDelivery(models.Model):
    _name = 'freight.delivery'
    _description = 'Freight Delivery'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        default='New',
        readonly=True,
    )
    container_no = fields.Char(required=True,tracking=True)
    bl_no = fields.Char(
        string='BL Number',
        required=True,
        tracking=True
    )
    customer_rate = fields.Float(string="Customer Rate",tracking=True)
    vendor_rate = fields.Float(string="Vendor Rate",tracking=True)
    order_date = fields.Date(
        string='Date',
        default=fields.Date.today(),
        tracking=True
    )
    shipper_id = fields.Many2one(
        'res.partner',
        required=True,
        tracking=True
    )
    expected_date = fields.Date(
        string='Expected Date',
        tracking=True
    )
    delivery_ids = fields.One2many(
        'freight.delivery.line',
        'delivery_id'
    )
    service_ids = fields.One2many(
        'freight.delivery.service.line',
        'delivery_id'
    )
    vendor_id = fields.Many2one(
        'res.partner',
        required=True,
        tracking=True
    )
    bill_id = fields.Many2one(
        'account.move',
        string="Vendor Bill",
        readonly=True
    )
    bill_count = fields.Integer(
        string="Vendor Bill Count",
        compute="count_bill"
    )
    invoice_ids = fields.One2many(
        'account.move',
        'delivery_id'
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute="_compute_invoice_count"
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    total_price = fields.Monetary(
        compute="_compute_total_price",
        store=True,
        currency_field="currency_id"
    )
    source_port_id = fields.Many2one(
        'freight.port',
        required=True,
        tracking=True
    )
    destination_port_id = fields.Many2one(
        'freight.port',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company
    )
    state = fields.Selection(
        [("draft", "Draft"), ("confirm", "Confirmed"), ("bill", "Billed")],
        string="Status",
        default='draft',
        copy=False,
        tracking=True
    )
    total_ctn = fields.Float(
        string="Total CTN",
        compute="_compute_totals",
        store=True,
        readonly=True
    )
    total_cbm = fields.Float(
        string="Total CBM",
        compute="_compute_totals",
        store=True,
        readonly=True
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
        tracking=True
    )
    def unlink(self):

        for rec in self:
            if rec.invoice_ids or rec.bill_id:
                raise ValidationError(
                    "Cannot delete delivery with invoices and bills")

            if rec.state == 'confirm':
                raise UserError(
                    "Delivery cannot be deleted once it is confirmed.")

        return super(FreightDelivery, self).unlink()

    @api.depends('delivery_ids.ctn', 'delivery_ids.cbm')
    def _compute_totals(self):
        for record in self:
            total_ctn = 0.0
            total_cbm = 0.0
            for line in record.delivery_ids:
                total_ctn += line.ctn
                total_cbm += line.cbm
            record.total_ctn = total_ctn
            record.total_cbm = total_cbm

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):
    #         vals['name'] = self.env['ir.sequence'].next_by_code(
    #             'freight.delivery')
    #     record =  super(FreightDelivery, self).create(vals)
        
    #     company = self.env.company
    #     if not company.analytic_plan_id:
    #         raise ValidationError("Please select an analytic plan in the configuration.")
        
    #     analytic_account = self.env['account.analytic.account'].create({
    #         'name': f"{record.container_no} - {record.bl_no}",
    #         'plan_id': company.analytic_plan_id.id,
    #         'company_id': record.company_id.id,
    #     })

    #     record.analytic_account_id = analytic_account.id
    #     return record
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("freight.delivery")
                    or _("New")
                )

        records = super().create(vals_list)

        for record in records:
            company = record.company_id or self.env.company

            if not company.analytic_plan_id:
                raise ValidationError(
                    _("Please select an analytic plan in the configuration.")
                )

            analytic_account = self.env["account.analytic.account"].create({
                "name": f"{record.container_no} - {record.bl_no}",
                "plan_id": company.analytic_plan_id.id,
                "company_id": company.id,
            })
            record.analytic_account_id = analytic_account.id
            
        return records
    def write(self, vals):
        res = super(FreightDelivery, self).write(vals)

        # If container_no or bl_no changed → update analytic account name
        for record in self:
            if 'container_no' in vals or 'bl_no' in vals:
                if record.analytic_account_id:
                    new_name = f"{record.container_no} - {record.bl_no}"
                    record.analytic_account_id.name = new_name

        return res
    @api.depends('delivery_ids.total_cbm')
    def _compute_total_price(self):
        for order in self:
            order.total_price = sum(
                line.total_cbm for line in order.delivery_ids)

    def action_confirm(self):
        for delivery in self:
            for line in delivery.delivery_ids:
                for product_line in line.product_ids:
                    # Get all receipt lines for the selected receipt_id and product
                    receipt_lines = self.env['freight.receipt.line'].search([
                        ('receipt_id', '=', line.receipt_id.id),
                        ('product_id', '=', product_line.product_id.id),
                        ('remaining', '>', 0),
                    ], order='id')  # Order by ID or any other logic to prioritize lines

                    remaining_to_load = product_line.ctn  # Total quantity to load

                    for receipt_line in receipt_lines:
                        if remaining_to_load <= 0:
                            break  # Stop if no more quantity needs to be loaded

                        # Calculate how much can be loaded from this receipt line
                        load_quantity = min(
                            remaining_to_load, receipt_line.remaining)

                        # Update the ctn_delivered and remaining fields
                        receipt_line.ctn_delivered += load_quantity
                        remaining_to_load -= load_quantity

                    if remaining_to_load > 0:
                        raise UserError(
                            _(f"Cannot load {product_line.ctn} ctn of {product_line.product_id.name}. Only {product_line.ctn - remaining_to_load} ctn were available."))

            delivery.write({'state': 'confirm'})

    def reset_to_draft(self):
        for delivery in self:
            if delivery.bill_id or delivery.invoice_ids:
                raise UserError("You cannot set this delivery to draft because it has already been billed or invoiced.")
            
            for line in delivery.delivery_ids:
                for product_line in line.product_ids:
                    # Get all receipt lines for the selected receipt_id and product
                    receipt_lines = self.env['freight.receipt.line'].search([
                        ('receipt_id', '=', line.receipt_id.id),
                        ('product_id', '=', product_line.product_id.id),
                        # Only consider lines with ctn_delivered > 0
                        ('ctn_delivered', '>', 0),
                    ])

                    remaining_to_reset = product_line.ctn  # Total quantity to reverse

                    for receipt_line in receipt_lines:
                        if remaining_to_reset <= 0:
                            break  # Stop if no more quantity needs to be reversed

                        # Calculate how much can be reversed from this receipt line
                        reverse_quantity = min(
                            remaining_to_reset, receipt_line.ctn_delivered)

                        # Revert the ctn_delivered 
                        receipt_line.ctn_delivered -= reverse_quantity
                        remaining_to_reset -= reverse_quantity

                    if remaining_to_reset > 0:
                        raise UserError(
                            _(f"Cannot reverse {product_line.ctn} ctn of {product_line.product_id.name}. Only {product_line.ctn - remaining_to_reset} ctn were delivered."))

        # Change the state back to draft
        self.write({'state': 'draft'})

    def create_bill(self):
        move_obj = self.env['account.move']
        for r in self:
            if not r.expected_date:
                raise UserError("Please select an expected date.")
            move_id = move_obj.create(r._prepare_bill())
            move_id.invoice_line_ids = []
            move_id.invoice_line_ids = r._prepare_bill_lines()
            move_id.action_post()
            r.bill_id = move_id.id
            self.write({'state': 'bill'})
    def action_view_bill(self):
        action = self.env.ref(
            'account.action_move_in_invoice_type').sudo().read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.bill_id.id
        return action

    @api.depends('bill_id')
    def count_bill(self):
        for r in self:
            r.bill_count = len(r.bill_id)

    def _prepare_bill_lines(self):
        analytic = self.analytic_account_id
        lines = []
        for line in self.delivery_ids:
            lines.append((0, 0, {
                'name': line.description,
                'quantity': line.cbm,
                'price_unit': line.shipper_rate,
                'analytic_distribution': {analytic.id: 100}
            }))
        return lines

    def _prepare_bill(self):
        if not self.vendor_id:
            raise ValidationError("Set Vendor to create a Bill")
        return {
            'move_type': 'in_invoice',
            'invoice_date': self.expected_date,
            'date': self.expected_date,
            'partner_id': self.vendor_id.id,
            'ref': f"{self.container_no} - {self.bl_no}"
        }

    def create_invoice(self):
        move_obj = self.env['account.move']
        for record in self:
            if not record.expected_date:
                raise UserError("Please select an expected date.")
            
            if not record.delivery_ids:
                raise ValidationError(
                    "No delivery lines found to create invoices.")

            for delivery in record.delivery_ids:
                invoice_vals = record._prepare_inv(delivery)
                move_id = move_obj.create(invoice_vals)

                # Prepare invoice lines
                invoice_lines = record._prepare_inv_lines(delivery)
                move_id.invoice_line_ids = invoice_lines

                move_id.action_post()
                record.invoice_ids = [(4, move_id.id)]

    def _prepare_inv(self, delivery):
        return {
            'move_type': 'out_invoice',
            'invoice_date': self.expected_date,
            'date': self.expected_date,
            'partner_id': delivery.receipt_id.customer_id.id,
            'ref': f"{self.container_no} - {self.bl_no}",
        }
        
    
  

    def _prepare_inv_lines(self, delivery):
        company = self.env.company
        if not company.freight_product_id:
            raise ValidationError("Cannot create invoice: Please configure the freight product in company settings")
        analytic = self.analytic_account_id
        lines = []
        lines.append((0, 0, {
            'product_id':company.freight_product_id.id,
            'name': delivery.description,
            'quantity': delivery.cbm,
            'price_unit': delivery.rate,
            'analytic_distribution': {analytic.id: 100}
           
        }))

        for service in self.service_ids:
            if service.product_id.measurement_type == 'cbm':
                quantity = delivery.cbm
            else:
                quantity = delivery.ctn

            lines.append((0, 0, {
                'product_id': service.product_id.id,
                'name': service.product_id.name,
                'quantity': quantity,
                'price_unit': service.product_id.list_price,
                'analytic_distribution': {analytic.id: 100}

            }))

        return lines

    def action_view_invoices(self, invoices=False):

        invoices = self.invoice_ids

        result = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_in_invoice_type')

        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + \
                    [(state, view)
                     for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)


class FreightDeliveryLine(models.Model):
    _name = 'freight.delivery.line'
    _description = 'Freight Delivery Line'

    delivery_id = fields.Many2one(
        'freight.delivery',
        ondelete="cascade"
    )
    receipt_id = fields.Many2one(
        'freight.receipts',
        required=True
    )
    description = fields.Char(
        compute="_compute_product_names",
        store=True
    )
    ctn = fields.Float(
        string="CTN Load",
        help="Number of cartons",
        compute="_compute_totals",
        store=True
    )
    cbm = fields.Float(
        string="CBM Load",
        help="Cubic meters per carton",
        compute="_compute_totals",
        store=True
    )
    rate = fields.Float(string="Customer Rate", related='delivery_id.customer_rate',
                        readonly=False, store=True, help="Customer Rate")
    shipper_rate = fields.Float(string="Shiiper Rate", related='delivery_id.vendor_rate',
                                readonly=False, store=True, help="Shiiper Rate per CBM")
    
    total_cbm = fields.Float(
        string="Total CBM Price",
        compute="_compute_total_cbm",
        store=True
    )
    product_ids = fields.One2many(
        'freight.product.line',
        'delivery_line_id'
    )
    state = fields.Selection(
        related='delivery_id.state',
        string="Status",
        readonly=True
    )

    @api.onchange('receipt_id')
    def _onchange_receipt_id(self):
        if self.receipt_id:
            self.product_ids = [(5, 0, 0)]
            for receipt_line in self.receipt_id.freight_receipt_ids.filtered(lambda r: r.remaining > 0):
                self.product_ids = [(0, 0, {
                    'product_id': receipt_line.product_id.id,
                    'ctn': receipt_line.remaining,
                    'pcs': receipt_line.pcs,
                    'model': receipt_line.model,
                    'reference': receipt_line.reference,
                    'item_image': receipt_line.item_image,
                    'cbm': receipt_line.cbm,
                    'size_ctn': f"{receipt_line.length}*{receipt_line.width}*{receipt_line.height} "
                })]

    @api.depends('product_ids.product_id')
    def _compute_product_names(self):
        for line in self:
            line.description = '/'.join(
                line.product_ids.mapped('product_id.name'))

    @api.depends('product_ids.ctn', 'product_ids.cbm')
    def _compute_totals(self):
        for line in self:
            line.ctn = sum(line.product_ids.mapped('ctn'))
            line.cbm = sum(line.product_ids.mapped('total_cbm'))

    @api.depends('rate', 'cbm')
    def _compute_total_cbm(self):
        for line in self:
            line.total_cbm = line.rate * line.cbm


class FreightDeliveryProductLine(models.Model):
    _name = 'freight.product.line'
    _description = 'Freight Product Line'

    delivery_line_id = fields.Many2one(
        'freight.delivery.line',
    )
    product_id = fields.Many2one(
        'product.template',
        required=True,
    )
    ctn = fields.Float(
        string="CTN Load",
        help="Number of cartons"
    )
    pcs = fields.Float(
        string="Qty/Ctn"
    )
    t_qty = fields.Float(
        string="T.Qty",
        compute="_compute_t_qty",
        store=True
    )
    cbm = fields.Float(
        string="CBM Load",
        help="Cubic meters per carton"
    )
    total_cbm = fields.Float(
        string="Total CBM Price",
        compute="_compute_total_cbm",
        store=True
    )
   
    reference = fields.Char()
    model = fields.Char()
    item_image = fields.Binary("Photo")
    select = fields.Boolean()
    size_ctn = fields.Char(
        string="Size/Ctn"
        )
    @api.depends('ctn', 'pcs')
    def _compute_t_qty(self):
        for line in self:
            line.t_qty = line.ctn * line.pcs

    @api.depends('ctn', 'cbm')
    def _compute_total_cbm(self):
        for line in self:
            line.total_cbm = line.ctn * line.cbm

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            vals for vals in vals_list
            if vals.get("select")
        ]

        if not vals_list:
            return self.browse()

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if not record.select:
                record.unlink()
        return res
class FreightDeliveryServiceLine(models.Model):
    _name = 'freight.delivery.service.line'
    _description = 'Freight Delivery Service Line'

    delivery_id = fields.Many2one(
        'freight.delivery',
        string='Freight Order',
    )
    product_id = fields.Many2one(
        'product.template',
        required=True,
    )
    price = fields.Float(
        related="product_id.list_price"
    )
