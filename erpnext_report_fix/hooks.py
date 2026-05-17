app_name = "erpnext_report_fix"
app_title = "ERPNext Report Fix"
app_publisher = "Abdul Rehman"
app_description = "Corrects Gross Profit COGS for product bundles (uses Packed Item row in SLE lookups)"
app_email = "abdulrehman1937@users.noreply.github.com"
app_license = "mit"

required_apps = ["erpnext"]

# Ensure patch is registered when hooks are loaded (import side effects).
# pylint: disable=unused-import
import erpnext_report_fix.monkeypatch  # noqa: F401

after_install = "erpnext_report_fix.install.after_install"
before_uninstall = "erpnext_report_fix.uninstall.before_uninstall"
