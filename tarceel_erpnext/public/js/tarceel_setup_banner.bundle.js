// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt
//
// A dismissible, Desk-wide banner nudging admins to set up Tarceel so they can
// send WhatsApp messages / notifications. Shown only to users who can access
// Tarceel Settings, and only while Tarceel isn't configured yet.

frappe.provide("tarceel_erpnext");

tarceel_erpnext._banner_status = null; // null = not fetched yet

$(document).on("app_ready", () => tarceel_erpnext.ensure_setup_banner());
if (frappe.router && frappe.router.on) {
	frappe.router.on("change", () => tarceel_erpnext.ensure_setup_banner());
}

tarceel_erpnext.ensure_setup_banner = function () {
	if (sessionStorage.getItem("tarceel_setup_banner_dismissed")) return;

	if (tarceel_erpnext._banner_status === null) {
		tarceel_erpnext._banner_status = "loading";
		frappe.call({
			method: "tarceel_erpnext.api.get_setup_status",
			callback(r) {
				tarceel_erpnext._banner_status = r.message || {};
				tarceel_erpnext.render_setup_banner();
			},
		});
	} else if (typeof tarceel_erpnext._banner_status === "object") {
		tarceel_erpnext.render_setup_banner();
	}
};

tarceel_erpnext.render_setup_banner = function () {
	const s = tarceel_erpnext._banner_status;
	if (!s || typeof s !== "object") return;
	// Only show to those who can fix it, and only while unconfigured.
	if (!s.can_manage || s.configured) return;
	if (sessionStorage.getItem("tarceel_setup_banner_dismissed")) return;
	if (document.getElementById("tarceel-setup-banner")) return; // already shown

	tarceel_erpnext._inject_banner_styles();

	const $banner = $(`
		<div id="tarceel-setup-banner" class="tarceel-setup-banner">
			<span class="tarceel-setup-banner-text">
				<span class="tarceel-setup-banner-icon">💬</span>
				${__("Set up Tarceel to send WhatsApp messages and notifications from your documents.")}
				<a href="/app/tarceel-settings">${__("Open Tarceel Settings")}</a>
			</span>
			<span class="tarceel-setup-banner-close" title="${__("Dismiss")}">&times;</span>
		</div>
	`);

	$banner.find(".tarceel-setup-banner-close").on("click", () => {
		sessionStorage.setItem("tarceel_setup_banner_dismissed", "1");
		$banner.remove();
	});

	// Insert as a sibling before #body so it survives route changes (only #body
	// is re-rendered on navigation).
	const $body = $(".main-section > #body").first();
	if ($body.length) {
		$body.before($banner);
	} else {
		$(".main-section").first().prepend($banner);
	}
};

tarceel_erpnext._inject_banner_styles = function () {
	if (document.getElementById("tarceel-setup-banner-styles")) return;
	const css = `
		.tarceel-setup-banner {
			display: flex; align-items: center; justify-content: space-between; gap: 12px;
			padding: 8px 20px; font-size: var(--text-md, 13px);
			background: var(--yellow-50, #fffbe6); color: var(--text-color, #383838);
			border-bottom: 1px solid var(--yellow-200, #ffe9a8);
		}
		.tarceel-setup-banner-text { display: inline-flex; align-items: center; gap: 8px; }
		.tarceel-setup-banner a { font-weight: 600; text-decoration: underline; margin-left: 4px; }
		.tarceel-setup-banner-close { cursor: pointer; font-size: 20px; line-height: 1; padding: 0 6px; opacity: 0.6; }
		.tarceel-setup-banner-close:hover { opacity: 1; }
	`;
	$(`<style id="tarceel-setup-banner-styles">${css}</style>`).appendTo("head");
};
