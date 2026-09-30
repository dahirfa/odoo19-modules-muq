from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

CONTAINER_CONDITION = [
    ('good', 'Good'),
    ('damage', 'Damage'),
]

RESPONSIBLE_PARTY = [
    ('customer', 'Customer'),
    ('port_operation', 'Port Operation'),
    ('carrier', 'Carrier'),
]


class ContainerControl(models.Model):
    _name = 'container.control'
    _description = 'Container Control'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'container_number'
    _check_company_auto = True

    # sequence = fields.Integer(string='No.', default=10)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('closed', 'Closed'),
        ],
        string='Status',
        required=True,
        default='draft',
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    # vessel_name = fields.Char(string='Vessel Name')
    # voyage_no = fields.Char(string='Voyage No.')
    delivery_order_id = fields.Many2one(
        comodel_name='container.delivery.order',
        string='Delivery Order',
        index='btree_not_null',
        ondelete='cascade',
        check_company=True,
        copy=False,
    )

    # Container identification
    bill_of_lading = fields.Char(string='Bill of Lading', tracking=True)
    consignee_id = fields.Many2one(comodel_name='res.partner', string='Consignee Name', tracking=True)
    size_type_id = fields.Many2one(
        comodel_name='container.size.type',
        string='Size/Type',
        required=True,
        check_company=True,
        tracking=True,
    )
    container_number = fields.Char(string='Container #', required=True, tracking=True)
    tare_weight = fields.Float(string='Tare Weight')
    cargo_weight = fields.Float(string='Cargo Weight')

    # Discharge side
    discharge_status = fields.Selection(selection=CONTAINER_CONDITION, string='Container Discharge Status')
    discharge_damage_report_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='container_control_discharge_damage_attachment_rel',
        column1='container_control_id',
        column2='attachment_id',
        string='Damage Discharge Report Doc',
    )
    discharge_pic = fields.Char(string='Discharge PIC')
    discharge_responsible_party = fields.Selection(selection=RESPONSIBLE_PARTY, string='Discharge Responsible Party')
    discharge_date = fields.Date(string='Container Discharge Date', tracking=True)
    do_date = fields.Date(
        string='Date of the Delivery Order to Consignee',
        compute='_compute_do_date',
        store=True,
        readonly=False,
        tracking=True,
    )
    gate_out_date = fields.Date(string='Gate Out Date', tracking=True)
    gate_in_date = fields.Date(string='Gate In Date', tracking=True)
    total_days_out = fields.Integer(string='Total Days Out', compute='_compute_days', store=True)
    free_days = fields.Integer(string='Free Time', default=14, tracking=True)
    demurrage_days = fields.Integer(string='Demurrage Days', compute='_compute_days', store=True)
    demurrage_amount = fields.Monetary(
        string='Demurrage Rate',
        compute='_compute_demurrage_amount',
        store=True,
        currency_field='currency_id',
        help="Demurrage days priced with the Week 1 / Week 2 / Week 3 rates of the size/type.",
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id',
        help="Demurrage days multiplied by the average tiered daily rate.",
    )

    # Loading side
    loading_status = fields.Selection(selection=CONTAINER_CONDITION, string='Container Loading Status')
    loading_date = fields.Date(string='Container Loading Date', tracking=True)
    dwell_days = fields.Integer(string='Dwell Days', compute='_compute_days', store=True)
    loading_pic = fields.Char(string='Loading PIC')
    loading_responsible_party = fields.Selection(selection=RESPONSIBLE_PARTY, string='Loading Responsible Party')
    loading_status_note = fields.Char(string='Container Loading Status Note')
    picture_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='container_control_picture_attachment_rel',
        column1='container_control_id',
        column2='attachment_id',
        string='Picture',
    )
    loading_damage_report_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='container_control_loading_damage_attachment_rel',
        column1='container_control_id',
        column2='attachment_id',
        string='Damage Report Doc',
    )
    remarks = fields.Text(string='Remarks')

    # Demurrage invoicing
    free_time_end_date = fields.Date(
        string='Free Time Ends',
        compute='_compute_free_time_end_date',
        store=True,
        help="Delivery order date + free time.",
    )
    demurrage_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='container_control_id',
        string='Demurrage Invoice Lines',
        readonly=True,
    )
    billed_demurrage_days = fields.Integer(
        string='Invoiced Demurrage Days',
        compute='_compute_billed_demurrage_days',
        store=True,
        help="Demurrage days already on customer invoices (draft or posted), net of credit notes. "
             "Cancelled invoices are excluded.",
    )
    demurrage_days_to_invoice = fields.Integer(
        string='Demurrage Days to Invoice',
        compute='_compute_demurrage_days_to_invoice',
        store=True,
    )
    last_billed_date = fields.Date(
        string='Last Billed Day',
        compute='_compute_last_billed_date',
        store=True,
        help="Calendar date of the last invoiced demurrage day.",
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Demurrage Invoices',
        compute='_compute_invoice_ids',
    )
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_ids')

    def unlink(self):
        for record in self:
            if record.sudo().demurrage_line_ids:
                raise UserError(
                    self.env._(
                        "You cannot delete Container Control '%(container)s' "
                        "because it has one or more invoices.",
                        container=record.container_number,
                    )
                )
            if record.state == 'closed':
                raise UserError(
                    self.env._(
                        "You cannot delete Container Control '%(container)s' "
                        "because it is closed.",
                        container=record.container_number,
                    )
                )

        return super().unlink()

    @api.depends('delivery_order_id.date')
    def _compute_do_date(self):
        for record in self:
            record.do_date = record.delivery_order_id.date or record.do_date

    @api.depends('discharge_date', 'gate_in_date', 'loading_date', 'free_days')
    def _compute_days(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.discharge_date:
                end_date = record.gate_in_date or today
                record.total_days_out = max((end_date - record.discharge_date).days, 0)
            else:
                record.total_days_out = 0
            record.demurrage_days = max(record.total_days_out - record.free_days, 0)
            if record.discharge_date and record.loading_date:
                record.dwell_days = (record.loading_date - record.discharge_date).days
            else:
                record.dwell_days = 0

    @api.depends(
        'demurrage_days',
        'size_type_id.week1_rate',
        'size_type_id.week2_rate',
        'size_type_id.week3_rate',
    )
    def _compute_demurrage_amount(self):
        for record in self:
            if record.size_type_id and record.demurrage_days > 0:
                total_amount = record.size_type_id._get_tiered_amount(
                    record.demurrage_days
                )
                record.demurrage_amount = total_amount / record.demurrage_days
            else:
                record.demurrage_amount = 0.0

    @api.depends('demurrage_amount', 'demurrage_days')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (
                record.demurrage_amount * record.demurrage_days
            )

    @api.depends('do_date', 'free_days')
    def _compute_free_time_end_date(self):
        for record in self:
            if record.do_date:
                record.free_time_end_date = (
                    record.do_date + timedelta(days=record.free_days - 1)
                )
            else:
                record.free_time_end_date = False

    @api.depends(
        'demurrage_line_ids.quantity',
        'demurrage_line_ids.display_type',
        'demurrage_line_ids.parent_state',
        'demurrage_line_ids.move_id.move_type',
    )
    def _compute_billed_demurrage_days(self):
        for record in self:
            billed_days = 0.0
            for line in record.demurrage_line_ids:
                if line.display_type != 'product' or line.parent_state == 'cancel':
                    continue
                if line.move_id.move_type == 'out_invoice':
                    billed_days += line.quantity
                elif line.move_id.move_type == 'out_refund':
                    billed_days -= line.quantity
            record.billed_demurrage_days = max(round(billed_days), 0)

    @api.depends('demurrage_days', 'billed_demurrage_days')
    def _compute_demurrage_days_to_invoice(self):
        for record in self:
            record.demurrage_days_to_invoice = max(record.demurrage_days - record.billed_demurrage_days, 0)

    @api.depends('discharge_date', 'free_days', 'billed_demurrage_days')
    def _compute_last_billed_date(self):
        for record in self:
            # Demurrage day N falls on discharge date + free time + N (see _compute_days).
            if record.discharge_date and record.billed_demurrage_days:
                record.last_billed_date = record.discharge_date + timedelta(
                    days=record.free_days + record.billed_demurrage_days)
            else:
                record.last_billed_date = False

    @api.depends('demurrage_line_ids.move_id')
    def _compute_invoice_ids(self):
        for record in self:
            record.invoice_ids = record.demurrage_line_ids.move_id
            record.invoice_count = len(record.invoice_ids)

    @api.constrains('discharge_date', 'gate_out_date', 'gate_in_date')
    def _check_dates(self):
        for record in self:
            if record.gate_out_date and record.gate_in_date and record.gate_in_date < record.gate_out_date:
                raise ValidationError(self.env._(
                    "Container %s: Gate In Date cannot be before Gate Out Date.", record.container_number))
            if record.discharge_date and record.gate_in_date and record.gate_in_date < record.discharge_date:
                raise ValidationError(self.env._(
                    "Container %s: Gate In Date cannot be before Discharge Date.", record.container_number))

    @api.constrains('free_days')
    def _check_free_days(self):
        for record in self:
            if record.free_days < 0:
                raise ValidationError(self.env._("Free time cannot be negative."))

    @api.onchange('delivery_order_id', 'do_date')
    def _onchange_do_date(self):
        for record in self:
            if record.do_date and not record.billed_demurrage_days:
                record.discharge_date = record.do_date
    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------

    def action_start(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(self.env._("Only draft records can be started."))
            missing = [
                label for field_name, label in (
                    ('consignee_id', self.env._("Consignee Name")),
                    ('size_type_id', self.env._("Size/Type")),
                    ('do_date', self.env._("Date of the Delivery Order to Consignee")),
                ) if not record[field_name]
            ]
            if missing:
                raise UserError(self.env._(
                    "Container %(container)s cannot be started. Missing: %(fields)s",
                    container=record.container_number,
                    fields=", ".join(missing),
                ))
        self.write({'state': 'in_progress'})

    def action_close(self):
        for record in self:
            if record.state != 'in_progress':
                raise UserError(self.env._("Only records In Progress can be closed."))
            if not record.gate_in_date:
                raise UserError(self.env._(
                    "Container %s: set the Gate In Date before closing.", record.container_number))
        self._refresh_demurrage_days()
        self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_view_invoices(self):
        self.ensure_one()
        invoices = self.invoice_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': self.env._("Demurrage Invoices"),
            'res_model': 'account.move',
            'context': {'default_move_type': 'out_invoice'},
        }
        if len(invoices) == 1:
            action.update({'view_mode': 'form', 'res_id': invoices.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', invoices.ids)]})
        return action

    # ------------------------------------------------------------
    # Demurrage billing
    # ------------------------------------------------------------

    def _refresh_demurrage_days(self):
        """Days out keep growing until Gate In: recompute the stored day counts and their dependents."""
        records = self.filtered('discharge_date')
        records.modified(['discharge_date'])
        records.flush_recordset()

    def _prepare_demurrage_invoice_line_vals(self):
        """One invoice line per container for its demurrage days not invoiced yet.

        Demurrage days billed_demurrage_days + 1 .. demurrage_days are priced with the
        Week 1 / Week 2 / Week 3 tiers; the unit price is their daily rate (averaged when
        the unbilled days span more than one tier). Lines carry no product: only
        the container number as label.
        """
        vals_list = []
        for record in self:
            quantity = record.demurrage_days_to_invoice
            if quantity <= 0:
                continue
            size_type = record.size_type_id
            amount = (
                size_type._get_tiered_amount(record.demurrage_days)
                - size_type._get_tiered_amount(record.billed_demurrage_days)
            )
            vals_list.append({
                'name': record.container_number,
                'quantity': quantity,
                'price_unit': amount / quantity,
                'container_control_id': record.id,
                'account_id': size_type.demurrage_account_id.id,
                
            })
        return vals_list
