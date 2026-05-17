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
		# so bundle parent rows fall through here. For non-stock bundle parents super()
		# returns 0 (no SLEs). Resolve packed items from SI → SO → bundle definition.
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

			# SI with update_stock=False usually has no tabPacked Item rows. Fall back to
			# the linked Sales Order, scaling qty if the SI invoices only part of the SO.
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
					return flt(
						self._buying_amount_from_packed_list(row, so_packed),
						self.currency_precision,
					)

			# Last resort: synthesize components from the Product Bundle definition.
			if frappe.db.exists("Product Bundle", item_code):
				return flt(
					self._buying_amount_from_bundle_definition(row, item_code),
					self.currency_precision,
				)

		return super().get_buying_amount(row, item_code)

	def _buying_amount_from_packed_list(self, row, packed_list):
		"""Sum buying amount across pre-filtered packed items, scaling for partial invoicing."""
		scale = 1.0
		if row.get("so_detail") and row.get("qty"):
			so_qty = frappe.db.get_value("Sales Order Item", row.get("so_detail"), "qty")
			if so_qty:
				scale = flt(row.qty) / flt(so_qty)
		buying_amount = 0.0
		for packed_item in packed_list:
			packed_item_row = row.copy()
			packed_item_row.item_code = packed_item.item_code
			packed_item_row.warehouse = packed_item.warehouse
			packed_item_row.qty = (packed_item.total_qty * -1) * scale
			packed_item_row.serial_and_batch_bundle = packed_item.serial_and_batch_bundle
			packed_item_row.item_row = packed_item.name
			buying_amount += self.get_buying_amount(packed_item_row, packed_item.item_code)
		return buying_amount

	def _buying_amount_from_bundle_definition(self, row, item_code):
		"""Compute COGS by walking the Product Bundle definition × row.qty."""
		components = frappe.db.get_all(
			"Product Bundle Item",
			filters={"parent": item_code},
			fields=["item_code", "qty"],
		)
		buying_amount = 0.0
		for component in components:
			component_row = row.copy()
			component_row.item_code = component.item_code
			component_row.qty = flt(component.qty) * flt(row.qty)
			buying_amount += self.get_buying_amount(component_row, component.item_code)
		return buying_amount

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
