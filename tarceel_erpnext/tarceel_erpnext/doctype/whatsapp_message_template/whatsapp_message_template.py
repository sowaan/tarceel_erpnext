# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppMessageTemplate(Document):
	def render(self, doc):
		"""Render this template's Jinja body against `doc` (a Document or dict),
		reusing Frappe's own sandboxed template engine — the same one Print Formats
		and Email Templates use. Returns the rendered text."""
		return frappe.render_template(self.message, {"doc": doc}).strip()
