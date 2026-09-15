// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("WhatsApp Message Template", {
	refresh: set_print_format_query,
	reference_doctype: set_print_format_query,
});

function set_print_format_query(frm) {
	frm.set_query("print_format", () => ({
		filters: frm.doc.reference_doctype ? { doc_type: frm.doc.reference_doctype } : {},
	}));
}
