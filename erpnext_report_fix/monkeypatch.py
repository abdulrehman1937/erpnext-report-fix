"""Replace ERPNext GrossProfitGenerator with bundle-aware implementation."""

from __future__ import annotations

_original_gross_profit_generator = None
_patch_applied = False


def apply_patch() -> None:
	"""Idempotent: swap GrossProfitGenerator on the gross_profit report module."""
	global _original_gross_profit_generator, _patch_applied
	if _patch_applied:
		return

	import erpnext.accounts.report.gross_profit.gross_profit as gross_profit_module
	from erpnext_report_fix.gross_profit_generator import GrossProfitGeneratorFixed

	_original_gross_profit_generator = gross_profit_module.GrossProfitGenerator
	gross_profit_module.GrossProfitGenerator = GrossProfitGeneratorFixed
	_patch_applied = True


def remove_patch() -> None:
	"""Restore stock GrossProfitGenerator (e.g. on app uninstall)."""
	global _patch_applied, _original_gross_profit_generator
	if not _patch_applied or _original_gross_profit_generator is None:
		return

	import erpnext.accounts.report.gross_profit.gross_profit as gross_profit_module

	gross_profit_module.GrossProfitGenerator = _original_gross_profit_generator
	_patch_applied = False


def _bootstrap_patch() -> None:
	"""Apply patch when Frappe loads this app's hooks (after ERPNext is available)."""
	try:
		apply_patch()
	except ImportError:
		# ERPNext not on path (e.g. partial clone) — patch applies on install when deps exist.
		pass


_bootstrap_patch()
