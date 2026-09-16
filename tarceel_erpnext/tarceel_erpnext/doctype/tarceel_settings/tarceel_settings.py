# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TarceelSettings(Document):
	def onload(self):
		# Expose whether the (encrypted) API key is set, so the form can decide
		# whether to nudge the user to create/connect a Tarceel account.
		self.set_onload("has_api_key", bool(self.get_password("api_key", raise_exception=False)))

	def validate(self):
		# Normalize the base URL so client.py can build paths as f"{base_url}/instances/...".
		if self.base_url:
			self.base_url = self.base_url.strip().rstrip("/")
