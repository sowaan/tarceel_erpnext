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

	// Don't nag on the Tarceel Settings page itself — the user is already there.
	const route = (frappe.get_route() || []).join("/").toLowerCase();
	if (route.includes("tarceel settings") || route.includes("tarceel-settings")) return;

	// The active page's content column (right of the sidebar).
	const $wrapper = $("#body .page-container:visible .layout-main-section-wrapper").last();
	if (!$wrapper.length) return;
	if ($wrapper.children(".tarceel-setup-banner").length) return; // already on this page

	tarceel_erpnext._inject_banner_styles();

	const whatsapp_icon = `
		<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
			<path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.885-9.885 9.885M20.52 3.449C18.24 1.245 15.24 0 12.045 0 5.463 0 .104 5.359.101 11.892c0 2.096.549 4.142 1.595 5.945L0 24l6.335-1.652a11.882 11.882 0 005.71 1.454h.006c6.585 0 11.946-5.359 11.949-11.945a11.821 11.821 0 00-3.48-8.413z"/>
		</svg>`;

	const $banner = $(`
		<div class="tarceel-setup-banner">
			<span class="tarceel-setup-banner-left">
				<span class="tarceel-setup-banner-icon">${whatsapp_icon}</span>
				<span class="tarceel-setup-banner-text">${__(
					"Set up Tarceel to send WhatsApp messages and notifications from your documents."
				)}</span>
			</span>
			<span class="tarceel-setup-banner-actions">
				<button class="btn btn-sm tarceel-setup-btn">${__("Setup WhatsApp")}</button>
				<span class="tarceel-setup-banner-close" title="${__("Dismiss")}">&times;</span>
			</span>
		</div>
	`);

	$banner.find(".tarceel-setup-btn").on("click", () => {
		frappe.set_route("Form", "Tarceel Settings");
	});

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
			display: flex; align-items: center; justify-content: space-between; gap: 16px;
			margin: 0 0 15px; padding: 10px 14px;
			font-size: var(--text-md, 13px); line-height: 1.4;
			background: var(--bg-color, #fff); color: var(--text-color, #383838);
			border: 1px solid var(--border-color, #e5e7eb);
			border-left: 3px solid #25D366;
			border-radius: var(--border-radius-md, 6px);
			box-shadow: var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.04));
		}
		.tarceel-setup-banner-left { display: inline-flex; align-items: center; gap: 10px; min-width: 0; }
		.tarceel-setup-banner-icon { flex: 0 0 auto; display: inline-flex; }
		.tarceel-setup-banner-text { font-weight: 500; }
		.tarceel-setup-banner-actions { display: inline-flex; align-items: center; gap: 10px; flex: 0 0 auto; }
		.tarceel-setup-btn {
			background: #25D366; border-color: #25D366; color: #fff; font-weight: 600; white-space: nowrap;
		}
		.tarceel-setup-btn:hover, .tarceel-setup-btn:focus { background: #1da851; border-color: #1da851; color: #fff; }
		.tarceel-setup-banner-close { cursor: pointer; font-size: 20px; line-height: 1; padding: 0 2px; opacity: 0.5; }
		.tarceel-setup-banner-close:hover { opacity: 1; }
	`;
	$(`<style id="tarceel-setup-banner-styles">${css}</style>`).appendTo("head");
};
