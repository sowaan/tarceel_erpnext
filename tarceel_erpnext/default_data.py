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
]

# template_name, reference_doctype, message (Jinja rendered against `doc`)
MESSAGE_TEMPLATES = [
	(
		"Invoice Reminder",
		"Sales Invoice",
		"Dear {{ doc.customer_name }}, invoice {{ doc.name }} for "
		"{{ doc.get_formatted('grand_total') }} is due on {{ doc.due_date }}. "
		"Please arrange payment. Thank you.",
	),
	(
		"Order Confirmation",
		"Sales Order",
		"Hi {{ doc.customer_name }}, your order {{ doc.name }} is confirmed. "
		"Total: {{ doc.get_formatted('grand_total') }}.",
	),
	(
		"Delivery Dispatched",
		"Delivery Note",
		"Hi {{ doc.customer_name }}, your order (Delivery Note {{ doc.name }}) "
		"has been dispatched.",
	),
	(
		"Quotation Sent",
		"Quotation",
		"Dear {{ doc.party_name }}, please find quotation {{ doc.name }} for "
		"{{ doc.get_formatted('grand_total') }}, valid till {{ doc.valid_till }}.",
	),
	(
		"Payment Received",
		"Payment Entry",
		"Dear {{ doc.party_name }}, we've received your payment of "
		"{{ doc.get_formatted('paid_amount') }} (ref {{ doc.name }}). Thank you.",
	),
]


def _field_exists(doctype, path):
	"""True if the first segment of `path` is a real field on `doctype`."""
	first = path.split(".", 1)[0]
	return bool(frappe.get_meta(doctype).get_field(first))


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
	for template_name, reference_doctype, message in MESSAGE_TEMPLATES:
		if not frappe.db.exists("DocType", reference_doctype):
			continue
		if frappe.db.exists("WhatsApp Message Template", template_name):
			continue
		frappe.get_doc(
			{
				"doctype": "WhatsApp Message Template",
				"template_name": template_name,
				"reference_doctype": reference_doctype,
				"message": message,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)


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
