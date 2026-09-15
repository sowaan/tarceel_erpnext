# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Phase 4 coverage: delivery-status webhook.

Signature verification and status handling are tested directly; handle() is
tested with a mocked request. No real Tarceel delivery is involved — the live
acceptance (a real signed delivery updating a log) is a separate manual step.
"""

import hashlib
import hmac
import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import webhook

_SECRET = "whsec_test_secret"


def _sign(secret, body):
	return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestWebhook(FrappeTestCase):
	def setUp(self):
		settings = frappe.get_single("Tarceel Settings")
		settings.webhook_secret = _SECRET
		settings.save()
		frappe.clear_cache(doctype="Tarceel Settings")

		self.log = frappe.get_doc(
			{
				"doctype": "WhatsApp Message Log",
				"recipient": "923001234567",
				"message": "hi",
				"status": "Sent",
				"message_id": "wamid.ABC",
			}
		).insert(ignore_permissions=True)

	def _status(self):
		return frappe.db.get_value("WhatsApp Message Log", self.log.name, "status")

	# --- signature ---

	def test_signature_valid_and_invalid(self):
		body = b'{"a":1}'
		self.assertTrue(webhook.is_valid_signature(_SECRET, body, _sign(_SECRET, body)))
		self.assertFalse(webhook.is_valid_signature(_SECRET, body, _sign("wrong", body)))
		self.assertFalse(webhook.is_valid_signature(_SECRET, body, None))
		self.assertFalse(webhook.is_valid_signature(None, body, _sign(_SECRET, body)))

	# --- status application ---

	def test_status_advances(self):
		webhook.apply_status_event({"data": {"id": "wamid.ABC", "status": "delivered"}})
		self.assertEqual(self._status(), "Delivered")

	def test_matches_on_messageid_when_id_is_wamid(self):
		# The fixed-Tarceel shape: data.id is the WAMID, data.messageId is our UUID.
		webhook.apply_status_event(
			{"data": {"id": "3EB0C6F5WAMID", "messageId": "wamid.ABC", "status": "delivered"}}
		)
		self.assertEqual(self._status(), "Delivered")

	def test_status_does_not_regress(self):
		frappe.db.set_value("WhatsApp Message Log", self.log.name, "status", "Read")
		webhook.apply_status_event({"data": {"id": "wamid.ABC", "status": "delivered"}})
		self.assertEqual(self._status(), "Read")  # late "delivered" ignored

	def test_status_failed_applies(self):
		webhook.apply_status_event({"data": {"id": "wamid.ABC", "status": "failed"}})
		self.assertEqual(self._status(), "Failed")

	def test_unknown_message_id_is_noop(self):
		self.assertIsNone(webhook.apply_status_event({"data": {"id": "nope", "status": "read"}}))

	def test_unknown_status_is_noop(self):
		self.assertIsNone(webhook.apply_status_event({"data": {"id": "wamid.ABC", "status": "??"}}))
		self.assertEqual(self._status(), "Sent")

	# --- full handle() with mocked request ---

	def _call_handle(self, body, signature, event="message.status"):
		headers = {"X-Tarceel-Event": event, "X-Tarceel-Signature": signature}
		fake_req = mock.Mock()
		fake_req.get_data.return_value = body
		# frappe.request is a LocalProxy; set the underlying frappe.local.request.
		orig_request = getattr(frappe.local, "request", None)
		frappe.local.request = fake_req
		try:
			with mock.patch.object(frappe, "get_request_header", side_effect=lambda h: headers.get(h)):
				return webhook.handle()
		finally:
			frappe.local.request = orig_request

	def test_handle_rejects_bad_signature(self):
		body = json.dumps({"event": "message.status", "data": {"id": "wamid.ABC", "status": "read"}}).encode()
		res = self._call_handle(body, _sign("wrong", body))
		self.assertFalse(res["ok"])
		self.assertEqual(frappe.local.response.get("http_status_code"), 401)
		self.assertEqual(self._status(), "Sent")  # untouched

	def test_handle_processes_valid_delivery(self):
		body = json.dumps({"event": "message.status", "data": {"id": "wamid.ABC", "status": "read"}}).encode()
		res = self._call_handle(body, _sign(_SECRET, body))
		self.assertTrue(res["ok"])
		self.assertEqual(self._status(), "Read")
