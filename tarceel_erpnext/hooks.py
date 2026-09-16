app_name = "tarceel_erpnext"
app_title = "Tarceel Erpnext"
app_publisher = "Sowaan"
app_description = "Custom ERPNext app for Tarceel"
app_email = "mubashir.abbasi@ahsaic.org"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "tarceel_erpnext",
# 		"logo": "/assets/tarceel_erpnext/logo.png",
# 		"title": "Tarceel Erpnext",
# 		"route": "/tarceel_erpnext",
# 		"has_permission": "tarceel_erpnext.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tarceel_erpnext/css/tarceel_erpnext.css"
app_include_js = [
	"tarceel_send_button.bundle.js",
	"tarceel_setup_banner.bundle.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/tarceel_erpnext/css/tarceel_erpnext.css"
# web_include_js = "/assets/tarceel_erpnext/js/tarceel_erpnext.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tarceel_erpnext/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Notification": "public/js/notification.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tarceel_erpnext/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "tarceel_erpnext.utils.jinja_methods",
# 	"filters": "tarceel_erpnext.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "tarceel_erpnext.install.before_install"
# after_install = "tarceel_erpnext.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tarceel_erpnext.uninstall.before_uninstall"
# after_uninstall = "tarceel_erpnext.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tarceel_erpnext.utils.before_app_install"
# after_app_install = "tarceel_erpnext.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tarceel_erpnext.utils.before_app_uninstall"
# after_app_uninstall = "tarceel_erpnext.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tarceel_erpnext.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["tarceel_erpnext.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Phase 5: add a native "WhatsApp" channel to Frappe's Notification by overriding
# its controller (Frappe's channel dispatch has no plugin hook). The property
# setter adding the channel option is applied by patches.txt.
override_doctype_class = {
	"Notification": "tarceel_erpnext.overrides.notification.TarceelNotification"
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tarceel_erpnext.tasks.all"
# 	],
# 	"daily": [
# 		"tarceel_erpnext.tasks.daily"
# 	],
# 	"hourly": [
# 		"tarceel_erpnext.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tarceel_erpnext.tasks.weekly"
# 	],
# 	"monthly": [
# 		"tarceel_erpnext.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "tarceel_erpnext.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tarceel_erpnext.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tarceel_erpnext.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tarceel_erpnext.utils.before_request"]
# after_request = ["tarceel_erpnext.utils.after_request"]

# Job Events
# ----------
# before_job = ["tarceel_erpnext.utils.before_job"]
# after_job = ["tarceel_erpnext.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tarceel_erpnext.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

