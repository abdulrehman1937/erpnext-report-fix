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

> **Important:** Do **not** use `bench get-app <url>` directly — bench derives the folder name from the URL (`erpnext-report-fix`, with hyphens) but Frappe's build system requires the folder to match the Python package name (`erpnext_report_fix`, with underscores). This mismatch causes the build step to crash.

**Option A — skip-assets (recommended, one-liner):**

```bash
bench get-app --skip-assets https://github.com/abdulrehman1937/erpnext-report-fix.git
bench --site your.site install-app erpnext_report_fix
bench restart
```

**Option B — manual clone (explicit folder name):**

```bash
cd /path/to/frappe-bench/apps
git clone https://github.com/abdulrehman1937/erpnext-report-fix.git erpnext_report_fix
cd ..
bench --site your.site install-app erpnext_report_fix
bench restart
```

Both options are equivalent. `--skip-assets` is correct here because this app has no JavaScript or CSS — it is a pure Python monkey-patch.

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
