# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Native WhatsApp channel for Frappe's Notification (Phase 5).

Frappe's Notification dispatches by channel in a hardcoded if/elif with no plugin
hook, so we subclass the controller (wired via override_doctype_class in hooks)
and handle the extra "WhatsApp" channel. Everything else — event matching,
conditions, recipients UI, scheduling — is inherited unchanged, so a WhatsApp
rule is configured exactly like an Email one.
"""

import base64

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
		"""Render the message and enqueue delivery. When Attach Print is set, the
		document's print format is rendered to a PDF and sent as a document with the
		message as its caption (mirrors email notifications' Attach Print). Delivery
		is enqueued (after commit) so a slow/failing send or PDF render never blocks
		or breaks the document save that triggered this notification."""
		# self.message is admin-authored Jinja on the Notification (configuring a
		# Notification requires System Manager), the same trusted-author model as
		# Frappe's own email notifications, which likewise render self.message.
		message = frappe.render_template(self.message, context).strip()  # nosemgrep

		numbers = []
		for number in self.get_whatsapp_recipients(doc, context):
			try:
				numbers.append(api.normalize_number(number))
			except TarceelError:
				continue  # skip malformed numbers rather than fail the whole rule
		if not numbers:
			return

		attach_pdf = bool(self.attach_print)
		if not message and not attach_pdf:
			return

		frappe.enqueue(
			"tarceel_erpnext.overrides.notification.deliver",
			enqueue_after_commit=True,
			queue="long" if attach_pdf else "short",
			timeout=600 if attach_pdf else 300,
			numbers=numbers,
			message=message,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
			attach_pdf=attach_pdf,
			print_format=self.print_format or None,
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


def deliver(numbers, message, reference_doctype, reference_name, attach_pdf=False, print_format=None):
	"""Background worker for a WhatsApp notification. Renders the print PDF once (if
	Attach Print was set) and sends to each recipient — as a document with the
	message as caption when attaching, else as plain text."""
	pdf_base64 = None
	filename = None
	if attach_pdf:
		pdf = frappe.get_print(reference_doctype, reference_name, print_format, as_pdf=True)
		pdf_base64 = base64.b64encode(pdf).decode()
		filename = f"{reference_name}.pdf"

	for number in numbers:
		if pdf_base64:
			api.send_media_and_log(
				number,
				"document",
				caption=message,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
				base64=pdf_base64,
				mimetype="application/pdf",
				filename=filename,
			)
		else:
			api.send_and_log(number, message, reference_doctype, reference_name)
