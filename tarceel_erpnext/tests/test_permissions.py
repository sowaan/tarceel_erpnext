# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Role-based send/view gating.

Sending needs `create` on WhatsApp Message Log (WhatsApp Sender / System
Manager); seeing the timeline needs `read` (WhatsApp Viewer / Sender / System
Manager). Both roles are shipped in the log doctype's permissions.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import api, timeline


def _make_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.set("roles", [])
	for role in roles:
		user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	frappe.clear_cache(user=email)
	return email


class TestSendPermissions(FrappeTestCase):
	def setUp(self):
		self.none = _make_user("tz_none@example.com", [])
		self.sender = _make_user("tz_sender@example.com", ["WhatsApp Sender"])
		self.viewer = _make_user("tz_viewer@example.com", ["WhatsApp Viewer"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_roles_are_shipped(self):
		self.assertTrue(frappe.db.exists("Role", "WhatsApp Sender"))
		self.assertTrue(frappe.db.exists("Role", "WhatsApp Viewer"))

	def test_permission_matrix(self):
		frappe.set_user(self.sender)
		self.assertTrue(frappe.has_permission("WhatsApp Message Log", "create"))
		self.assertTrue(frappe.has_permission("WhatsApp Message Log", "read"))

		frappe.set_user(self.viewer)
		self.assertTrue(frappe.has_permission("WhatsApp Message Log", "read"))
		self.assertFalse(frappe.has_permission("WhatsApp Message Log", "create"))

		frappe.set_user(self.none)
		self.assertFalse(frappe.has_permission("WhatsApp Message Log", "read"))
		self.assertFalse(frappe.has_permission("WhatsApp Message Log", "create"))

	def test_non_sender_cannot_send(self):
		frappe.set_user(self.none)
		with self.assertRaises(frappe.PermissionError):
			api.send_message("923001234567", "hi")

	def test_timeline_hidden_from_non_viewer(self):
		todo = frappe.get_doc({"doctype": "ToDo", "description": "tz perm test"}).insert(
			ignore_permissions=True
		)
		log = frappe.get_doc(
			{
				"doctype": "WhatsApp Message Log",
				"recipient": "923001234567",
				"message": "secret",
				"status": "Sent",
				"reference_doctype": "ToDo",
				"reference_name": todo.name,
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.viewer)
		self.assertEqual(len(timeline.get_timeline_content("ToDo", todo.name)), 1)

		frappe.set_user(self.none)
		self.assertEqual(timeline.get_timeline_content("ToDo", todo.name), [])

		frappe.set_user("Administrator")
		log.delete(ignore_permissions=True)
		todo.delete(ignore_permissions=True)
