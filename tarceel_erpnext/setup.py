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
	"""Collapse the desk icon to a single "Tarceel" app icon (v16 only).

	`app_title` was once "Tarceel Erpnext" while the workspace is "Tarceel", so
	Frappe generated a "Tarceel Erpnext" app *folder* holding a letter-avatar
	"Tarceel" child (clicking opened a popup instead of the workspace). Now that
	app_title is "Tarceel", it matches the workspace name, so regenerating yields
	one "Tarceel" app icon with the logo that opens the workspace directly. Only
	acts when the old shape is present, so it's a no-op once fixed.
	"""
	if not frappe.db.exists("DocType", "Desktop Icon"):
		return  # not v16

	from frappe.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons

	stale_folder = frappe.db.exists(
		"Desktop Icon", {"label": "Tarceel Erpnext", "app": "tarceel_erpnext"}
	)
	tarceel = frappe.db.get_value("Desktop Icon", "Tarceel", "icon_type")
	if not stale_folder and tarceel == "App":
		return  # already the single app icon

	for name in ["Tarceel Erpnext", "Tarceel"]:
		if frappe.db.exists("Desktop Icon", name):
			frappe.delete_doc("Desktop Icon", name, ignore_permissions=True, force=True)
	create_desktop_icons()
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
