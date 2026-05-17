import frappe

# Save original reference at module-import time, before override_whitelisted_methods
# replaces it in the module namespace. This prevents infinite recursion.
from frappe.desk.query_report import run as _original_run


@frappe.whitelist()
def run(report_name, filters=None, user=None, ignore_prepared_report=False, for_page=None):
    from erpnext_report_fix.monkeypatch import apply_patch

    apply_patch()
    return _original_run(
        report_name=report_name,
        filters=filters,
        user=user,
        ignore_prepared_report=ignore_prepared_report,
        for_page=for_page,
    )
