# ERPNext Report Fix

Monkey-patches ERPNext **`GrossProfitGenerator`** so the **Gross Profit** report matches Stock Ledger valuation for **product bundles**.

## Problem

For bundled items, Stock Ledger entries use `voucher_detail_no` = `tabPacked Item`.`name`. The standard Gross Profit report uses the parent Sales Invoice / Delivery Note item row name when resolving COGS, finds no matching SLE line, treats buying amount as **0**, and shows **~100% gross margin**.

## Fix

This app replaces the report generator with a small subclass that:

1. Loads **Packed Item** `name` into the product bundle map.
2. Uses that name as `item_row` when costing bundle components (both the aggregated bundle line and expanded child rows when grouping by Invoice).

## Requirements

- Frappe / ERPNext **v15+** (developed against v16-style `gross_profit.py`).
- ERPNext installed on the bench.

## Install

From your bench directory:

```bash
# Get the app (or clone into apps/erpnext_report_fix)
bench get-app https://github.com/abdulrehman1937/erpnext-report-fix.git

bench --site your.site install-app erpnext_report_fix
bench restart
```

## Uninstall

```bash
bench --site your.site uninstall-app erpnext_report_fix
bench restart
```

The uninstall hook restores ERPNext’s original `GrossProfitGenerator`.

## Support

Validate on a copy of production data: run **Gross Profit** for invoices that include product bundles with **Update Stock** and/or Delivery Notes, and compare buying amounts to Stock Ledger / BOM expectations.

## License

MIT. ERPNext remains under the GNU GPLv3.
