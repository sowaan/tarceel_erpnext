// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt

const TARCEEL_ICON = "/assets/tarceel_erpnext/images/tarceel_icon_sm.png";

// Session states where the number is (or can be) linked by scanning a QR.
const QR_SESSION_STATES = ["qr_pending", "logged_out", "connecting", "reconnecting"];

// Active QR poll timers, so a re-render or leaving the page stops the loop.
let qrPollTimers = [];
function stopQrPolling() {
	qrPollTimers.forEach(clearTimeout);
	qrPollTimers = [];
}

frappe.ui.form.on("Tarceel Settings", {
	refresh(frm) {
		// Connect + webhook setup live in the cards (render_intro), not the toolbar.
		frm.add_custom_button(__("Test Connection"), () => test_connection(frm));
		render_intro(frm);
	},
});

function render_intro(frm) {
	inject_intro_styles();
	stopQrPolling(); // any previous QR poll loop is stale now
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
	// saved credentials (401, wrong key/instance id), show the Connect hero
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
			} else if (conn && !conn.ok && QR_SESSION_STATES.includes(conn.session_status)) {
				// Number isn't linked (qr_pending / logged_out / (re)connecting):
				// let the user scan the QR right here instead of opening Tarceel.
				render_qr_card(frm, field, disclosure);
			} else if (conn) {
				field.html(connection_status_card(conn) + (conn.ok ? webhook_card(frm) : "") + disclosure);
				field.$wrapper.find(".tarceel-recheck-btn").on("click", () => test_connection(frm));
				field.$wrapper.find(".tarceel-reconnect-btn").on("click", () => connect_to_tarceel(frm));
				field.$wrapper.find(".tarceel-webhook-btn").on("click", () => configure_webhook(frm));
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
				"Send messages, invoices and alerts from any document. Unofficial, QR-linked integration, not the official WhatsApp Business Platform."
			)}</div>
			<button type="button" class="tarceel-hero-cta tarceel-intro-connect">
				<svg class="tarceel-hero-cta-ic" viewBox="0 0 24 24" width="19" height="19" fill="currentColor" aria-hidden="true"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 004.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0012.04 2zm0 18.15h-.01a8.2 8.2 0 01-4.18-1.15l-.3-.18-3.11.82.83-3.04-.2-.31a8.22 8.22 0 01-1.26-4.38c0-4.54 3.7-8.24 8.24-8.24a8.2 8.2 0 015.82 2.42 8.18 8.18 0 012.41 5.83c0 4.54-3.69 8.23-8.23 8.23zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.25-.64.81-.79.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.13-.14.17-.25.25-.41.08-.17.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.4-.42-.56-.42l-.48-.01c-.17 0-.43.06-.66.31-.23.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.68-1.18.21-.58.21-1.07.14-1.18-.06-.11-.22-.17-.47-.29z"/></svg>
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

	// Open the approval tab now, inside the click gesture, so the browser's popup
	// blocker allows it; we point it at the real URL once the server replies.
	const approval_window = window.open("about:blank", "_blank");

	frappe.call({
		method: "tarceel_erpnext.api.connect_start",
		freeze: true,
		freeze_message: __("Starting Tarceel connection…"),
		callback: (r) => {
			const res = r.message;
			if (!res || !res.flow_id) {
				if (approval_window) approval_window.close();
				frappe.msgprint({
					title: __("Connect failed"),
					message: frappe.utils.escape_html(
						(res && res.error) || __("Could not start the connection. Please try again.")
					),
					indicator: "red",
				});
				return;
			}
			if (approval_window && res.verification_uri) {
				approval_window.location.href = res.verification_uri;
			}
			open_connect_dialog(frm, res, approval_window);
		},
	});
}

function open_connect_dialog(frm, res, approval_window) {
	inject_intro_styles();
	const verify_url = res.verification_uri || "";
	const code = res.user_code || "";
	const interval = Math.max(2, res.interval || 5) * 1000;

	const dialog = new frappe.ui.Dialog({
		title: __("Connect to Tarceel"),
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action_label: __("Reopen Approval Page"),
		primary_action: () => {
			if (!verify_url) return;
			// The approval tab was already opened on click; focus it if it's still
			// around, otherwise open a fresh one.
			if (approval_window && !approval_window.closed) {
				approval_window.focus();
			} else {
				window.open(verify_url, "_blank", "noopener");
			}
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
				<li>${__("The Tarceel approval page opened in a new tab (use the link below if it didn't).")}</li>
				${code ? `<li>${__("Enter the code shown below when asked.")}</li>` : ""}
				<li>${__("Approve. This window updates on its own.")}</li>
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
				// Transient error; keep trying until the flow expires server-side.
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
		.tarceel-wh-card {
			display: flex; align-items: center; justify-content: space-between; gap: 14px;
			padding: 14px 16px; margin: 0 0 14px;
			border: 1px solid var(--border-color, #e5e7eb); border-radius: var(--border-radius-lg, 10px);
			background: var(--card-bg, #fff);
		}
		.tarceel-wh-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
		.tarceel-wh-ic {
			flex: 0 0 auto; width: 36px; height: 36px; border-radius: 9px;
			display: inline-flex; align-items: center; justify-content: center;
			background: rgba(37, 211, 102, 0.12); color: #12b459;
		}
		.tarceel-wh-title { font-weight: 600; }
		.tarceel-wh-sub { font-size: var(--text-sm, 12px); color: var(--text-muted); margin-top: 2px; }
		.tarceel-wh-url { font-size: 11px; color: var(--text-muted); word-break: break-all; margin-top: 3px; }
		.tarceel-wh-right { display: flex; align-items: center; gap: 10px; flex: 0 0 auto; }
		.tarceel-wh-on { display: inline-flex; align-items: center; gap: 5px; color: #12b459; font-weight: 600; font-size: var(--text-sm, 13px); }
		.tarceel-wh-btn {
			flex: 0 0 auto; border: 0; cursor: pointer; color: #fff; font-weight: 600;
			padding: 8px 22px; border-radius: 999px; font-size: var(--text-sm, 13px);
			background: linear-gradient(135deg, #25D366, #12b459);
			box-shadow: 0 4px 12px rgba(37, 211, 102, 0.35);
			animation: tarceel-pulse 2.4s ease-in-out infinite;
			transition: transform 0.12s ease, box-shadow 0.12s ease;
		}
		.tarceel-wh-btn:hover, .tarceel-wh-btn:focus {
			color: #fff; transform: translateY(-1px); outline: none;
			box-shadow: 0 8px 18px rgba(37, 211, 102, 0.5); animation: none;
		}
		.tarceel-wh-btn:disabled { opacity: 0.7; cursor: default; animation: none; box-shadow: none; }
		.tarceel-qr-card {
			text-align: center; padding: 24px 22px; margin: 0 0 14px;
			border: 1px solid rgba(37, 211, 102, 0.25); border-radius: var(--border-radius-lg, 12px);
			background:
				radial-gradient(120% 90% at 50% 0%, rgba(37, 211, 102, 0.08), rgba(37, 211, 102, 0) 60%),
				var(--card-bg, #fff);
		}
		.tarceel-qr-title { font-weight: 700; font-size: 16px; color: var(--heading-color, #1f272e); }
		.tarceel-qr-sub { margin: 6px auto 16px; max-width: 360px; line-height: 1.5; }
		.tarceel-qr-box {
			display: inline-flex; align-items: center; justify-content: center;
			width: 232px; height: 232px; padding: 10px;
			background: #fff; border: 1px solid var(--border-color, #e5e7eb); border-radius: 12px;
		}
		.tarceel-qr-img { width: 100%; height: 100%; object-fit: contain; }
		.tarceel-qr-err { color: #b02a2a; font-size: 12px; padding: 12px; line-height: 1.4; }
		.tarceel-qr-status { margin-top: 12px; }
	`;
	$(`<style id="tarceel-intro-styles">${css}</style>`).appendTo("head");
}

function webhook_card(frm) {
	const configured = !!frm.doc.webhook_url;
	const bell = `<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M12 22a2.5 2.5 0 002.45-2h-4.9A2.5 2.5 0 0012 22zm6.7-6.3-1.2-1.2V11a5.5 5.5 0 0 0-4-5.3V5.2a1.5 1.5 0 0 0-3 0v.5A5.5 5.5 0 0 0 6.5 11v3.5l-1.2 1.2a1 1 0 0 0 .7 1.7h12a1 1 0 0 0 .7-1.7z"/></svg>`;
	const left = `
		<div class="tarceel-wh-left">
			<span class="tarceel-wh-ic">${bell}</span>
			<div>
				<div class="tarceel-wh-title">${__("Delivery status updates")}</div>
				<div class="tarceel-wh-sub">${
					configured
						? __("On. You'll see delivered and read receipts on your messages.")
						: __("Get delivered and read receipts back on the messages you send.")
				}</div>
				${
					configured
						? `<div class="tarceel-wh-url">${frappe.utils.escape_html(frm.doc.webhook_url)}</div>`
						: ""
				}
			</div>
		</div>`;
	const right = configured
		? `<div class="tarceel-wh-right"><span class="tarceel-wh-on">&#10003; ${__(
				"On"
		  )}</span><button class="btn btn-xs btn-default tarceel-webhook-btn">${__(
				"Re-register"
		  )}</button></div>`
		: `<button type="button" class="tarceel-wh-btn tarceel-webhook-btn">${__("Enable")}</button>`;
	return `<div class="tarceel-wh-card">${left}${right}</div>`;
}

function render_qr_card(frm, field, disclosure) {
	stopQrPolling();
	field.html(
		`<div class="tarceel-qr-card">
			<div class="tarceel-qr-title">${__("Link your WhatsApp number")}</div>
			<div class="tarceel-qr-sub text-muted">${__(
				"On your phone open WhatsApp, go to Linked Devices, tap Link a Device, and scan this code."
			)}</div>
			<div class="tarceel-qr-box"><span class="tarceel-connect-spinner"></span></div>
			<div class="tarceel-qr-status text-muted small">${__("Loading QR code…")}</div>
		</div>` + disclosure
	);
	const $box = field.$wrapper.find(".tarceel-qr-box");
	const $status = field.$wrapper.find(".tarceel-qr-status");
	qr_tick(frm, $box, $status);
}

function qr_tick(frm, $box, $status) {
	// Stop if the card is gone (form re-rendered or user navigated away).
	if (!$box.length || !document.body.contains($box[0])) return;

	const later = (ms) => qrPollTimers.push(setTimeout(() => qr_tick(frm, $box, $status), ms));

	frappe.call({
		method: "tarceel_erpnext.api.get_session_qr",
		callback: (r) => {
			if (!document.body.contains($box[0])) return;
			const res = r.message || {};

			if (res.session_status === "connected") {
				frappe.show_alert({ message: __("WhatsApp connected."), indicator: "green" });
				frm.reload_doc();
				return;
			}
			if (res.error) {
				$box.html(`<div class="tarceel-qr-err">${frappe.utils.escape_html(res.error)}</div>`);
				$status.text(__("Retrying…"));
				later(8000);
				return;
			}
			if (res.needs_relink) {
				// Logged out: no pending QR until we request a relink.
				$status.text(__("Your number was logged out."));
				$box.html(
					`<button type="button" class="tarceel-wh-btn tarceel-qr-relink">${__(
						"Generate QR code"
					)}</button>`
				);
				$box.find(".tarceel-qr-relink").on("click", () => {
					$box.html(`<span class="tarceel-connect-spinner"></span>`);
					$status.text(__("Requesting a fresh QR code…"));
					frappe.call({
						method: "tarceel_erpnext.api.relink_session",
						callback: () => later(3000),
						error: () => later(4000),
					});
				});
				return; // wait for the user's click
			}
			if (res.qr_image) {
				$box.html(`<img class="tarceel-qr-img" src="${res.qr_image}" alt="WhatsApp QR code" />`);
				$status.text(__("Waiting for you to scan…"));
			} else {
				$box.html(`<span class="tarceel-connect-spinner"></span>`);
				$status.text(__("Preparing QR code…"));
			}
			later(5000); // QR rotates; refresh and keep watching for a successful scan
		},
		error: () => later(8000),
	});
}

function configure_webhook(frm) {
	if (frm.is_dirty()) {
		frappe.show_alert({ message: __("Save your changes first."), indicator: "orange" });
		return;
	}

	const $btn = frm.get_field("disclosure_html").$wrapper.find(".tarceel-webhook-btn");
	const original = $btn.html();
	$btn.prop("disabled", true).html(__("Enabling…"));

	frappe.call({
		method: "tarceel_erpnext.api.configure_webhook",
		callback: (r) => {
			const res = r.message || {};
			frappe.show_alert({
				message: frappe.utils.escape_html(
					res.message || (res.ok ? __("Delivery updates enabled.") : __("Could not enable delivery updates."))
				),
				indicator: res.ok ? "green" : "red",
			});
			if (res.ok) {
				frm.reload_doc(); // picks up webhook_url/secret and re-renders the card as "On"
			} else {
				$btn.prop("disabled", false).html(original);
			}
		},
	});
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
