# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""The branded hero banner shown at the top of the Tarceel workspace.

It's a standard Frappe "Custom HTML Block" (rendered in an isolated shadow DOM,
so the CSS below is fully scoped) that the workspace references by name. Seeded
and kept current on install/migrate so the branding ships with the app.
"""

import frappe

HERO_BLOCK_NAME = "Tarceel Hero"

_HERO_HTML = """
<div class="tz-hero">
	<div class="tz-hero-main">
		<div class="tz-badge">
			<img src="/assets/tarceel_erpnext/images/tarceel_icon_sm.png" alt="Tarceel" />
		</div>
		<div class="tz-copy">
			<div class="tz-title">Tarceel <span class="tz-pill">WhatsApp</span></div>
			<div class="tz-sub">
				Send WhatsApp messages, templates, and notifications straight from any
				document, then watch delivery status appear on the timeline. New here?
				Connect your account in Tarceel Settings to get started.
			</div>
		</div>
	</div>
	<a class="tz-cta" href="/app/tarceel-settings">Open Tarceel Settings</a>
</div>
"""

_HERO_STYLE = """
.tz-hero {
	display: flex; align-items: center; justify-content: space-between;
	gap: 24px; flex-wrap: wrap;
	padding: 20px 24px; border-radius: 12px;
	background: linear-gradient(90deg, rgba(37, 211, 102, 0.08), rgba(37, 211, 102, 0.015) 42%, #ffffff 100%);
	border: 1px solid #e6eaed; border-left: 4px solid #25D366;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.tz-hero-main { display: flex; align-items: center; gap: 16px; min-width: 0; }
.tz-badge {
	flex: 0 0 auto; width: 52px; height: 52px; border-radius: 13px;
	background: #f0fbf5; border: 1px solid rgba(37, 211, 102, 0.25);
	display: flex; align-items: center; justify-content: center;
}
.tz-badge img { width: 38px; height: 38px; object-fit: contain; }
.tz-title {
	font-size: 22px; font-weight: 700; color: #1a2a3a; letter-spacing: 0.2px;
	display: flex; align-items: center; gap: 9px;
}
.tz-pill {
	font-size: 10.5px; font-weight: 700; background: #25D366; color: #fff;
	padding: 3px 9px; border-radius: 999px; letter-spacing: 0.5px; text-transform: uppercase;
}
.tz-sub {
	margin-top: 5px; max-width: 620px; line-height: 1.5; color: #5e6c84; font-size: 13px;
}
.tz-cta {
	flex: 0 0 auto;
	background: transparent; color: #0f9d58; font-weight: 600; font-size: 13px;
	padding: 9px 18px; border-radius: 8px; text-decoration: none; white-space: nowrap;
	border: 1.5px solid #25D366; transition: all 0.12s ease;
}
.tz-cta:hover { background: #25D366; color: #ffffff; border-color: #25D366; }
@media (max-width: 640px) {
	.tz-hero { padding: 16px; }
	.tz-title { font-size: 19px; }
	.tz-cta { width: 100%; text-align: center; }
}
"""


def ensure_workspace_hero():
	"""Create or refresh the Tarceel workspace hero block. Idempotent; keeps the
	shipped branding current without disturbing anything else."""
	html = _HERO_HTML.strip()
	style = _HERO_STYLE.strip()

	if frappe.db.exists("Custom HTML Block", HERO_BLOCK_NAME):
		doc = frappe.get_doc("Custom HTML Block", HERO_BLOCK_NAME)
		if (doc.html or "") != html or (doc.style or "") != style or doc.private:
			doc.html = html
			doc.style = style
			doc.private = 0
			doc.save(ignore_permissions=True)
		return

	doc = frappe.get_doc(
		{"doctype": "Custom HTML Block", "html": html, "style": style, "private": 0}
	)
	doc.name = HERO_BLOCK_NAME
	doc.flags.name_set = True  # autoname is "prompt" — use our fixed name
	doc.insert(ignore_permissions=True)
