# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Coverage for the Tarceel "Connect" device-authorization flow.

Offline tests — `requests` is mocked, so they never touch a real Tarceel
instance. They pin down that the flow works, and the two guardrail-3 properties
that matter most: the secret `deviceCode` never leaves the server, and the
`apiKey` (returned once, on approval) lands in the encrypted Password field and
is never echoed back to the caller.
"""

import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from tarceel_erpnext import api

_DEVICE_CODE = "dev_secret_stays_server_side"
_USER_CODE = "WXYZ-1234"
_VERIFY_URI = "https://app.tarceel.com/connect/approve"
_NEW_KEY = "sk_connected_secret_do_not_leak"


def _resp(status_code, payload):
	r = mock.Mock()
	r.ok = 200 <= status_code < 300
	r.status_code = status_code
	r.json.return_value = payload
	return r


def _device_code_resp():
	return _resp(
		200,
		{
			"deviceCode": _DEVICE_CODE,
			"userCode": _USER_CODE,
			"verificationUri": _VERIFY_URI,
			"interval": 5,
		},
	)


class TestTarceelConnect(FrappeTestCase):
	def setUp(self):
		# Simulate the fresh, pre-connect state: base_url set, but no instance_id /
		# api_key yet (they are reqd, so set them via db to avoid mandatory
		# validation and mirror a site that hasn't connected). connect_poll's
		# approval path is what first saves real credentials.
		frappe.db.set_single_value("Tarceel Settings", "base_url", "https://app.tarceel.com")
		frappe.db.set_single_value("Tarceel Settings", "enabled", 0)
		frappe.clear_cache(doctype="Tarceel Settings")

	def _start_flow(self, req):
		req.return_value = _device_code_resp()
		return api.connect_start()

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_connect_start_returns_prompt_but_hides_device_code(self, req):
		res = self._start_flow(req)

		self.assertIn("flow_id", res)
		self.assertEqual(res["user_code"], _USER_CODE)
		self.assertEqual(res["verification_uri"], _VERIFY_URI)
		self.assertEqual(res["interval"], 5)

		# The secret deviceCode must never be in the client-facing payload.
		blob = json.dumps(res)
		self.assertNotIn(_DEVICE_CODE, blob)
		self.assertNotIn("deviceCode", res)
		self.assertNotIn("device_code", res)

		# ...it lives only in server-side cache, keyed by the flow id.
		flow = frappe.cache().get_value(api._connect_flow_key(res["flow_id"]))
		self.assertEqual(flow["device_code"], _DEVICE_CODE)
		self.assertEqual(flow["user"], frappe.session.user)

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_connect_start_sends_app_name(self, req):
		self._start_flow(req)
		_, kwargs = req.call_args
		self.assertEqual(kwargs["json"]["appName"], "Tarceel for ERPNext")
		self.assertTrue(req.call_args[0][1].endswith("/connect/device-code"))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_poll_pending(self, req):
		res = self._start_flow(req)
		req.return_value = _resp(200, {"status": "pending"})
		out = api.connect_poll(res["flow_id"])
		self.assertEqual(out["status"], "pending")
		# Flow is still alive so the next poll can succeed.
		self.assertIsNotNone(frappe.cache().get_value(api._connect_flow_key(res["flow_id"])))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_poll_approved_saves_credentials_without_echoing_key(self, req):
		res = self._start_flow(req)
		req.return_value = _resp(
			200, {"status": "approved", "instanceId": "inst_connected", "apiKey": _NEW_KEY}
		)
		out = api.connect_poll(res["flow_id"])

		self.assertEqual(out["status"], "approved")
		# The API key must never be echoed back to the browser.
		self.assertNotIn(_NEW_KEY, json.dumps(out))
		self.assertNotIn("apiKey", out)

		settings = frappe.get_doc("Tarceel Settings")
		self.assertEqual(settings.instance_id, "inst_connected")
		self.assertEqual(settings.get_password("api_key"), _NEW_KEY)
		self.assertTrue(settings.enabled)

		# A completed flow is forgotten so the code can't be replayed.
		self.assertIsNone(frappe.cache().get_value(api._connect_flow_key(res["flow_id"])))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_poll_denied_forgets_flow(self, req):
		res = self._start_flow(req)
		req.return_value = _resp(200, {"status": "denied"})
		out = api.connect_poll(res["flow_id"])
		self.assertEqual(out["status"], "denied")
		self.assertIsNone(frappe.cache().get_value(api._connect_flow_key(res["flow_id"])))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_poll_approved_missing_credentials_is_error(self, req):
		res = self._start_flow(req)
		req.return_value = _resp(200, {"status": "approved"})  # no instanceId/apiKey
		out = api.connect_poll(res["flow_id"])
		self.assertEqual(out["status"], "error")
		self.assertIsNone(frappe.cache().get_value(api._connect_flow_key(res["flow_id"])))

	def test_poll_unknown_flow_is_expired(self):
		out = api.connect_poll("no-such-flow-id")
		self.assertEqual(out["status"], "expired")

	def test_poll_rejects_a_flow_started_by_another_user(self):
		flow_id = "someone-elses-flow"
		frappe.cache().set_value(
			api._connect_flow_key(flow_id),
			{"device_code": "x", "user": "intruder@example.com", "interval": 5},
			expires_in_sec=600,
		)
		self.assertRaises(frappe.PermissionError, api.connect_poll, flow_id)

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_connect_start_surfaces_error_instead_of_crashing(self, req):
		# Tarceel can return `error` as a bare string, not a {code, message} dict —
		# that must produce a clean {error: ...} result, not an AttributeError.
		req.return_value = _resp(400, {"error": "invalid_request"})
		out = api.connect_start()
		self.assertIn("error", out)
		self.assertNotIn("flow_id", out)
		self.assertIn("invalid_request", out["error"])

	def test_error_message_tolerates_string_and_missing_error(self):
		from tarceel_erpnext import client

		self.assertIn("boom", client._tarceel_error_message(400, {"error": "boom"}))
		self.assertIn("nested", client._tarceel_error_message(400, {"error": {"message": "nested"}}))
		# no `error` key at all must still yield a plain HTTP message, not crash.
		self.assertIn("500", client._tarceel_error_message(500, {}))

	@mock.patch("tarceel_erpnext.client.requests.request")
	def test_poll_surfaces_tarceel_errors_gracefully(self, req):
		res = self._start_flow(req)
		# A bad/expired device code -> Tarceel 4xx -> client raises -> poll returns error.
		req.return_value = _resp(400, {"error": {"code": "invalid_grant", "message": "bad code"}})
		out = api.connect_poll(res["flow_id"])
		self.assertEqual(out["status"], "error")
		self.assertTrue(out["message"])
