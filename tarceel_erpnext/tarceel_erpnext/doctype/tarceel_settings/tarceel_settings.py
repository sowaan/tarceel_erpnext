# Copyright (c) 2026, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TarceelSettings(Document):
	def validate(self):
		# Normalize the base URL so client.py can build paths as f"{base_url}/instances/...".
		if self.base_url:
			self.base_url = self.base_url.strip().rstrip("/")
