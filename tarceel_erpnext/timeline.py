# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Render WhatsApp Message Log entries into a document's activity timeline.

Wired via the `additional_timeline_content` hook so every sent/received WhatsApp
message linked to a document shows at the bottom of that document with its
delivery status — the way emails appear in the Communication timeline.
"""

import frappe
from frappe import _
from frappe.utils import escape_html, pretty_date

# WhatsApp Message Log status -> Frappe indicator-pill colour.
_STATUS_COLOR = {
	"Pending": "orange",
	"Sent": "blue",
	"Delivered": "green",
	"Read": "green",
	"Failed": "red",
	"Received": "blue",
}


def get_timeline_content(doctype, docname):
	"""Return timeline items for WhatsApp messages linked to (doctype, docname)."""
	if doctype == "WhatsApp Message Log":
		return []

	logs = frappe.get_all(
		"WhatsApp Message Log",
		filters={"reference_doctype": doctype, "reference_name": docname},
		fields=[
			"name",
			"recipient",
			"message",
			"status",
			"direction",
			"media_type",
			"media_filename",
			"creation",
		],
		order_by="creation asc",
	)

	return [
		{"icon": "whatsapp", "is_card": True, "creation": log.creation, "content": _render(log)}
		for log in logs
	]


def _render(log):
	incoming = log.direction == "Incoming"
	verb = _("received from") if incoming else _("sent to")

	pill = ""
	if not incoming and log.status:
		color = _STATUS_COLOR.get(log.status, "gray")
		pill = f'<span class="indicator-pill {color}" style="margin-left:6px">{escape_html(log.status)}</span>'

	link = f"/app/whatsapp-message-log/{log.name}"
	# Cards don't get Frappe's auto timestamp, so add it here (relative, like the
	# rest of the timeline).
	when = f'<span class="text-muted" style="margin-left:6px">· {escape_html(pretty_date(log.creation))}</span>'
	header = (
		f'<span><b>WhatsApp</b> {verb} '
		f'<a href="{link}">{escape_html(log.recipient or "")}</a>{pill}{when}</span>'
	)
	body = (
		f'<div class="text-muted" style="margin-top:4px;white-space:pre-wrap">'
		f'{escape_html(log.message or "")}</div>'
	)
	media = ""
	if log.media_type:
		label = log.media_filename or log.media_type
		media = f'<div class="small text-muted" style="margin-top:2px">📎 {escape_html(label)}</div>'

	return f"<div>{header}{body}{media}</div>"
