// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt

const TARCEEL_ICON = "/assets/tarceel_erpnext/images/tarceel_icon_sm.png";

frappe.ui.form.on("Tarceel Settings", {
	refresh(frm) {
		// "Connect to Tarceel" lives in the hero card (render_intro), not the toolbar.
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
	if (!configured) {
		render_connect_hero(frm, field);
		return;
	}

	// Configured: show the live connection status. But if Tarceel rejected the
	// saved credentials (401 — wrong key/instance id), show the Connect hero
	// again so the user can re-link.
	field.html(
		`<div class="tarceel-conn-card tarceel-conn-card--checking"><div class="tarceel-conn-left"><span class="tarceel-conn-dot"></span><div class="tarceel-conn-title">${__(
			"Checking connection…"
		)}</div></div></div>` + disclosure
	);
	frappe.call({
		method: "tarceel_erpnext.api.get_setup_status",
		callback(r) {
			const s = r.message || {};
			const conn = s.connection;
			if (conn && conn.auth_failed) {
				render_connect_hero(
					frm,
					field,
					__(
						"The saved API Key or Instance ID was rejected by Tarceel (401). Connect again to re-link your WhatsApp instance."
					)
				);
			} else if (conn) {
				field.html(connection_status_card(conn) + disclosure);
				field.$wrapper.find(".tarceel-recheck-btn").on("click", () => test_connection(frm));
				field.$wrapper.find(".tarceel-reconnect-btn").on("click", () => connect_to_tarceel(frm));
			} else {
				field.html(disclosure);
			}
		},
	});
}

function render_connect_hero(frm, field, note) {
	const dot = (n, label) =>
		`<span class="tarceel-stepper-item"><span class="tarceel-stepper-num">${n}</span>${label}</span>`;
	const note_html = note
		? `<div class="tarceel-hero-note">&#9888; ${frappe.utils.escape_html(note)}</div>`
		: "";

	field.html(`
		<div class="tarceel-hero">
			<div class="tarceel-hero-glow"></div>
			${note_html}
			<img src="${TARCEEL_ICON}" alt="Tarceel" class="tarceel-hero-logo" />
			<div class="tarceel-hero-title">${__("Connect WhatsApp to your ERP")}</div>
			<div class="tarceel-hero-sub text-muted">${__(
				"Send messages, invoices and alerts from any document. Unofficial, QR-linked integration — not the official WhatsApp Business Platform."
			)}</div>
			<button type="button" class="tarceel-hero-cta tarceel-intro-connect">
				<span class="tarceel-hero-cta-ic">&#128279;</span>
				<span>${__("Connect to Tarceel")}</span>
				<span class="tarceel-hero-cta-arrow">&rarr;</span>
			</button>
			<div class="tarceel-stepper">
				${dot(1, __("Connect"))}
				<span class="tarceel-stepper-line"></span>
				${dot(2, __("Approve"))}
				<span class="tarceel-stepper-line"></span>
				${dot(3, __("Done"))}
			</div>
			<div class="tarceel-hero-alt text-muted small">
				${__("No account yet?")}
				<a href="https://app.tarceel.com" target="_blank" rel="noopener">${__("Create a Tarceel account")}</a>
			</div>
		</div>
	`);
	field.$wrapper.find(".tarceel-intro-connect").on("click", () => connect_to_tarceel(frm));
}

function connect_to_tarceel(frm) {
	if (frm.is_dirty()) {
		frappe.msgprint({
			title: __("Save first"),
			message: __("Save your changes before connecting to Tarceel."),
			indicator: "orange",
		});
		return;
	}

	frappe.call({
		method: "tarceel_erpnext.api.connect_start",
		freeze: true,
		freeze_message: __("Starting Tarceel connection…"),
		callback: (r) => {
			const res = r.message;
			if (!res || !res.flow_id) {
				frappe.msgprint({
					title: __("Connect failed"),
					message: frappe.utils.escape_html(
						(res && res.error) || __("Could not start the connection. Please try again.")
					),
					indicator: "red",
				});
				return;
			}
			open_connect_dialog(frm, res);
		},
	});
}

function open_connect_dialog(frm, res) {
	inject_intro_styles();
	const verify_url = res.verification_uri || "";
	const code = res.user_code || "";
	const interval = Math.max(2, res.interval || 5) * 1000;

	const dialog = new frappe.ui.Dialog({
		title: __("Connect to Tarceel"),
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action_label: __("Open Approval Page"),
		primary_action: () => {
			if (verify_url) window.open(verify_url, "_blank", "noopener");
		},
	});

	const $body = dialog.fields_dict.body.$wrapper;
	const code_block = code
		? `<div class="tarceel-usercode-label text-muted small">${__("Your confirmation code")}</div>
		   <div class="tarceel-usercode">${frappe.utils.escape_html(code)}</div>`
		: "";
	const link_block = verify_url
		? `<div class="tarceel-verify-link small"><a href="${frappe.utils.escape_html(
				verify_url
		  )}" target="_blank" rel="noopener">${frappe.utils.escape_html(verify_url)}</a></div>`
		: "";

	$body.html(`
		<div class="tarceel-connect-flow">
			<div class="tarceel-dlg-steps">
				<span class="tarceel-dlg-dot tarceel-dlg-done">1</span>
				<span class="tarceel-dlg-seg tarceel-dlg-seg--done"></span>
				<span class="tarceel-dlg-dot tarceel-dlg-active" data-step="2">2</span>
				<span class="tarceel-dlg-seg" data-seg="2"></span>
				<span class="tarceel-dlg-dot" data-step="3">3</span>
			</div>
			<div class="tarceel-dlg-steplabels"><span>${__("Start")}</span><span>${__(
				"Approve"
			)}</span><span>${__("Done")}</span></div>
			<p>${__(
				"Approve this request in your Tarceel account to link your WhatsApp instance automatically."
			)}</p>
			<ol class="tarceel-connect-steps">
				<li>${__("Click <b>Open Approval Page</b> below (or use the link).")}</li>
				${code ? `<li>${__("Enter the code shown below when asked.")}</li>` : ""}
				<li>${__("Approve — this window updates on its own.")}</li>
			</ol>
			${code_block}
			${link_block}
			<div class="tarceel-connect-status tarceel-connect-status--wait">
				<span class="tarceel-connect-spinner"></span>
				<span class="tarceel-connect-status-text">${__("Waiting for approval…")}</span>
			</div>
		</div>
	`);

	let poll_timer = null;
	let stopped = false;
	const stop = () => {
		stopped = true;
		if (poll_timer) {
			clearTimeout(poll_timer);
			poll_timer = null;
		}
	};

	const set_status = (variant, text, retry) => {
		const $s = $body.find(".tarceel-connect-status");
		$s.removeClass(
			"tarceel-connect-status--wait tarceel-connect-status--ok tarceel-connect-status--err"
		).addClass(`tarceel-connect-status--${variant}`);
		const icon = variant === "ok" ? "✓" : variant === "err" ? "!" : "";
		$s.html(
			`${
				variant === "wait"
					? '<span class="tarceel-connect-spinner"></span>'
					: `<span class="tarceel-connect-ic">${icon}</span>`
			}<span class="tarceel-connect-status-text">${frappe.utils.escape_html(text)}</span>` +
				(retry
					? ` <button type="button" class="btn btn-xs btn-default tarceel-connect-retry">${__(
							"Try Again"
					  )}</button>`
					: "")
		);
		if (retry) {
			$s.find(".tarceel-connect-retry").on("click", () => {
				dialog.hide();
				connect_to_tarceel(frm);
			});
		}
	};

	const poll = () => {
		if (stopped) return;
		frappe.call({
			method: "tarceel_erpnext.api.connect_poll",
			args: { flow_id: res.flow_id },
			callback: (r) => {
				if (stopped) return;
				const out = r.message || {};
				if (out.status === "pending") {
					poll_timer = setTimeout(poll, interval);
					return;
				}
				stop();
				if (out.status === "approved") {
					$body.find('[data-step="2"]').removeClass("tarceel-dlg-active").addClass("tarceel-dlg-done");
					$body.find('[data-seg="2"]').addClass("tarceel-dlg-seg--done");
					$body.find('[data-step="3"]').addClass("tarceel-dlg-done");
					set_status("ok", out.message || __("Connected to Tarceel."));
					frappe.show_alert({ message: __("Connected to Tarceel."), indicator: "green" });
					setTimeout(() => {
						dialog.hide();
						frm.reload_doc();
					}, 1200);
				} else {
					set_status("err", out.message || __("Connection was not completed."), true);
				}
			},
			error: () => {
				if (stopped) return;
				// Transient error — keep trying until the flow expires server-side.
				poll_timer = setTimeout(poll, interval);
			},
		});
	};

	dialog.$wrapper.on("hide.bs.modal", stop);
	dialog.show();
	poll_timer = setTimeout(poll, interval);
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
			<div class="tarceel-conn-actions">
				<button class="btn btn-sm tarceel-recheck-btn">${__("Test Connection")}</button>
				<button class="btn btn-sm tarceel-reconnect-btn">${__("Reconnect")}</button>
			</div>
		</div>`;
}

function inject_intro_styles() {
	if (document.getElementById("tarceel-intro-styles")) return;
	const css = `
		.tarceel-hero {
			position: relative; overflow: hidden; text-align: center;
			padding: 34px 26px 26px; margin: 6px 0 22px;
			background:
				radial-gradient(120% 90% at 50% 0%, rgba(37, 211, 102, 0.12), rgba(37, 211, 102, 0) 60%),
				var(--card-bg, #fff);
			border: 1px solid rgba(37, 211, 102, 0.25);
			border-radius: var(--border-radius-lg, 12px);
		}
		.tarceel-hero-glow {
			position: absolute; top: -70px; left: 50%; width: 280px; height: 170px;
			transform: translateX(-50%); pointer-events: none;
			background: radial-gradient(circle, rgba(37, 211, 102, 0.30), rgba(37, 211, 102, 0) 70%);
			filter: blur(6px);
		}
		.tarceel-hero-logo { position: relative; width: 52px; height: 52px; object-fit: contain; margin-bottom: 12px; }
		.tarceel-hero-title { position: relative; font-weight: 700; font-size: 22px; color: var(--heading-color, #1f272e); }
		.tarceel-hero-sub { position: relative; max-width: 520px; margin: 8px auto 22px; line-height: 1.55; }
		.tarceel-hero-cta {
			position: relative; overflow: hidden; border: 0; cursor: pointer;
			display: inline-flex; align-items: center; gap: 10px;
			padding: 13px 30px; font-size: 15px; font-weight: 600; color: #fff;
			border-radius: 999px;
			background: linear-gradient(135deg, #25D366, #12b459);
			box-shadow: 0 6px 18px rgba(37, 211, 102, 0.40);
			animation: tarceel-pulse 2.4s ease-in-out infinite;
			transition: transform 0.12s ease, box-shadow 0.12s ease;
		}
		/* keep label/icon above the moving shine */
		.tarceel-hero-cta > * { position: relative; z-index: 1; }
		/* periodic light sweep so the button clearly reads as an action */
		.tarceel-hero-cta::before {
			content: ""; position: absolute; top: 0; left: -70%; z-index: 0;
			width: 45%; height: 100%; transform: skewX(-18deg);
			background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.5), transparent);
			animation: tarceel-shine 3.2s ease-in-out infinite;
		}
		.tarceel-hero-cta:hover, .tarceel-hero-cta:focus {
			color: #fff; transform: translateY(-2px) scale(1.02); outline: none;
			box-shadow: 0 12px 30px rgba(37, 211, 102, 0.55); animation: none;
		}
		.tarceel-hero-cta-ic { font-size: 16px; }
		.tarceel-hero-cta-arrow { display: inline-block; animation: tarceel-nudge 1.5s ease-in-out infinite; }
		@keyframes tarceel-pulse {
			0%, 100% { box-shadow: 0 6px 18px rgba(37, 211, 102, 0.40); }
			50% { box-shadow: 0 8px 28px rgba(37, 211, 102, 0.66); }
		}
		@keyframes tarceel-shine {
			0% { left: -70%; }
			55%, 100% { left: 130%; }
		}
		@keyframes tarceel-nudge {
			0%, 100% { transform: translateX(0); }
			50% { transform: translateX(4px); }
		}
		.tarceel-stepper {
			position: relative; display: flex; align-items: center; justify-content: center;
			flex-wrap: wrap; gap: 8px; max-width: 470px; margin: 26px auto 2px;
		}
		.tarceel-stepper-item { display: inline-flex; align-items: center; gap: 7px; font-size: var(--text-sm, 12px); color: var(--text-muted); }
		.tarceel-stepper-num {
			flex: 0 0 auto; width: 22px; height: 22px; border-radius: 50%;
			display: inline-flex; align-items: center; justify-content: center;
			background: #25D366; color: #fff; font-size: 11px; font-weight: 700;
		}
		.tarceel-stepper-line { width: 26px; height: 2px; background: rgba(37, 211, 102, 0.35); }
		.tarceel-hero-alt { position: relative; margin-top: 20px; }
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
		.tarceel-intro-alt { margin-top: 14px; }
		.tarceel-connect-flow p { margin-bottom: 10px; }
		.tarceel-connect-steps { margin: 0 0 14px; padding-left: 20px; line-height: 1.7; }
		.tarceel-usercode-label { margin-bottom: 4px; }
		.tarceel-usercode {
			font-family: var(--font-stack-monospace, monospace); font-size: 26px; font-weight: 700;
			letter-spacing: 4px; text-align: center; padding: 12px; margin-bottom: 10px;
			background: var(--gray-50, #f4f5f6); border: 1px dashed var(--border-color, #d1d8dd);
			border-radius: var(--border-radius, 6px); color: #16606b;
		}
		.tarceel-verify-link { word-break: break-all; margin-bottom: 16px; }
		.tarceel-connect-status {
			display: flex; align-items: center; gap: 9px; padding: 11px 14px;
			border-radius: var(--border-radius, 6px); font-size: var(--text-sm, 13px);
			border: 1px solid var(--border-color, #e5e7eb);
		}
		.tarceel-connect-status--wait { background: var(--gray-50, #f4f5f6); }
		.tarceel-connect-status--ok { background: rgba(37, 211, 102, 0.08); border-color: rgba(37, 211, 102, 0.35); }
		.tarceel-connect-status--err { background: var(--red-50, #fff5f5); border-color: #f0a9a9; }
		.tarceel-connect-ic {
			flex: 0 0 auto; width: 18px; height: 18px; border-radius: 50%;
			display: inline-flex; align-items: center; justify-content: center;
			color: #fff; font-size: 12px; font-weight: 700;
		}
		.tarceel-connect-status--ok .tarceel-connect-ic { background: #25D366; }
		.tarceel-connect-status--err .tarceel-connect-ic { background: #d9534f; }
		.tarceel-connect-spinner {
			flex: 0 0 auto; width: 15px; height: 15px; border-radius: 50%;
			border: 2px solid var(--gray-300, #c4cdd5); border-top-color: #25D366;
			animation: tarceel-spin 0.8s linear infinite;
		}
		@keyframes tarceel-spin { to { transform: rotate(360deg); } }
		.tarceel-conn-actions { display: flex; gap: 8px; flex: 0 0 auto; }
		.tarceel-dlg-steps { display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 2px; }
		.tarceel-dlg-dot {
			width: 26px; height: 26px; border-radius: 50%;
			display: inline-flex; align-items: center; justify-content: center;
			font-size: 12px; font-weight: 700;
			background: var(--gray-200, #e2e6e9); color: var(--text-muted, #6b7280);
			transition: background 0.2s ease, box-shadow 0.2s ease;
		}
		.tarceel-dlg-dot.tarceel-dlg-active { background: #25D366; color: #fff; box-shadow: 0 0 0 4px rgba(37, 211, 102, 0.18); }
		.tarceel-dlg-dot.tarceel-dlg-done { background: #12b459; color: #fff; }
		.tarceel-dlg-seg { width: 42px; height: 2px; background: var(--gray-300, #d1d8dd); transition: background 0.2s ease; }
		.tarceel-dlg-seg.tarceel-dlg-seg--done { background: #12b459; }
		.tarceel-dlg-steplabels { display: flex; justify-content: space-between; width: 162px; margin: 6px auto 16px; font-size: 11px; color: var(--text-muted); }
		.tarceel-hero-note {
			position: relative; display: inline-block; max-width: 520px; margin: 0 auto 18px;
			padding: 8px 14px; border-radius: 8px; font-size: var(--text-sm, 13px); line-height: 1.5;
			background: var(--red-50, #fff5f5); border: 1px solid #f0b4b4; color: #b02a2a;
		}
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
