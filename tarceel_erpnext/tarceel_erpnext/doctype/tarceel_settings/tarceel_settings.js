// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt

const TARCEEL_WA_LOGO = `
	<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
		<path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.885-9.885 9.885M20.52 3.449C18.24 1.245 15.24 0 12.045 0 5.463 0 .104 5.359.101 11.892c0 2.096.549 4.142 1.595 5.945L0 24l6.335-1.652a11.882 11.882 0 005.71 1.454h.006c6.585 0 11.946-5.359 11.949-11.945a11.821 11.821 0 00-3.48-8.413z"/>
	</svg>`;

frappe.ui.form.on("Tarceel Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), () => test_connection(frm));
		frm.add_custom_button(__("Configure Webhook"), () => configure_webhook(frm));
		render_intro(frm);
	},
});

function render_intro(frm) {
	inject_intro_styles();
	const field = frm.get_field("disclosure_html");
	if (!field) return;

	const configured = frm.doc.instance_id && frm.doc.__onload && frm.doc.__onload.has_api_key;
	if (configured) {
		field.html(
			`<div class="text-muted small" style="margin-bottom:0">${__(
				"Unofficial, QR-linked WhatsApp integration — not the official WhatsApp Business Platform."
			)}</div>`
		);
		return;
	}

	field.html(`
		<div class="tarceel-intro-card">
			<div class="tarceel-intro-left">
				<span class="tarceel-intro-logo">${TARCEEL_WA_LOGO}</span>
				<div>
					<div class="tarceel-intro-title">${__("Connect your Tarceel account")}</div>
					<div class="tarceel-intro-sub text-muted">${__(
						"Send WhatsApp messages and notifications from your documents. Unofficial, QR-linked integration — not the official WhatsApp Business Platform."
					)}</div>
				</div>
			</div>
			<a href="https://app.tarceel.com" target="_blank" rel="noopener"
				class="btn btn-primary btn-sm tarceel-intro-btn">${__("Create Tarceel Account")}</a>
		</div>
	`);
}

function inject_intro_styles() {
	if (document.getElementById("tarceel-intro-styles")) return;
	const css = `
		.tarceel-intro-card {
			display: flex; align-items: center; justify-content: space-between; gap: 16px;
			padding: 14px 16px; margin-bottom: 4px;
			background: var(--bg-color, #fff); border: 1px solid var(--border-color, #e5e7eb);
			border-left: 3px solid #25D366; border-radius: var(--border-radius-md, 8px);
		}
		.tarceel-intro-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
		.tarceel-intro-logo { flex: 0 0 auto; display: inline-flex; }
		.tarceel-intro-title { font-weight: 600; font-size: var(--text-lg, 15px); }
		.tarceel-intro-sub { margin-top: 2px; max-width: 620px; }
		.tarceel-intro-btn { background: #25D366; border-color: #25D366; color: #fff; font-weight: 600; white-space: nowrap; }
		.tarceel-intro-btn:hover, .tarceel-intro-btn:focus { background: #1da851; border-color: #1da851; color: #fff; }
	`;
	$(`<style id="tarceel-intro-styles">${css}</style>`).appendTo("head");
}

function configure_webhook(frm) {
	if (frm.is_dirty()) {
		frappe.msgprint({
			title: __("Save first"),
			message: __("Save your changes before configuring the webhook."),
			indicator: "orange",
		});
		return;
	}

	frappe.confirm(
		__(
			"Register this site's URL with Tarceel to receive delivery-status updates? This issues a new signing secret and replaces any existing one."
		),
		() => {
			frappe.call({
				method: "tarceel_erpnext.api.configure_webhook",
				freeze: true,
				freeze_message: __("Configuring webhook…"),
				callback: (r) => {
					const res = r.message || {};
					frappe.msgprint({
						title: res.ok ? __("Webhook configured") : __("Webhook setup failed"),
						message: frappe.utils.escape_html(res.message || __("No response from server.")),
						indicator: res.ok ? "green" : "red",
					});
					if (res.ok) frm.reload_doc();
				},
			});
		}
	);
}

function test_connection(frm) {
	// The server method reads the *saved* settings, so unsaved edits won't be tested.
	if (frm.is_dirty()) {
		frappe.msgprint({
			title: __("Save first"),
			message: __("Save your changes before testing the connection."),
			indicator: "orange",
		});
		return;
	}

	frappe.call({
		method: "tarceel_erpnext.api.test_connection",
		freeze: true,
		freeze_message: __("Testing connection to Tarceel…"),
		callback: (r) => {
			const res = r.message || {};
			frappe.msgprint({
				title: res.ok ? __("Connection OK") : __("Connection failed"),
				message: frappe.utils.escape_html(res.message || __("No response from server.")),
				indicator: res.ok ? "green" : "red",
			});
		},
	});
}
