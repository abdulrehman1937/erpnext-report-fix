# Copyright (c) 2026, Abdul Rehman and contributors
# License: MIT. Fixes ERPNext Gross Profit COGS for product bundles; see ERPNext license for upstream code.

from __future__ import annotations

import frappe
from frappe import qb
from frappe.utils import flt

from erpnext.accounts.report.gross_profit.gross_profit import GrossProfitGenerator


class GrossProfitGeneratorFixed(GrossProfitGenerator):
	"""
	Stock Ledger rows for bundle components use ``voucher_detail_no`` = `tabPacked Item`.`name`.
	The standard report uses the parent Sales Invoice Item / DN row name, so COGS resolves to 0
	and gross profit shows as 100% of revenue.

	This subclass aligns ``item_row`` with the packed-item row before valuation lookups.
	"""

	def load_product_bundle(self):
		self.product_bundles = {}
		pki = qb.DocType("Packed Item")
		pki_query = (
			frappe.qb.from_(pki)
			.select(
				pki.parenttype,
				pki.parent,
				pki.parent_item,
				pki.item_code,
				pki.warehouse,
				(-1 * pki.qty).as_("total_qty"),
				pki.rate,
				(pki.rate * pki.qty).as_("base_amount"),
				pki.parent_detail_docname,
				pki.serial_and_batch_bundle,
				pki.name,
			)
			.where(pki.docstatus == 1)
		)
		for d in pki_query.run(as_dict=True):
			self.product_bundles.setdefault(d.parenttype, frappe._dict()).setdefault(
				d.parent, frappe._dict()
			).setdefault(d.parent_item, []).append(d)

	def get_buying_amount(self, row, item_code):
		self._fix_packed_item_voucher_detail_no(row)

		# process() leaves product_bundles=[] when update_stock=False and dn_detail=None,
		# so bundle parent rows fall through here and super() returns 0 (non-stock, no SLE).
		# Intercept: look up SI packed items and compute per-component buying amount instead.
		if not row.get("update_stock") and not row.get("dn_detail") and row.get("parent"):
			si_bundles = (
				self.product_bundles.get("Sales Invoice", {})
				.get(row.get("parent"), frappe._dict())
			)
			if item_code in si_bundles:
				return flt(
					self.get_buying_amount_from_product_bundle(row, si_bundles[item_code]),
					self.currency_precision,
				)

		return super().get_buying_amount(row, item_code)

	def get_buying_amount_from_product_bundle(self, row, product_bundle):
		buying_amount = 0.0
		for packed_item in product_bundle:
			if packed_item.get("parent_detail_docname") == row.item_row:
				packed_item_row = row.copy()
				packed_item_row.item_code = packed_item.item_code
				packed_item_row.warehouse = packed_item.warehouse
				packed_item_row.qty = packed_item.total_qty * -1
				packed_item_row.serial_and_batch_bundle = packed_item.serial_and_batch_bundle
				packed_item_row.item_row = packed_item.name
				buying_amount += self.get_buying_amount(packed_item_row, packed_item.item_code)
		return flt(buying_amount, self.currency_precision)

	def _fix_packed_item_voucher_detail_no(self, row):
		"""Expand-tree rows only (indent > 1): map SI/DN child name → Packed Item name."""
		if self.filters.get("group_by") != "Invoice":
			return
		if not row.get("indent") or row.indent <= 1:
			return
		if not row.get("parent_invoice"):
			return

		parent_detail_docname = row.item_row
		candidates = []
		if row.get("delivery_note") and row.get("dn_detail"):
			candidates = (
				self.product_bundles.get("Delivery Note", {})
				.get(row.delivery_note, frappe._dict())
				.get(row.parent_invoice, [])
			)
		elif row.get("invoice"):
			candidates = (
				self.product_bundles.get("Sales Invoice", {})
				.get(row.invoice, frappe._dict())
				.get(row.parent_invoice, [])
			)
		for pi in candidates:
			if (
				pi.item_code == row.item_code
				and pi.get("parent_detail_docname") == parent_detail_docname
			):
				row.item_row = pi.name
				break
