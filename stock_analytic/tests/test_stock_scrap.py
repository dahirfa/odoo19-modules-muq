# Copyright (C) 2019 Open Source Integrators
# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import StockAnalyticCommon


@tagged("post_install", "-at_install")
class TestStockScrap(StockAnalyticCommon):
    def _create_scrap(self, analytic_distribution=False):
        return self.env["stock.scrap"].create(
            {
                "product_id": self.product.id,
                "scrap_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "location_id": self.stock_location.id,
                "analytic_distribution": analytic_distribution,
            }
        )

    def test_scrap_without_analytic_optional(self):
        self._add_stock(self.product, 1)
        scrap = self._create_scrap()
        scrap.action_validate()
        self.assertEqual(scrap.state, "done")
        self.assertFalse(scrap.move_ids.analytic_distribution)

    def test_scrap_without_analytic_mandatory(self):
        self.analytic_applicability.applicability = "mandatory"
        self._add_stock(self.product, 1)
        scrap = self._create_scrap()
        with self.assertRaises(ValidationError):
            scrap.action_validate()

    def test_scrap_with_analytic(self):
        self._add_stock(self.product, 1)
        scrap = self._create_scrap(self.analytic_distribution)
        scrap.action_validate()
        self.assertEqual(scrap.state, "done")
        self.assertEqual(scrap.move_ids.analytic_distribution, self.analytic_distribution)
        self.assertEqual(len(self._analytic_lines()), 1)
