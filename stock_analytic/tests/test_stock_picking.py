# Copyright 2013 Julius Network Solutions
# Copyright 2015 Clear Corp
# Copyright 2016 OpenSynergy Indonesia
# Copyright 2017 ForgeFlow S.L.
# Copyright 2018 Hibou Corp.
# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import StockAnalyticCommon


@tagged("post_install", "-at_install")
class TestStockPicking(StockAnalyticCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.consumption_account = cls.env["account.account"].create(
            {
                "name": "Consumption Expense",
                "code": "600999",
                "account_type": "expense",
            }
        )
        cls.override_account = cls.env["account.account"].create(
            {
                "name": "Project Expense",
                "code": "600998",
                "account_type": "expense_direct_cost",
            }
        )
        # Location with a valuation account: Odoo 19 posts a journal entry
        # for every valued move into it.
        cls.consumption_location = cls.env["stock.location"].create(
            {
                "name": "Consumption",
                "usage": "inventory",
                "company_id": cls.company.id,
                "valuation_account_id": cls.consumption_account.id,
            }
        )

    def _create_picking(self, location_dest, analytic_distribution=False, **move_vals):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": location_dest.id,
            }
        )
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": self.product.id,
                "location_id": self.stock_location.id,
                "location_dest_id": location_dest.id,
                "product_uom": self.product.uom_id.id,
                "product_uom_qty": 1.0,
                "analytic_distribution": analytic_distribution,
                **move_vals,
            }
        )
        return picking

    def _validate(self, picking):
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = 1.0
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    def test_outgoing_with_analytic_and_journal_entry(self):
        self._add_stock(self.product, 1)
        picking = self._create_picking(
            self.consumption_location, self.analytic_distribution
        )
        self._validate(picking)
        move = picking.move_ids
        account_move = move.account_move_id
        self.assertTrue(account_move, "A journal entry should be posted")
        valuation_account = self.product._get_product_accounts()["stock_valuation"]
        for line in account_move.line_ids:
            if line.account_id == valuation_account:
                self.assertFalse(line.analytic_distribution)
            else:
                self.assertEqual(line.account_id, self.consumption_account)
                self.assertEqual(line.analytic_distribution, self.analytic_distribution)
        # Analytic lines come from the journal item only (no duplicates).
        aal = self._analytic_lines()
        self.assertEqual(len(aal), 1)
        self.assertAlmostEqual(aal.amount, -self.product.standard_price)
        self.assertFalse(move.analytic_account_line_ids)

    def test_outgoing_with_account_override(self):
        self._add_stock(self.product, 1)
        picking = self._create_picking(
            self.consumption_location,
            self.analytic_distribution,
            mgs_account_id=self.override_account.id,
        )
        self._validate(picking)
        lines = picking.move_ids.account_move_id.line_ids
        self.assertIn(self.override_account, lines.account_id)
        self.assertNotIn(self.consumption_account, lines.account_id)

    def test_outgoing_with_analytic_without_journal_entry(self):
        self._add_stock(self.product, 1)
        picking = self._create_picking(
            self.customer_location, self.analytic_distribution
        )
        self._validate(picking)
        move = picking.move_ids
        self.assertFalse(move.account_move_id)
        # Analytic lines are generated from the stock move itself.
        self.assertEqual(move.analytic_account_line_ids, self._analytic_lines())
        self.assertEqual(len(move.analytic_account_line_ids), 1)
        self.assertAlmostEqual(
            move.analytic_account_line_ids.amount, -self.product.standard_price
        )

    def test_outgoing_without_analytic_optional(self):
        self._add_stock(self.product, 1)
        picking = self._create_picking(self.consumption_location)
        self._validate(picking)
        self.assertFalse(
            picking.move_ids.account_move_id.line_ids.filtered("analytic_distribution")
        )
        self.assertFalse(self._analytic_lines())

    def test_outgoing_without_analytic_mandatory(self):
        self.analytic_applicability.applicability = "mandatory"
        self._add_stock(self.product, 1)
        picking = self._create_picking(self.customer_location)
        with self.assertRaises(ValidationError):
            self._validate(picking)

    def test_incoming_not_validated(self):
        self.analytic_applicability.applicability = "mandatory"
        move = self._make_in_move(self.product, 1, create_picking=True)
        self.assertEqual(move.state, "done")

    def test_move_line_propagates_to_move(self):
        picking = self._create_picking(
            self.customer_location, self.analytic_distribution
        )
        picking.action_confirm()
        other_product = self.product_fifo_auto
        self._add_stock(other_product, 1)
        move_before = picking.move_ids
        self.env["stock.move.line"].create(
            {
                "picking_id": picking.id,
                "product_id": other_product.id,
                "product_uom_id": other_product.uom_id.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "quantity": 1.0,
                "analytic_distribution": self.analytic_distribution,
            }
        )
        new_move = picking.move_ids - move_before
        self.assertEqual(new_move.analytic_distribution, self.analytic_distribution)

    def test_move_line_from_move(self):
        self._add_stock(self.product, 1)
        picking = self._create_picking(
            self.customer_location, self.analytic_distribution
        )
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(
            picking.move_line_ids.analytic_distribution, self.analytic_distribution
        )

    def test_prepare_procurement_values(self):
        picking = self._create_picking(
            self.customer_location, self.analytic_distribution
        )
        values = picking.move_ids._prepare_procurement_values()
        self.assertEqual(values["analytic_distribution"], self.analytic_distribution)
        picking = self._create_picking(self.customer_location)
        values = picking.move_ids._prepare_procurement_values()
        self.assertIsNone(values.get("analytic_distribution"))
