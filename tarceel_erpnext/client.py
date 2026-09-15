# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

"""Thin wrapper around the Tarceel WhatsApp gateway REST API.

This module is intentionally minimal: one authenticated HTTP call per public
function, no retry / queueing / rate-limiting of its own. Tarceel already queues
and rate-limits on its side, and guardrail #2 forbids this app from routing
around that. Guardrail #3 forbids ever logging the instance API key: it lives
only in the request headers, is never placed in an exception message, and the
request headers are never attached to a raised error.
"""

import requests

import frappe
from frappe import _

# Network timeout (seconds) for a single Tarceel call. Not a retry budget —
# a timeout just surfaces as a plain failure the user can act on.
REQUEST_TIMEOUT = 30


class TarceelError(frappe.ValidationError):
	"""A Tarceel API call failed. Message is safe to show to the user and never
	contains the API key or request headers."""


def get_settings():
	"""Return the (cached) Tarceel Settings single doc, validating it is usable."""
	settings = frappe.get_cached_doc("Tarceel Settings")
	if not settings.enabled:
		frappe.throw(_("Tarceel is disabled. Enable it in Tarceel Settings first."), TarceelError)
	if not (settings.base_url and settings.instance_id):
		frappe.throw(
			_("Tarceel Settings is incomplete: set the Base URL and Instance ID first."),
			TarceelError,
		)
	return settings


def _headers(settings):
	api_key = settings.get_password("api_key", raise_exception=False)
	if not api_key:
		frappe.throw(_("Tarceel Settings has no Instance API Key set."), TarceelError)
	return {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}


def _instance_url(settings, suffix=""):
	return f"{settings.base_url}/instances/{settings.instance_id}{suffix}"


def _request(method, url, headers, json=None):
	"""Make one Tarceel call and return parsed JSON, or raise TarceelError with a
	plain, key-free message. Headers (which carry the API key) are never included
	in any raised error."""
	try:
		response = requests.request(method, url, headers=headers, json=json, timeout=REQUEST_TIMEOUT)
	except requests.RequestException:
		# Scrub: requests' exception text can echo the URL but not the headers;
		# still, don't surface the raw exception, only a plain message.
		frappe.throw(
			_("Could not reach Tarceel. Check the Base URL and this site's network access."),
			TarceelError,
			title=_("Tarceel connection failed"),
		)

	try:
		payload = response.json()
	except ValueError:
		payload = {}

	if not response.ok:
		frappe.throw(_tarceel_error_message(response.status_code, payload), TarceelError)

	return payload


def _tarceel_error_message(status_code, payload):
	"""Map a Tarceel error response to a plain, user-facing message. Never includes
	request headers or the API key."""
	error = (payload or {}).get("error") or {}
	code = error.get("code")
	detail = error.get("message")

	if status_code == 401:
		return _("Tarceel rejected the API key (401). Re-check the Instance API Key in Tarceel Settings.")
	if status_code == 402:
		return _("Tarceel: this instance needs a plan/payment before it can send (402).")
	if status_code == 409:
		return _(
			"Tarceel: the linked WhatsApp session isn't connected right now (409). "
			"Re-scan the QR code in the Tarceel dashboard."
		)

	if detail:
		return _("Tarceel error ({0}): {1}").format(code or status_code, detail)
	return _("Tarceel request failed (HTTP {0}).").format(status_code)


# --- Public API -----------------------------------------------------------


def get_instance_status():
	"""GET /instances/{id} — used by the Test connection button (Phase 1)."""
	settings = get_settings()
	return _request("GET", _instance_url(settings), _headers(settings))


def send_text(to, text):
	"""POST /instances/{id}/messages/text. `to` is a bare number with country code,
	no '+' or '@s.whatsapp.net' suffix. Returns {"id": "<message id>"}."""
	settings = get_settings()
	return _request(
		"POST",
		_instance_url(settings, "/messages/text"),
		_headers(settings),
		json={"to": to, "text": text},
	)


def send_media(to, media_type, url=None, base64=None, caption=None, mimetype=None):
	"""POST /instances/{id}/messages/media. Provide either `url` or `base64`.
	`mimetype` is required when media_type == "document". Returns {"id": ...}."""
	if not (url or base64):
		frappe.throw(_("send_media needs either a url or base64 payload."), TarceelError)

	settings = get_settings()
	body = {"to": to, "type": media_type}
	if url:
		body["url"] = url
	if base64:
		body["base64"] = base64
	if caption:
		body["caption"] = caption
	if mimetype:
		body["mimetype"] = mimetype

	return _request("POST", _instance_url(settings, "/messages/media"), _headers(settings), json=body)
