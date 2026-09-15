# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Phase 5 coverage: the native WhatsApp channel on Frappe's Notification.

Recipient resolution, rendering, and enqueue behaviour are tested directly (no
network, no worker). The live acceptance (a configured rule fires on a real
submitted document and actually sends) is a separate manual step.
"""

from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase


def _make_notification(name, **overrides):
	if frappe.db.exists("Notification", name):
		frappe.delete_doc("Notification", name, force=True)
	values = {
		"doctype": "Notification",
		"__newname": name,
		"subject": "WA",
		"document_type": "ToDo",
		"event": "New",
		"channel": "WhatsApp",
		"message": "Hi about {{ doc.description }}",
		"enabled": 1,
		"recipients": [{"receiver_by_document_field": "allocated_to.mobile_no"}],
	}
	values.update(overrides)
	return frappe.get_doc(values).insert()


class TestWhatsAppNotification(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("User", "Administrator", "mobile_no", "923001110000")
		self.todo = frappe.get_doc(
			{"doctype": "ToDo", "description": "Ship it", "allocated_to": "Administrator"}
		).insert()

	def test_controller_is_overridden(self):
		notif = _make_notification("TAR Test WA Basic")
		self.assertEqual(notif.__class__.__name__, "TarceelNotification")

	def test_recipients_resolved_via_dotted_path(self):
		notif = _make_notification("TAR Test WA Recips")
		nums = notif.get_whatsapp_recipients(self.todo, {"doc": self.todo})
		self.assertEqual(nums, ["923001110000"])

	def test_recipients_deduped(self):
		notif = _make_notification(
			"TAR Test WA Dedup",
			recipients=[
				{"receiver_by_document_field": "allocated_to.mobile_no"},
				{"receiver_by_document_field": "allocated_to.mobile_no"},
			],
		)
		nums = notif.get_whatsapp_recipients(self.todo, {"doc": self.todo})
		self.assertEqual(nums, ["923001110000"])

	def test_send_renders_and_enqueues(self):
		notif = _make_notification("TAR Test WA Send")
		with mock.patch("frappe.enqueue") as enq:
			notif.send_whatsapp(self.todo, {"doc": self.todo})
		self.assertTrue(enq.called)
		self.assertEqual(enq.call_args.args[0], "tarceel_erpnext.api.send_and_log")
		kw = enq.call_args.kwargs
		self.assertEqual(kw["number"], "923001110000")
		self.assertEqual(kw["message"], "Hi about Ship it")
		self.assertEqual(kw["reference_doctype"], "ToDo")
		self.assertEqual(kw["reference_name"], self.todo.name)

	def test_no_recipient_number_enqueues_nothing(self):
		# allocated_to has no mobile -> nothing to send.
		frappe.db.set_value("User", "Administrator", "mobile_no", "")
		notif = _make_notification("TAR Test WA Empty")
		with mock.patch("frappe.enqueue") as enq:
			notif.send_whatsapp(self.todo, {"doc": self.todo})
		self.assertFalse(enq.called)

	def test_validate_requires_message(self):
		with self.assertRaises(frappe.ValidationError):
			_make_notification("TAR Test WA NoMsg", message="")

	def test_validate_requires_recipient(self):
		with self.assertRaises(frappe.ValidationError):
			_make_notification("TAR Test WA NoRecip", recipients=[])

	def test_other_channels_unaffected(self):
		# An Email notification still validates/saves through the subclass.
		notif = _make_notification(
			"TAR Test Email",
			channel="Email",
			recipients=[{"receiver_by_document_field": "allocated_to"}],
		)
		self.assertEqual(notif.channel, "Email")
