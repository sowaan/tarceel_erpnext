// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt
//
// Adds a generic "Send WhatsApp" button to every saved document form, using
// Frappe's global `form-refresh` event so no per-DocType wiring is needed.

frappe.provide("tarceel_erpnext");

// DocTypes where the button would just be noise.
tarceel_erpnext.SEND_BUTTON_EXCLUDE = new Set([
	"Tarceel Settings",
	"WhatsApp Message Log",
	"WhatsApp Phone Field Mapping",
]);

// Bind once, no matter how many times this script is included.
if (!tarceel_erpnext._send_button_bound) {
	tarceel_erpnext._send_button_bound = true;
	$(document).on("form-refresh", function (e, frm) {
		tarceel_erpnext.add_send_button(frm);
	});
}

tarceel_erpnext.add_send_button = function (frm) {
	// Need a saved document so the message has something to link back to.
	if (!frm || frm.is_new()) return;
	if (tarceel_erpnext.SEND_BUTTON_EXCLUDE.has(frm.doctype)) return;

	frm.add_custom_button(__("Send WhatsApp"), function () {
		tarceel_erpnext.open_send_dialog(frm);
	});
};

tarceel_erpnext.open_send_dialog = function (frm) {
	const d = new frappe.ui.Dialog({
		title: __("Send WhatsApp"),
		fields: [
			{
				fieldname: "recipient",
				fieldtype: "Data",
				label: __("Recipient Number"),
				description: __("Full number with country code, e.g. 923001234567"),
				reqd: 1,
			},
			{
				fieldname: "message",
				fieldtype: "Small Text",
				label: __("Message"),
				reqd: 1,
			},
		],
		primary_action_label: __("Send"),
		primary_action(values) {
			d.get_primary_btn().prop("disabled", true);
			frappe.call({
				method: "tarceel_erpnext.api.send_message",
				args: {
					recipient: values.recipient,
					message: values.message,
					reference_doctype: frm.doctype,
					reference_name: frm.docname,
				},
				freeze: true,
				freeze_message: __("Sending WhatsApp message…"),
				callback(r) {
					const res = r.message || {};
					if (res.ok) {
						frappe.show_alert({ message: __("WhatsApp message sent."), indicator: "green" });
						d.hide();
					} else {
						d.get_primary_btn().prop("disabled", false);
						frappe.msgprint({
							title: __("Send failed"),
							message: frappe.utils.escape_html(res.error || __("Unknown error.")),
							indicator: "red",
						});
					}
				},
				error() {
					d.get_primary_btn().prop("disabled", false);
				},
			});
		},
	});

	// Pre-fill the recipient from the per-DocType mapping in Tarceel Settings.
	frappe.call({
		method: "tarceel_erpnext.api.get_default_recipient",
		args: { reference_doctype: frm.doctype, reference_name: frm.docname },
		callback(r) {
			if (r.message && r.message.recipient) {
				d.set_value("recipient", r.message.recipient);
			}
		},
	});

	d.show();
};
