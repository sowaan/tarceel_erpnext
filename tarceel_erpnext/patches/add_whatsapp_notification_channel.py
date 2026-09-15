# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Add a "WhatsApp" option to Frappe Notification's `channel` field.

Appends to whatever options the framework currently ships (rather than hardcoding
the full list) so a future core addition isn't dropped. Idempotent —
make_property_setter updates the existing Property Setter in place.
"""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	options = (frappe.get_meta("Notification").get_field("channel").options or "").split("\n")
	if "WhatsApp" in options:
		return

	options.append("WhatsApp")
	make_property_setter(
		"Notification",
		"channel",
		"options",
		"\n".join(options),
		"Text",
		validate_fields_for_doctype=False,
	)
