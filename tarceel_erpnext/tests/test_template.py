# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Phase 3 coverage: WhatsApp Message Template rendering and scoping.

Rendering is exercised against a real document with Frappe's own Jinja engine
(no network). The live acceptance (compose from a template and actually send) is
a separate manual step.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import api


def _make_template(name, message, reference_doctype=""):
	if frappe.db.exists("WhatsApp Message Template", name):
		frappe.delete_doc("WhatsApp Message Template", name, force=True)
	return frappe.get_doc(
		{
			"doctype": "WhatsApp Message Template",
			"template_name": name,
			"message": message,
			"reference_doctype": reference_doctype,
			"enabled": 1,
		}
	).insert()


class TestMessageTemplate(FrappeTestCase):
	def setUp(self):
		self.todo = frappe.get_doc(
			{"doctype": "ToDo", "description": "Ship the crates"}
		).insert()

	def test_render_interpolates_document_fields(self):
		_make_template("TAR Test Render", "Task: {{ doc.description }} ({{ doc.name }})", "ToDo")
		out = api.render_template("TAR Test Render", "ToDo", self.todo.name)
		self.assertEqual(out["message"], f"Task: Ship the crates ({self.todo.name})")

	def test_render_returns_print_format(self):
		if not frappe.db.exists("Print Format", "TAR ToDo PF"):
			frappe.get_doc(
				{
					"doctype": "Print Format",
					"name": "TAR ToDo PF",
					"doc_type": "ToDo",
					"print_format_type": "Jinja",
					"html": "<p>{{ doc.name }}</p>",
				}
			).insert(ignore_permissions=True)

		t = _make_template("TAR Test PF", "Hi {{ doc.name }}", "ToDo")
		t.print_format = "TAR ToDo PF"
		t.save()
		out = api.render_template("TAR Test PF", "ToDo", self.todo.name)
		self.assertEqual(out["print_format"], "TAR ToDo PF")

	def test_scoped_template_rejects_wrong_doctype(self):
		_make_template("TAR Test Scoped", "Hi {{ doc.name }}", "Sales Invoice")
		with self.assertRaises(Exception):
			api.render_template("TAR Test Scoped", "ToDo", self.todo.name)

	def test_get_templates_for_includes_scoped_and_global(self):
		_make_template("TAR Test Global", "Global {{ doc.name }}", "")
		_make_template("TAR Test ToDo", "ToDo {{ doc.name }}", "ToDo")
		_make_template("TAR Test Other", "Other", "Sales Invoice")

		names = {t["name"] for t in api.get_templates_for("ToDo")}
		self.assertIn("TAR Test Global", names)  # unscoped -> always offered
		self.assertIn("TAR Test ToDo", names)  # scoped to ToDo
		self.assertNotIn("TAR Test Other", names)  # scoped elsewhere -> excluded

	def test_disabled_template_excluded(self):
		t = _make_template("TAR Test Disabled", "x {{ doc.name }}", "ToDo")
		t.enabled = 0
		t.save()
		names = {x["name"] for x in api.get_templates_for("ToDo")}
		self.assertNotIn("TAR Test Disabled", names)
