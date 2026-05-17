app_name = "erpnext_report_fix"
app_title = "ERPNext Report Fix"
app_publisher = "Abdul Rehman"
app_description = "Corrects Gross Profit COGS for product bundles (uses Packed Item row in SLE lookups)"
app_email = "abdulrehman1937@users.noreply.github.com"
app_license = "mit"

required_apps = ["erpnext"]

# Frappe v16 caches hooks in Redis and does not re-import hooks.py in worker
# processes, so a module-level import side-effect is unreliable. The
# before_request hook is resolved by name from the Redis cache and is called
# by Frappe before every HTTP request, guaranteeing the patch is applied in
# each worker process before any report can run.
before_request = ["erpnext_report_fix.monkeypatch.apply_patch"]

# Belt-and-suspenders: intercept the exact API endpoint Frappe calls for
# every report run. apply_patch() is idempotent so the double-call is free.
override_whitelisted_methods = {
    "frappe.desk.query_report.run": "erpnext_report_fix.query_report_patch.run"
}

after_install = "erpnext_report_fix.install.after_install"
before_uninstall = "erpnext_report_fix.uninstall.before_uninstall"
