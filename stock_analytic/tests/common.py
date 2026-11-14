# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


class StockAnalyticCommon(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Stock Analytic Plan"}
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Stock Analytic Account",
                "plan_id": cls.analytic_plan.id,
                "company_id": cls.company.id,
            }
        )
        cls.analytic_distribution = {str(cls.analytic_account.id): 100.0}
        cls.analytic_applicability = cls.env["account.analytic.applicability"].create(
            {
                "business_domain": "stock_move",
                "applicability": "optional",
                "analytic_plan_id": cls.analytic_plan.id,
                "company_id": cls.company.id,
            }
        )
        cls.product = cls.product_standard_auto

    def _analytic_lines(self):
        column = self.analytic_plan._column_name()
        return self.env["account.analytic.line"].search(
            [(column, "=", self.analytic_account.id)]
        )

    def _add_stock(self, product, quantity):
        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_location, quantity
        )
