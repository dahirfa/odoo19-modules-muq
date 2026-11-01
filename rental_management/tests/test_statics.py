import datetime
import psycopg2
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, AccessError
from odoo.tests.common import tagged
from .common import CreateRentalData


@tagged("property_statics")
class TestPropertyStatics(CreateRentalData):

    def test_statics_all(self):
        self.env["product.template"].create({
            "name": "Product"})
        self.env["maintenance.team"].create({
            "name": "Team One",
            "member_ids": [
                (0, 0,
                 {"name": "Team Member One", "login": "team_member_one"}),
                (0, 0,
                 {"name": "Team Member Two", "login": "team_member_two"}), ],
        })
        project = self._create_project(
            name="Project One",
            project_sequence="10",
            project_for="rent",
            property_type="residential",
            property_subtype_id=1,
            date_of_project=datetime.datetime.today(),
        )

        subproject_wizard = self._create_sub_project_wizard(
            "SP1", "01", 5, 5, project.id, )
        subproject_action = subproject_wizard.create_sub_project()
        subproject = self.env["property.sub.project"].browse(
            subproject_action["res_id"])
        unit_wizard = self._create_units_wizard(
            1, 8, 1, subproject.id, "sub_project")
        unit_wizard.action_create_property_unit()
        rent_property_ids = self.env["property.details"].search(
            [("subproject_id", "=", subproject.id)], limit=3)
        sale_property_ids = self.env["property.details"].search(
            [("subproject_id", "=", subproject.id)], limit=3, offset=3)
        avaiable_properties_ids = self.env["property.details"].search(
            [("subproject_id", "=", subproject.id)], offset=6)
        sale_contracts = []
        rent_contracts = []
        avaiable_properties_ids[0].sale_lease = "for_tenancy"
        avaiable_properties_ids[1].sale_lease = "for_sale"
        avaiable_properties_ids[0].total_area = 100.0
        avaiable_properties_ids[1].total_area = 100.0
        avaiable_properties_ids[0].action_in_available()
        avaiable_properties_ids[1].action_in_available()

        for rent, sale in zip(rent_property_ids, sale_property_ids):
            rent.sale_lease = "for_tenancy"
            sale.sale_lease = "for_sale"
            rent.total_area = 100.0
            sale.total_area = 100.0
            rent.price = 50.0
            sale.price = 50.0
            rent.is_maintenance_service = True
            sale.is_maintenance_service = True
            rent.maintenance_rent_type = "once"
            sale.maintenance_rent_type = "recurring"
            rent.maintenance_type = "fixed"
            sale.maintenance_type = "area_wise"
            rent.total_maintenance = 100
            sale.per_area_maintenance = 1

            contract_wizard = self._create_booking_wizard(
                sale.id, self.customer_one.id, sale.id, 1000, 800, )
            contract_action = contract_wizard.create_booking_action()
            sale_contracts.append(self.env["property.vendor"].browse(
                contract_action["res_id"]))

            contract_wizard = self._create_contract_wizard(
                active_model="property.details",
                active_id=rent.id, data={"customer_id": self.customer_one.id,
                                         "start_date": "2025-03-01", "payment_term": "full_payment",
                                         "duration_type": "by_date", "total_rent": 100,
                                         "duration_end_date":
                                             "2025-04-01", "property_id": rent.id})
            contract_wizard_action = contract_wizard.contract_action()
            rent_contracts.append(self.env["tenancy.details"].browse(
                contract_wizard_action["res_id"]))

        rent_intsallment_invoices = []
        sale_intsallment_invoices = []

        for sale, rent, sale_property in zip(
                sale_contracts, rent_contracts, sale_property_ids):
            property_vender = self._create_installment_wizard(
                active_id=sale.id, property_id=sale_property.id, payment_term="full_payment",
                final_price=10000, company_id=self.company.id,
                customer_id=sale.id)
            property_vender.property_sale_action()
            sale.action_confirm_sale()
            sale.sale_invoice_ids.action_create_invoice()
            sale_intsallment_invoices.append(sale.sale_invoice_ids.invoice_id)
            rent_intsallment_invoices.append(
                rent.rent_invoice_ids.rent_invoice_id)

        self.assertEqual(project.total_area, 400)
        self.assertEqual(project.available_area, 100)
        self.assertEqual(project.total_maintenance, 300)
        self.assertEqual(project.total_collection, 0)
        for rent_invoice, sale_invoice, sale, rent in zip(
                rent_intsallment_invoices, sale_intsallment_invoices,
                sale_contracts, rent_contracts):
            rent_invoice.action_post()
            sale_invoice.action_post()
            payment_wizard = self.env[
                "account.payment.register"].with_context(
                active_model="account.move", active_ids=rent_invoice.id,
            ).create({
                "amount": 3200, "journal_id": self.journal_bank.id,
                "payment_date": "2025-03-21",
                "currency_id": self.company_currency.id,
                "payment_method_line_id":
                    self.journal_bank.inbound_payment_method_line_ids[0].id, })
            payment_wizard.action_create_payments()
            rent._compute_tenancy_calculation()

        self.assertEqual(project.scope_of_collection, 9945.0)
        self.assertEqual(project.total_collection, 0)

        project.compute_properties_statics()
        self.assertEqual(project.total_area, 400.0)
        self.assertEqual(project.available_area, 100.0)
        self.assertEqual(project.total_values, 150.0)
        self.assertEqual(project.total_maintenance, 300.0)
        self.assertEqual(project.total_collection, 0)
        self.assertEqual(project.scope_of_collection, 9945.0)

        subproject.compute_properties_statics()
        self.assertEqual(subproject.total_area, 400.0)
        self.assertEqual(subproject.available_area, 100.0)
        self.assertEqual(subproject.total_values, 150.0)
        self.assertEqual(subproject.total_maintenance, 300.0)
        self.assertEqual(subproject.total_collection, 0)
        self.assertEqual(subproject.scope_of_collection, 9945.0)
