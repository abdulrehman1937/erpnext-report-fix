"""Install hook — ensures Gross Profit generator patch is active."""

from erpnext_report_fix.monkeypatch import apply_patch


def after_install():
	apply_patch()
	print(
		"ERPNext Report Fix: Gross Profit bundle COGS patch applied. "
		"Restart bench (web and workers) if the report still shows old behaviour."
	)
