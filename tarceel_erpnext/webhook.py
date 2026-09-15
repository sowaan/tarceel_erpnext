# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Inbound webhook receiver for Tarceel (Phase 4: delivery status).

Tarceel POSTs signed events to /api/method/tarceel_erpnext.webhook.handle. Every
delivery carries an X-Tarceel-Signature header — an HMAC-SHA256 of the *raw*
request body keyed by the webhook secret. We verify that against the exact raw
bytes (re-serialising parsed JSON would change whitespace and break the check)
before trusting anything in the payload.
"""

import hashlib
import hmac
import json

import frappe

# Map Tarceel's lowercase status to the WhatsApp Message Log Select options.
_STATUS_MAP = {
	"pending": "Pending",
	"sent": "Sent",
	"delivered": "Delivered",
	"read": "Read",
	"failed": "Failed",
}

# Monotonic ordering so out-of-order webhooks can't regress a status
# (e.g. a late "delivered" arriving after "read" must not downgrade it).
_STATUS_RANK = {"Pending": 0, "Sent": 1, "Delivered": 2, "Read": 3, "Failed": 4}


def is_valid_signature(secret, raw_body, signature_header):
	"""True if signature_header matches HMAC-SHA256(secret, raw_body). Constant-time."""
	if not secret or not signature_header:
		return False
	expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, signature_header)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def handle():
	"""Entry point for Tarceel webhook deliveries."""
	raw_body = frappe.request.get_data()  # exact raw bytes — do NOT use form_dict
	event = frappe.get_request_header("X-Tarceel-Event")
	signature = frappe.get_request_header("X-Tarceel-Signature")

	secret = _get_webhook_secret()
	if not is_valid_signature(secret, raw_body, signature):
		frappe.local.response["http_status_code"] = 401
		return {"ok": False, "error": "invalid signature"}

	try:
		payload = json.loads(raw_body or b"{}")
	except ValueError:
		frappe.local.response["http_status_code"] = 400
		return {"ok": False, "error": "invalid payload"}

	# Phase 4 handles delivery status. message.received (Phase 6) and
	# session.status are acknowledged but not acted on yet.
	if event == "message.status":
		apply_status_event(payload)

	return {"ok": True}


def _get_webhook_secret():
	settings = frappe.get_cached_doc("Tarceel Settings")
	return settings.get_password("webhook_secret", raise_exception=False)


def apply_status_event(payload):
	"""Update the matching WhatsApp Message Log row from a message.status event.
	Returns the log name if updated, else None. Never raises for ordinary
	no-op cases (unknown id, unknown status, out-of-order)."""
	data = (payload or {}).get("data") or {}
	# We store the id returned by the send call (Tarceel's message UUID). Match on
	# that. Tarceel's fix exposes it either as data.messageId (WAMID stays in
	# data.id) or by making data.id itself the UUID again — prefer messageId, fall
	# back to id, so this works under either shape. See
	# docs/tarceel-webhook-correlation.md.
	message_id = data.get("messageId") or data.get("id")
	new_status = _STATUS_MAP.get(data.get("status"))
	if not message_id or not new_status:
		return None

	current = frappe.db.get_value(
		"WhatsApp Message Log", {"message_id": message_id}, ["name", "status"], as_dict=True
	)
	if not current:
		return None

	# Only advance status; never regress on a late/out-of-order delivery.
	if _STATUS_RANK.get(new_status, 0) <= _STATUS_RANK.get(current.status, -1):
		return current.name

	frappe.db.set_value("WhatsApp Message Log", current.name, "status", new_status)
	return current.name
