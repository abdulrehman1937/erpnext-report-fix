# Copyright (c) 2026, Abdul Rehman and contributors
# License: MIT. Fixes ERPNext Gross Profit COGS for product bundles; see ERPNext license for upstream code.

from __future__ import annotations

import frappe
from frappe.utils import flt

from erpnext.accounts.report.gross_profit.gross_profit import GrossProfitGenerator


class GrossProfitGeneratorFixed(GrossProfitGenerator):
	"""
	Fixes the Gross Profit report for product bundles whose Sales Invoice has
	``update_stock=False`` and no ``dn_detail`` written back (the linked DN
	exists but the back-reference was never set). The bundle parent is a
	non-stock item, so the standard report finds no SLE for it and reports
	100% margin.

	For invoices where ``dn_detail`` IS set, the standard ERPNext flow already
	works on this installation — SLEs use the DN bundle parent's item row as
	``voucher_detail_no``, which equals ``row.dn_detail`` after process(). We
	intentionally do NOT override ``item_row`` to ``packed_item.name``.
	"""

	def get_buying_amount(self, row, item_code):
		# Only fires for bundle parent rows that process() couldn't resolve
		# (update_stock=False AND dn_detail=None AND parent set).
		if not row.get("update_stock") and not row.get("dn_detail") and row.get("parent"):
			if frappe.db.exists("Product Bundle", item_code):
				resolved = self._resolve_bundle_cogs(row, item_code)
				if resolved is not None:
					return flt(resolved, self.currency_precision)
		return super().get_buying_amount(row, item_code)

	def _resolve_bundle_cogs(self, row, item_code):
		# Prefer Sales Order packed items (linked via so_detail), scaled if
		# the SI invoices a partial qty of the SO.
		if row.get("sales_order") and row.get("so_detail"):
			so_packed = (
				self.product_bundles.get("Sales Order", {})
				.get(row.get("sales_order"), frappe._dict())
				.get(item_code, [])
			)
			so_packed = [
				p for p in so_packed
				if p.get("parent_detail_docname") == row.get("so_detail")
			]
			if so_packed:
				return self._sum_from_packed(row, so_packed, scale_from_so=True)

		# Fall back to the Product Bundle definition (× row.qty).
		components = frappe.db.get_all(
			"Product Bundle Item",
			filters={"parent": item_code},
			fields=["item_code", "qty"],
		)
		if components:
			synthetic = [
				frappe._dict({
					"item_code": c.item_code,
					"total_qty": -flt(c.qty) * flt(row.qty),
					"warehouse": row.get("warehouse"),
					"serial_and_batch_bundle": None,
				})
				for c in components
			]
			return self._sum_from_packed(row, synthetic, scale_from_so=False)
		return None

	def _sum_from_packed(self, row, packed_list, scale_from_so):
		scale = 1.0
		if scale_from_so and row.get("so_detail") and row.get("qty"):
			so_qty = frappe.db.get_value("Sales Order Item", row.get("so_detail"), "qty")
			if so_qty:
				scale = flt(row.qty) / flt(so_qty)
		buying_amount = 0.0
		for packed_item in packed_list:
			component_row = row.copy()
			component_row.item_code = packed_item.item_code
			component_row.warehouse = packed_item.get("warehouse") or row.get("warehouse")
			component_row.qty = (flt(packed_item.total_qty) * -1) * scale
			component_row.serial_and_batch_bundle = packed_item.get("serial_and_batch_bundle")
			buying_amount += self.get_buying_amount(component_row, packed_item.item_code)
		return buying_amount
