# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Phase 1 coverage: the Tarceel REST client and the Test connection method.

These are offline tests — `requests` is mocked, so they never touch a real
Tarceel instance. They pin down request shape, error-code mapping, and the
guardrail-3 property that the API key never leaks into a user-facing error.
The *live* acceptance (real key -> real "connected") is a separate manual step.
"""

from unittest import mock

import requests

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import api, client

_TEST_KEY = "sk_secret_do_not_leak"


def _resp(status_code, payload):
	r = mock.Mock()
	r.ok = 200 <= status_code < 300
	r.status_code = status_code
	r.json.return_value = payload
	return r


class TestTarceelClient(FrappeTestCase):
	def setUp(self):
		settings = frappe.get_single("Tarceel Settings")
		settings.enabled = 1
		settings.base_url = "https://api.example.test/"  # trailing slash -> normalized away
		settings.instance_id = "inst_123"
		settings.api_key = _TEST_KEY
		settings.save()
		frappe.clear_cache(doctype="Tarceel Settings")

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_send_text_builds_request(self, req):
		req.return_value = _resp(200, {"id": "msg_1"})
		out = client.send_text("923001234567", "Hello from Frappe")
		self.assertEqual(out["id"], "msg_1")

		method, url = req.call_args.args
		kwargs = req.call_args.kwargs
		self.assertEqual(method, "POST")
		self.assertEqual(url, "https://api.example.test/instances/inst_123/messages/text")
		self.assertEqual(kwargs["json"], {"to": "923001234567", "text": "Hello from Frappe"})
		self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {_TEST_KEY}")

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_send_media_requires_url_or_base64(self, req):
		with self.assertRaises(client.TarceelError):
			client.send_media("923001234567", "image")
		req.assert_not_called()

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_402_maps_to_billing_message(self, req):
		req.return_value = _resp(402, {"error": {"code": "billing_suspended", "message": "unpaid"}})
		with self.assertRaises(client.TarceelError) as cm:
			client.get_instance_status()
		self.assertIn("plan/payment", str(cm.exception))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_409_maps_to_session_message(self, req):
		req.return_value = _resp(409, {"error": {"code": "not_connected", "message": "no session"}})
		with self.assertRaises(client.TarceelError) as cm:
			client.get_instance_status()
		self.assertIn("QR code", str(cm.exception))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_api_error_never_contains_key(self, req):
		# Even if Tarceel echoed something odd, the key lives only in headers.
		req.return_value = _resp(500, {"error": {"code": "x", "message": "boom"}})
		with self.assertRaises(client.TarceelError) as cm:
			client.get_instance_status()
		self.assertNotIn(_TEST_KEY, str(cm.exception))

	@mock.patch(
		"tarceel_erpnext.client.requests.request",
		side_effect=requests.ConnectionError(f"failed with {_TEST_KEY}"),
	)
	def test_network_error_is_scrubbed(self, req):
		# A raw requests exception could carry anything; we must not re-surface it.
		with self.assertRaises(client.TarceelError) as cm:
			client.get_instance_status()
		self.assertNotIn(_TEST_KEY, str(cm.exception))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_disabled_settings_blocks_send(self, req):
		settings = frappe.get_single("Tarceel Settings")
		settings.enabled = 0
		settings.save()
		frappe.clear_cache(doctype="Tarceel Settings")
		with self.assertRaises(client.TarceelError):
			client.send_text("923001234567", "Hello")
		req.assert_not_called()

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_test_connection_reports_connected(self, req):
		req.return_value = _resp(200, {"name": "Sales", "status": "active", "sessionStatus": "connected"})
		result = api.test_connection()
		self.assertTrue(result["ok"])
		self.assertEqual(result["session_status"], "connected")

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_test_connection_reports_logged_out(self, req):
		req.return_value = _resp(200, {"name": "Sales", "status": "active", "sessionStatus": "logged_out"})
		result = api.test_connection()
		self.assertFalse(result["ok"])
		self.assertIn("QR code", result["message"])
