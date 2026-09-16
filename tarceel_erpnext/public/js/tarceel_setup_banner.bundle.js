// Copyright (c) 2026, Sowaan and contributors
// For license information, please see license.txt
//
// A dismissible banner nudging admins to set up Tarceel so they can send
// WhatsApp messages / notifications. It renders inside the page content column
// (right of the sidebar), like the Frappe Cloud trial banner — not full width.
// Shown only to users who can access Tarceel Settings, and only while Tarceel
// isn't configured yet.

frappe.provide("tarceel_erpnext");

tarceel_erpnext._banner_status = null; // null = not fetched yet

$(document).on("app_ready", () => tarceel_erpnext.schedule_banner());
if (frappe.router && frappe.router.on) {
	frappe.router.on("change", () => tarceel_erpnext.schedule_banner());
}

tarceel_erpnext.schedule_banner = function () {
	// Let the new page's content column render first, then inject.
	setTimeout(() => tarceel_erpnext.ensure_setup_banner(), 250);
};

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
	if (!s.can_manage || s.configured) return; // only those who can fix it, only if unset
	if (sessionStorage.getItem("tarceel_setup_banner_dismissed")) return;

	// The active page's content column (right of the sidebar).
	const $wrapper = $("#body .page-container:visible .layout-main-section-wrapper").last();
	if (!$wrapper.length) return;
	if ($wrapper.children(".tarceel-setup-banner").length) return; // already on this page

	tarceel_erpnext._inject_banner_styles();

	const $banner = $(`
		<div class="tarceel-setup-banner">
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
		$(".tarceel-setup-banner").remove(); // clear from any cached pages too
	});

	$wrapper.prepend($banner);
};

tarceel_erpnext._inject_banner_styles = function () {
	if (document.getElementById("tarceel-setup-banner-styles")) return;
	const css = `
		.tarceel-setup-banner {
			display: flex; align-items: center; justify-content: space-between; gap: 12px;
			margin: 0 0 15px; padding: 10px 15px;
			font-size: var(--text-md, 13px); line-height: 1.4;
			background: var(--yellow-50, #fffbe6); color: var(--text-color, #383838);
			border: 1px solid var(--yellow-200, #ffe9a8); border-radius: var(--border-radius-md, 6px);
		}
		.tarceel-setup-banner-text { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }
		.tarceel-setup-banner a { font-weight: 600; text-decoration: underline; margin-left: 4px; }
		.tarceel-setup-banner-close { cursor: pointer; font-size: 20px; line-height: 1; padding: 0 4px; opacity: 0.55; }
		.tarceel-setup-banner-close:hover { opacity: 1; }
	`;
	$(`<style id="tarceel-setup-banner-styles">${css}</style>`).appendTo("head");
};
