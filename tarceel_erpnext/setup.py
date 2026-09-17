# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Setup steps run on install and every migrate (both idempotent)."""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from tarceel_erpnext.branding import ensure_workspace_hero
from tarceel_erpnext.default_data import seed_default_data


def ensure_whatsapp_notification_channel():
	"""Ensure Frappe's Notification `channel` field offers a "WhatsApp" option.

	Applied via after_install and after_migrate (not only a patch) because a fresh
	`bench install-app` can mark patches as already-run without executing them, so
	the option would otherwise never be added on a new production site.
	"""
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
	frappe.clear_cache(doctype="Notification")


def ensure_tarceel_desktop_icon():
	"""Ensure a single top-level "Tarceel" desk icon that opens the workspace in
	the same tab and shows the logo (v16 only).

	The desk icon must be the *workspace* (a "Link" icon), not an "App" icon: an
	App icon's route is an absolute URL, which the desk opens in a new tab. Prior
	versions produced either a "Tarceel Erpnext" app folder (with a letter-avatar
	child) or a "Tarceel" App icon (opened a new tab); both are converted here to
	the workspace Link icon, with `app` set so the logo renders. Idempotent.
	"""
	if not frappe.db.exists("DocType", "Desktop Icon"):
		return  # not v16

	from frappe.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons

	# Drop the old app folder, and any "Tarceel" that is the wrong (App) type.
	if frappe.db.exists("Desktop Icon", {"label": "Tarceel Erpnext", "app": "tarceel_erpnext"}):
		frappe.delete_doc("Desktop Icon", "Tarceel Erpnext", ignore_permissions=True, force=True)
	current = frappe.db.get_value(
		"Desktop Icon", "Tarceel", ["icon_type", "app", "parent_icon"], as_dict=True
	)
	if current and current.icon_type == "App":
		frappe.delete_doc("Desktop Icon", "Tarceel", ignore_permissions=True, force=True)
		current = None

	if not current:
		create_desktop_icons()  # regenerates the workspace Link icon
		current = frappe.db.get_value(
			"Desktop Icon", "Tarceel", ["icon_type", "app", "parent_icon"], as_dict=True
		)

	# Frappe sets `app_name` (not `app`) on workspace icons, so the logo lookup
	# fails and it falls back to a letter avatar; also detach it from any folder.
	if current:
		changes = {}
		if current.app != "tarceel_erpnext":
			changes["app"] = "tarceel_erpnext"
		if current.parent_icon:
			changes["parent_icon"] = None
		if changes:
			frappe.db.set_value("Desktop Icon", "Tarceel", changes)
			frappe.cache.hdel("desktop_icons", "Administrator")


def after_install():
	ensure_whatsapp_notification_channel()
	ensure_tarceel_desktop_icon()
	ensure_workspace_hero()
	seed_default_data()


def after_migrate():
	ensure_whatsapp_notification_channel()
	ensure_tarceel_desktop_icon()
	ensure_workspace_hero()
	seed_default_data()
