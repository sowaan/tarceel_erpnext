# Privacy Policy

**App:** Tarceel for Frappe / ERPNext (`tarceel_erpnext`)
**Publisher:** Sowaan
**Contact:** support@sowaan.com
**Effective date:** 18 September 2026

This policy explains how the `tarceel_erpnext` app handles data. Please read it together
with the app's [README](README.md) and [Terms of Service](TERMS.md).

## Summary

`tarceel_erpnext` is software you install on your own Frappe / ERPNext site. It does not send
your data to Sowaan, and it has no central server that collects information from your site. Any
data it processes stays in your own site's database, except for the WhatsApp messages you choose
to send, which are relayed through your own Tarceel account.

## Roles

- **You (the site operator)** are the controller of the data processed on your site. You decide
  who to message, what to send, and how long to keep the records.
- **This app** is a tool running inside your site. It does not phone home.
- **Tarceel** (a Sowaan product, `app.tarceel.com`) is the WhatsApp API gateway your messages are
  relayed through, under your own Tarceel account and Tarceel's own terms and privacy policy.
- **WhatsApp / Meta** ultimately deliver the messages. This app is not affiliated with, endorsed
  by, or connected to WhatsApp or Meta.

## What the app processes

When you use the app, it may process:

- **Recipient phone numbers** you enter or that are read from your documents.
- **Message content** you write, or that a template renders from your documents.
- **Attachments** you choose to send (a document rendered as a PDF, or files you attach).
- **Delivery status** (sent, delivered, read, failed) reported back by Tarceel.
- **A message log** linking each message to the document it was sent from.
- **Your Tarceel credentials** (instance id, API key) and the **webhook signing secret**.

## Where the data is stored

- Message logs, templates, settings, and recipient mappings are stored in **your own Frappe
  database**, on the infrastructure where your site runs.
- The **Tarceel API key** and the **webhook secret** are stored using Frappe's encrypted
  `Password` field type. They are never written to logs and are never returned to the browser.

## Where the data is sent

- To **your Tarceel instance** over an encrypted (HTTPS) connection, using your instance API key,
  only when you send a message, register a webhook, link a number, or check status.
- Tarceel relays the message to **WhatsApp**, which delivers it to the recipient.
- **Delivery receipts** are sent back to your site through a signed webhook, verified before use.

The app does not transmit your data to any other third party, and does not use any external
service to render QR codes or process messages.

## Retention

The app does not delete data on its own. Message logs and other records remain in your database
until you remove them. You control retention through your normal Frappe data-management tools.

## Your responsibilities

Because you decide who receives messages, you are responsible for having a lawful basis and the
recipient's consent to contact them on WhatsApp, and for complying with WhatsApp's terms and any
applicable anti-spam and data-protection laws.

## Third-party policies

- Tarceel: see the privacy policy at `https://app.tarceel.com`.
- WhatsApp / Meta: see WhatsApp's own privacy policy.

## Changes

We may update this policy. Material changes will be reflected in this file with a new effective
date.

## Contact

Questions about this policy: **support@sowaan.com**.
