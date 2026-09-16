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
	padding: 22px 26px; border-radius: 16px;
	background: linear-gradient(120deg, #0b141a 0%, #111b21 45%, #1f6e4d 100%);
	color: #fff; position: relative; overflow: hidden;
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.tz-hero::after {
	content: ""; position: absolute; right: -50px; top: -60px;
	width: 240px; height: 240px; pointer-events: none;
	background: radial-gradient(circle, rgba(37, 211, 102, 0.35), transparent 70%);
}
.tz-hero-main { display: flex; align-items: center; gap: 18px; min-width: 0; z-index: 1; }
.tz-badge {
	flex: 0 0 auto; width: 56px; height: 56px; border-radius: 14px; background: #fff;
	display: flex; align-items: center; justify-content: center;
	box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
}
.tz-badge img { width: 40px; height: 40px; object-fit: contain; }
.tz-title {
	font-size: 24px; font-weight: 700; letter-spacing: 0.2px;
	display: flex; align-items: center; gap: 10px;
}
.tz-pill {
	font-size: 11.5px; font-weight: 600; background: #25D366; color: #04220f;
	padding: 3px 10px; border-radius: 999px; letter-spacing: 0.3px;
}
.tz-sub {
	margin-top: 7px; max-width: 640px; line-height: 1.55;
	color: rgba(255, 255, 255, 0.82); font-size: 13.5px;
}
.tz-cta {
	flex: 0 0 auto; z-index: 1;
	background: #25D366; color: #04220f; font-weight: 600; font-size: 13.5px;
	padding: 10px 18px; border-radius: 10px; text-decoration: none; white-space: nowrap;
	box-shadow: 0 4px 14px rgba(37, 211, 102, 0.35);
	transition: transform 0.12s ease, background 0.12s ease;
}
.tz-cta:hover { background: #1ebe5b; color: #04220f; transform: translateY(-1px); }
@media (max-width: 640px) {
	.tz-hero { padding: 18px; }
	.tz-title { font-size: 20px; }
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
