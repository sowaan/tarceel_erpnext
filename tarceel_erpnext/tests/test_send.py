# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Phase 2 coverage: manual send + WhatsApp Message Log.

`requests` is mocked, so these never hit a real Tarceel instance. They verify
the log is created and lands in the right state on success and failure, that the
number is normalized, and that the per-DocType recipient default resolves. The
live acceptance (a real message from a real document) is a separate manual step.
"""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import api

_TEST_KEY = "sk_secret_do_not_leak"


def _resp(status_code, payload):
	r = mock.Mock()
	r.ok = 200 <= status_code < 300
	r.status_code = status_code
	r.json.return_value = payload
	return r


class TestSendMessage(FrappeTestCase):
	def setUp(self):
		settings = frappe.get_single("Tarceel Settings")
		settings.enabled = 1
		settings.base_url = "https://api.example.test"
		settings.instance_id = "inst_123"
		settings.api_key = _TEST_KEY
		settings.set("phone_field_mappings", [])
		settings.append("phone_field_mappings", {"document_type": "User", "phone_field": "mobile_no"})
		settings.save()
		frappe.clear_cache(doctype="Tarceel Settings")

		self.todo = frappe.get_doc({"doctype": "ToDo", "description": "tarceel test"}).insert()

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_send_creates_sent_log(self, req):
		req.return_value = _resp(200, {"id": "wamid.123"})
		res = api.send_message("+92 300 1234567", "Hi there", "ToDo", self.todo.name)

		self.assertTrue(res["ok"])
		self.assertEqual(res["status"], "Sent")
		self.assertEqual(res["message_id"], "wamid.123")

		log = frappe.get_doc("WhatsApp Message Log", res["name"])
		self.assertEqual(log.status, "Sent")
		self.assertEqual(log.recipient, "923001234567")  # normalized
		self.assertEqual(log.reference_doctype, "ToDo")
		self.assertEqual(log.reference_name, self.todo.name)
		self.assertEqual(log.direction, "Outgoing")

		# Verify the number actually sent to Tarceel is the normalized one.
		self.assertEqual(req.call_args.kwargs["json"]["to"], "923001234567")

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_failed_send_is_logged_not_lost(self, req):
		req.return_value = _resp(402, {"error": {"code": "billing", "message": "unpaid"}})
		res = api.send_message("923001234567", "Hi", "ToDo", self.todo.name)

		self.assertFalse(res["ok"])
		self.assertEqual(res["status"], "Failed")

		log = frappe.get_doc("WhatsApp Message Log", res["name"])
		self.assertEqual(log.status, "Failed")
		self.assertIn("plan/payment", log.error)

	def test_empty_message_rejected(self):
		with self.assertRaises(Exception):
			api.send_message("923001234567", "   ", "ToDo", self.todo.name)

	def test_normalize_number(self):
		self.assertEqual(api.normalize_number("(92) 300-1234567"), "923001234567")
		self.assertEqual(api.normalize_number("+92 300 1234567"), "923001234567")
		with self.assertRaises(Exception):
			api.normalize_number("123")

	def test_get_default_recipient_from_mapping(self):
		frappe.db.set_value("User", "Administrator", "mobile_no", "923009998877")
		res = api.get_default_recipient("User", "Administrator")
		self.assertEqual(res["recipient"], "923009998877")

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_send_media_and_log_records_attachment(self, req):
		req.return_value = _resp(200, {"id": "wamid.MEDIA"})
		res = api.send_media_and_log(
			"923001234567",
			"document",
			caption="Invoice PDF",
			reference_doctype="ToDo",
			reference_name=self.todo.name,
			base64="ZmFrZQ==",
			mimetype="application/pdf",
			filename="INV-001.pdf",
		)
		self.assertTrue(res["ok"])
		log = frappe.get_doc("WhatsApp Message Log", res["name"])
		self.assertEqual(log.media_type, "document")
		self.assertEqual(log.media_filename, "INV-001.pdf")
		self.assertEqual(log.message, "Invoice PDF")
		body = req.call_args.kwargs["json"]
		self.assertEqual(body["type"], "document")
		self.assertEqual(body["mimetype"], "application/pdf")
		self.assertEqual(body["base64"], "ZmFrZQ==")

	def test_get_default_recipient_no_mapping(self):
		# ToDo has no configured mapping -> no default.
		res = api.get_default_recipient("ToDo", self.todo.name)
		self.assertIsNone(res["recipient"])

	def test_recipient_via_dotted_link_path(self):
		# Mirrors Sales Invoice "contact_person.mobile_no": hop ToDo.allocated_to
		# (Link -> User) then read the User's mobile_no.
		frappe.db.set_value("User", "Administrator", "mobile_no", "923004445566")
		todo = frappe.get_doc(
			{"doctype": "ToDo", "description": "hop test", "allocated_to": "Administrator"}
		).insert()

		settings = frappe.get_single("Tarceel Settings")
		settings.set("phone_field_mappings", [])
		settings.append(
			"phone_field_mappings",
			{"document_type": "ToDo", "phone_field": "allocated_to.mobile_no"},
		)
		settings.save()
		frappe.clear_cache(doctype="Tarceel Settings")

		res = api.get_default_recipient("ToDo", todo.name)
		self.assertEqual(res["recipient"], "923004445566")

	def test_dotted_path_empty_link_returns_none(self):
		# allocated_to is empty on self.todo -> no recipient, no error.
		settings = frappe.get_single("Tarceel Settings")
		settings.set("phone_field_mappings", [])
		settings.append(
			"phone_field_mappings",
			{"document_type": "ToDo", "phone_field": "allocated_to.mobile_no"},
		)
		settings.save()
		frappe.clear_cache(doctype="Tarceel Settings")

		res = api.get_default_recipient("ToDo", self.todo.name)
		self.assertIsNone(res["recipient"])
