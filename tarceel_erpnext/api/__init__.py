# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Whitelisted (client-callable) server methods for tarceel_erpnext."""

import frappe
from frappe import _

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
