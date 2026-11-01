import datetime
import psycopg2
from odoo.exceptions import ValidationError, AccessError
from odoo.tests.common import tagged
from .common import CreateRentalData


@tagged("property_sub_project")
class TestSubProject(CreateRentalData):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_property_one = cls._create_project(
            name="Project One", project_sequence="10",
            project_for="rent", property_type="residential",
            property_subtype_id=1, date_of_project=datetime.datetime.today(), )
        cls.test_property_two = cls._create_project(
            name="Project Two", project_sequence="20", project_for="sale",
            property_type="commercial", property_subtype_id=11,
            date_of_project=datetime.datetime.today(), )

        cls.test_sub_project_one = cls.env["property.sub.project"].create({
            "company_id": cls.env.ref("base.main_company"),
            "name": "Sub Project One", "project_sequence": "10",
            "property_type": "residential",
            "property_project_id": cls.test_property_one.id, })

        cls.test_sub_project_two = cls.env["property.sub.project"].create({
            "company_id": cls.env.ref("base.main_company"),
            "name": "Sub Project Two", "project_sequence": "20",
            "property_type": "commercial", "property_project_id":
                cls.test_property_two.id, })

    def test_subproject_creation(self):
        self.assertTrue(self.test_sub_project_one)
        self.assertTrue(self.test_sub_project_two)
        with self.assertLogs("odoo.sql_db", level="ERROR"):
            with self.assertRaises(psycopg2.errors.NotNullViolation):
                self.env["property.sub.project"].create({})
        self.assertTrue(self.test_sub_project_two.property_project_id)
        self.assertIn(self.test_sub_project_two.property_project_id,
                      self.env["property.project"].search([]), )

    def test_compute_methods(self):
        self.document_one = self.env["subproject.document"].create({
            "name": "Document One", "document_name": "Common",
            "document_file": self.file_to_base64(
                "rental_management/rental_management/tests/common.py"),
            "user_id": self.env.user.id,
            "subproject_id": self.test_sub_project_one.id, })

        self.document_two = self.env["subproject.document"].create({
            "name": "Document One", "document_name": "Common",
            "document_file": self.file_to_base64(
                "rental_management/rental_management/tests/common.py"),
            "user_id": self.env.user.id,
            "subproject_id": self.test_sub_project_one.id, })

        self.document_three = self.env["subproject.document"].create({
            "name": "Document One", "document_name": "Common",
            "document_file": self.file_to_base64(
                "rental_management/rental_management/tests/common.py"),
            "user_id": self.env.user.id,
            "subproject_id": self.test_sub_project_one.id, })

        create_unit_wizard = self._create_units_wizard(
            5, 5, 1, self.test_sub_project_one.id, "sub_project")
        create_unit_wizard.action_create_property_unit()
        sub_project_one_units = self.env["property.details"].search(
            [("subproject_id", "=", self.test_sub_project_one.id)], limit=10)

        for rec in sub_project_one_units:
            if rec.id % 2 == 0:
                rec.action_in_available()
                self.assertEqual(rec.stage, "available")
                self.assertEqual(rec.sale_lease, "for_tenancy")
            else:
                rec.sale_lease = "for_sale"
                self.assertEqual(rec.stage, "draft")
                self.assertEqual(rec.sale_lease, "for_sale")

        sub_project_one_units = self.env["property.details"].search(
            [("subproject_id", "=", self.test_sub_project_one.id)],
            limit=10,
            offset=10,
        )
        for rec in sub_project_one_units:
            if rec.id % 2 == 0:
                rec.stage = "sale"
                self.assertEqual(rec.stage, "sale")
            else:
                rec.stage = "sold"
                self.assertEqual(rec.stage, "sold")

        sub_project_one_units = self.env["property.details"].search(
            [("subproject_id", "=", self.test_sub_project_one.id)], limit=5,
            offset=20, )

        for rec in sub_project_one_units:
            rec.stage = "on_lease"
            self.assertEqual(rec.stage, "on_lease")

        self.test_sub_project_one.compute_count()
        self.test_sub_project_two.compute_count()

        self.assertEqual(self.test_sub_project_one.document_count, 3)
        self.assertEqual(self.test_sub_project_two.document_count, 0)
        self.assertEqual(self.test_sub_project_one.unit_count, 25)
        self.assertEqual(self.test_sub_project_two.unit_count, 0)
        self.assertEqual(self.test_sub_project_one.available_unit_count, 5)
        self.assertEqual(self.test_sub_project_two.available_unit_count, 0)
        self.assertEqual(self.test_sub_project_one.sold_count, 10)
        self.assertEqual(self.test_sub_project_two.sold_count, 0)
        self.assertEqual(self.test_sub_project_one.rent_count, 5)
        self.assertEqual(self.test_sub_project_two.rent_count, 0)

    def test_onchange_methods(self):

        self.test_property_one.street = "Street One"
        self.test_property_one.street2 = "Street Two"
        self.test_property_one.country_id = 104
        self.test_property_one.city_id = (
            self.env["property.res.city"].create({"name": "City One"}).id)
        self.test_property_one.state_id = (
            self.test_property_one.country_id.state_ids.ids[11])
        self.test_property_one.zip = "123456"
        self.test_property_one.total_floors = 5
        self.test_property_one.total_area = 1000
        self.test_property_one.available_area = 750
        self.test_property_one.property_brochure = self.file_to_base64(
            "rental_management/rental_management/tests/common.py")
        self.test_property_one.brochure_name = "Docuemnt One"

        self.test_sub_project_one._onchange_property_project_id()

        self.assertEqual(
            self.test_sub_project_one.street, self.test_property_one.street)
        self.assertEqual(
            self.test_sub_project_one.street2, self.test_property_one.street2)
        self.assertEqual(
            self.test_sub_project_one.city_id, self.test_property_one.city_id)
        self.assertEqual(
            self.test_sub_project_one.state_id, self.test_property_one.state_id)
        self.assertEqual(self.test_sub_project_one.zip,
                         self.test_property_one.zip)
        self.assertEqual(self.test_sub_project_one.country_id,
                         self.test_property_one.country_id)
        self.assertEqual(self.test_sub_project_one.total_floors,
                         self.test_property_one.total_floors)
        self.assertEqual(self.test_sub_project_one.total_area,
                         self.test_property_one.total_area)
        self.assertEqual(self.test_sub_project_one.available_area,
                         self.test_property_one.available_area, )
        self.assertEqual(self.test_sub_project_one.property_brochure,
                         self.test_property_one.property_brochure, )
        self.assertEqual(self.test_sub_project_one.brochure_name,
                         self.test_property_one.brochure_name, )

        # ---------------------------------------------------------------------

        self.test_sub_project_one._onchange_country_id()
        self.assertTrue(self.test_sub_project_one.state_id)
        self.assertEqual(self.test_sub_project_one.state_id.name, "Gujarat")

        # ---------------------------------------------------------------------

        self.test_sub_project_one.state_id = 588
        self.test_sub_project_one.country_id = False
        self.test_sub_project_one._onchange_state()
        self.assertEqual(self.test_sub_project_one.country_id.id, 104)

        # ---------------------------------------------------------------------

        self.property_sub_type = self.env["property.sub.type"].create({
            "name": "Property Type", "type": "land", "sequence": 10})
        self.test_sub_project_one.property_subtype_id = self.property_sub_type.id
        self.test_sub_project_one.onchange_property_sub_type()
        self.assertFalse(self.test_sub_project_one.property_subtype_id)

    def test_action_methods(self):
        action = self.test_sub_project_one.action_document_count()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Documents")
        self.assertEqual({
            "default_subproject_id": self.test_sub_project_one.id},
            action.get("context"), )
        self.assertIn(("subproject_id", "=", self.test_sub_project_one.id),
                      action.get("domain", []), )

        # ---------------------------------------------------------------------

        action = self.test_sub_project_one.action_view_unit()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Units")
        self.assertEqual({
            "create": False}, action.get("context"), )
        self.assertIn(("subproject_id", "=", self.test_sub_project_one.id),
                      action.get("domain", []), )

        # ---------------------------------------------------------------------

        action = self.test_sub_project_one.action_view_available_unit()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Available Units")
        self.assertEqual({"create": False}, action.get("context"), )
        self.assertIn(("subproject_id", "=", self.test_sub_project_one.id),
                      action.get("domain", []), )
        self.assertIn(("stage", "=", "available"), action.get("domain", []), )

        # ---------------------------------------------------------------------

        action = self.test_sub_project_one.action_view_sold_unit()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Sold / Sale Units")
        self.assertEqual({"create": False}, action.get("context"), )
        self.assertIn(("subproject_id", "=", self.test_sub_project_one.id),
                      action.get("domain", []), )
        self.assertIn(("stage", "in", ["sold", "sale"]),
                      action.get("domain", []), )

        # ---------------------------------------------------------------------

        action = self.test_sub_project_one.action_view_rent_unit()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["name"], "Rent Units")
        self.assertEqual({"create": False}, action.get("context"), )
        self.assertIn(("subproject_id", "=", self.test_sub_project_one.id),
                      action.get("domain", []), )
        self.assertIn(("stage", "=", "on_lease"), action.get("domain", []), )

        # ---------------------------------------------------------------------

        self.test_sub_project_one.latitude = 30
        self.test_sub_project_one.longitude = 45
        action = self.test_sub_project_one.action_gmap_location()
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["url"],
                         "https://maps.google.com/maps?q=loc:30,45", )
        with self.assertRaises(ValidationError):
            self.test_sub_project_two.action_gmap_location()

        # ---------------------------------------------------------------------

        self.test_sub_project_one.action_status_draft()
        self.assertEqual(self.test_sub_project_one.status, "draft")
        self.test_sub_project_one.action_status_available()
        self.assertEqual(self.test_sub_project_one.status, "available")

    def test_unlink(self):
        create_unit_wizard = self._create_units_wizard(
            5, 5, 1, self.test_sub_project_one.id, "sub_project")
        create_unit_wizard.action_create_property_unit()
        with self.assertRaises(ValidationError):
            self.test_sub_project_one.unlink()
