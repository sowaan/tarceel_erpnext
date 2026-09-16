# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Timeline: linked WhatsApp messages appear on a document with delivery status."""

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import timeline


class TestTimeline(FrappeTestCase):
	def setUp(self):
		self.todo = frappe.get_doc({"doctype": "ToDo", "description": "tl test"}).insert()

	def _log(self, **kw):
		values = {
			"doctype": "WhatsApp Message Log",
			"recipient": "923001234567",
			"message": "Hello there",
			"direction": "Outgoing",
			"status": "Delivered",
			"reference_doctype": "ToDo",
			"reference_name": self.todo.name,
		}
		values.update(kw)
		return frappe.get_doc(values).insert(ignore_permissions=True)

	def test_linked_message_appears_in_timeline(self):
		self._log()
		items = timeline.get_timeline_content("ToDo", self.todo.name)
		self.assertEqual(len(items), 1)
		self.assertEqual(items[0]["icon"], "whatsapp")
		content = items[0]["content"]
		self.assertIn("Hello there", content)
		self.assertIn("Delivered", content)  # delivery status pill
		self.assertIn("923001234567", content)
		self.assertIn("frappe-timestamp", content)  # native timestamp (hover + auto-refresh)
		self.assertIn("data-timestamp", content)

	def test_unrelated_document_has_no_items(self):
		self._log()
		other = frappe.get_doc({"doctype": "ToDo", "description": "other"}).insert()
		self.assertEqual(timeline.get_timeline_content("ToDo", other.name), [])

	def test_incoming_renders_received_verb(self):
		self._log(direction="Incoming", status="Sent", message="hi back")
		items = timeline.get_timeline_content("ToDo", self.todo.name)
		self.assertIn("received from", items[0]["content"])
