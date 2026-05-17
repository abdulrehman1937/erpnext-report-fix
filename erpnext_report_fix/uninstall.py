"""Uninstall hook — restores stock GrossProfitGenerator."""

from erpnext_report_fix.monkeypatch import remove_patch


def before_uninstall():
	remove_patch()
	print(
		"ERPNext Report Fix: Gross Profit patch removed. Restart bench if workers still use the old code."
	)
