# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Native WhatsApp channel for Frappe's Notification (Phase 5).

Frappe's Notification dispatches by channel in a hardcoded if/elif with no plugin
hook, so we subclass the controller (wired via override_doctype_class in hooks)
and handle the extra "WhatsApp" channel. Everything else — event matching,
conditions, recipients UI, scheduling — is inherited unchanged, so a WhatsApp
rule is configured exactly like an Email one.
"""

import frappe
from frappe import _
from frappe.email.doctype.notification.notification import (
	Notification,
	get_info_based_on_role,
)

from tarceel_erpnext import api
from tarceel_erpnext.client import TarceelError


class TarceelNotification(Notification):
	def validate(self):
		super().validate()
		if self.channel == "WhatsApp":
			if not self.message:
				frappe.throw(_("Set a Message for the WhatsApp notification."))
			if not (self.recipients or self.send_to_all_assignees):
				frappe.throw(
					_("Add at least one recipient — a document field/path holding a phone number.")
				)

	def send_notification_by_channel(self, doc, context):
		if self.channel == "WhatsApp":
			try:
				self.send_whatsapp(doc, context)
			except Exception:
				self.log_error("Failed to send WhatsApp Notification")
			# Honour the extra "also create a system notification" toggle, like core.
			if self.send_system_notification:
				self.create_system_notification(doc, context)
			return
		super().send_notification_by_channel(doc, context)

	def send_whatsapp(self, doc, context):
		"""Render the message once and enqueue one send per resolved number. Sends
		are enqueued (after commit) so a slow/failing Tarceel call never blocks or
		breaks the document save that triggered this notification."""
		message = frappe.render_template(self.message, context).strip()
		if not message:
			return

		for number in self.get_whatsapp_recipients(doc, context):
			try:
				normalized = api.normalize_number(number)
			except TarceelError:
				continue  # skip malformed numbers rather than fail the whole rule
			frappe.enqueue(
				"tarceel_erpnext.api.send_and_log",
				enqueue_after_commit=True,
				queue="short",
				number=normalized,
				message=message,
				reference_doctype=doc.doctype,
				reference_name=doc.name,
			)

	def get_whatsapp_recipients(self, doc, context):
		"""Resolve recipient phone numbers from the standard Notification Recipient
		rows. `receiver_by_document_field` is read as a fieldname or dotted path
		(e.g. contact_person.mobile_no); `receiver_by_role` pulls users' mobile_no."""
		numbers = []
		for recipient in self.recipients:
			if recipient.condition and not frappe.safe_eval(recipient.condition, None, context):
				continue

			if recipient.receiver_by_document_field:
				value = api.resolve_field_path(
					doc.doctype, doc.name, recipient.receiver_by_document_field
				)
				if value:
					numbers.append(value)

			if recipient.receiver_by_role:
				for mobiles in get_info_based_on_role(
					recipient.receiver_by_role, "mobile_no", ignore_permissions=True
				):
					numbers.extend(m for m in (mobiles or "").split("\n") if m.strip())

		if self.send_to_all_assignees:
			for user in self._assignees(doc):
				mobile = frappe.db.get_value("User", user, "mobile_no")
				if mobile:
					numbers.append(mobile)

		# De-duplicate, preserve order.
		return list(dict.fromkeys(n for n in numbers if n))

	def _assignees(self, doc):
		assignees = doc.get("_assign")
		return frappe.parse_json(assignees) if assignees else []
