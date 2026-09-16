# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Whitelisted (client-callable) server methods for tarceel_erpnext."""

import base64
import mimetypes
import re

import frappe
from frappe import _
from frappe.utils import get_url

from tarceel_erpnext import client
from tarceel_erpnext.client import TarceelError, get_instance_status

# How each Tarceel sessionStatus should read to a Frappe admin, and whether it
# counts as a healthy, send-ready instance.
_SESSION_HINTS = {
	"connected": (True, _("Connected and ready to send.")),
	"connecting": (False, _("The WhatsApp session is still connecting. Try again shortly.")),
	"qr_pending": (False, _("Waiting for a QR scan. Link the number in the Tarceel dashboard.")),
	"reconnecting": (False, _("The WhatsApp session is reconnecting. Try again shortly.")),
	"logged_out": (
		False,
		_("The WhatsApp number is logged out. Re-scan the QR code in the Tarceel dashboard."),
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
		# Keep the cached snapshot (read by the status card/banner) in sync.
		_store_connection_snapshot({"ok": False, "session_status": None, "message": str(exc)})
		return {"ok": False, "message": str(exc)}

	session_status = data.get("sessionStatus")
	instance_status = data.get("status")
	instance_name = data.get("name")

	healthy, hint = _SESSION_HINTS.get(
		session_status,
		(False, _("No WhatsApp session is linked yet. Link a number in the Tarceel dashboard.")),
	)

	if instance_status and instance_status != "active":
		healthy = False
		hint = _("The Tarceel instance is '{0}', not active.").format(instance_status)

	# This is a fresh live check — refresh the snapshot the status card/banner read,
	# so they reflect it immediately instead of a stale (up to 60s) cached value.
	_store_connection_snapshot(
		{"ok": bool(healthy), "session_status": session_status, "message": str(hint)}
	)

	prefix = _("Reached '{0}'.").format(instance_name) if instance_name else _("Reached Tarceel.")

	return {
		"ok": healthy,
		"message": f"{prefix} {hint}",
		"instance_status": instance_status,
		"session_status": session_status,
		"instance_name": instance_name,
	}


@frappe.whitelist()
def get_setup_status():
	"""Setup/connection snapshot for the Notification form banner. Only meaningful
	to users who can access Tarceel Settings — others get {can_manage: False} so no
	banner is shown. Returns {can_manage, configured, connection?}."""
	if not frappe.has_permission("Tarceel Settings", "read"):
		return {"can_manage": False}

	settings = frappe.get_cached_doc("Tarceel Settings")
	has_key = bool(settings.get_password("api_key", raise_exception=False))
	configured = bool(settings.enabled and settings.instance_id and has_key)

	result = {
		"can_manage": True,
		"configured": configured,
		"enabled": bool(settings.enabled),
		"settings_url": "/app/tarceel-settings",
	}
	if configured:
		result["connection"] = _connection_snapshot()
	return result


_CONNECTION_SNAPSHOT_KEY = "tarceel_connection_snapshot"
_CONNECTION_SNAPSHOT_TTL = 30


def _store_connection_snapshot(snapshot):
	frappe.cache().set_value(
		_CONNECTION_SNAPSHOT_KEY, snapshot, expires_in_sec=_CONNECTION_SNAPSHOT_TTL
	)


def _connection_snapshot():
	"""Live instance/session health, cached briefly so opening forms doesn't hit
	Tarceel on every load. Test Connection refreshes this immediately."""
	cached = frappe.cache().get_value(_CONNECTION_SNAPSHOT_KEY)
	if cached is not None:
		return cached

	try:
		data = get_instance_status()
		session_status = data.get("sessionStatus")
		healthy, hint = _SESSION_HINTS.get(
			session_status, (False, _("No WhatsApp session is linked yet."))
		)
		if data.get("status") and data.get("status") != "active":
			healthy = False
			hint = _("The Tarceel instance is '{0}', not active.").format(data.get("status"))
		snapshot = {"ok": bool(healthy), "session_status": session_status, "message": str(hint)}
	except TarceelError as exc:
		snapshot = {"ok": False, "session_status": None, "message": str(exc)}

	_store_connection_snapshot(snapshot)
	return snapshot


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
def send_message(
	recipient,
	message=None,
	reference_doctype=None,
	reference_name=None,
	file_url=None,
	file_urls=None,
	print_format=None,
):
	"""Send one or more WhatsApp messages and log them (Phase 2). Attachments —
	`print_format` (the document rendered to PDF) and any `file_url`/`file_urls`
	(Frappe Files) — each go as their own media message; the typed `message` rides
	as the caption on the first. With no attachment, a plain text message is sent.

	Per-message, individually composed send tied optionally to the source document
	(guardrail #1: never a list blast). A WhatsApp Message Log row is always
	created, so a failed send is recorded as Failed rather than vanishing.
	"""
	# Sending is gated on create access to the log — the WhatsApp Sender role, or
	# System Manager. Keeps sending to the people an admin has authorised.
	if not frappe.has_permission("WhatsApp Message Log", "create"):
		frappe.throw(
			_("You are not permitted to send WhatsApp messages."), frappe.PermissionError
		)

	message = (message or "").strip()
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

	urls = []
	if file_urls:
		urls = frappe.parse_json(file_urls) if isinstance(file_urls, str) else list(file_urls)
	if file_url:
		urls.append(file_url)

	# Ordered list of attachments: the print PDF first, then each file.
	senders = []
	if print_format:
		senders.append(("print", print_format))
	senders.extend(("file", u) for u in urls if u)

	if not senders:
		if not message:
			frappe.throw(_("Message body is required."), TarceelError)
		return send_and_log(number, message, reference_doctype, reference_name)

	# One WhatsApp message per attachment; the text rides as caption on the first.
	results = []
	for idx, (kind, ref) in enumerate(senders):
		caption = message if idx == 0 else None
		if kind == "print":
			results.append(_send_print(number, caption, reference_doctype, reference_name, ref))
		else:
			results.append(_send_file(number, caption, reference_doctype, reference_name, ref))

	if len(results) == 1:
		return results[0]
	return {"ok": all(r["ok"] for r in results), "count": len(results), "results": results}


def _send_print(number, caption, reference_doctype, reference_name, print_format):
	"""Render the source document with the given Print Format and send the PDF.
	The generated PDF is not persisted (nothing to open from the timeline)."""
	if not (reference_doctype and reference_name):
		frappe.throw(_("A source document is required to attach a print format."), TarceelError)
	pdf = frappe.get_print(reference_doctype, reference_name, print_format or None, as_pdf=True)
	return send_media_and_log(
		number,
		"document",
		caption=caption,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		base64=base64.b64encode(pdf).decode(),
		mimetype="application/pdf",
		filename=f"{reference_name}.pdf",
	)


def _media_type_for(mimetype):
	"""Map a mimetype to the Tarceel media `type`."""
	if mimetype.startswith("image/"):
		return "image"
	if mimetype.startswith("video/"):
		return "video"
	if mimetype.startswith("audio/"):
		return "audio"
	return "document"


def _send_file(number, caption, reference_doctype, reference_name, file_url):
	"""Resolve a Frappe File the current user may read, then send it as media."""
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	if not file_doc.has_permission("read"):
		frappe.throw(_("You do not have permission to send that file."), frappe.PermissionError)

	filename = file_doc.file_name or "attachment"
	mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
	content = file_doc.get_content()
	if isinstance(content, str):
		content = content.encode("utf-8")
	encoded = base64.b64encode(content).decode()

	return send_media_and_log(
		number,
		_media_type_for(mimetype),
		caption=caption or None,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
		base64=encoded,
		mimetype=mimetype,
		filename=filename,
		media_url=file_url,
	)


def send_and_log(number, message, reference_doctype=None, reference_name=None):
	"""Send one text via Tarceel and record a WhatsApp Message Log row. No
	permission check or number normalization — callers handling untrusted input
	must gate and normalize first (send_message does). A row is always created, so
	a failed send is recorded as Failed rather than vanishing. Returns
	{ok, name, status, message_id, error}."""
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


def send_media_and_log(
	number,
	media_type,
	caption=None,
	reference_doctype=None,
	reference_name=None,
	url=None,
	base64=None,
	mimetype=None,
	filename=None,
	media_url=None,
):
	"""Send a media message (image/document/…) via Tarceel and record a WhatsApp
	Message Log row. `media_url` is a link to the sent file, so it can be opened
	from the document timeline. No permission check or normalization — callers
	handling untrusted input must gate first."""
	log = frappe.get_doc(
		{
			"doctype": "WhatsApp Message Log",
			"recipient": number,
			"message": caption or f"({media_type})",
			"media_type": media_type,
			"media_filename": filename,
			"media_url": media_url,
			"direction": "Outgoing",
			"status": "Pending",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		}
	)
	log.insert(ignore_permissions=True)

	try:
		response = client.send_media(
			number, media_type, url=url, base64=base64, caption=caption, mimetype=mimetype, filename=filename
		)
		log.status = "Sent"
		log.message_id = response.get("id")
	except TarceelError as exc:
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

	value = resolve_field_path(reference_doctype, reference_name, mapping.phone_field)
	return {"recipient": value}


def resolve_field_path(doctype, name, path):
	"""Resolve a (possibly dotted) field path against a document and return the
	value. A single segment reads a direct field. A dotted path hops through Link
	/ Dynamic Link fields, e.g. on Sales Invoice "contact_person.mobile_no" reads
	the linked Contact's mobile_no. Returns None if any hop is missing/empty or a
	non-link segment is used mid-path."""
	try:
		parts = (path or "").split(".")
		cur_dt, cur_name = doctype, name

		for i, part in enumerate(parts):
			field = frappe.get_meta(cur_dt).get_field(part)
			if not field:
				return None

			value = frappe.db.get_value(cur_dt, cur_name, part)

			# Last segment: return whatever it holds.
			if i == len(parts) - 1:
				return value

			# Intermediate segment: must be a link we can follow.
			if not value:
				return None
			if field.fieldtype == "Link":
				cur_dt = field.options
			elif field.fieldtype == "Dynamic Link":
				cur_dt = frappe.db.get_value(cur_dt, cur_name, field.options)
			else:
				return None
			if not cur_dt:
				return None
			cur_name = value

		return None
	except Exception:
		# A prefill helper must never break the Send dialog; just yield no default.
		return None


@frappe.whitelist()
def get_templates_for(reference_doctype=None):
	"""List enabled WhatsApp Message Templates usable when sending from
	`reference_doctype` — i.e. templates scoped to that DocType plus unscoped
	(global) ones. Returns a list of {name} dicts."""
	or_filters = {"reference_doctype": ["in", [reference_doctype, ""]]} if reference_doctype else None
	filters = {"enabled": 1}
	if not reference_doctype:
		filters["reference_doctype"] = ""

	return frappe.get_all(
		"WhatsApp Message Template",
		filters=filters,
		or_filters=or_filters,
		fields=["name"],
		order_by="template_name asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def render_template(template, reference_doctype, reference_name):
	"""Render a WhatsApp Message Template against a real document and return the
	text, for previewing/prefilling the Send dialog. Uses Frappe's own Jinja
	engine (frappe.render_template). Requires read permission on the document."""
	if not frappe.has_permission(reference_doctype, "read", reference_name):
		frappe.throw(
			_("You do not have permission to read {0} {1}.").format(reference_doctype, reference_name),
			frappe.PermissionError,
		)

	doc = frappe.get_doc(reference_doctype, reference_name)
	tpl = frappe.get_doc("WhatsApp Message Template", template)

	# A scoped template must match the document it's rendered against.
	if tpl.reference_doctype and tpl.reference_doctype != reference_doctype:
		frappe.throw(
			_("Template '{0}' does not apply to {1}.").format(template, reference_doctype),
			TarceelError,
		)

	return {"message": tpl.render(doc), "print_format": tpl.print_format}


@frappe.whitelist()
def configure_webhook():
	"""Register this site's webhook endpoint with Tarceel and store the returned
	signing secret (Phase 4). Re-running issues a fresh secret; we always keep the
	most recent one. Returns {ok, message}."""
	frappe.only_for("System Manager")

	url = get_url("/api/method/tarceel_erpnext.webhook.handle")
	try:
		result = client.set_webhook(url)
	except TarceelError as exc:
		return {"ok": False, "message": str(exc)}

	settings = frappe.get_doc("Tarceel Settings")
	settings.webhook_url = result.get("url") or url
	settings.webhook_secret = result.get("secret")
	settings.save(ignore_permissions=True)

	return {"ok": True, "message": _("Webhook registered at {0}").format(settings.webhook_url)}
