# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""One-time, ERPNext-only starter data to make onboarding easier.

On a site that has ERPNext installed, seed a set of sensible phone-field
mappings and a few ready-to-use WhatsApp message templates for common sales
documents. This runs from after_install / after_migrate but only once — tracked
by the `default_data_seeded` flag on Tarceel Settings — so anything the customer
edits or deletes afterwards is never re-created.

Everything here is guarded: a mapping/template is skipped if its DocType (or the
phone field it points at) doesn't exist on this ERPNext version, and nothing
overwrites a mapping/template the customer already has.
"""

import frappe

# DocType -> phone-number path (dotted paths resolve through link/dynamic-link
# fields, e.g. Payment Entry's `party` -> the party's mobile_no).
PHONE_FIELD_MAPPINGS = [
	("Sales Invoice", "contact_mobile"),
	("Sales Order", "contact_mobile"),
	("Delivery Note", "contact_mobile"),
	("Quotation", "contact_mobile"),
	("POS Invoice", "contact_mobile"),
	("Purchase Order", "contact_mobile"),
	("Payment Entry", "party.mobile_no"),
	("Customer", "mobile_no"),
	("Supplier", "mobile_no"),
	("Lead", "mobile_no"),
	("Contact", "mobile_no"),
	("Employee", "cell_number"),
]

# (template_name, reference_doctype, message, attach_pdf). Message is Jinja
# rendered against `doc`. When attach_pdf is True, the template's Attach Print
# Format is auto-filled at seed time with a real print format for that DocType
# (so the document PDF rides along with the message).
MESSAGE_TEMPLATES = [
	(
		"Invoice Reminder",
		"Sales Invoice",
		"Dear {{ doc.customer_name }}, invoice {{ doc.name }} for "
		"{{ doc.get_formatted('grand_total') }} is due on {{ doc.due_date }}. "
		"Please arrange payment. Thank you.",
		False,
	),
	(
		"Order Confirmation",
		"Sales Order",
		"Hi {{ doc.customer_name }}, your order {{ doc.name }} is confirmed. "
		"Total: {{ doc.get_formatted('grand_total') }}.",
		False,
	),
	(
		"Delivery Dispatched",
		"Delivery Note",
		"Hi {{ doc.customer_name }}, your order (Delivery Note {{ doc.name }}) "
		"has been dispatched.",
		False,
	),
	(
		"Quotation Sent",
		"Quotation",
		"Dear {{ doc.party_name }}, please find quotation {{ doc.name }} for "
		"{{ doc.get_formatted('grand_total') }}, valid till {{ doc.valid_till }}.",
		False,
	),
	(
		"Payment Received",
		"Payment Entry",
		"Dear {{ doc.party_name }}, we've received your payment of "
		"{{ doc.get_formatted('paid_amount') }} (ref {{ doc.name }}). Thank you.",
		False,
	),
	(
		"Overdue Payment Reminder",
		"Sales Invoice",
		"Dear {{ doc.customer_name }}, invoice {{ doc.name }} was due on "
		"{{ doc.due_date }} and shows an outstanding balance of "
		"{{ doc.get_formatted('outstanding_amount') }}. Kindly arrange payment "
		"at your earliest convenience.",
		False,
	),
	(
		"Invoice Sent",
		"Sales Invoice",
		"Dear {{ doc.customer_name }}, please find invoice {{ doc.name }} for "
		"{{ doc.get_formatted('grand_total') }}. Thank you for your business.",
		True,
	),
	(
		"POS Sale Receipt",
		"POS Invoice",
		"Thank you for your purchase! Receipt {{ doc.name }}, total "
		"{{ doc.get_formatted('grand_total') }}.",
		False,
	),
	(
		"Purchase Order to Supplier",
		"Purchase Order",
		"Dear {{ doc.supplier_name }}, please find our purchase order {{ doc.name }} "
		"for {{ doc.get_formatted('grand_total') }}. Requested delivery by "
		"{{ doc.schedule_date }}.",
		True,
	),
	(
		"Lead Follow-up",
		"Lead",
		"Hi {{ doc.lead_name }}, thank you for your interest"
		"{% if doc.company_name %} on behalf of {{ doc.company_name }}{% endif %}. "
		"Our team will reach out to you shortly.",
		False,
	),
	(
		"Opportunity Follow-up",
		"Opportunity",
		"Hi {{ doc.party_name }}, just following up on opportunity {{ doc.name }}. "
		"Happy to answer any questions.",
		False,
	),
	(
		"Support Ticket Received",
		"Issue",
		"Hi, we've received your request (ticket {{ doc.name }}: {{ doc.subject }}) "
		"and will get back to you soon.",
		False,
	),
	(
		"Support Ticket Resolved",
		"Issue",
		"Hi, your ticket {{ doc.name }} has been marked resolved. Please let us "
		"know if anything's still outstanding.",
		False,
	),
	(
		"Leave Approved",
		"Leave Application",
		"Hi {{ doc.employee_name }}, your {{ doc.leave_type }} leave from "
		"{{ doc.from_date }} to {{ doc.to_date }} has been approved.",
		False,
	),
	(
		"Payslip Ready",
		"Salary Slip",
		"Hi {{ doc.employee_name }}, your payslip for {{ doc.start_date }} "
		"– {{ doc.end_date }} is ready.",
		True,
	),
]


def _field_exists(doctype, path):
	"""True if the first segment of `path` is a real field on `doctype`."""
	first = path.split(".", 1)[0]
	return bool(frappe.get_meta(doctype).get_field(first))


def _resolve_print_format(doctype):
	"""A real Print Format name for `doctype`, or None. Prefer the DocType's
	default; otherwise a customer-facing "print"/"standard" format; otherwise the
	first enabled one. Never returns the built-in "Standard" (not a Print Format
	record, so it can't be a valid Link value)."""
	default = frappe.get_meta(doctype).default_print_format
	if default and frappe.db.exists("Print Format", default):
		return default
	names = frappe.get_all(
		"Print Format",
		filters={"doc_type": doctype, "disabled": 0},
		order_by="creation asc",
		pluck="name",
	)
	if not names:
		return None
	# No site default set — prefer a customer-facing format over niche ones
	# (auditing, drop-ship) that can happen to sort first.
	preferred = [n for n in names if any(w in n.lower() for w in ("standard", "print"))]
	return preferred[0] if preferred else names[0]


def seed_default_data():
	"""Seed ERPNext starter mappings/templates once. Idempotent and safe to
	call on every migrate."""
	if "erpnext" not in frappe.get_installed_apps():
		return  # default data is ERPNext-specific
	if frappe.db.get_single_value("Tarceel Settings", "default_data_seeded"):
		return  # already done — respect the customer's later edits/deletions

	_seed_templates()
	_seed_phone_mappings_and_flag()
	frappe.db.commit()


def _seed_templates():
	for template_name, reference_doctype, message, attach_pdf in MESSAGE_TEMPLATES:
		if not frappe.db.exists("DocType", reference_doctype):
			continue
		if frappe.db.exists("WhatsApp Message Template", template_name):
			continue
		values = {
			"doctype": "WhatsApp Message Template",
			"template_name": template_name,
			"reference_doctype": reference_doctype,
			"message": message,
			"enabled": 1,
		}
		if attach_pdf:
			print_format = _resolve_print_format(reference_doctype)
			if print_format:
				values["print_format"] = print_format
		frappe.get_doc(values).insert(ignore_permissions=True)


def _seed_phone_mappings_and_flag():
	settings = frappe.get_single("Tarceel Settings")
	existing = {m.document_type for m in settings.phone_field_mappings}
	for doctype, phone_field in PHONE_FIELD_MAPPINGS:
		if doctype in existing:
			continue
		if not frappe.db.exists("DocType", doctype) or not _field_exists(doctype, phone_field):
			continue
		settings.append("phone_field_mappings", {"document_type": doctype, "phone_field": phone_field})

	settings.default_data_seeded = 1
	# instance_id / api_key are mandatory but empty on a fresh install — this seed
	# runs before the admin has entered credentials, so skip mandatory validation.
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
