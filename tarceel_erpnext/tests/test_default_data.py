# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Coverage for the one-time ERPNext starter-data seeding.

seed_default_data() commits so it works from install/migrate hooks; here we mock
the commit away so each assertion stays inside the test transaction and rolls
back cleanly.
"""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import default_data


class TestDefaultData(FrappeTestCase):
	def setUp(self):
		if "erpnext" not in frappe.get_installed_apps():
			self.skipTest("default data is ERPNext-specific")

	def _reset_unseeded(self):
		for template_name, *_ in default_data.MESSAGE_TEMPLATES:
			frappe.delete_doc_if_exists("WhatsApp Message Template", template_name)
		settings = frappe.get_single("Tarceel Settings")
		settings.phone_field_mappings = []
		settings.default_data_seeded = 0
		settings.flags.ignore_mandatory = True
		settings.save(ignore_permissions=True)

	def test_seeds_mappings_templates_and_sets_flag(self):
		self._reset_unseeded()
		with mock.patch.object(frappe.db, "commit"):
			default_data.seed_default_data()

		self.assertTrue(frappe.db.get_single_value("Tarceel Settings", "default_data_seeded"))
		self.assertTrue(frappe.db.exists("WhatsApp Message Template", "Invoice Reminder"))

		maps = {m.document_type: m.phone_field for m in frappe.get_single("Tarceel Settings").phone_field_mappings}
		self.assertEqual(maps.get("Sales Invoice"), "contact_mobile")
		self.assertEqual(maps.get("Payment Entry"), "party.mobile_no")  # dotted path via Dynamic Link
		self.assertEqual(maps.get("Customer"), "mobile_no")

	def test_reseed_is_noop_and_respects_deletions(self):
		self._reset_unseeded()
		with mock.patch.object(frappe.db, "commit"):
			default_data.seed_default_data()

		# Customer deletes a seeded template; the next migrate must not resurrect it.
		frappe.delete_doc("WhatsApp Message Template", "Invoice Reminder")
		before = frappe.get_single("Tarceel Settings").phone_field_mappings
		with mock.patch.object(frappe.db, "commit"):
			default_data.seed_default_data()

		self.assertFalse(frappe.db.exists("WhatsApp Message Template", "Invoice Reminder"))
		after = frappe.get_single("Tarceel Settings").phone_field_mappings
		self.assertEqual(len(after), len(before))  # no duplicate mappings

	def test_skips_when_erpnext_absent(self):
		self._reset_unseeded()
		with (
			mock.patch.object(frappe.db, "commit"),
			mock.patch("frappe.get_installed_apps", return_value=["frappe"]),
		):
			default_data.seed_default_data()

		self.assertFalse(frappe.db.get_single_value("Tarceel Settings", "default_data_seeded"))
		self.assertFalse(frappe.db.exists("WhatsApp Message Template", "Order Confirmation"))
