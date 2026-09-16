# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Render WhatsApp Message Log entries into a document's activity timeline.

Wired via the `additional_timeline_content` hook so every sent/received WhatsApp
message linked to a document shows at the bottom of that document with its
delivery status — the way emails appear in the Communication timeline.
"""

import frappe
from frappe import _
from frappe.utils import escape_html

# WhatsApp Message Log status -> Frappe indicator-pill colour.
_STATUS_COLOR = {
	"Pending": "orange",
	"Sent": "blue",
	"Delivered": "green",
	"Read": "green",
	"Failed": "red",
	"Received": "blue",
}

_WA_ICON = (
	'<svg viewBox="0 0 24 24" width="13" height="13" style="vertical-align:-1px;margin-right:4px" '
	'aria-hidden="true"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273'
	'-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463'
	'-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52'
	'.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579'
	'-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479'
	'0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227'
	'1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272'
	'-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235'
	'-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825'
	'9.825 0 012.893 6.994c-.003 5.45-4.437 9.885-9.885 9.885M20.52 3.449C18.24 1.245 15.24 0 12.045 0'
	'5.463 0 .104 5.359.101 11.892c0 2.096.549 4.142 1.595 5.945L0 24l6.335-1.652a11.882 11.882 0 005.71'
	'1.454h.006c6.585 0 11.946-5.359 11.949-11.945a11.821 11.821 0 00-3.48-8.413z"/></svg>'
)


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
		{"icon": "mobile", "is_card": True, "creation": log.creation, "content": _render(log)}
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
	header = (
		f'<span>{_WA_ICON}<b>WhatsApp</b> {verb} '
		f'<a href="{link}">{escape_html(log.recipient or "")}</a>{pill}</span>'
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
