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


def ensure_tarceel_desktop_icon_app():
	"""Set `app` on the Tarceel workspace's Desktop Icon (v16 only).

	v16 renders the workspace's sidebar-header icon from
	public/icons/desktop_icons/<variant>/tarceel.svg, but only when the Desktop
	Icon record has its `app` set. It can be left null (e.g. the record was synced
	before the workspace's app field existed), which falls back to a letter-avatar.
	"""
	if not frappe.db.exists("DocType", "Desktop Icon"):
		return  # not v16
	for name in frappe.get_all(
		"Desktop Icon", filters={"label": "Tarceel", "app": ["in", ["", None]]}, pluck="name"
	):
		frappe.db.set_value("Desktop Icon", name, "app", "tarceel_erpnext")
		frappe.cache.hdel("desktop_icons", "Administrator")


def after_install():
	ensure_whatsapp_notification_channel()
	ensure_tarceel_desktop_icon_app()
	ensure_workspace_hero()
	seed_default_data()


def after_migrate():
	ensure_whatsapp_notification_channel()
	ensure_tarceel_desktop_icon_app()
	ensure_workspace_hero()
	seed_default_data()
