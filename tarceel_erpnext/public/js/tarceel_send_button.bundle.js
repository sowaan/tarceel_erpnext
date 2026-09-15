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
				fieldname: "template",
				fieldtype: "Select",
				label: __("Template (optional)"),
				options: [""],
				description: __("Pick a template to fill the message; you can still edit it before sending."),
				onchange() {
					tarceel_erpnext.apply_template(frm, d);
				},
			},
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
				description: __("Optional when a file is attached (used as the caption)."),
			},
			{
				fieldname: "attachment",
				fieldtype: "Attach",
				label: __("Attach File (optional)"),
			},
		],
		primary_action_label: __("Send"),
		primary_action(values) {
			if (!values.message && !values.attachment) {
				frappe.msgprint(__("Enter a message or attach a file."));
				return;
			}
			d.get_primary_btn().prop("disabled", true);
			frappe.call({
				method: "tarceel_erpnext.api.send_message",
				args: {
					recipient: values.recipient,
					message: values.message,
					reference_doctype: frm.doctype,
					reference_name: frm.docname,
					file_url: values.attachment,
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

	// Load the templates that apply to this document type.
	frappe.call({
		method: "tarceel_erpnext.api.get_templates_for",
		args: { reference_doctype: frm.doctype },
		callback(r) {
			const names = (r.message || []).map((t) => t.name);
			if (names.length) {
				d.set_df_property("template", "options", [""].concat(names));
			} else {
				d.set_df_property("template", "hidden", 1);
			}
		},
	});

	d.show();
};

// Render the selected template against the current document and drop it into
// the message box. Server-side rendering reuses Frappe's Jinja engine.
tarceel_erpnext.apply_template = function (frm, d) {
	const template = d.get_value("template");
	if (!template) return;

	frappe.call({
		method: "tarceel_erpnext.api.render_template",
		args: {
			template: template,
			reference_doctype: frm.doctype,
			reference_name: frm.docname,
		},
		callback(r) {
			if (r.message && r.message.message != null) {
				d.set_value("message", r.message.message);
			}
		},
	});
};
