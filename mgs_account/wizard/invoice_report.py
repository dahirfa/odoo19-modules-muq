import xlsxwriter  # type: ignore
from io import BytesIO
import base64
from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class MgsInvoiceReportWiz(models.TransientModel):
    _name = "mgs_account.invoice_report"
    _description = "MGS Invoice Report Wizard"

    # Date Range
    date_from = fields.Date(
        string="Date From", default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(string="Date To", default=lambda self: fields.Date.today())

    # Invoice/Bill Type
    invoice_or_bill = fields.Selection(
        [("invoice", "Invoices Report"), ("bill", "Vendor Bill Report")],
        string="Invoices/Bills",
        default="invoice",
        required=True,
    )

    # Sales Filters
    user_id = fields.Many2one("res.users", string="Salesperson")
    team_id = fields.Many2one("crm.team", string="Sales Team")

    # Company & Currency
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    # Partner & Product Filters
    partner_id = fields.Many2one("res.partner", string="Partner")
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
        [("partner", "Invoices by Partner"), ("item", "Invoices by Item")],
        string="Group By",
        default="partner",
        required=True,
    )

    datas = fields.Binary("File", readonly=True)
    datas_fname = fields.Char("Filename", readonly=True)

    # Computed field for allowed companies
    allowed_company_ids = fields.Many2many(
        "res.company", compute="_compute_allowed_companies"
    )

    @api.depends_context("allowed_company_ids")
    def _compute_allowed_companies(self):
        for record in self:
            record.allowed_company_ids = self.env.companies

    @api.constrains("date_from", "date_to")
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError("From Date should be less than To Date.")

    def check_report(self):
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": self.read()[0],
        }
        return self.env.ref("mgs_account.action_report_mgs_invoice").report_action(
            self, data=data
        )

    def export_to_excel(self):
        """Generates an Excel file for Invoice Report"""
        invoice_report_obj = self.env["report.mgs_account.invoice_report"]
        data = self.read()[0]
        grouped_lines = invoice_report_obj._grouped_lines(data)

        # Prepare Excel Workbook
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet("Invoice Report")

        # --- Styling ---
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

        date_format = workbook.add_format(
            {
                "num_format": "yyyy-mm-dd",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        int_format = workbook.add_format(
            {
                "num_format": "#,##0",
                "border": 1,
                "align": "right",
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        money_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        # Row striping
        even_row = workbook.add_format(
            {
                "bg_color": "#FFFFFF",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 10,
            }
        )
        odd_row = workbook.add_format(
            {
                "bg_color": "#FBFCFD",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        # Total formats
        total_label_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#E6F4EA",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        int_total_format = workbook.add_format(
            {
                "num_format": "#,##0",
                "border": 1,
                "align": "right",
                "bg_color": "#57FF87",
                "font_name": "Calibri",
                "bold": True,
                "font_size": 10,
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
                "font_size": 10,
            }
        )

        # Group formats
        group_label_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#D1E7DD",
                "border": 1,
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        # Overall total formats
        overall_label_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#3C93EB",
                "border": 1,
                "font_name": "Calibri",
                "font_color": "#FFFFFF",
                "font_size": 11,
            }
        )

        int_overall_format = workbook.add_format(
            {
                "num_format": "#,##0",
                "border": 1,
                "align": "right",
                "bg_color": "#3C93EB",
                "font_color": "#FFFFFF",
                "bold": True,
                "font_size": 11,
            }
        )

        money_overall_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "bg_color": "#3C93EB",
                "font_color": "#FFFFFF",
                "bold": True,
                "font_size": 11,
            }
        )

        # Define headers based on report type and grouping

        first_col_name = "Partner" if self.group_by == "partner" else "Product"

        if self.report_type == "summary":
            headers = [
                first_col_name,
                "Quantity",
                "Total Without Tax",
                "Tax Amount",
                "Total Amount",
            ]
            col_count = 5
        else:
            headers = [
                first_col_name,
                "Date",
                "Invoice Ref",
                "Quantity",
                "Total Without Tax",
                "Tax Amount",
                "Total Amount",
            ]
            col_count = 7

        # Write header
        worksheet.write_row(0, 0, headers, header_format)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, 0, col_count - 1)

        # Column widths
        worksheet.set_column(0, 0, 36)  # Partner/Product column
        if self.report_type == "detail":
            worksheet.set_column(1, 1, 12)  # Date
            worksheet.set_column(2, 2, 20)  # Invoice Ref
            worksheet.set_column(3, 6, 15)  # Quantity, Subtotal, Tax, Total
        else:
            worksheet.set_column(1, 4, 15)  # Quantity, Subtotal, Tax, Total for summary

        # Initialize totals
        total_quantity = 0
        total_subtotal = 0
        total_tax = 0
        total_amount = 0
        row = 1

        for group in grouped_lines.values():
            group_name = (
                group.get("partner_name", "")
                if self.group_by == "partner"
                else group.get("product_name", "")
            )

            if self.report_type == "summary":
                # SUMMARY REPORT - Simple one row per group
                row_fmt = odd_row if row % 2 else even_row

                worksheet.write(row, 0, group_name, row_fmt)
                worksheet.write_number(row, 1, group["quantity"], int_format)
                worksheet.write_number(
                    row, 2, group.get("price_subtotal", 0), money_format
                )
                worksheet.write_number(row, 3, group.get("tax_amount", 0), money_format)
                worksheet.write_number(row, 4, group["price_total"], money_format)

                total_quantity += group["quantity"]
                total_subtotal += group.get("price_subtotal", 0)
                total_tax += group.get("tax_amount", 0)
                total_amount += group["price_total"]
                row += 1

            else:
                # DETAIL REPORT - Group with multiple lines
                # Write group header
                worksheet.write(row, 0, group_name, group_label_format)
                # Merge remaining cells for group header
                for col in range(1, col_count):
                    worksheet.write_blank(row, col, None, group_label_format)
                row += 1

                # Write detail lines
                for line in group["lines"]:
                    row_fmt = odd_row if row % 2 else even_row

                    # Leave first column empty (indented under group)
                    worksheet.write_blank(row, 0, None, row_fmt)
                    worksheet.write(row, 1, line.get("invoice_date", ""), date_format)
                    worksheet.write(row, 2, line.get("invoice_number", ""), row_fmt)
                    worksheet.write_number(row, 3, line.get("quantity", 0), int_format)
                    worksheet.write_number(
                        row, 4, line.get("price_subtotal", 0), money_format
                    )
                    worksheet.write_number(
                        row, 5, line.get("tax_amount", 0), money_format
                    )
                    worksheet.write_number(
                        row, 6, line.get("price_total", 0), money_format
                    )
                    row += 1

                # Write group total
                total_label = f"Total {group_name}:"
                worksheet.write(row, 0, total_label, total_label_format)
                for col in range(1, 3):  # Blank cells for Date and Invoice Ref
                    worksheet.write_blank(row, col, None, total_label_format)
                worksheet.write_number(row, 3, group["quantity"], int_total_format)
                worksheet.write_number(
                    row, 4, group.get("price_subtotal", 0), money_total_format
                )
                worksheet.write_number(
                    row, 5, group.get("tax_amount", 0), money_total_format
                )
                worksheet.write_number(row, 6, group["price_total"], money_total_format)

                total_quantity += group["quantity"]
                total_subtotal += group.get("price_subtotal", 0)
                total_tax += group.get("tax_amount", 0)
                total_amount += group["price_total"]
                row += 1

                # Add empty row between groups
                row += 1

        # Write overall totals
        if self.report_type == "summary":
            worksheet.write(row, 0, "Overall Total:", overall_label_format)
            worksheet.write_number(row, 1, total_quantity, int_overall_format)
            worksheet.write_number(row, 2, total_subtotal, money_overall_format)
            worksheet.write_number(row, 3, total_tax, money_overall_format)
            worksheet.write_number(row, 4, total_amount, money_overall_format)
        else:
            # For detail report, overall total should span columns
            worksheet.write(row, 0, "Overall Total:", overall_label_format)
            worksheet.write_blank(row, 1, None, overall_label_format)
            worksheet.write_blank(row, 2, None, overall_label_format)
            worksheet.write_number(row, 3, total_quantity, int_overall_format)
            worksheet.write_number(row, 4, total_subtotal, money_overall_format)
            worksheet.write_number(row, 5, total_tax, money_overall_format)
            worksheet.write_number(row, 6, total_amount, money_overall_format)

        # Save and return file
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        report_type = "Invoice" if self.invoice_or_bill == "invoice" else "Bill"
        filename = f"{report_type}Report"
        self.write({"datas": out, "datas_fname": filename})
        fp.close()

        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": "web/content/?model="
            + self._name
            + "&id="
            + str(self.id)
            + "&field=datas&download=true&filename="
            + filename
            + ".xlsx",
        }


class MgsInvoiceReport(models.AbstractModel):
    _name = "report.mgs_account.invoice_report"
    _description = "MGS Invoice Report"

    def _invoice_query(self, where_clause=""):
        query = """
            SELECT
                line.move_id,
                move.name as invoice_number,
                move.invoice_date,
                move.partner_id,
                line.product_id,
                SUM(line.quantity *
                    COALESCE(uom_line.factor, 1) / NULLIF(COALESCE(uom_template.factor, 1), 0.0) *
                    CASE
                        WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1
                        ELSE 1
                    END ) AS quantity,
                sum(line.price_subtotal *
                    CASE
                        WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1
                        ELSE 1
                    END ) AS price_subtotal,
                SUM(line.price_total *
                    CASE
                        WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1
                        ELSE 1
                    END ) AS price_total,
                SUM((line.price_total - line.price_subtotal) *
                    CASE
                        WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1
                        ELSE 1
                    END) AS tax_amount,
                partner.name as partner_name,
                template.name->>'en_US' as product_name
            FROM account_move_line line
            LEFT JOIN account_move move ON move.id = line.move_id
            LEFT JOIN res_partner partner ON partner.id = move.partner_id
            LEFT JOIN product_product product ON product.id = line.product_id
            LEFT JOIN product_template template ON template.id = product.product_tmpl_id
            LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
            LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
            LEFT JOIN product_category category ON category.id = template.categ_id
            WHERE move.move_type IN %s
                AND move.state = 'posted'
                AND line.product_id IS NOT NULL
                {where_clause}
            GROUP BY 
                move.partner_id, line.product_id, partner.name, line.move_id, move.invoice_date,
                move.name, template.name->>'en_US'
            ORDER BY move.invoice_date DESC
        """.format(where_clause=where_clause)
        return query

    def _lines(self, data):
        """Build dynamic SQL based on wizard filters"""
        where_clause = ""
        params = []

        # Determine move types
        move_types = (
            ("out_invoice", "out_refund")
            if data.get("invoice_or_bill") == "invoice"
            else ("in_invoice", "in_refund")
        )
        params.append(move_types)

        # Build where clause
        if data.get("date_from"):
            where_clause += " AND move.invoice_date >= %s"
            params.append(data["date_from"])
        if data.get("date_to"):
            where_clause += " AND move.invoice_date <= %s"
            params.append(data["date_to"])
        if data.get("user_id"):
            where_clause += " AND move.invoice_user_id = %s"
            params.append(data["user_id"][0])
        if data.get("team_id"):
            where_clause += " AND move.team_id = %s"
            params.append(data["team_id"][0])
        if data.get("company_id"):
            where_clause += " AND line.company_id = %s"
            params.append(data["company_id"][0])
        if data.get("partner_id"):
            where_clause += " AND move.partner_id = %s"
            params.append(data["partner_id"][0])
        if data.get("product_id"):
            where_clause += " AND line.product_id = %s"
            params.append(data["product_id"][0])
        if data.get("categ_id"):
            where_clause += " AND template.categ_id = %s"
            params.append(data["categ_id"][0])

        if data.get("parent_categ_id"):
            where_clause += " AND template.categ_id IN (SELECT id FROM product_category WHERE parent_id = %s)"
            params.append(data["parent_categ_id"][0])

        query = self._invoice_query(where_clause)

        _logger.info("Invoice Report Query: %s", query)
        _logger.info("Params: %s", params)

        self.env.cr.execute(query, tuple(params))
        results = self.env.cr.dictfetchall()
        return results

    def _grouped_lines(self, data):
        """Group lines based on group_by (partner or item)"""
        lines = self._lines(data)
        grouped = {}

        if data.get("group_by") == "partner":
            for line in lines:
                partner_id = line["partner_id"]
                if partner_id not in grouped:
                    grouped[partner_id] = {
                        "partner_name": line["partner_name"],
                        "lines": [],
                        "quantity": 0.0,
                        "price_subtotal": 0.0,
                        "price_total": 0.0,
                        "tax_amount": 0.0,
                    }

                grouped[partner_id]["lines"].append(line)
                grouped[partner_id]["quantity"] += line["quantity"]
                grouped[partner_id]["price_subtotal"] += line.get("price_subtotal", 0)
                grouped[partner_id]["price_total"] += line["price_total"]
                grouped[partner_id]["tax_amount"] += line.get("tax_amount", 0)

        elif data.get("group_by") == "item":
            for line in lines:
                product_id = line["product_id"]
                if product_id not in grouped:
                    grouped[product_id] = {
                        "product_name": line["product_name"],
                        "lines": [],
                        "quantity": 0.0,
                        "price_subtotal": 0.0,
                        "price_total": 0.0,
                        "tax_amount": 0.0,
                    }

                grouped[product_id]["lines"].append(line)
                grouped[product_id]["quantity"] += line["quantity"]
                grouped[product_id]["price_subtotal"] += line.get("price_subtotal", 0)
                grouped[product_id]["price_total"] += line["price_total"]
                grouped[product_id]["tax_amount"] += line.get("tax_amount", 0)

        _logger.info("Grouped lines: %s", grouped)
        return grouped

    @api.model
    def _get_report_values(self, docids, data=None):
        doc_model = self.env.context.get("active_model")
        doc_ids = self.env.context.get("active_ids")
        docs = self.env[doc_model].browse(doc_ids)

        report_engine = self.env["report.mgs_account.invoice_report"]
        grouped_lines = report_engine._grouped_lines(data["form"])  # type: ignore

        return {
            "doc_ids": docids,
            "doc_model": doc_model,
            "docs": docs,
            "date_from": data["form"]["date_from"],  # type: ignore
            "date_to": data["form"]["date_to"],  # type: ignore
            "invoice_or_bill": data["form"]["invoice_or_bill"],  # type: ignore
            "group_by": data["form"]["group_by"],  # type: ignore
            "report_type": data["form"]["report_type"],  # type: ignore
            "grouped_lines": grouped_lines,
            "partner_id": data["form"].get("partner_id"),  # type: ignore
            "product_id": data["form"].get("product_id"),  # type: ignore
            "parent_categ_id": data["form"].get("parent_categ_id"),  # type: ignore
            "categ_id": data["form"].get("categ_id"),  # type: ignore
            "user_id": data["form"].get("user_id"),  # type: ignore
            "team_id": data["form"].get("team_id"),  # type: ignore
            "company_id": self.env["res.company"].browse(data["form"]["company_id"][0])  # type: ignore
            if data["form"].get("company_id")  # type: ignore
            else self.env.company,
        }
