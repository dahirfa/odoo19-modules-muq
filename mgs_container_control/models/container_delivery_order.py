import base64
import io
from datetime import datetime, time, timedelta

import xlsxwriter
from PIL import Image

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

# Pixel box left for the report logo in the Excel header (columns A:E, rows 1-2).
LOGO_MAX_WIDTH = 300
LOGO_MAX_HEIGHT = 300


class ContainerDeliveryOrder(models.Model):
    _name = 'container.delivery.order'
    _description = 'Delivery Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='D.O No.', required=True, readonly=True, copy=False, default='New')
    date = fields.Date(string='D.O Date', required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    consignee_id = fields.Many2one(comodel_name='res.partner', string='Consignee (Messrs.)', tracking=True)
    bl_number = fields.Char(string='BL Number', tracking=True)
    vessel_name = fields.Char(string='Vessel Name')
    voyage_no = fields.Char(string='Voyage No.')
    vessel_eta = fields.Date(string='Vessel ETA')
    declaration_date = fields.Date(string='Declaration Date')
    total_packages = fields.Integer(string='Total Packages')
    total_weight = fields.Float(
        string='Total Weight',
        compute='_compute_total_weight',
        store=True,
        readonly=False,
    )
    
    container_qty_summary = fields.Char(string='Quantity of Containers', compute='_compute_container_quantities')
    terminal = fields.Char(string='Terminal', default="Mogadishu Port, Albayrak terminal")
    goods_description = fields.Text(string='Goods Description')
    haulage = fields.Char(string='Haulage', default="YES")
    port_of_load = fields.Char(string='Port of Load')
    port_of_discharge = fields.Char(string='Port of Discharge', default="MOGADISHU")
    haulage_instructions = fields.Text(string='Haulage Instructions')
    free_time_valid_date = fields.Date(
        string='Free Time Valid',
        compute='_compute_free_time_valid_date',
        store=True,
        readonly=False,
    )
    container_date_in = fields.Date(string='Container Date In')
    container_ids = fields.One2many(
        comodel_name='container.control',
        inverse_name='delivery_order_id',
        string='Containers',
    )
    invoice_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='container_delivery_order_id',
        string='Demurrage Invoices',
        readonly=True,
    )
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    @api.depends('container_ids.cargo_weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(order.container_ids.mapped('cargo_weight'))

    @api.depends('container_ids.size_type_id')
    def _compute_container_quantities(self):
        for order in self:
            size_counts = {}

            for container in order.container_ids:
                size_type = container.size_type_id
                if size_type:
                    size_counts[size_type] = size_counts.get(size_type, 0) + 1

            order.container_qty_summary = " / ".join(
                f"{qty}x{size_type.size_feet}"
                for size_type, qty in sorted(
                    size_counts.items(),
                    key=lambda x: x[0].size_feet
                )
            )

    @api.depends('date', 'container_ids.free_days')
    def _compute_free_time_valid_date(self):
        for order in self:
            if order.date:
                free_days = max(order.container_ids.mapped('free_days') or [0])
                order.free_time_valid_date = order.date + timedelta(days=free_days)
            else:
                order.free_time_valid_date = False

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                company = self.env['res.company'].browse(vals.get('company_id')) or self.env.company
                vals['name'] = self.env['ir.sequence'].with_company(company).next_by_code(
                    'container.delivery.order', sequence_date=vals.get('date')) or 'New'
        return super().create(vals_list)

    def unlink(self):
        for order in self:
            if order.sudo().invoice_ids:
                raise UserError(self.env._(
                    "You cannot delete Delivery Order '%s' because it has demurrage invoices.", order.name))
            started = order.container_ids.filtered(lambda c: c.state != 'draft')
            if started:
                raise UserError(self.env._(
                    "You cannot delete Delivery Order '%(order)s' because it has started containers: %(containers)s",
                    order=order.name,
                    containers=", ".join(started.mapped('container_number')),
                ))
        return super().unlink()

    # ------------------------------------------------------------
    # Demurrage invoicing
    # ------------------------------------------------------------

    def action_generate_demurrage_invoice(self):
        invoices = self.env['account.move']
        for order in self:
            invoices |= order._create_demurrage_invoice()
        return invoices._get_records_action(name=self.env._("Demurrage Invoices"))

    def action_view_invoices(self):
        self.ensure_one()
        return self.invoice_ids._get_records_action(
            name=self.env._("Demurrage Invoices"),
            context={'default_move_type': 'out_invoice'},
        )

    def _create_demurrage_invoice(self):
        """One customer invoice for the delivery order, one line per container.

        Each line bills only the container's demurrage days that are not on an invoice
        yet, so running this again later adds just the newly accrued days. Invoiced
        containers that have their Gate In Date are closed afterwards.
        """
        self.ensure_one()
        if not self.consignee_id:
            raise UserError(self.env._(
                "Delivery Order %s: set the Consignee before generating the demurrage invoice.", self.name))
        containers = self.container_ids.filtered(lambda container: container.state != 'draft')
        containers._refresh_demurrage_days()
        line_vals_list = containers._prepare_demurrage_invoice_line_vals()
        if not line_vals_list:
            raise UserError(self.env._(
                "Delivery Order %s has no uninvoiced demurrage days on its started containers.", self.name))
        invoice = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'out_invoice',
            'partner_id': self.consignee_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.company_id.currency_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'ref': " / ".join(filter(None, [self.name, self.bl_number])),
            'container_delivery_order_id': self.id,
            'invoice_line_ids': [Command.create(vals) for vals in line_vals_list],
        })
        self.message_post(body=self.env._("Demurrage invoice %s created.", invoice._get_html_link()))
        # Containers back in (Gate In set) are fully billed now: close them. Containers
        # still out stay In Progress so their next demurrage days can be invoiced later.
        self.container_ids.filtered(
            lambda container: container.state == 'in_progress' and container.gate_in_date
        ).action_close()
        return invoice

    def action_export_xlsx(self):
        self.ensure_one()
        attachment = self.env['ir.attachment'].create({
            'name': self._get_xlsx_filename(),
            'type': 'binary',
            'datas': base64.b64encode(self._get_xlsx_content()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    # ------------------------------------------------------------
    # Excel export
    # ------------------------------------------------------------

    def _get_xlsx_filename(self):
        self.ensure_one()
        return f"Delivery Order - {self.name.replace('/', '-')}.xlsx"

    def _get_xlsx_content(self):
        """Delivery order workbook laid out like the DO sample; day columns are live formulas."""
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self.env._("Delivery Order"))
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.fit_to_pages(1, 0)
        # sheet.hide_gridlines(2)

        base = {'font_size': 10, 'valign': 'vcenter'}
        fmt = {
            'title': workbook.add_format({ 'bold': True, 'font_size': 16, 'align': 'center'}),
            'address': workbook.add_format({**base, 'font_size': 8, 'text_wrap': True, 'align': 'left'}),
            'label': workbook.add_format({**base, 'bold': True}),
            'value': workbook.add_format({**base, 'text_wrap': True}),
            'value_date': workbook.add_format({**base, 'num_format': 'dd/mm/yyyy', 'align': 'left'}),
            'value_number': workbook.add_format({**base, 'num_format': '#,##0.00', 'align': 'left'}),
            'th': workbook.add_format({
                **base, 'bold': True, 'border': 1, 'align': 'center',  'bg_color': '#DCE6F1'}),
            'td': workbook.add_format({**base, 'border': 1, 'align': 'center'}),
            'td_date': workbook.add_format({**base, 'border': 1, 'align': 'center', 'num_format': 'dd/mm/yyyy'}),
            'td_int': workbook.add_format({**base, 'border': 1, 'align': 'center', 'num_format': '0'}),
            'td_number': workbook.add_format({**base, 'border': 1, 'align': 'right', 'num_format': '#,##0.00'}),
            'total_label': workbook.add_format({**base, 'bold': True, 'border': 1, 'align': 'right'}),
            'total_number': workbook.add_format({
                **base, 'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0.00'}),
            'confirm': workbook.add_format({**base, 'bold': True, 'text_wrap': True, 'valign': 'top'}),
        }

        column_widths = {
            'A': 6, 'B': 10, 'C': 10, 'D': 8, 'E': 8, 'F': 9, 'G': 9, 'H': 8, 'I': 8, 'J': 8,
            'K': 12, 'L': 12, 'M': 12, 'N': 12, 'O': 10, 'P': 9, 'Q': 11, 'R': 10, 'S': 10, 'T': 10,
            'U': 14, 'V': 12, 'W': 10,
        }
        for column, width in column_widths.items():
            sheet.set_column(f'{column}:{column}', width)

        def to_datetime(value):
            return datetime.combine(value, time.min) if value else None

        def write_merged(cell_range, value, cell_format):
            first_cell = cell_range.split(':')[0]
            sheet.merge_range(cell_range, '', cell_format)
            if value in (None, False, ''):
                return
            if isinstance(value, datetime):
                sheet.write_datetime(first_cell, value, cell_format)
            elif isinstance(value, (int, float)):
                sheet.write_number(first_cell, value, cell_format)
            else:
                sheet.write_string(first_cell, str(value), cell_format)

        # Header: logo, title, company address
        # company = self.company_id
        # sheet.set_row(0, 45)
        # sheet.set_row(1, 55)
        # self._xlsx_insert_logo(sheet, 'B1')
        # write_merged('F1:H1', self.env._("DELIVERY ORDER"), fmt['title'])
        # write_merged('F2:H2', company.delivery_address or '', fmt['address'])
        # Header: title on row 1, logo and address on row 2
        company = self.company_id

        sheet.set_row(0, 35)
        sheet.set_row(1, 65)

        # Row 1 - Delivery Order title
        write_merged('A1:J1', self.env._("DELIVERY ORDER"), fmt['title'])

        # Row 2 - Logo and company address
        sheet.merge_range('A2:E2', '', fmt['value'])
        self._xlsx_insert_logo(sheet, 'A2')

        write_merged(
            'F2:J2',
            company.delivery_address or '',
            fmt['address']
        )
        # Delivery order information
        vessel_voyage = " / ".join(filter(None, [self.vessel_name, self.voyage_no]))
        info_rows = [
            (self.env._("D.O No."), self.name, self.env._("BL Number"), self.bl_number),
            (self.env._("Vessel Name / Voyage No."), vessel_voyage,
             self.env._("Declaration Date"), to_datetime(self.declaration_date)),
            (self.env._("Vessel ETA"), to_datetime(self.vessel_eta), self.env._("D.O Date"), to_datetime(self.date)),
            (self.env._("Total Packages"), self.total_packages, self.env._("Consignee"), self.consignee_id.name),
            (self.env._("Total Weight"), self.total_weight, self.env._("Terminal"), self.terminal),
            (self.env._("Quantity of Containers"), self.container_qty_summary, self.env._("Haulage"), self.haulage),
            (self.env._("Goods Description"), self.goods_description, None, None),
            (self.env._("Port of Load"), self.port_of_load, self.env._("Port of Discharge"), self.port_of_discharge),
        ]
        row = 3
        for left_label, left_value, right_label, right_value in info_rows:
            for label, value, label_range, value_range in (
                (left_label, left_value, f'A{row}:B{row}', f'C{row}:E{row}'),
                (right_label, right_value, f'F{row}:G{row}', f'H{row}:J{row}'),
            ):
                if label is None:
                    continue
                write_merged(label_range, f"{label} :", fmt['label'])
                if isinstance(value, datetime):
                    value_format = fmt['value_date']
                elif isinstance(value, float):
                    value_format = fmt['value_number']
                else:
                    value_format = fmt['value']
                write_merged(value_range, value, value_format)
            row += 1

        # Container table - ONLY these 5 columns
        # A = NO. | B = Container No | C = Size/Type | D = Tare Weight | E = Cargo Weight
        # Keep the original design: borders, border colors, header background, fonts, etc.
        header_row = row + 1
        headers = [
            ('A', self.env._("NO.")),
            ('B', self.env._("Container No")),
            ('C', self.env._("Size/Type")),
            ('D', self.env._("Tare Weight")),
            ('E', self.env._("Cargo Weight")),
        ]
        sheet.set_row(header_row - 1, 30)
        for column, label in headers:
            sheet.write_string(f'{column}{header_row}', label, fmt['th'])

        first_line_row = header_row + 1
        row = first_line_row
        for index, container in enumerate(self.container_ids, start=1):
            size_type = container.size_type_id

            sheet.write_number(f'A{row}', index, fmt['td'])
            sheet.write_string(f'B{row}', container.container_number or '', fmt['td'])
            sheet.write_string(f'C{row}', size_type.name if size_type else '', fmt['td'])
            sheet.write_number(f'D{row}', container.tare_weight or 0.0, fmt['td_number'])
            sheet.write_number(f'E{row}', container.cargo_weight or 0.0, fmt['td_number'])
            row += 1

        last_line_row = row - 1

        # Total row - only the same 5 columns
        sheet.write_string(f'C{row}', self.env._("Total"), fmt['total_label'])
        if self.container_ids:
            sheet.write_formula(
                f'D{row}',
                f'=SUM(D{first_line_row}:D{last_line_row})',
                fmt['total_number'],
                sum(self.container_ids.mapped('tare_weight')),
            )
            sheet.write_formula(
                f'E{row}',
                f'=SUM(E{first_line_row}:E{last_line_row})',
                fmt['total_number'],
                sum(self.container_ids.mapped('cargo_weight')),
            )
        else:
            sheet.write_number(f'D{row}', 0.0, fmt['total_number'])
            sheet.write_number(f'E{row}', 0.0, fmt['total_number'])

        # Footer
        row += 2
        write_merged(f'A{row}:E{row}', self.env._("Haulage Instructions:"), fmt['label'])
        write_merged(
            f'F{row}:J{row + 2}',
            self.env._('WE KINDLY CONFIRM RELEASING OF ABOVE MENTIONED CARGOES TO MESSRS. "%s" WITH THANKS.',
                       self.consignee_id.name or ''),
            fmt['confirm'])
        write_merged(f'A{row + 1}:E{row + 2}', self.haulage_instructions, fmt['value'])
        row += 3
        write_merged(f'A{row}:B{row}', self.env._("FREE TIME VALID"), fmt['label'])
        write_merged(f'C{row}:E{row}', to_datetime(self.free_time_valid_date), fmt['value_date'])
        row += 4
        write_merged(f'A{row}:D{row}', self.env._("APPROVED STAMP/SIGNATURE"), fmt['label'])
        write_merged(f'F{row}:H{row}', self.env._("CONTAINER DATE IN :"), fmt['label'])
        write_merged(f'I{row}:J{row}', to_datetime(self.container_date_in), fmt['value_date'])
        sheet.write_string(f'A{row + 1}', "......................................................", fmt['value'])

        workbook.close()
        return output.getvalue()

    def _xlsx_insert_logo(self, sheet, cell):
        logo = self.company_id.delivery_order_report_logo
        if not logo:
            return
        try:
            image_bytes = base64.b64decode(logo)
            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
        except (OSError, ValueError):
            # e.g. SVG logos, which xlsxwriter cannot embed
            return
       
        scale = min(LOGO_MAX_WIDTH / width, LOGO_MAX_HEIGHT / height) if width and height else 1
        sheet.insert_image(cell, 'logo.png', {
            'image_data': io.BytesIO(image_bytes),
            'x_scale': scale,
            'y_scale': scale,
            'x_offset': 4,
            'y_offset': 4,
        })
