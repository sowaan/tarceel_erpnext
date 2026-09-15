## Tarceel for Frappe (`tarceel_erpnext`)

Send and receive WhatsApp messages from any Frappe / ERPNext document through your own
[Tarceel](https://app.tarceel.com) account — natively, the way Frappe's built-in Email Account and
Notification system already work. Install the app, paste your Tarceel instance API key into
**Tarceel Settings**, and from then on you can message from a document (manually, from a template,
or automatically via a Notification rule) and see delivery status come back without leaving Frappe.

> ### ⚠️ Unofficial WhatsApp integration — please read
>
> Tarceel is an **unofficial**, QR-linked WhatsApp integration. It is **not** the official WhatsApp
> Business Platform / Cloud API, and it is not affiliated with, endorsed by, or supported by
> WhatsApp or Meta. It works by linking a real WhatsApp number via QR code (the same way WhatsApp
> Web does), which carries the risk that the number can be rate-limited or banned by WhatsApp if it
> is used to send unsolicited or bulk messages.
>
> Because of this, `tarceel_erpnext` is deliberately built for **per-document, consented messaging
> only** — every send is tied to a specific Frappe document or an individually composed message.
> It has no bulk-send or contact-list-blast feature by design, and it never bypasses the rate
> limiting and anti-ban safety that the Tarceel service enforces on its side. Use it accordingly.

### What it depends on

This app is a **customer** of the Tarceel WhatsApp API gateway (a Sowaan Limited product) — it
talks to Tarceel over its documented REST API (instance-scoped API key auth) and signed webhooks.
You need an active Tarceel account and a connected instance; this app does not create, host, or
rotate WhatsApp sessions itself.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO
bench --site $YOUR_SITE install-app tarceel_erpnext
```

### Status

Early development. See `CLAUDE.md` in this repo for the phase-by-phase build plan and the current
phase marker. Current phase: **1 — Settings & connectivity**.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please
[install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/tarceel_erpnext
pre-commit install
```

Pre-commit is configured to use ruff, eslint, prettier, and pyupgrade.

### License

MIT
