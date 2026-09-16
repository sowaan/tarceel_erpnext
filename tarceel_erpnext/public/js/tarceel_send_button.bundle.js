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

tarceel_erpnext.WHATSAPP_ICON = `<svg class="tarceel-wa-ic" viewBox="0 0 24 24" width="13" height="13" style="margin-right:5px;vertical-align:-1px" aria-hidden="true"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.885-9.885 9.885M20.52 3.449C18.24 1.245 15.24 0 12.045 0 5.463 0 .104 5.359.101 11.892c0 2.096.549 4.142 1.595 5.945L0 24l6.335-1.652a11.882 11.882 0 005.71 1.454h.006c6.585 0 11.946-5.359 11.949-11.945a11.821 11.821 0 00-3.48-8.413z"/></svg>`;

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

	const $btn = frm.add_custom_button(__("Send WhatsApp"), function () {
		tarceel_erpnext.open_send_dialog(frm);
	});
	// Prepend the WhatsApp glyph (guard against re-adding on repeated refreshes).
	if ($btn && $btn.find && !$btn.find(".tarceel-wa-ic").length) {
		$btn.prepend(tarceel_erpnext.WHATSAPP_ICON);
	}
};

tarceel_erpnext.open_send_dialog = function (frm) {
	// Fetch the document's existing file attachments first so they can be offered
	// as checkboxes (mirrors Frappe's own email dialog).
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "File",
			filters: { attached_to_doctype: frm.doctype, attached_to_name: frm.docname },
			fields: ["file_url", "file_name"],
			limit_page_length: 0,
		},
		callback(r) {
			tarceel_erpnext.build_send_dialog(frm, r.message || []);
		},
	});
};

tarceel_erpnext.build_send_dialog = function (frm, files) {
	const fields = [
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
			description: __("Optional when something is attached (used as the caption)."),
		},
		{ fieldtype: "Section Break", label: __("Attachments (optional)") },
		{
			fieldname: "print_format",
			fieldtype: "Link",
			label: __("Attach Print Format"),
			options: "Print Format",
			get_query: () => ({ filters: { doc_type: frm.doctype } }),
			description: __("Send this document rendered as a PDF."),
		},
	];

	if (files.length) {
		fields.push({
			fieldname: "attachments",
			fieldtype: "MultiCheck",
			label: __("Existing Attachments"),
			columns: 1,
			options: files.map((f) => ({ label: f.file_name, value: f.file_url })),
		});
	}

	fields.push({
		fieldname: "upload",
		fieldtype: "Attach",
		label: __("Upload a File"),
	});

	const d = new frappe.ui.Dialog({
		title: __("Send WhatsApp"),
		fields: fields,
		primary_action_label: __("Send"),
		primary_action(values) {
			const file_urls = (values.attachments || []).slice();
			if (values.upload) file_urls.push(values.upload);

			if (!values.message && !values.print_format && !file_urls.length) {
				frappe.msgprint(__("Enter a message or attach something."));
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
					file_urls: JSON.stringify(file_urls),
					print_format: values.print_format,
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
							message: frappe.utils.escape_html(
								res.error || __("One or more messages failed — check the WhatsApp Message Log.")
							),
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
			if (!r.message) return;
			if (r.message.message != null) {
				d.set_value("message", r.message.message);
			}
			if (r.message.print_format) {
				d.set_value("print_format", r.message.print_format);
			}
		},
	});
};
