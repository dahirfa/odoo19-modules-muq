from odoo import models, fields, api  # type: ignore
import xlsxwriter  # type: ignore
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class GrossProfit(models.TransientModel):
    _name = "mgs_account.gross_profit"
    _description = "Gross Profit Wizard"

    report_by = fields.Selection(
        [("Product", "Product"), ("Partner", "Partner"), ("Category", "Category")],
        string="Group by",
        default="Product",
        required=True,
    )
    target_moves = fields.Selection(
        [("all", "All Entries"), ("posted", "All Posted Entries")],
        string="Target Moves",
        default="all",
        required=True,
    )
    product_type = fields.Selection(
        [
            ("all", "All Products"),
            ("product", "Storable/Consumable Products"),
            ("service", "Service Products"),
        ],
        string="Product Type",
        default="all",
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company.id,
        required=True,
    )
    date_from = fields.Date(
        string="Date From", default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(string="Date To", default=lambda self: fields.Date.today())
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account"
    )

    product_id = fields.Many2one("product.product", string="Product")
    partner_id = fields.Many2one("res.partner", string="Partner")
    categ_id = fields.Many2one("product.category", string="Product Category")
    parent_categ_id = fields.Many2one("product.category", string="Parent Category")

    datas = fields.Binary("File", readonly=True)
    datas_fname = fields.Char("Filename", readonly=True)

    # ---------- ONCHANGE FIXES ----------
    @api.onchange("product_id")
    def _onchange_product_id(self):
        """When a product is chosen, automatically set its category."""
        if self.product_id:
            self.categ_id = self.product_id.categ_id.id  # type: ignore
            return {
                "domain": {
                    "categ_id": [("id", "=", self.product_id.categ_id.id)],  # type: ignore
                    "product_id": [("categ_id", "=", self.product_id.categ_id.id)],  # type: ignore
                }
            }
        else:
            # If product cleared, show all categories and products
            return {"domain": {"categ_id": [], "product_id": []}}

    @api.onchange("categ_id")
    def _onchange_categ_id(self):
        """When category is selected, restrict products to that category."""
        if self.categ_id:
            domain = [("categ_id", "=", self.categ_id.id)]
            # Reset product if it doesn't belong to the selected category
            if self.product_id and self.product_id.categ_id != self.categ_id:  # type: ignore
                self.product_id = False
            return {"domain": {"product_id": domain}}
        else:
            # If category cleared, show all products
            return {"domain": {"product_id": []}}

    # ---------- REPORT LOGIC ----------
    def check_report(self):
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": {
                "company_id": [self.company_id.id, self.company_id.name],
                "partner_id": [self.partner_id.id, self.partner_id.name]
                if self.partner_id
                else False,
                "product_id": [self.product_id.id, self.product_id.name]  # type: ignore
                if self.product_id
                else False,
                "categ_id": [self.categ_id.id, self.categ_id.name]
                if self.categ_id
                else False,
                "parent_categ_id": [self.parent_categ_id.id, self.parent_categ_id.name]
                if self.parent_categ_id
                else False,
                "analytic_account_id": [
                    self.analytic_account_id.id,
                    self.analytic_account_id.name,
                ]
                if self.analytic_account_id
                else False,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "report_by": self.report_by,
                "target_moves": self.target_moves,
                "product_type": self.product_type,
            },
        }
        return self.env.ref("mgs_account.action_report_gross_profit").report_action(
            self, data=data
        )

    def export_to_excel(self):
        lines = self.env["report.mgs_account.gross_profit_report"]._lines(
            self.company_id.id,
            self.date_from,
            self.date_to,
            self.partner_id.id if self.partner_id else False,
            self.product_id.id if self.product_id else False,  # type: ignore
            self.categ_id.id if self.categ_id else False,
            self.parent_categ_id.id if self.parent_categ_id else False,
            self.analytic_account_id.id if self.analytic_account_id else False,
            self.target_moves,
            self.product_type,
            self.report_by,
        )

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet("Gross Profit Report")

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
        money_format = workbook.add_format(
            {
                "num_format": "#,##0.00",
                "border": 1,
                "align": "right",
                "font_name": "Calibri",
                "font_size": 10,
            }
        )
        total_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#3D8BDA",
                "border": 1,
                "num_format": "#,##0.00",
                "font_name": "Calibri",
                "font_color": "#FFFFFF",
                "font_size": 11,
            }
        )

        headers = {
            "Product": ["Product Name", "Cost Total", "Revenue Total", "Gross Profit"],
            "Partner": ["Partner Name", "Cost Total", "Revenue Total", "Gross Profit"],
            "Category": [
                "Category Name",
                "Cost Total",
                "Revenue Total",
                "Gross Profit",
            ],
        }[self.report_by]

        worksheet.write_row(0, 0, headers, header_format)
        worksheet.freeze_panes(1, 0)
        worksheet.set_column(0, 0, 40)
        worksheet.set_column(1, 3, 15)

        total_cost = total_revenue = total_profit = 0
        row = 1

        for line in lines:
            worksheet.write(row, 0, line.get("group_name", ""))
            worksheet.write_number(row, 1, line.get("act_cost", 0), money_format)
            worksheet.write_number(row, 2, line.get("act_revenue", 0), money_format)
            worksheet.write_number(row, 3, line.get("gross_profit", 0), money_format)
            total_cost += line.get("act_cost", 0)
            total_revenue += line.get("act_revenue", 0)
            total_profit += line.get("gross_profit", 0)
            row += 1

        total_row = row + 1
        worksheet.write(total_row, 0, "Overall Total", total_format)
        worksheet.write_number(total_row, 1, total_cost, total_format)
        worksheet.write_number(total_row, 2, total_revenue, total_format)
        worksheet.write_number(total_row, 3, total_profit, total_format)

        workbook.close()
        out = base64.encodebytes(fp.getvalue())
        filename = f"Gross_Profit_Report_{fields.Date.today()}.xlsx"

        self.write({"datas": out, "datas_fname": filename})
        fp.close()

        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": f"web/content/?model={self._name}&id={self.id}&field=datas&download=true&filename={filename}",
        }


class GrossProfitReport(models.AbstractModel):
    _name = "report.mgs_account.gross_profit_report"
    _description = "Gross Profit Report"

    def _lines(
        self,
        company_id,
        date_from,
        date_to,
        partner_id,
        product_id,
        categ_id,
        parent_categ_id,
        analytic_account_id,
        target_moves,
        product_type,
        report_by,
    ):
        params = []
        lang_code = self.env.user.lang or "en_US"
        states = "('posted','draft')" if target_moves == "all" else "('posted')"

        # Determine accounts from category logic
        income_accounts, expense_accounts = set(), set()

        def collect_accounts(cat):
            if cat.property_account_income_categ_id:
                income_accounts.add(cat.property_account_income_categ_id.id)
            if cat.property_account_expense_categ_id:
                expense_accounts.add(cat.property_account_expense_categ_id.id)

        if categ_id:
            collect_accounts(self.env["product.category"].browse(categ_id))
        elif product_id:
            prod = self.env["product.product"].browse(product_id)
            collect_accounts(prod.categ_id)
        else:
            for c in self.env["product.category"].search([]):
                collect_accounts(c)

        if not income_accounts and not expense_accounts:
            _logger.info("No income/expense accounts found for selected filters.")
            return []

        income_tuple = tuple(income_accounts) if income_accounts else (0,)
        expense_tuple = tuple(expense_accounts) if expense_accounts else (0,)

        def safe_name_expr(field):
            return f"CASE WHEN ({field}::text) LIKE '{{%%' THEN ({field}::jsonb)->>'{lang_code}' ELSE ({field}::text) END"

        product_name_expr = safe_name_expr("pt.name")
        category_name_expr = safe_name_expr("pc.name")

        if report_by == "Product":
            group_expr = product_name_expr
            extra_group = ", pp.id"
        elif report_by == "Partner":
            group_expr = "rp.name"
            extra_group = ""
        else:
            group_expr = category_name_expr
            extra_group = ", pc.id"

        select_query = f"""
        SELECT {group_expr} AS group_name,
            ABS(COALESCE(SUM(CASE WHEN aml.account_id IN %s THEN aml.balance ELSE 0 END), 0)) AS act_cost,
            ABS(COALESCE(SUM(CASE WHEN aml.account_id IN %s THEN aml.balance ELSE 0 END), 0)) AS act_revenue,
            (ABS(COALESCE(SUM(CASE WHEN aml.account_id IN %s THEN aml.balance ELSE 0 END), 0)) * -1
             + ABS(COALESCE(SUM(CASE WHEN aml.account_id IN %s THEN aml.balance ELSE 0 END), 0))) AS gross_profit
        """

        from_query = f"""
        FROM account_move_line AS aml
        LEFT JOIN account_account AS aa ON aml.account_id = aa.id
        LEFT JOIN product_product AS pp ON aml.product_id = pp.id
        LEFT JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
        LEFT JOIN product_category AS pc ON pt.categ_id = pc.id
        LEFT JOIN product_category AS parent_pc ON pc.parent_id = parent_pc.id
        LEFT JOIN res_partner AS rp ON aml.partner_id = rp.id
        LEFT JOIN account_analytic_line AS aal ON aal.move_line_id = aml.id
        WHERE aml.parent_state IN {states}
        """

        params += [expense_tuple, income_tuple, expense_tuple, income_tuple]

        if date_from:
            from_query += " AND aml.date >= %s"
            params.append(date_from)
        if date_to:
            from_query += " AND aml.date <= %s"
            params.append(date_to)
        if company_id:
            from_query += " AND aml.company_id = %s"
            params.append(company_id)
        if product_id:
            from_query += " AND aml.product_id = %s"
            params.append(product_id)
        if categ_id:
            from_query += " AND pt.categ_id = %s"
            params.append(categ_id)
        if partner_id:
            from_query += " AND aml.partner_id = %s"
            params.append(partner_id)
        if parent_categ_id:
            from_query += " AND parent_pc.id = %s"
            params.append(parent_categ_id)
        if analytic_account_id:
            from_query += " AND aal.account_id = %s"
            params.append(analytic_account_id)
        if product_type == "product":
            from_query += " AND pt.type IN ('product','consu')"
        elif product_type == "service":
            from_query += " AND pt.type = 'service'"

        group_by = f" GROUP BY {group_expr}{extra_group} ORDER BY gross_profit DESC"

        query = select_query + from_query + group_by
        _logger.info("Gross Profit Query: %s", query)
        _logger.info("Params: %s", params)

        self.env.cr.execute(query, tuple(params))
        return self.env.cr.dictfetchall()

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare values for the QWeb report template."""
        model = self.env.context.get("active_model")
        docs = self.env[model].browse(self.env.context.get("active_id"))
        form_data = data.get("form", {}) if data else {}
        return {
            "doc_ids": self.ids,
            "doc_model": model,
            "docs": docs,
            "date_from": form_data.get("date_from"),
            "date_to": form_data.get("date_to"),
            "product_id": form_data.get("product_id"),
            "partner_id": form_data.get("partner_id"),
            "categ_id": form_data.get("categ_id"),
            "parent_categ_id": form_data.get("parent_categ_id"),
            "analytic_account_id": form_data.get("analytic_account_id"),
            "company_id": self.env["res.company"].search(
                [("id", "=", form_data.get("company_id", [False])[0])]
            ),
            "report_by": form_data.get("report_by", "Product"),
            "target_moves": form_data.get("target_moves", "all"),
            "product_type": form_data.get("product_type", "all"),
            "lines": self._lines,  # Pass the method reference for QWeb to call
        }
