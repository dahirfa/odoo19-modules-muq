import xlsxwriter  # type: ignore
from io import BytesIO
import base64
from odoo import models, fields, api  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class MgsPurchaseReportWizard(models.TransientModel):
    _name = "mgs_purchase.report_wizard"
    _description = "Purchase Report Wizard"

    # Date Range
    date_from = fields.Date(
        string="Date From", default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(string="Date To", default=lambda self: fields.Date.today())

    # Purchase Filters
    user_id = fields.Many2one("res.users", string="Buyer")
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

    # Vendor & Product Filters
    partner_id = fields.Many2one("res.partner", string="Vendor")
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
        [("vendor", "Purchases by Vendor"), ("item", "Purchases by Item")],
        string="Group By",
        default="vendor",
        required=True,
    )

    datas = fields.Binary("File", readonly=True)
    datas_fname = fields.Char("Filename", readonly=True)

    def check_report(self):
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": self.read()[0],
        }
        return self.env.ref("mgs_purchase.action_report_mgs_purchase").report_action(
            self, data=data
        )

    def export_to_excel(self):
        """Generates an Excel file supporting both Summary and Detail formats"""

        # Fetch data based on filters
        purchase_report_obj = self.env["report.mgs_purchase.purchase_report"]
        data = self.read()[0]
        grouped_lines = purchase_report_obj._grouped_lines(data)

        # Prepare Excel Workbook
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet("Purchase Report")

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

        # Check user group for cost visibility
        show_cost = self.env.user.has_group("account.group_account_manager")

        # Determine if we should show unit cost column
        show_unit_cost = show_cost and not (
            self.report_type == "summary" and self.group_by == "vendor"
        )

        # Define headers dynamically based on report type and new column order
        first_col_name = "Vendor" if self.group_by == "vendor" else "Product"
        if self.report_type == "summary":
            headers = [
                first_col_name,
                "Qty Ordered",
                "Qty Received",
                "Qty Billed",
            ]
            if show_unit_cost:
                headers.append("U.Cost")
            if show_cost:
                headers.append("Tax")
            headers.append("Amount")
        else:
            headers = [
                first_col_name,
                "Date",
                "Order#",
                "Product" if self.group_by == "vendor" else "Vendor",
                "Qty Ordered",
                "Qty Received",
                "Qty Billed",
            ]
            if show_unit_cost:
                headers.append("U.Cost")
            if show_cost:
                headers.append("Tax")
            headers.append("Amount")

        # Write header and freeze it
        worksheet.write_row(0, 0, headers, header_format)
        worksheet.freeze_panes(1, 0)
        # enable autofilter on header row
        worksheet.autofilter(0, 0, 0, len(headers) - 1)

        # Column widths for a clean, modern layout
        worksheet.set_column(0, 0, 36)  # Vendor/Product
        # Qty columns: Qty Ordered, Qty Received, Qty Billed
        worksheet.set_column(1, 3, 14)
        # Money / cost / tax columns
        worksheet.set_column(4, len(headers) - 1, 16)

        # Initialize overall totals
        total_qty_ordered = 0
        total_qty_received = 0
        total_qty_billed = 0
        total_amount = 0
        total_tax = 0

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
                if self.group_by == "vendor"
                else group.get("product_name", "")
            )

            if self.report_type == "summary":
                # Summary shows one row per group; color the row green up to last column
                worksheet.write(row, 0, group_name, group_label_format)
                # fill blanks across to last_col so bg is applied
                for c in range(1, last_col + 1):
                    worksheet.write_blank(row, c, None, group_label_format)

                # Write quantities
                worksheet.write_number(
                    row, 1, group["product_uom_qty"], int_group_format
                )
                worksheet.write_number(row, 2, group["qty_received"], int_group_format)
                worksheet.write_number(row, 3, group["qty_billed"], int_group_format)

                # Adjusted Column Indices based on visible columns
                current_col = 4

                # Unit Cost column (only if shown)
                if show_unit_cost:
                    worksheet.write_number(
                        row, current_col, group.get("unit_cost", 0), money_group_format
                    )
                    current_col += 1

                # Tax column (only if show_cost)
                if show_cost:
                    worksheet.write_number(
                        row, current_col, group.get("tax", 0), money_group_format
                    )
                    current_col += 1

                # Amount is the last column
                worksheet.write_number(
                    row, last_col, group["subtotal"], money_group_format
                )

                # Update overall totals
                total_qty_ordered += group["product_uom_qty"]
                total_qty_received += group["qty_received"]
                total_qty_billed += group["qty_billed"]
                total_amount += group["subtotal"]
                total_tax += group.get("tax", 0)

            else:
                # Detail report - Group header
                worksheet.write(row, 0, group_name, group_label_format)
                for c in range(1, last_col + 1):
                    worksheet.write_blank(row, c, None, group_label_format)
                row += 1

                # Detail rows
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
                            if self.group_by == "vendor"
                            else "partner_name",
                            "",
                        ),
                        row_fmt,
                    )
                    col += 1
                    worksheet.write_number(
                        row, col, line.get("product_uom_qty", 0), int_format
                    )
                    col += 1
                    worksheet.write_number(
                        row, col, line.get("qty_received", 0), int_format
                    )
                    col += 1
                    worksheet.write_number(
                        row, col, line.get("qty_billed", 0), int_format
                    )
                    col += 1

                    # Unit Cost column (only if shown)
                    if show_unit_cost:
                        worksheet.write_number(
                            row, col, line.get("unit_cost", 0), money_format
                        )
                        col += 1

                    # Tax column (only if show_cost)
                    if show_cost:
                        worksheet.write_number(
                            row, col, line.get("tax", 0), money_format
                        )
                        col += 1

                    # Amount column
                    worksheet.write_number(
                        row, col, line.get("price_total", 0), money_format
                    )
                    col += 1

                    row += 1

                # Group subtotal row
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

                # Write subtotal row quantities
                worksheet.write_number(
                    row, 4, group["product_uom_qty"], int_total_format
                )
                worksheet.write_number(row, 5, group["qty_received"], int_total_format)
                worksheet.write_number(row, 6, group["qty_billed"], int_total_format)

                current_col = 7

                # Unit Cost column (only if shown)
                if show_unit_cost:
                    worksheet.write_number(
                        row, current_col, group.get("unit_cost", 0), money_total_format
                    )
                    current_col += 1

                # Tax column (only if show_cost)
                if show_cost:
                    worksheet.write_number(
                        row, current_col, group.get("tax", 0), money_total_format
                    )
                    current_col += 1

                # Amount column
                worksheet.write_number(
                    row, current_col, group["subtotal"], money_total_format
                )

                row += 1

                # Update overall totals
                total_qty_ordered += group.get("product_uom_qty", 0)
                total_qty_received += group.get("qty_received", 0)
                total_qty_billed += group.get("qty_billed", 0)
                total_amount += group.get("subtotal", 0)
                total_tax += group.get("tax", 0)

            row += 1

        # Write **Overall Totals**
        total_col_start = 1 if self.report_type == "summary" else 4

        # Make the overall totals row blue across the sheet
        for c in range(0, last_col + 1):
            worksheet.write_blank(row, c, None, overall_label_format)
        worksheet.write(row, 0, "Overall Total:", overall_label_format)

        current_col = total_col_start

        # QTY columns
        worksheet.write_number(row, current_col, total_qty_ordered, int_overall_format)
        current_col += 1
        worksheet.write_number(row, current_col, total_qty_received, int_overall_format)
        current_col += 1
        worksheet.write_number(row, current_col, total_qty_billed, int_overall_format)
        current_col += 1

        # Skip unit cost column if shown (we don't total unit costs)
        if show_unit_cost:
            current_col += 1

        # Tax column (only if show_cost)
        if show_cost:
            worksheet.write_number(row, current_col, total_tax, money_overall_format)
            current_col += 1

        # Amount column
        worksheet.write_number(row, current_col, total_amount, money_overall_format)

        # Save and return file
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        filename = "PurchaseReport"
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


class MgsPurchaseReport(models.AbstractModel):
    _name = "report.mgs_purchase.purchase_report"
    _description = "Purchase Report"

    def _purchase_query(self, where_clause=""):
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
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.product_qty * u.factor / u2.factor) ELSE 0 END AS product_uom_qty,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_received * u.factor / u2.factor) ELSE 0 END AS qty_received,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.qty_invoiced * u.factor / u2.factor) ELSE 0 END AS qty_billed,
            -- qty_to_be_billed removed per request
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_total
                    / CASE COALESCE(po.currency_rate, 0) WHEN 0 THEN 1.0 ELSE po.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                    ) ELSE 0
                END AS price_total,
                CASE WHEN l.product_id IS NOT NULL THEN SUM(l.price_subtotal
                    / CASE COALESCE(po.currency_rate, 0) WHEN 0 THEN 1.0 ELSE po.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                    ) ELSE 0
                END AS price_subtotal,
                COUNT(*) AS nbr,
                po.name AS name,
                po.date_order AS date,
                po.state AS state,
                po.partner_id AS partner_id,
                po.user_id AS user_id,
                po.company_id AS company_id,
                t.categ_id AS categ_id,
                p.product_tmpl_id,
                partner.commercial_partner_id AS commercial_partner_id,
                {self.env.company.currency_id.id} AS currency_id,
                -- Your additional columns
                partner.name AS partner_name,
                t.name ->>'en_US' AS product_name,
                -- Use unit price as unit_cost (single value per line aggregated by MIN for grouping)
                MIN(l.price_unit) AS unit_cost,
                -- Tax: sum of (price_total - price_subtotal) converted by currency rates
                SUM(
                    COALESCE(l.price_total - l.price_subtotal, 0)
                    / CASE COALESCE(po.currency_rate, 0) WHEN 0 THEN 1.0 ELSE po.currency_rate END
                    * CASE COALESCE(account_currency_table.rate, 0) WHEN 0 THEN 1.0 ELSE account_currency_table.rate END
                ) AS tax,
                po.partner_ref
        """

        from_query = f"""
            FROM 
                purchase_order_line l
                LEFT JOIN purchase_order po ON po.id = l.order_id
                JOIN res_partner partner ON po.partner_id = partner.id
                LEFT JOIN product_product p ON l.product_id = p.id
                LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN product_category pc ON t.categ_id = pc.id
                LEFT JOIN product_category parent_pc ON pc.parent_id = parent_pc.id
                LEFT JOIN uom_uom u ON u.id = l.product_uom_id
                LEFT JOIN uom_uom u2 ON u2.id = t.uom_id
                JOIN {currency_table} ON account_currency_table.company_id = po.company_id
        """

        where_query = (
            "WHERE l.display_type IS NULL AND po.state IN ('purchase', 'done')"
        )
        if where_clause:
            where_query += where_clause

        group_by_query = """
            GROUP BY 
                l.product_id,
                l.order_id,
                t.uom_id,
                t.categ_id,
                po.name,
                po.date_order,
                po.partner_id,
                po.user_id,
                po.state,
                po.company_id,
                p.product_tmpl_id,
                partner.commercial_partner_id,
                partner.name,
                t.name,
                pc.id,
                parent_pc.id,
                parent_pc.name,
                po.partner_ref
                ORDER BY date DESC
        """

        return select_query + from_query + where_query + group_by_query

    def _lines(self, data):
        """Build dynamic SQL based on wizard filters"""

        where_clause = ""
        params = []

        if data.get("date_from"):
            date_from = str(data["date_from"]) + " 00:00:00"
            where_clause += " AND po.date_order >= %s"
            params.append(date_from)
        if data.get("date_to"):
            date_to = str(data["date_to"]) + " 23:59:59"
            where_clause += " AND po.date_order <= %s"
            params.append(date_to)
        if data.get("user_id"):
            where_clause += " AND po.user_id = %s"
            params.append(data["user_id"][0])
        if data.get("company_id"):
            where_clause += " AND po.company_id = %s"
            params.append(data["company_id"][0])
        if data.get("currency_id"):
            where_clause += " AND po.currency_id = %s"
            params.append(data["currency_id"][0])
        if data.get("partner_id"):
            where_clause += " AND po.partner_id = %s"
            params.append(data["partner_id"][0])
        if data.get("product_id"):
            where_clause += " AND l.product_id = %s"
            params.append(data["product_id"][0])
        if data.get("categ_id"):
            where_clause += " AND t.categ_id = %s"
            params.append(data["categ_id"][0])
        if data.get("parent_categ_id"):
            where_clause += " AND parent_pc.id = %s"
            params.append(data["parent_categ_id"][0])

        query = self._purchase_query(where_clause)

        # Debug logging
        _logger.info("Purchase WHERE clause: %s", where_clause)
        _logger.info("Purchase params count: %s", len(params))
        _logger.info("Purchase params: %s", params)
        _logger.info("Final Query: %s", query)

        self.env.cr.execute(query, tuple(params))
        results = self.env.cr.dictfetchall()
        return results

    def _grouped_lines(self, data):
        """Group lines based on group_by (vendor or item)"""

        lines = self._lines(data)
        grouped = {}

        if data.get("group_by") == "vendor":
            for line in lines:
                partner_id = line["partner_id"]
                grouped.setdefault(
                    partner_id,
                    {
                        "partner_name": line["partner_name"],
                        "lines": [],
                        "product_uom_qty": 0.0,
                        "qty_received": 0.0,
                        "qty_billed": 0.0,
                        "subtotal": 0.0,
                        "unit_cost": 0.0,
                        "tax": 0.0,
                    },
                )
                grouped[partner_id]["lines"].append(line)
                grouped[partner_id]["product_uom_qty"] += line["product_uom_qty"]
                grouped[partner_id]["qty_received"] += line["qty_received"]
                grouped[partner_id]["qty_billed"] += line["qty_billed"]
                grouped[partner_id]["subtotal"] += line["price_total"]
                # keep a representative unit_cost for the group (do not sum)
                grouped[partner_id]["unit_cost"] = grouped[partner_id].get(
                    "unit_cost"
                ) or line.get("unit_cost", 0)
                grouped[partner_id]["tax"] += line.get("tax", 0)

        elif data.get("group_by") == "item":
            for line in lines:
                product_id = line["product_id"]
                grouped.setdefault(
                    product_id,
                    {
                        "product_name": line["product_name"],
                        "lines": [],
                        "product_uom_qty": 0.0,
                        "qty_received": 0.0,
                        "qty_billed": 0.0,
                        "subtotal": 0.0,
                        "unit_cost": 0.0,
                        "tax": 0.0,
                    },
                )
                grouped[product_id]["lines"].append(line)
                grouped[product_id]["product_uom_qty"] += line["product_uom_qty"]
                grouped[product_id]["qty_received"] += line["qty_received"]
                grouped[product_id]["qty_billed"] += line["qty_billed"]
                grouped[product_id]["subtotal"] += line["price_total"]
                # representative unit cost for the product group
                grouped[product_id]["unit_cost"] = grouped[product_id].get(
                    "unit_cost"
                ) or line.get("unit_cost", 0)
                grouped[product_id]["tax"] += line.get("tax", 0)

        _logger.info(grouped)
        return grouped

    @api.model
    def _get_report_values(self, docids, data=None):
        doc_model = self.env.context.get("active_model")
        doc_ids = self.env.context.get("active_ids")
        docs = (
            self.env[doc_model].browse(doc_ids)
            if doc_model and doc_ids
            else self.env["mgs_purchase.report_wizard"].browse(docids)
        )

        # Get the wizard data from the provided `data` (report_action passes it as `form`)
        wizard_data = data.get("form", {}) if data else {}

        # Get the report engine and grouped lines
        report_engine = self.env["report.mgs_purchase.purchase_report"]
        grouped_lines = report_engine._grouped_lines(wizard_data)

        # Resolve company to a company record

        company_id = wizard_data.get("company_id")
        company = (
            self.env["res.company"].browse(company_id[0])
            if company_id and company_id[0]
            else self.env.company
        )

        return {
            "doc_ids": docids,
            "doc_model": doc_model or "mgs_purchase.report_wizard",
            "docs": docs,
            "date_from": wizard_data.get("date_from"),
            "date_to": wizard_data.get("date_to"),
            "group_by": wizard_data.get("group_by", "vendor"),
            "grouped_lines": grouped_lines,
            "partner_id": wizard_data.get("partner_id"),
            "product_id": wizard_data.get("product_id"),
            "parent_categ_id": wizard_data.get("parent_categ_id"),
            "categ_id": wizard_data.get("categ_id"),
            "user_id": wizard_data.get("user_id"),
            "company_id": company,
            "currency_id": wizard_data.get("currency_id"),
            "report_type": wizard_data.get("report_type", "summary"),
        }
