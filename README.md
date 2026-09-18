<div align="center">
  <img src="tarceel_erpnext/public/images/tarceel_icon_sm.png" alt="Tarceel" width="96" height="96" />
  <h1>Tarceel for Frappe / ERPNext</h1>
  <p>Send WhatsApp messages, templates and delivery-tracked notifications from any Frappe or ERPNext document, through your own <a href="https://app.tarceel.com">Tarceel</a> account, without ever leaving Frappe.</p>
</div>

---

> ### ⚠️ Unofficial WhatsApp integration, please read
>
> Tarceel is an **unofficial**, QR-linked WhatsApp integration. It is **not** the official WhatsApp
> Business Platform / Cloud API, and it is not affiliated with, endorsed by, or supported by WhatsApp
> or Meta. It works by linking a real WhatsApp number via QR code (the same way WhatsApp Web does),
> which carries the risk that the number can be rate-limited or banned by WhatsApp if it is used to
> send unsolicited or bulk messages.
>
> Because of this, `tarceel_erpnext` is deliberately built for **per-document, consented messaging
> only**. Every send is tied to a specific Frappe document or an individually composed message. It
> has no bulk-send or contact-list-blast feature by design, and it never bypasses the rate limiting
> and anti-ban safety that the Tarceel service enforces on its side. Please use it accordingly.

## What it does

- **Connect in one click.** Link your Tarceel instance from **Tarceel Settings** without copying an
  API key by hand: approve the request in your Tarceel account and the credentials are saved for you.
- **Link the WhatsApp number by QR, in Frappe.** If the number is not linked (or gets logged out),
  scan a QR code shown right on the settings page. No need to open the Tarceel dashboard.
- **Send from any document.** A "Send WhatsApp" button on every saved form opens a dialog to send a
  free-text message, a rendered template, or attachments (the document as a PDF print format, or any
  attached file) to a recipient that is pre-filled from the document.
- **Templates.** Reusable Jinja message templates, optionally scoped to a DocType, rendered against
  the current document.
- **No-code automation.** Adds a **WhatsApp** channel to Frappe's own **Notification** DocType, so a
  rule like "on Sales Invoice submit, WhatsApp the invoice reminder to the customer" is configured
  exactly like an email notification.
- **Delivery status.** A signed webhook brings `delivered` / `read` receipts back and updates the
  message log automatically.
- **Full message log.** Every outgoing message is recorded (recipient, body, status, the Tarceel
  message id, and a link back to the document it came from).

## Requirements

- A Frappe / ERPNext site:
  - **v15** (use the `main` branch), or
  - **v16** (use the `version-16` branch).
- A **Tarceel account** with an instance (create one at [app.tarceel.com](https://app.tarceel.com)).
  This app is a customer of the Tarceel WhatsApp API gateway (a Sowaan product); it does not create,
  host, or rotate WhatsApp sessions itself.
- The `qrcode` Python package (installed automatically from `requirements.txt`).

## Installation

### On a self-hosted bench

```bash
cd $PATH_TO_YOUR_BENCH

# ERPNext / Frappe v15
bench get-app https://github.com/sowaan/tarceel_erpnext --branch main

# ERPNext / Frappe v16
bench get-app https://github.com/sowaan/tarceel_erpnext --branch version-16

bench --site $YOUR_SITE install-app tarceel_erpnext
bench --site $YOUR_SITE migrate
```

### On Frappe Cloud

Search for **Tarceel** in the Frappe Cloud Marketplace and add it to your bench, or add the repo
`sowaan/tarceel_erpnext` directly. Frappe Cloud matches the branch to your bench's Frappe version
automatically.

## Getting started

Open **Tarceel Settings** (search "Tarceel Settings" in the awesome bar) and follow the cards on the
page.

1. **Connect your account.** Click **Connect to Tarceel**. An approval page opens in a new tab;
   approve it in your Tarceel account and the Instance ID and API key are saved automatically.
   (Prefer to do it by hand? You can still paste the **Instance ID** and **Instance API Key** into the
   fields and click **Test Connection**.)
2. **Link the WhatsApp number.** If the number is not connected yet, a **QR card** appears. Open
   WhatsApp on your phone, go to **Linked Devices → Link a Device**, and scan it. If the number was
   logged out, click **Generate QR code** first. The page updates on its own once it connects.
3. **Turn on delivery updates (optional).** Under **Delivery status updates**, click **Enable** to
   register this site's webhook with Tarceel so `delivered` / `read` receipts flow back to the
   message log. Your site must be reachable from the internet for Tarceel to call it.
4. **Set default recipients (optional).** In **Default Recipient Fields**, map a DocType to the field
   that holds the phone number, so the Send dialog pre-fills the right number. Dotted paths through
   links are supported, for example `contact_person.mobile_no` on a Sales Invoice.

## Usage

### Send a message from a document

1. Open any saved document and click **Send WhatsApp**.
2. The recipient is pre-filled from your Default Recipient Fields mapping (edit it if needed).
3. Type a message, or pick a **template** to render it against the document.
4. Optionally attach the document as a **PDF** (choose a print format) and/or any **files**.
5. Send. A **WhatsApp Message Log** row is created and shows the live status.

Numbers are entered with the country code and no `+` (for example `9665XXXXXXXX`); the app normalises
them for you.

### Create a message template

Create a **WhatsApp Message Template**:

- **Template Name**, an **Enabled** flag, and an optional **Reference DocType** to scope it.
- A **Message** written in Jinja, rendered with the document as `doc`, for example:

  ```jinja
  Hello {{ doc.customer_name }}, your invoice {{ doc.name }} for
  {{ doc.get_formatted("grand_total") }} is ready. Thank you!
  ```

Scoped templates only appear in the Send dialog for their DocType; unscoped templates are available
everywhere.

### Automate with a Notification

Use Frappe's built-in **Notification** DocType:

1. Create a Notification and set **Channel** to **WhatsApp**.
2. Choose the **Document Type** and the event (New, Submit, Value Change, a scheduled date, and so on),
   plus any condition, exactly as you would for an email notification.
3. Set the **Recipients**. The recipient's phone number is resolved from:
   - **Receiver by Document Field**: a phone fieldname or dotted path (for example
     `contact_person.mobile_no`), and/or
   - **Receiver by Role** (each user's mobile number), and/or
   - the document's **assignees**.
4. Write the **Message** (Jinja). When the event fires, the message is rendered and sent to each
   resolved number, and logged.

Sends are enqueued after the document is saved, so a slow or failed WhatsApp send never blocks the
save.

### Delivery status and the message log

Open **WhatsApp Message Log** to see every message, its status
(`Pending` / `Sent` / `Delivered` / `Read` / `Failed`), the Tarceel message id, and the document it
was sent from. With the webhook enabled, statuses update automatically as WhatsApp reports them
(status can only move forward, so a late "delivered" never overwrites a "read").

## Configuration reference (Tarceel Settings)

| Field | Purpose |
|---|---|
| **Enabled** | Master switch for the integration. |
| **Base URL** | Tarceel API base. Defaults to `https://app.tarceel.com`; override only for a non-production Tarceel deployment. |
| **Instance ID** | Your Tarceel instance id (set by Connect, or by hand). |
| **Instance API Key** | The instance API key, stored encrypted (set by Connect, or by hand). |
| **Webhook URL / Secret** | Set for you when you click **Enable** under Delivery status updates. |
| **Phone Field Mappings** | Per-DocType field (or dotted path) used to pre-fill the recipient number. |

## Responsible use

This app inherits Tarceel's product and safety guardrails:

- **No bulk or unsolicited messaging.** Every send is tied to a specific document or an individually
  composed message. There is no "message every row" feature by design.
- **It never routes around Tarceel's rate limiting or anti-ban safety.** Those protect the underlying
  WhatsApp number.
- **Secrets stay secret.** The API key and webhook secret are stored in Frappe's encrypted `Password`
  fields and are never logged or echoed back to the browser.

## Development

```bash
# run the offline test suite
bench --site $YOUR_SITE run-tests --app tarceel_erpnext
```

This app uses `pre-commit` (ruff, eslint, prettier, pyupgrade) for formatting and linting:

```bash
cd apps/tarceel_erpnext
pre-commit install
```

## Support

- Issues and source: <https://github.com/sowaan/tarceel_erpnext>
- Tarceel service and account: <https://app.tarceel.com>
- Publisher: Sowaan (support@sowaan.com)

## License

[MIT](license.txt)
