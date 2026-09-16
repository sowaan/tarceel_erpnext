// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt
//
// Adds a Tarceel setup hint + banner to the Notification form when the WhatsApp
// channel is selected. The banner is only fetched/shown for users who can access
// Tarceel Settings.

frappe.ui.form.on("Notification", {
	refresh: tarceel_whatsapp_hint,
	channel: tarceel_whatsapp_hint,
});

function tarceel_whatsapp_hint(frm) {
	if (frm.doc.channel !== "WhatsApp") {
		frm.set_intro("");
		return;
	}

	// Little title/link on the channel field, mirroring the SMS -> SMS Settings hint.
	frm.set_df_property(
		"channel",
		"description",
		__("Sends through Tarceel. Set it up in {0}.", [
			"<a href='/app/tarceel-settings'>Tarceel Settings</a>",
		])
	);

	frappe.call({
		method: "tarceel_erpnext.api.get_setup_status",
		callback(r) {
			const s = r.message || {};
			// Only users who can access Tarceel Settings see the banner.
			if (!s.can_manage) {
				frm.set_intro("");
				return;
			}
			const link = `<a href='${s.settings_url}'>Tarceel Settings</a>`;

			if (!s.configured) {
				frm.set_intro(
					__(
						"Tarceel is not set up yet. Set the Instance API Key and Instance ID in {0} before this notification can send.",
						[link]
					),
					"orange"
				);
			} else if (s.connection && !s.connection.ok) {
				frm.set_intro(
					__("Tarceel connection problem: {0} Check {1}.", [
						frappe.utils.escape_html(s.connection.message || ""),
						link,
					]),
					"red"
				);
			} else {
				frm.set_intro("");
			}
		},
	});
}
