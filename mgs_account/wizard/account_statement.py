from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from itertools import groupby
from operator import itemgetter
import xlsxwriter  # type: ignore
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class AccountStatement(models.TransientModel):
    _name = "mgs_account.account_statement"
    _description = "MGS Account Statement"

    account_id = fields.Many2one("account.account", string="Account")
    partner_id = fields.Many2one("res.partner", string="Partner")
    analytic_account_id = fields.Many2one(
        "account.analytic.account", "Analytic Account"
    )
    date_from = fields.Date(
        "From Date", default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date("To Date", default=lambda self: fields.Date.today())
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company.id
    )
    report_by = fields.Selection(
        [("detail", "Detail"), ("summary", "Summary")],
        string="Report Type",
        default="detail",
    )
    target_moves = fields.Selection(
        [("all", "All Entries"), ("posted", "All Posted Entries")],
        string="Target Moves",
        default="posted",
    )
    datas = fields.Binary("File", readonly=True)
    datas_fname = fields.Char("Filename", readonly=True)

    @api.constrains("date_from", "date_to")
    def _check_the_date_from_and_to(self):
        if self.date_to and self.date_from and self.date_to < self.date_from:
            raise ValidationError("""From Date should be less than To Date.""")

    def check_report(self):
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": {
                "company_id": [self.company_id.id, self.company_id.name],
                "partner_id": [self.partner_id.id, self.partner_id.name],
                "account_id": [self.account_id.id, self.account_id.name],
                "analytic_account_id": [
                    self.analytic_account_id.id,
                    self.analytic_account_id.name,
                ],
                "date_from": self.date_from,
                "date_to": self.date_to,
                "report_by": self.report_by,
                "target_moves": self.target_moves,
            },
        }

        return self.env.ref(
            "mgs_account.action_account_statement_report"
        ).report_action(self, data=data)

    def export_to_excel(self):
        """Generates an Excel file for Account Statement Report"""
        statement_report_obj = self.env["report.mgs_account.account_statement_report"]

        # Get the report data
        lines = statement_report_obj._lines(
            self.company_id.id,
            self.date_from,
            self.date_to,
            self.account_id.id if self.account_id else None,
            self.partner_id.id if self.partner_id else None,
            self.analytic_account_id.id if self.analytic_account_id else None,
            self.target_moves,
        )

        # Prepare Excel Workbook
        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet("Account Statement")

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

        money_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "font_name": "Calibri",
                "font_size": 10,
            }
        )

        text_format = workbook.add_format(
            {
                "border": 1,
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

        # Define headers based on report type
        if self.report_by == "summary":
            headers = [
                "Account",
                "Opening Balance",
                "Total Debit",
                "Total Credit",
                "Closing Balance",
                "Currency Balance",
            ]
            col_count = 6
        else:
            headers = [
                "Date",
                "Voucher Type",
                "Voucher No",
                "Partner",
                "Reference",
                "Debit",
                "Credit",
                "Balance",
                "Currency Amount",
            ]
            col_count = 9

        # Write header
        worksheet.write_row(0, 0, headers, header_format)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, 0, col_count - 1)

        # Column widths
        if self.report_by == "summary":
            worksheet.set_column(0, 0, 30)  # Account
            worksheet.set_column(1, 5, 15)  # Amount columns
        else:
            worksheet.set_column(0, 0, 12)  # Date
            worksheet.set_column(1, 1, 15)  # Voucher Type
            worksheet.set_column(2, 2, 15)  # Voucher No
            worksheet.set_column(3, 3, 25)  # Partner
            worksheet.set_column(
                4, 4, 40
            )  # Reference (wider to accommodate combined label+ref)
            worksheet.set_column(5, 8, 15)  # Amount columns

        # Initialize overall totals
        total_opening = 0
        total_debit = 0
        total_credit = 0
        total_closing = 0
        total_currency = 0
        row = 1

        for account_group in lines:
            account_name = account_group.get("name", "")

            if self.report_by == "summary":
                # SUMMARY REPORT - One row per account
                row_fmt = odd_row if row % 2 else even_row

                worksheet.write(row, 0, account_name, row_fmt)
                worksheet.write_number(
                    row, 1, account_group.get("open_balance", 0), money_format
                )
                worksheet.write_number(
                    row, 2, account_group.get("total_debit", 0), money_format
                )
                worksheet.write_number(
                    row, 3, account_group.get("total_credit", 0), money_format
                )
                worksheet.write_number(
                    row, 4, account_group.get("balance", 0), money_format
                )
                worksheet.write_number(
                    row, 5, account_group.get("balance_fc", 0), money_format
                )

                total_opening += account_group.get("open_balance", 0)
                total_debit += account_group.get("total_debit", 0)
                total_credit += account_group.get("total_credit", 0)
                total_closing += account_group.get("balance", 0)
                total_currency += account_group.get("balance_fc", 0)
                row += 1

            else:
                # DETAIL REPORT - Group with multiple lines
                # Write account header
                worksheet.write(row, 0, account_name, group_label_format)
                # Merge remaining cells for account header
                for col in range(1, col_count):
                    worksheet.write_blank(row, col, None, group_label_format)
                row += 1

                # Write opening balance
                worksheet.write(row, 0, "Opening Balance", total_label_format)
                for col in range(
                    1, 5
                ):  # Blank cells for Voucher Type, Voucher No, Partner, Reference
                    worksheet.write_blank(row, col, None, total_label_format)
                for col in range(5, 7):  # Blank cells for Debit and Credit columns
                    worksheet.write_blank(row, col, None, total_label_format)
                worksheet.write_number(
                    row,
                    7,
                    account_group.get("open_balance", 0),
                    money_total_format,  # Balance column
                )
                worksheet.write_blank(
                    row, 8, None, total_label_format
                )  # Currency Amount column
                row += 1

                # Write detail lines
                running_balance = account_group.get("open_balance", 0)
                for line in account_group.get("lines", []):
                    row_fmt = odd_row if row % 2 else even_row

                    worksheet.write(row, 0, line.get("date", ""), date_format)
                    worksheet.write(row, 1, line.get("voucher_type", ""), row_fmt)
                    worksheet.write(row, 2, line.get("voucher_no", ""), row_fmt)
                    worksheet.write(row, 3, line.get("partner_name", ""), row_fmt)

                    # Combine label and reference in Reference column
                    label = line.get("label", "")
                    ref = line.get("ref", "")
                    if label and ref:
                        reference_text = f"{label} ({ref})"
                    elif label:
                        reference_text = label
                    elif ref:
                        reference_text = ref
                    else:
                        reference_text = ""

                    worksheet.write(row, 4, reference_text, row_fmt)
                    worksheet.write_number(row, 5, line.get("debit", 0), money_format)
                    worksheet.write_number(row, 6, line.get("credit", 0), money_format)

                    # Calculate running balance
                    running_balance += line.get("debit", 0) - line.get("credit", 0)
                    worksheet.write_number(row, 7, running_balance, money_format)

                    worksheet.write_number(
                        row, 8, line.get("amount_currency", 0), money_format
                    )
                    row += 1

                # Write account total
                total_label = f"Total {account_name}:"
                worksheet.write(row, 0, total_label, total_label_format)
                for col in range(1, 5):  # Blank cells for non-amount columns
                    worksheet.write_blank(row, col, None, total_label_format)
                worksheet.write_number(
                    row, 5, account_group.get("total_debit", 0), money_total_format
                )
                worksheet.write_number(
                    row, 6, account_group.get("total_credit", 0), money_total_format
                )
                worksheet.write_number(
                    row, 7, account_group.get("balance", 0), money_total_format
                )
                worksheet.write_number(
                    row, 8, account_group.get("balance_fc", 0), money_total_format
                )

                total_opening += account_group.get("open_balance", 0)
                total_debit += account_group.get("total_debit", 0)
                total_credit += account_group.get("total_credit", 0)
                total_closing += account_group.get("balance", 0)
                total_currency += account_group.get("balance_fc", 0)
                row += 1

                # Add empty row between account groups
                row += 1

        # Write overall totals
        if self.report_by == "summary":
            worksheet.write(row, 0, "Overall Total:", overall_label_format)
            worksheet.write_number(row, 1, total_opening, money_overall_format)
            worksheet.write_number(row, 2, total_debit, money_overall_format)
            worksheet.write_number(row, 3, total_credit, money_overall_format)
            worksheet.write_number(row, 4, total_closing, money_overall_format)
            worksheet.write_number(row, 5, total_currency, money_overall_format)
        else:
            # For detail report, overall total should span columns
            worksheet.write(row, 0, "Overall Total:", overall_label_format)
            for col in range(1, 5):  # Blank cells for non-amount columns
                worksheet.write_blank(row, col, None, overall_label_format)
            worksheet.write_number(row, 5, total_debit, money_overall_format)
            worksheet.write_number(row, 6, total_credit, money_overall_format)
            worksheet.write_number(row, 7, total_closing, money_overall_format)
            worksheet.write_number(row, 8, total_currency, money_overall_format)

        # Save and return file
        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        filename = f"AccountStatement_{self.date_from}_{self.date_to}"
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


class AccountStatementReport(models.AbstractModel):
    _name = "report.mgs_account.account_statement_report"
    _description = "Account Statement Report"

    @api.model
    def _lines(
        self,
        company_id,
        date_from,
        date_to,
        account_id,
        partner_id,
        analytic_account_id,
        target_moves,
    ):
        lines = []
        states = """('posted','draft')"""
        if target_moves == "posted":
            states = """('posted')"""
        params = []

        query = (
            """
        select aml.id, aml.date as date, aml.move_id as move_id, aj.name->>'en_US' as voucher_type,
        rp.name as partner_name, aml.name as label, aml.ref as ref, am.name as voucher_no,
        aml.partner_id, aml.account_id as account_id, aa.name->>'en_US' as account_name, aml.debit as debit, aml.credit as credit,
        am.ref as move_ref, aml.amount_currency
        from account_move_line as aml
        left join account_account as aa on aml.account_id=aa.id
        left join res_partner as rp on aml.partner_id=rp.id
        left join account_move as am on aml.move_id=am.id
        left join account_journal as aj on aml.journal_id=aj.id
        where am.state in """
            + states
        )

        if date_from:
            params.append(date_from)
            query += " and aml.date >= %s"

        if date_to:
            params.append(date_to)
            query += " and aml.date <= %s"

        if account_id:
            params.append(account_id)
            query += " and aml.account_id = %s"

        if analytic_account_id:
            query += " and aml.analytic_distribution @> '{\"%s\": 100}'::jsonb" % str(
                analytic_account_id
            )

        if partner_id:
            params.append(partner_id)
            query += " and aml.partner_id = %s"

        if company_id:
            params.append(company_id)
            query += " and aml.company_id = %s"

        query += " order by date asc, id asc"

        self.env.cr.execute(query, tuple(params))
        _logger.info("Query: %s", query)
        key = itemgetter("account_id", "account_name")
        res = sorted(self.env.cr.dictfetchall(), key=key)
        _logger.info("Query Result: %s", res)

        for key, value in groupby(res, key):
            sub_lines = []
            open_balance = 0
            open_balance_fc = 0
            if date_from:
                open_balance = self._sum_open_balance(
                    company_id,
                    date_from,
                    key[0],
                    analytic_account_id,
                    partner_id,
                    target_moves,
                )
                open_balance_fc = self._sum_open_balance_fc(
                    company_id,
                    date_from,
                    key[0],
                    analytic_account_id,
                    partner_id,
                    target_moves,
                )
            total_debit = 0
            total_credit = 0
            balance = open_balance
            balance_fc = open_balance_fc

            for k in value:
                sub_lines.append(k)
                total_debit += k["debit"]
                total_credit += k["credit"]
                balance += k["debit"] - k["credit"]

                balance_fc += k["amount_currency"]

            lines.append(
                {
                    "name": key[1],
                    "lines": sub_lines,
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                    "open_balance": open_balance,
                    "open_balance_fc": open_balance_fc,
                    "balance": balance,
                    "balance_fc": balance_fc,
                }
            )
            _logger.info("Lines: %s", lines)
        return lines

    def _sum_open_balance(
        self,
        company_id,
        date_from,
        account_id,
        analytic_account_id,
        partner_id,
        target_moves,
    ):
        result = 0.0
        states = """('posted','draft')"""
        if target_moves == "posted":
            states = """('posted')"""

        params = [account_id, date_from]
        query = (
            """
            select sum(aml.debit-aml.credit)
            from account_move_line as aml
            left join account_move as am on aml.move_id=am.id
            where aml.account_id = %s and aml.date < %s and am.state in """
            + states
        )

        if analytic_account_id:
            query += " and aml.analytic_distribution @> '{\"%s\": 100}'::jsonb" % str(
                analytic_account_id
            )

        if partner_id:
            params.append(partner_id)
            query += " and aml.partner_id = %s"

        if company_id:
            params.append(company_id)
            query += " and aml.company_id = %s"

        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    def _sum_open_balance_fc(
        self,
        company_id,
        date_from,
        account_id,
        analytic_account_id,
        partner_id,
        target_moves,
    ):
        result = 0.0
        states = """('posted','draft')"""
        if target_moves == "posted":
            states = """('posted')"""

        params = [account_id, date_from]
        query = (
            """
            select sum(aml.amount_currency)
            from account_move_line as aml
            left join account_move as am on aml.move_id=am.id
            where aml.account_id = %s and aml.date < %s and am.state in """
            + states
        )

        if analytic_account_id:
            # params.append(analytic_account_id)
            # query += " and aml.analytic_account_id = %s"
            query += " and aml.analytic_distribution @> '{\"%s\": 100}'::jsonb" % str(
                analytic_account_id
            )

        if partner_id:
            params.append(partner_id)
            query += " and aml.partner_id = %s"

        if company_id:
            params.append(company_id)
            query += " and aml.company_id = %s"

        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    @api.model
    # def _get_report_values(self, docids, data=None):
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get("active_model")
        docs = self.env[model].browse(self.env.context.get("active_id"))
        lines_data = self._lines(
            data["form"]["company_id"][0] if data["form"].get("company_id") else False,  # type: ignore
            data["form"]["date_from"],  # type: ignore
            data["form"]["date_to"],  # type: ignore
            data["form"]["account_id"][0] if data["form"].get("account_id") else False,  # type: ignore
            data["form"]["partner_id"][0] if data["form"].get("partner_id") else False,  # type: ignore
            data["form"]["analytic_account_id"][0]  # type: ignore
            if data["form"].get("analytic_account_id")  # type: ignore
            else False,  # type: ignore
            data["form"]["target_moves"],  # type: ignore
        )

        return {
            "doc_ids": self.ids,
            "doc_model": model,
            "docs": docs,
            "date_from": data["form"]["date_from"],  # type: ignore
            "date_to": data["form"]["date_to"],  # type: ignore
            "account_id": data["form"]["account_id"],  # type: ignore
            "company_id": self.env["res.company"].search(
                [("id", "=", data["form"]["company_id"][0])]  # type: ignore
            ),
            "report_by": data["form"]["report_by"],  # type: ignore
            "target_moves": data["form"]["target_moves"],  # type: ignore
            "analytic_account_id": data["form"]["analytic_account_id"],  # type: ignore
            "partner_id": data["form"]["partner_id"],  # type: ignore
            "lines": lines_data,
        }
