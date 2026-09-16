// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt

const TARCEEL_ICON = "/assets/tarceel_erpnext/images/tarceel_icon_sm.png";

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

	const disclosure = `<div class="tarceel-disclosure text-muted small"><span class="tarceel-disclosure-ic">&#9432;</span>${__(
		"Unofficial, QR-linked WhatsApp integration. Not the official WhatsApp Business Platform."
	)}</div>`;

	const configured = frm.doc.instance_id && frm.doc.__onload && frm.doc.__onload.has_api_key;
	if (configured) {
		// Always show the live connection status here (connected or not), then the
		// disclosure below it.
		field.html(
			`<div class="tarceel-conn-card tarceel-conn-card--checking"><div class="tarceel-conn-left"><span class="tarceel-conn-dot"></span><div class="tarceel-conn-title">${__(
				"Checking connection…"
			)}</div></div></div>` + disclosure
		);
		frappe.call({
			method: "tarceel_erpnext.api.get_setup_status",
			callback(r) {
				const s = r.message || {};
				if (s.connection) {
					field.html(connection_status_card(s.connection) + disclosure);
					field.$wrapper.find(".tarceel-recheck-btn").on("click", () => test_connection(frm));
				} else {
					field.html(disclosure);
				}
			},
		});
		return;
	}

	const step = (n, text) =>
		`<div class="tarceel-intro-step"><span class="tarceel-step-num">${n}</span><span>${text}</span></div>`;

	field.html(`
		<div class="tarceel-intro-card">
			<div class="tarceel-intro-header">
				<div class="tarceel-intro-left">
					<img src="${TARCEEL_ICON}" alt="Tarceel" class="tarceel-intro-logo" />
					<div>
						<div class="tarceel-intro-title">${__("Connect your Tarceel account")}</div>
						<div class="tarceel-intro-sub text-muted">${__(
							"Send WhatsApp messages and notifications from your documents. Unofficial, QR-linked integration, not the official WhatsApp Business Platform."
						)}</div>
					</div>
				</div>
				<a href="https://app.tarceel.com" target="_blank" rel="noopener"
					class="btn btn-primary btn-sm tarceel-intro-btn">${__("Create Tarceel Account")}</a>
			</div>
			<div class="tarceel-intro-steps">
				${step(1, __("Create a Tarceel account"))}
				${step(2, __("Paste your Instance ID and API Key below"))}
				${step(3, __("Click Test Connection"))}
			</div>
		</div>
	`);
}

function connection_status_card(conn) {
	const ok = !!conn.ok;
	const variant = ok ? "tarceel-conn-card--ok" : "tarceel-conn-card--warn";
	const title = ok ? __("WhatsApp connected") : __("WhatsApp not connected");
	return `
		<div class="tarceel-conn-card ${variant}">
			<div class="tarceel-conn-left">
				<span class="tarceel-conn-dot"></span>
				<div>
					<div class="tarceel-conn-title">${title}</div>
					<div class="tarceel-conn-msg text-muted">${frappe.utils.escape_html(conn.message || "")}</div>
				</div>
			</div>
			<button class="btn btn-sm tarceel-recheck-btn">${__("Test Connection")}</button>
		</div>`;
}

function inject_intro_styles() {
	if (document.getElementById("tarceel-intro-styles")) return;
	const css = `
		.tarceel-intro-card {
			padding: 20px 22px; margin: 6px 0 22px;
			background: rgba(37, 211, 102, 0.05);
			border: 1px solid rgba(37, 211, 102, 0.25); border-left: 3px solid #25D366;
			border-radius: var(--border-radius-lg, 10px);
		}
		.tarceel-intro-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
		.tarceel-intro-left { display: flex; align-items: center; gap: 16px; min-width: 0; }
		.tarceel-intro-logo { flex: 0 0 auto; width: 40px; height: 40px; object-fit: contain; }
		.tarceel-intro-title { font-weight: 600; font-size: var(--text-xl, 16px); }
		.tarceel-intro-sub { margin-top: 3px; max-width: 640px; line-height: 1.5; }
		.tarceel-intro-btn { background: #25D366; border-color: #25D366; color: #fff; font-weight: 600; white-space: nowrap; }
		.tarceel-intro-btn:hover, .tarceel-intro-btn:focus { background: #1da851; border-color: #1da851; color: #fff; }
		.tarceel-intro-steps {
			display: flex; flex-wrap: wrap; gap: 10px 28px;
			margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(37, 211, 102, 0.2);
		}
		.tarceel-intro-step { display: inline-flex; align-items: center; gap: 8px; font-size: var(--text-sm, 12px); }
		.tarceel-step-num {
			flex: 0 0 auto; width: 21px; height: 21px; border-radius: 50%;
			display: inline-flex; align-items: center; justify-content: center;
			background: #25D366; color: #fff; font-size: 11px; font-weight: 600;
		}
		.tarceel-conn-card {
			display: flex; align-items: center; justify-content: space-between; gap: 16px;
			padding: 14px 16px; margin: 4px 0 14px; border-radius: var(--border-radius-lg, 10px);
			border: 1px solid var(--border-color, #e5e7eb); border-left: 3px solid #ccc;
		}
		.tarceel-conn-card--ok { background: rgba(37, 211, 102, 0.06); border-color: rgba(37, 211, 102, 0.3); border-left-color: #25D366; }
		.tarceel-conn-card--warn { background: var(--yellow-50, #fff8e6); border-color: #f0d48a; border-left-color: #e8a33d; }
		.tarceel-conn-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
		.tarceel-conn-dot { flex: 0 0 auto; width: 10px; height: 10px; border-radius: 50%; background: #b7bcc4; }
		.tarceel-conn-card--ok .tarceel-conn-dot { background: #25D366; }
		.tarceel-conn-card--warn .tarceel-conn-dot { background: #e8a33d; }
		.tarceel-conn-title { font-weight: 600; }
		.tarceel-conn-msg { margin-top: 2px; }
		.tarceel-disclosure { display: flex; align-items: center; gap: 6px; margin: 6px 0 22px; }
		.tarceel-disclosure-ic { opacity: 0.55; font-size: 13px; }
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
			// test_connection just refreshed the cached snapshot; re-render the
			// status card so it reflects the live result immediately.
			render_intro(frm);
		},
	});
}
