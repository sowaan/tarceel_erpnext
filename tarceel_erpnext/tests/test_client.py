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
		frappe.cache().delete_value("tarceel_connection_snapshot")

	def test_setup_status_gated_for_non_manager(self):
		with mock.patch("frappe.has_permission", return_value=False):
			result = api.get_setup_status()
		self.assertFalse(result["can_manage"])
		self.assertNotIn("configured", result)

	def test_setup_status_not_configured(self):
		# api_key/instance_id are mandatory, so an unconfigured single can't be saved
		# blank — simulate the fresh state with a stub doc.
		fake = frappe._dict(enabled=1, instance_id=None)
		fake.get_password = lambda *a, **k: None
		with mock.patch("frappe.get_cached_doc", return_value=fake):
			result = api.get_setup_status()
		self.assertTrue(result["can_manage"])
		self.assertFalse(result["configured"])
		self.assertNotIn("connection", result)

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_setup_status_reports_connection(self, req):
		req.return_value = _resp(200, {"name": "X", "status": "active", "sessionStatus": "connected"})
		result = api.get_setup_status()
		self.assertTrue(result["configured"])
		self.assertTrue(result["connection"]["ok"])

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

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_401_raises_auth_error(self, req):
		# A wrong key/instance id -> the auth-specific error, not a plain TarceelError.
		req.return_value = _resp(401, {"error": {"code": "unauthorized", "message": "bad key"}})
		with self.assertRaises(client.TarceelAuthError):
			client.get_instance_status()

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_test_connection_flags_auth_failed_on_401(self, req):
		req.return_value = _resp(401, {})
		result = api.test_connection()
		self.assertFalse(result["ok"])
		self.assertTrue(result["auth_failed"])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_setup_status_flags_auth_failed_on_401(self, req):
		# The form uses this to decide whether to show the Connect hero again.
		req.return_value = _resp(401, {})
		result = api.get_setup_status()
		self.assertTrue(result["configured"])
		self.assertTrue(result["connection"]["auth_failed"])
		self.assertFalse(result["connection"]["ok"])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_setup_status_does_not_queue_blocking_dialog_on_401(self, req):
		# The 401 throw inside get_instance_status must not leak as a server message
		# (which the client would auto-render as a blocking dialog on form load).
		req.return_value = _resp(401, {})
		frappe.clear_messages()
		api.get_setup_status()
		self.assertEqual(frappe.local.message_log, [])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_test_connection_does_not_leave_duplicate_server_message(self, req):
		req.return_value = _resp(401, {})
		frappe.clear_messages()
		api.test_connection()
		self.assertEqual(frappe.local.message_log, [])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_session_qr_connected_returns_no_qr(self, req):
		req.return_value = _resp(200, {"status": "active", "sessionStatus": "connected"})
		out = api.get_session_qr()
		self.assertEqual(out["session_status"], "connected")
		self.assertIsNone(out["qr_image"])
		self.assertFalse(out["needs_relink"])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_session_qr_logged_out_needs_relink_without_fetching_qr(self, req):
		req.return_value = _resp(200, {"status": "active", "sessionStatus": "logged_out"})
		out = api.get_session_qr()
		self.assertTrue(out["needs_relink"])
		self.assertIsNone(out["qr_image"])
		# It must NOT call the /qr endpoint when logged out (no pending QR yet).
		self.assertEqual(req.call_count, 1)

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_session_qr_pending_renders_scannable_image(self, req):
		req.side_effect = [
			_resp(200, {"status": "active", "sessionStatus": "qr_pending"}),
			_resp(200, {"qr": "2@rawpairingstring,abc,def"}),
		]
		out = api.get_session_qr()
		self.assertEqual(out["session_status"], "qr_pending")
		self.assertTrue(out["qr_image"].startswith("data:image/png;base64,"))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_session_qr_refreshes_connection_snapshot(self, req):
		# Polling for the QR must keep the shared snapshot current, so a reload right
		# after connecting shows the connected card instead of looping on a stale one.
		frappe.cache().delete_value("tarceel_connection_snapshot")
		req.return_value = _resp(200, {"status": "active", "sessionStatus": "connected"})
		api.get_session_qr()
		snap = frappe.cache().get_value("tarceel_connection_snapshot")
		self.assertIsNotNone(snap)
		self.assertTrue(snap["ok"])
		self.assertEqual(snap["session_status"], "connected")

	def test_render_qr_data_uri(self):
		import base64 as b64

		# raw pairing string -> a real PNG data URI
		uri = api._render_qr_data_uri("2@rawpairingstring")
		self.assertTrue(uri.startswith("data:image/png;base64,"))
		self.assertEqual(b64.b64decode(uri.split(",", 1)[1])[:8], b"\x89PNG\r\n\x1a\n")
		# an already-rendered data URI is passed through untouched
		passthrough = "data:image/png;base64,QUJD"
		self.assertEqual(api._render_qr_data_uri(passthrough), passthrough)

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_relink_session_ok(self, req):
		req.return_value = _resp(200, {"status": "relink_requested"})
		self.assertTrue(api.relink_session()["ok"])
		_, kwargs = req.call_args
		self.assertTrue(req.call_args[0][1].endswith("/relink"))
		# A bodyless POST must still send a JSON body ({}), or a Fastify server
		# rejects it with FST_ERR_CTP_EMPTY_JSON_BODY.
		self.assertEqual(kwargs["json"], {})

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_session_qr_error_does_not_leak_message(self, req):
		req.return_value = _resp(401, {})
		frappe.clear_messages()
		out = api.get_session_qr()
		self.assertIn("error", out)
		self.assertEqual(frappe.local.message_log, [])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_configure_webhook_error_does_not_leak_message(self, req):
		# A failed webhook registration must not leave a queued (blocking) dialog;
		# the form shows a toast from the returned message instead.
		req.return_value = _resp(500, {"message": "boom"})
		frappe.clear_messages()
		out = api.configure_webhook()
		self.assertFalse(out["ok"])
		self.assertEqual(frappe.local.message_log, [])

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_setup_status_not_auth_failed_on_409(self, req):
		# A session-not-connected (409) is not a credential problem -> no re-link prompt.
		req.return_value = _resp(409, {"error": {"code": "session"}})
		result = api.get_setup_status()
		self.assertFalse(result["connection"]["ok"])
		self.assertFalse(result["connection"].get("auth_failed"))
