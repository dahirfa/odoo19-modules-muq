import xlsxwriter  # type: ignore
from io import BytesIO
import base64
from odoo import models, fields, api  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class MgsSaleReportWizard(models.TransientModel):
    _name = "mgs.sale.report.wizard"
    _description = "Sales Report Wizard"

    # Date Range
    date_from = fields.Date(
        string="Date From", default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(string="Date To", default=lambda self: fields.Date.today())

    # Sales Filters
    user_id = fields.Many2one("res.users", string="Salesperson")
    team_id = fields.Many2one("crm.team", string="Sales Team")
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist")

    # Company & Currency
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )

    # Sales Tags
    sales_tag_ids = fields.Many2many("crm.tag", string="Sales Tags")

    # Customer & Product Filters
    partner_id = fields.Many2one("res.partner", string="Customer")
    product_id = fields.Many2one("product.product", string="Product")
    categ_id = fields.Many2one("product.category", string="Product Category")
    parent_categ_id = fields.Many2one("product.category", string="Parent Category")

    # Report Options
    report_type = fields.Selection(
        [("summary", "Summary"), ("detail", "Detail")],
        string="Report Type",
        default="summary",
        required=True,
    )

    group_by = fields.Selection(
        [("customer", "Sales by Customer"), ("item", "Sales by Item")],
        string="Group By",
        default="customer",
        required=True,
    )

    datas = fields.Binary("File", readonly=True)
    datas_fname = fields.Char("Filename", readonly=True)

    def check_report(self):
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": self.read()[0],  # Read all field values
        }
        return self.env.ref("mgs_sale.action_report_mgs_sale").report_action(
            self, data=data
        )

    def export_to_excel(self):
        """Generates an Excel file supporting both Summary and Detail formats"""

        # Fetch data based on filters
        sales_report_obj = self.env["report.mgs_sale.sale_report"]
        data = self.read()[0]  # Read field values dynamically
        grouped_lines = sales_report_obj._grouped_lines(data)

        # Prepare Excel Workbook
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet("Sales Report")

        # --- Styling: modern, clean, professional ---
        header_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#F2F6FA",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 11,
            }
        )

        # Basic cell formats
        date_format = workbook.add_format(
            {
                "num_format": "yyyy-mm-dd",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 10,
            }
        )
        int_format = workbook.add_format(
            {"num_format": "#,##0", "border": 1, "align": "right"}
        )
        money_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "font_name": "Calibri",
            }
        )

        # Row striping for readability
        even_row = workbook.add_format(
            {"bg_color": "#FFFFFF", "border": 1, "font_name": "Calibri"}
        )
        odd_row = workbook.add_format(
            {"bg_color": "#FBFCFD", "border": 1, "font_name": "Calibri"}
        )

        # Overall total row: light green and bold
        total_label_format = workbook.add_format(
            {"bold": True, "bg_color": "#E6F4EA", "border": 1, "font_name": "Calibri"}
        )
        # Per-column total formats (green background, numeric formats preserved)
        int_total_format = workbook.add_format(
            {
                "num_format": "#,##0",
                "border": 1,
                "align": "right",
                "bg_color": "#57FF87",
                "font_name": "Calibri",
                "bold": True,
            }
        )
        money_total_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "bg_color": "#57FF87",
                "font_name": "Calibri",
                "bold": True,
            }
        )

        # Check user group for cost & margin visibility
        show_cost_margin = self.env.user.has_group("account.group_account_manager")

        # Define headers dynamically based on report type
        first_col_name = "Customer" if self.group_by == "customer" else "Product"
        if self.report_type == "summary":
            headers = [
                first_col_name,
                "Qty Ordered",
                "Qty Delivered",
                "Qty Invoiced",
                "Qty to Invoice",
                "Total",
            ]
            if show_cost_margin:
                headers.extend(["T.Cost", "Margin"])
        else:
            headers = [
                first_col_name,
                "Date",
                "Order#",
                "Product" if self.group_by == "customer" else "Partner",
                "Qty Ordered",
                "Qty Delivered",
                "Qty Invoiced",
                "Qty to Invoice",
                "Total",
            ]
            if show_cost_margin:
                headers.extend(["U.Cost", "Margin"])

        # Write header and freeze it
        worksheet.write_row(0, 0, headers, header_format)
        worksheet.freeze_panes(1, 0)
        # enable autofilter on header row
        worksheet.autofilter(0, 0, 0, len(headers) - 1)

        # Column widths for a clean, modern layout
        worksheet.set_column(0, 0, 36)  # Customer/Product
        worksheet.set_column(1, 4, 14)  # Qty columns
        worksheet.set_column(5, 11, 16)  # Money / cost / margin

        # Initialize overall totals
        total_qty_ordered = 0
        total_qty_delivered = 0
        total_qty_invoiced = 0
        total_qty_to_invoice = 0
        total_amount = 0
        total_cost = 0
        total_margin = 0

        row = 1
        # Last column index (we'll paint totals only up to this column)
        last_col = len(headers) - 1

        # Formats for group header/total (green) and overall total (blue)
        group_label_format = workbook.add_format(
            {"bold": True, "bg_color": "#57FF87", "border": 1, "font_name": "Calibri"}
        )
        int_group_format = workbook.add_format(
            {
                "num_format": "#,##0",
                "border": 1,
                "align": "right",
                "bg_color": "#57FF87",
            }
        )
        money_group_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "bg_color": "#57FF87",
            }
        )

        overall_label_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#3C93EB",
                "border": 1,
                "font_name": "Calibri",
                "font_color": "#FFFFFF",
            }
        )
        int_overall_format = workbook.add_format(
            {
                "num_format": "#,##0",
                "border": 1,
                "align": "right",
                "bg_color": "#3C93EB",
                "font_color": "#FFFFFF",
            }
        )
        money_overall_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "bg_color": "#3C93EB",
                "font_color": "#FFFFFF",
            }
        )
        for group in grouped_lines.values():
            # Dynamically set group name based on `group_by`
            group_name = (
                group.get("partner_name", "")
                if self.group_by == "customer"
                else group.get("product_name", "")
            )

            # Write group name

            # Generate rows based on report type
            # alternate row formats for readability (used per-row in detail loop)

            if self.report_type == "summary":
                # Summary shows one row per group; color the row green up to last column
                worksheet.write(row, 0, group_name, group_label_format)
                # fill blanks across to last_col so bg is applied
                for c in range(1, last_col + 1):
                    worksheet.write_blank(row, c, None, group_label_format)

                # numbers (overwrite blanks with numeric formats)
                if self.group_by == "item" and group.get("lines"):
                    # Display quantity with UoM (assuming same UoM when grouped by item)
                    uom_name = group["lines"][0].get("uom_name", "")
                    quantity_str = f"{group['product_uom_qty']:.2f} ({uom_name})"
                    worksheet.write(row, 1, quantity_str, int_group_format)
                else:
                    # If grouped by partner, UoMs are mixed, so just write the number
                    worksheet.write_number(
                        row, 1, group["product_uom_qty"], int_group_format
                    )
                # --- END QUANTITY MODIFICATION FOR SUMMARY ---

                worksheet.write_number(row, 2, group["qty_delivered"], int_group_format)
                worksheet.write_number(row, 3, group["qty_invoiced"], int_group_format)
                worksheet.write_number(
                    row, 4, group["qty_to_invoice"], int_group_format
                )
                worksheet.write_number(row, 5, group["subtotal"], money_group_format)

                if show_cost_margin:
                    worksheet.write_number(row, 6, group["cost"], money_group_format)
                    worksheet.write_number(row, 7, group["margin"], money_group_format)

                # Update overall totals **only once**
                total_qty_ordered += group["product_uom_qty"]
                total_qty_delivered += group["qty_delivered"]
                total_qty_invoiced += group["qty_invoiced"]
                total_qty_to_invoice += group["qty_to_invoice"]
                total_amount += group["subtotal"]
                if show_cost_margin:
                    total_cost += group["cost"]
                    total_margin += group["margin"]

            else:
                # Group header (customer/product) - color across up to last_col
                worksheet.write(row, 0, group_name, group_label_format)
                for c in range(1, last_col + 1):
                    worksheet.write_blank(row, c, None, group_label_format)
                row += 1
                for line in group["lines"]:
                    col = 0
                    # alternate row format
                    row_fmt = odd_row if row % 2 else even_row
                    # don't repeat the group name for each detail row
                    worksheet.write(row, col, "", row_fmt)
                    col += 1
                    worksheet.write(row, col, line.get("date", ""), date_format)
                    col += 1
                    worksheet.write(row, col, line.get("name", ""), row_fmt)
                    col += 1
                    worksheet.write(
                        row,
                        col,
                        line.get(
                            "product_name"
                            if self.group_by == "customer"
                            else "partner_name",
                            "",
                        ),
                        row_fmt,
                    )
                    col += 1
                    uom_name = line.get("uom_name", "")
                    quantity_str = f"{line.get('product_uom_qty', 0):.2f} ({uom_name})"
                    worksheet.write(row, col, quantity_str, int_format)

                    col += 1
                    worksheet.write_number(
                        row, col, line.get("qty_delivered", 0), int_format
                    )
                    col += 1
                    worksheet.write_number(
                        row, col, line.get("qty_invoiced", 0), int_format
                    )
                    col += 1
                    worksheet.write_number(
                        row, col, line.get("qty_to_invoice", 0), int_format
                    )
                    col += 1
                    worksheet.write_number(
                        row, col, line.get("price_total", 0), money_format
                    )
                    col += 1

                    if show_cost_margin:
                        worksheet.write_number(
                            row, col, line.get("cost", 0), money_format
                        )
                        col += 1
                        worksheet.write_number(
                            row, col, line.get("margin", 0), money_format
                        )
                        col += 1

                    row += 1
                # Group subtotal row (subtotals for this group)
                # Subtotal label on the left side (label, date, order#, partner) use the label format
                worksheet.write(
                    row,
                    0,
                    f"Total {group.get('partner_name', group.get('product_name', ''))}:",
                    total_label_format,
                )
                # Apply the same label format to the left-side cells up to the numeric columns
                numeric_start = 4
                for c in range(1, numeric_start):
                    worksheet.write_blank(row, c, None, total_label_format)

                # Now write numeric totals using the green numeric formats (do NOT override the left label format)
                worksheet.write_number(
                    row, 4, group["product_uom_qty"], int_total_format
                )
                worksheet.write_number(row, 5, group["qty_delivered"], int_total_format)
                worksheet.write_number(row, 6, group["qty_invoiced"], int_total_format)
                worksheet.write_number(
                    row, 7, group["qty_to_invoice"], int_total_format
                )
                worksheet.write_number(row, 8, group["subtotal"], money_total_format)
                if show_cost_margin:
                    worksheet.write_number(row, 9, group["cost"], money_total_format)
                    worksheet.write_number(row, 10, group["margin"], money_total_format)

                row += 1

                # Update overall totals **only once** using pre-calculated group totals
                # (the grouped data already contains totals for the group)
                total_qty_ordered += group.get("product_uom_qty", 0)
                total_qty_delivered += group.get("qty_delivered", 0)
                total_qty_invoiced += group.get("qty_invoiced", 0)
                total_qty_to_invoice += group.get("qty_to_invoice", 0)
                total_amount += group.get("subtotal", 0)
                if show_cost_margin:
                    total_cost += group.get("cost", 0)
                    total_margin += group.get("margin", 0)

            row += 1

        # Write **Overall Totals**
        total_col_start = 1 if self.report_type == "summary" else 4
        # Make the whole totals row light-green and bold
        worksheet.set_row(row, None, total_label_format)
        worksheet.write(row, 0, "Overall Total:", total_label_format)
        # Make the overall totals row blue across the sheet and use blue numeric formats
        for c in range(0, last_col + 1):
            worksheet.write_blank(row, c, None, overall_label_format)
        worksheet.write(row, 0, "Overall Total:", overall_label_format)
        worksheet.write_number(
            row, total_col_start, total_qty_ordered, int_overall_format
        )
        worksheet.write_number(
            row, total_col_start + 1, total_qty_delivered, int_overall_format
        )
        worksheet.write_number(
            row, total_col_start + 2, total_qty_invoiced, int_overall_format
        )
        worksheet.write_number(
            row, total_col_start + 3, total_qty_to_invoice, int_overall_format
        )
        worksheet.write_number(
            row, total_col_start + 4, total_amount, money_overall_format
        )

        if show_cost_margin:
            worksheet.write_number(
                row, total_col_start + 5, total_cost, money_overall_format
            )
            worksheet.write_number(
                row, total_col_start + 6, total_margin, money_overall_format
            )

        # Save and return file
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        filename = "SalesReport"
        self.write({"datas": out, "datas_fname": filename})
        fp.close()
        filename += "%2Exlsx"

        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": "web/content/?model="
            + self._name
            + "&id="
            + str(self.id)
            + "&field=datas&download=true&filename="
            + filename,
        }


class MgsSaleReport(models.AbstractModel):
    _name = "report.mgs_sale.sale_report"
    _description = "Sales Report"

    def _sale_query(self, where_clause="", pos_where=None):
        """Modify to accept pos_where parameter for compatibility with POS module"""
        currency_table = self.env["res.currency"]._get_simple_currency_table(
            self.env.companies
        )
        currency_table = self.env.cr.mogrify(currency_table).decode(
            self.env.cr.connection.encoding
        )

        select_query = f"""
            SELECT 
                MIN(l.id) AS id,
                l.product_id AS product_id,
                t.uom_id AS product_uom_id,
                u2.name->>'en_US' as uom_name,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.product_uom_qty * u.factor / u2.factor) ELSE 0 END AS product_uom_qty,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_delivered * u.factor / u2.factor) ELSE 0 END AS qty_delivered,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_invoiced * u.factor / u2.factor) ELSE 0 END AS qty_invoiced,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_to_invoice * u.factor / u2.factor) ELSE 0 END AS qty_to_invoice,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total
                    / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                    ) ELSE 0
                END AS price_total,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal
                    / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                    ) ELSE 0
                END AS price_subtotal,
                COUNT(*) AS nbr,
                s.name AS name,
                s.date_order AS date,
                s.state AS state,
                s.partner_id AS partner_id,
                s.user_id AS user_id,
                s.company_id AS company_id,
                t.categ_id AS categ_id,
                s.pricelist_id AS pricelist_id,
                s.team_id AS team_id,
                p.product_tmpl_id,
                partner.commercial_partner_id AS commercial_partner_id,
                {self.env.company.currency_id.id} AS currency_id,
                -- Your additional columns
                partner.name AS partner_name,
                t.name ->>'en_US' AS product_name,
                COALESCE(
                    SUM(
                        (l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END)
                        - (l.margin / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END)
                    ), 0
                ) AS cost,
                SUM(COALESCE(l.margin / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END, 0)) AS margin,
                s.client_order_ref
        """

        from_query = f"""
            FROM 
                sale_order_line l
                LEFT JOIN sale_order s ON s.id = l.order_id
                JOIN res_partner partner ON s.partner_id = partner.id
                LEFT JOIN product_product p ON l.product_id = p.id
                LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN product_category pc ON t.categ_id = pc.id
                LEFT JOIN product_category parent_pc ON pc.parent_id = parent_pc.id
                LEFT JOIN uom_uom u ON u.id = l.product_uom_id
                LEFT JOIN uom_uom u2 ON u2.id = t.uom_id
                LEFT JOIN sale_order_tag_rel tag_rel ON tag_rel.order_id = s.id
                LEFT JOIN crm_tag tag ON tag.id = tag_rel.tag_id
                JOIN {currency_table} ON account_currency_table.company_id = s.company_id
        """

        where_query = "WHERE l.display_type IS NULL AND s.state = 'sale'"
        if where_clause:
            where_query += where_clause

        group_by_query = """
            GROUP BY 
                l.product_id,
                l.order_id,
                t.uom_id,
                uom_name,
                t.categ_id,
                s.name,
                s.date_order,
                s.partner_id,
                s.user_id,
                s.state,
                s.company_id,
                s.pricelist_id,
                s.team_id,
                p.product_tmpl_id,
                partner.commercial_partner_id,
                partner.name,
                t.name,
                pc.id,
                parent_pc.id,
                parent_pc.name,
                s.client_order_ref
        """
        return select_query + from_query + where_query + group_by_query

    def _lines(self, data):
        """Build dynamic SQL based on wizard filters."""

        # Build sale filters
        sale_where = ""
        sale_params = []
        if data.get("date_from"):
            date_from = str(data["date_from"]) + " 00:00:00"
            sale_where += " AND s.date_order >= %s"
            sale_params.append(date_from)
        if data.get("date_to"):
            date_to = str(data["date_to"]) + " 23:59:59"
            sale_where += " AND s.date_order <= %s"
            sale_params.append(date_to)
        if data.get("user_id"):
            sale_where += " AND s.user_id = %s"
            sale_params.append(data["user_id"][0])
        if data.get("team_id"):
            sale_where += " AND s.team_id = %s"
            sale_params.append(data["team_id"][0])
        if data.get("pricelist_id"):
            sale_where += " AND s.pricelist_id = %s"
            sale_params.append(data["pricelist_id"][0])
        if data.get("company_id"):
            sale_where += " AND s.company_id = %s"
            sale_params.append(data["company_id"][0])
        if data.get("currency_id"):
            sale_where += " AND s.currency_id = %s"
            sale_params.append(data["currency_id"][0])
        if data.get("sales_tag_ids"):
            tag_ids = tuple(data.get("sales_tag_ids"))
            if len(tag_ids) == 1:
                sale_where += " AND tag.id = %s"
                sale_params.append(tag_ids[0])
            else:
                sale_where += " AND tag.id IN %s"
                sale_params.append(tag_ids)
        if data.get("partner_id"):
            sale_where += " AND s.partner_id = %s"
            sale_params.append(data["partner_id"][0])
        if data.get("product_id"):
            sale_where += " AND l.product_id = %s"
            sale_params.append(data["product_id"][0])
        if data.get("categ_id"):
            sale_where += " AND t.categ_id = %s"
            sale_params.append(data["categ_id"][0])
        if data.get("parent_categ_id"):
            sale_where += " AND parent_pc.id = %s"
            sale_params.append(data["parent_categ_id"][0])

        # Check if POS module is installed
        pos_module_installed = self.env["ir.module.module"].search(
            [
                (
                    "name",
                    "=",
                    "mgs_pos",
                ),  # Replace with your actual POS module name
                ("state", "=", "installed"),
            ],
            limit=1,
        )

        if pos_module_installed:
            # Build POS filters only if POS module is installed
            pos_where = ""
            pos_params = []
            if data.get("date_from"):
                date_from = str(data["date_from"]) + " 00:00:00"
                pos_where += " AND s.date_order >= %s"
                pos_params.append(date_from)
            if data.get("date_to"):
                date_to = str(data["date_to"]) + " 23:59:59"
                pos_where += " AND s.date_order <= %s"
                pos_params.append(date_to)
            if data.get("company_id"):
                pos_where += " AND s.company_id = %s"
                pos_params.append(data["company_id"][0])
            if data.get("categ_id"):
                pos_where += " AND pt.categ_id = %s"
                pos_params.append(data["categ_id"][0])
            if data.get("parent_categ_id"):
                pos_where += " AND parent_pc.id = %s"
                pos_params.append(data["parent_categ_id"][0])
            if data.get("pricelist_id"):
                pos_where += " AND s.pricelist_id = %s"
                pos_params.append(data["pricelist_id"][0])
            if data.get("partner_id"):
                pos_where += " AND s.partner_id = %s"
                pos_params.append(data["partner_id"][0])
            if data.get("product_id"):
                pos_where += " AND l.product_id = %s"
                pos_params.append(data["product_id"][0])
            if data.get("user_id"):
                pos_where += " AND s.user_id = %s"
                pos_params.append(data["user_id"][0])

            # Generate the final query with POS parameters
            query = self._sale_query(sale_where, pos_where=pos_where)
            final_params = sale_params + pos_params

            # Debug logging for POS
            _logger.info("POS WHERE clause: %s", pos_where)
            _logger.info("POS params count: %s", len(pos_params))
            _logger.info("POS params: %s", pos_params)
        else:
            # Generate query without POS parameters
            query = self._sale_query(sale_where)
            final_params = sale_params

        # Debug logging for sale
        _logger.info("Sale WHERE clause: %s", sale_where)
        _logger.info("Sale params count: %s", len(sale_params))
        _logger.info("Sale params: %s", sale_params)
        _logger.info("Final Query: %s", query)
        _logger.info("Final params count: %s", len(final_params))

        # Execute with appropriate parameters
        self.env.cr.execute(query, tuple(final_params))
        results = self.env.cr.dictfetchall()
        return results

    def _grouped_lines(self, data):
        """Group lines based on group_by (customer or item)"""

        lines = self._lines(data)
        grouped = {}

        if data.get("group_by") == "customer":
            for line in lines:
                partner_id = line["partner_id"]
                grouped.setdefault(
                    partner_id,
                    {
                        "partner_name": line["partner_name"],
                        "lines": [],
                        "product_uom_qty": 0.0,
                        "qty_delivered": 0.0,
                        "qty_invoiced": 0.0,
                        "qty_to_invoice": 0.0,
                        "subtotal": 0.0,
                        "cost": 0.0,
                        "margin": 0.0,
                    },
                )
                grouped[partner_id]["lines"].append(line)
                grouped[partner_id]["product_uom_qty"] += line["product_uom_qty"]
                grouped[partner_id]["qty_delivered"] += line["qty_delivered"]
                grouped[partner_id]["qty_invoiced"] += line["qty_invoiced"]
                grouped[partner_id]["qty_to_invoice"] += line["qty_to_invoice"]
                grouped[partner_id]["subtotal"] += line["price_total"]
                grouped[partner_id]["cost"] += line["cost"]
                grouped[partner_id]["margin"] += line["margin"]

        elif data.get("group_by") == "item":
            for line in lines:
                product_id = line["product_id"]
                grouped.setdefault(
                    product_id,
                    {
                        "product_name": line["product_name"],
                        "lines": [],
                        "product_uom_qty": 0.0,
                        "qty_delivered": 0.0,
                        "qty_invoiced": 0.0,
                        "qty_to_invoice": 0.0,
                        "subtotal": 0.0,
                        "cost": 0.0,
                        "margin": 0.0,
                    },
                )
                grouped[product_id]["lines"].append(line)
                grouped[product_id]["product_uom_qty"] += line["product_uom_qty"]
                grouped[product_id]["qty_delivered"] += line["qty_delivered"]
                grouped[product_id]["qty_invoiced"] += line["qty_invoiced"]
                grouped[product_id]["qty_to_invoice"] += line["qty_to_invoice"]
                grouped[product_id]["subtotal"] += line["price_total"]
                grouped[product_id]["cost"] += line["cost"]
                grouped[product_id]["margin"] += line["margin"]
        _logger.info(grouped)

        return grouped

    @api.model
    def _get_report_values(self, docids, data=None):
        doc_model = self.env.context.get("active_model")
        doc_ids = self.env.context.get("active_ids")
        docs = self.env[doc_model].browse(doc_ids)

        report_engine = self.env["report.mgs_sale.sale_report"]

        grouped_lines = report_engine._grouped_lines(data["form"])  # type: ignore

        return {
            "doc_ids": docids,
            "doc_model": doc_model,
            "docs": docs,
            "date_from": data["form"]["date_from"],  # type: ignore
            "date_to": data["form"]["date_to"],  # type: ignore
            "group_by": data["form"]["group_by"],  # type: ignore
            "grouped_lines": grouped_lines,  # type: ignore
            "partner_id": data["form"].get("partner_id"),  # type: ignore
            "product_id": data["form"].get("product_id"),  # type: ignore
            "parent_categ_id": data["form"].get("parent_categ_id"),  # type: ignore
            "categ_id": data["form"].get("categ_id"),  # type: ignore
            "user_id": data["form"].get("user_id"),  # type: ignore
            "team_id": data["form"].get("team_id"),  # type: ignore
            "report_type": data["form"].get("report_type"),  # type: ignore
            "pricelist_id": data["form"].get("pricelist_id"),  # type: ignore
            "sales_tag_ids": data["form"].get("sales_tag_ids"),  # type: ignore
            "company_id": self.env["res.company"].browse(data["form"]["company_id"][0])  # type: ignore
            if data["form"].get("company_id")  # type: ignore
            else self.env.company,  # type: ignore
            "currency_id": data["form"].get("currency_id"),  # type: ignore
        }
