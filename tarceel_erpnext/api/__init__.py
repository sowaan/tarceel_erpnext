# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Whitelisted (client-callable) server methods for tarceel_erpnext."""

import re

import frappe
from frappe import _

from tarceel_erpnext import client
from tarceel_erpnext.client import TarceelError, get_instance_status

# How each Tarceel sessionStatus should read to a Frappe admin, and whether it
# counts as a healthy, send-ready instance.
_SESSION_HINTS = {
	"connected": (True, _("Connected and ready to send.")),
	"connecting": (False, _("The WhatsApp session is still connecting — try again shortly.")),
	"qr_pending": (False, _("Waiting for a QR scan — link the number in the Tarceel dashboard.")),
	"reconnecting": (False, _("The WhatsApp session is reconnecting — try again shortly.")),
	"logged_out": (
		False,
		_("The WhatsApp number is logged out — re-scan the QR code in the Tarceel dashboard."),
	),
}


@frappe.whitelist()
def test_connection():
	"""Test connection button (Phase 1). Calls GET /instances/{id} with the saved
	credentials and returns a plain success/failure result for the form to render.

	Returns a dict: {ok, message, instance_status, session_status, instance_name}.
	Never raises for an ordinary API failure — the message is meant to be shown
	inline, not thrown as a traceback (guardrail: report failure, never silently).
	"""
	frappe.only_for("System Manager")

	try:
		data = get_instance_status()
	except TarceelError as exc:
		return {"ok": False, "message": str(exc)}

	session_status = data.get("sessionStatus")
	instance_status = data.get("status")
	instance_name = data.get("name")

	healthy, hint = _SESSION_HINTS.get(
		session_status,
		(False, _("No WhatsApp session is linked yet — link a number in the Tarceel dashboard.")),
	)

	if instance_status and instance_status != "active":
		healthy = False
		hint = _("The Tarceel instance is '{0}', not active.").format(instance_status)

	prefix = _("Reached '{0}'.").format(instance_name) if instance_name else _("Reached Tarceel.")

	return {
		"ok": healthy,
		"message": f"{prefix} {hint}",
		"instance_status": instance_status,
		"session_status": session_status,
		"instance_name": instance_name,
	}


def normalize_number(raw):
	"""Reduce a user-entered phone number to the bare country-code + number digits
	Tarceel expects (no '+', spaces, dashes, or brackets). Raises on anything that
	can't be a real number."""
	digits = re.sub(r"\D", "", raw or "")
	if len(digits) < 8:
		frappe.throw(
			_("'{0}' is not a valid WhatsApp number. Use the full number with country code.").format(raw),
			TarceelError,
		)
	return digits


@frappe.whitelist()
def send_message(recipient, message, reference_doctype=None, reference_name=None):
	"""Send one WhatsApp text message and log it (Phase 2).

	This is a per-message, individually composed send — one recipient, one body,
	optionally tied to the document it was triggered from (guardrail #1: never a
	list blast). A WhatsApp Message Log row is always created, so a failed send is
	recorded as Failed rather than vanishing.

	Returns {ok, name, status, message_id, error}.
	"""
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Message body is required."), TarceelError)

	number = normalize_number(recipient)

	# Guardrail #1: if this send names a source document, the user must be allowed
	# to see that document — you can't message "about" a record you can't read.
	if reference_doctype and reference_name:
		if not frappe.has_permission(reference_doctype, "read", reference_name):
			frappe.throw(
				_("You do not have permission to send from {0} {1}.").format(
					reference_doctype, reference_name
				),
				frappe.PermissionError,
			)

	log = frappe.get_doc(
		{
			"doctype": "WhatsApp Message Log",
			"recipient": number,
			"message": message,
			"direction": "Outgoing",
			"status": "Pending",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	log.insert(ignore_permissions=True)

	try:
		response = client.send_text(number, message)
		log.status = "Sent"
		log.message_id = response.get("id")
	except TarceelError as exc:
		# Record the failure on the log; don't let the throw's queued message also
		# pop a second, duplicate error dialog on the client.
		log.status = "Failed"
		log.error = str(exc)
		frappe.clear_messages()

	log.save(ignore_permissions=True)

	return {
		"ok": log.status == "Sent",
		"name": log.name,
		"status": log.status,
		"message_id": log.message_id,
		"error": log.error,
	}


@frappe.whitelist()
def get_default_recipient(reference_doctype, reference_name):
	"""Resolve the pre-fill phone number for the Send WhatsApp dialog from the
	per-DocType mapping configured in Tarceel Settings. Returns {recipient}."""
	if not (reference_doctype and reference_name):
		return {"recipient": None}
	if not frappe.has_permission(reference_doctype, "read", reference_name):
		return {"recipient": None}

	settings = frappe.get_cached_doc("Tarceel Settings")
	mapping = next(
		(m for m in settings.phone_field_mappings if m.document_type == reference_doctype),
		None,
	)
	if not mapping:
		return {"recipient": None}

	# Guard against a stale/typo'd fieldname so we never build a bad query.
	if not frappe.get_meta(reference_doctype).get_field(mapping.phone_field):
		return {"recipient": None}

	value = frappe.db.get_value(reference_doctype, reference_name, mapping.phone_field)
	return {"recipient": value}
