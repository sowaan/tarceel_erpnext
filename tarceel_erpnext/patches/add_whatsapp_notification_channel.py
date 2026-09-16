# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Add a "WhatsApp" option to Frappe Notification's `channel` field.

Kept for sites that migrate through this patch; the same idempotent logic also
runs via after_install / after_migrate (tarceel_erpnext.setup) so fresh installs
that skip patches still get the option.
"""

from tarceel_erpnext.setup import ensure_whatsapp_notification_channel


def execute():
	ensure_whatsapp_notification_channel()
