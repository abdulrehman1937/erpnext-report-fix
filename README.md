# ERPNext Gross Profit Report Fix for Product Bundles (100% Margin Bug)

Frappe app that fixes the **ERPNext Gross Profit report showing 100% profit / zero COGS / zero buying amount for product bundle items**. Compatible with **ERPNext v15 and v16**.

If you searched for any of the following, you are in the right place:

- ERPNext Gross Profit report shows 100% profit for product bundle
- ERPNext bundle item buying amount is 0
- ERPNext Gross Profit COGS not calculated for packed items
- ERPNext product bundle wrong margin in report
- ERPNext Gross Profit wrong gross profit percent
- Sales Invoice product bundle COGS missing from Gross Profit report
- ERPNext `tabPacked Item` not matched in Gross Profit
- ERPNext gross profit zero buying amount bundle
- Gross Profit report ignores bundled / packed items

## The Problem

In ERPNext's standard Gross Profit report, a **Sales Invoice line that contains a Product Bundle** can show **100% gross margin** because the report fails to resolve the **Cost of Goods Sold (COGS)** for the bundle's components.

This happens when:

- The Sales Invoice has **Update Stock = unchecked** (the common case where stock moves via a separate Delivery Note), AND
- The Delivery Note's back-reference (`dn_detail` on the SI item) is not written back to the Sales Invoice.

In that situation, ERPNext's `GrossProfitGenerator.process()` has no entry point to look up the bundle's component (`tabPacked Item`) rows for the SI, and the bundle parent is a **non-stock item** with no Stock Ledger Entries of its own. The report ends up with `buying_amount = 0` for the bundle line, which displays as **100% Gross Profit %**.

**Important:** This is purely a **reporting** bug. Your actual accounting (General Ledger, Profit & Loss, Balance Sheet, Stock Ledger) is **not affected** — COGS is posted correctly to the GL when the Delivery Note submits, using the real Stock Ledger valuation rate. Only the Gross Profit report's display is wrong.

## The Fix

This app installs a small subclass of `GrossProfitGenerator` (`GrossProfitGeneratorFixed`) and monkey-patches ERPNext at request time. It adds **one targeted intervention**:

When ERPNext's `process()` cannot resolve a bundle parent line (because `update_stock = False` AND `dn_detail` is empty), the subclass walks the SI item's `sales_order` / `so_detail` link to the linked **Sales Order's Packed Items**, scales the qty if the SI invoices only part of the SO, and computes per-component COGS via the normal `get_buying_amount()` path. If no linked Sales Order exists, it falls back to the **Product Bundle definition** (`Product Bundle Item` rows × invoice qty).

For every other case (SI with `update_stock = True`, or SI with `dn_detail` properly populated), the app **does not change ERPNext's behavior** — the original flow is correct and the override does not activate.

## Requirements

- Frappe / ERPNext **v15 or v16** (developed against v16's `gross_profit.py`)
- Python 3.10+
- ERPNext app already installed on the bench

## Installation

> **Important:** Do **not** use `bench get-app <url>` directly. Bench derives the folder name from the URL (`erpnext-report-fix`, with hyphens), but Frappe's build system requires the folder to match the Python package name (`erpnext_report_fix`, with underscores). This mismatch will crash the build.

### Option A — `--skip-assets` (recommended)

```bash
bench get-app --skip-assets https://github.com/abdulrehman1937/erpnext-report-fix.git
bench --site your.site.name install-app erpnext_report_fix
bench restart
```

### Option B — manual clone with explicit folder name

```bash
cd /path/to/frappe-bench/apps
git clone https://github.com/abdulrehman1937/erpnext-report-fix.git erpnext_report_fix
cd ..
bench --site your.site.name install-app erpnext_report_fix
bench restart
```

Both options are equivalent. `--skip-assets` is correct because this app has no JavaScript or CSS — it is a pure Python report patch.

## How to Verify the Fix

1. Open the **Gross Profit** report (`/app/query-report/Gross Profit`).
2. Filter to an invoice that has a product bundle with the symptom (100% margin / 0 buying amount on the bundle line).
3. Run the report — the bundle line should now show a non-zero **Buying Amount** computed from the components' moving-average valuation.

If you want to verify your **books** are correct (independent of this fix), check the Delivery Note's GL entries against its Stock Ledger Entries:

```python
dn = "MAT-DN-XXXX-XXXXX"  # the DN that delivered the bundle

# Stock value that left inventory:
frappe.db.sql("SELECT SUM(ABS(stock_value_difference)) FROM `tabStock Ledger Entry` WHERE voucher_no = %s AND is_cancelled = 0", dn)

# GL posting to Cost of Goods Sold:
frappe.db.sql("SELECT SUM(debit) FROM `tabGL Entry` WHERE voucher_no = %s AND account LIKE 'Cost of Goods Sold%%' AND is_cancelled = 0", dn)
```

The two numbers must be equal — and they will be, even without this app.

## Uninstall

```bash
bench --site your.site.name uninstall-app erpnext_report_fix
bench restart
```

The `before_uninstall` hook restores ERPNext's original `GrossProfitGenerator` class so no monkey-patched state lingers.

## Technical Details

- **Patch mechanism:** `before_request` hook + `override_whitelisted_methods` for `frappe.desk.query_report.run`. Both call an idempotent `apply_patch()` that swaps `gross_profit.GrossProfitGenerator` with `GrossProfitGeneratorFixed`. Two entry points are used because Frappe v16 caches `hooks.py` in Redis and worker processes don't re-import the hooks module, so a module-level import side-effect is unreliable.
- **What the override does:** subclasses `GrossProfitGenerator` and overrides only `get_buying_amount()`. The override is a guarded no-op for every case the parent class already handles correctly. It only fires for non-stock bundle parents that the parent cannot resolve.
- **What the override does NOT do:** it does not modify `item_row`, does not rewrite the product-bundle map structure, does not change the SLE lookup, and does not touch GL postings or stock balances.

## Keywords

ERPNext, Frappe, Gross Profit report, Product Bundle, Packed Item, COGS, Cost of Goods Sold, buying amount, gross margin, 100% profit, 100% margin, zero buying amount, update_stock unchecked, dn_detail, voucher_detail_no, Sales Invoice, Delivery Note, Sales Order, monkey patch, ERPNext v15, ERPNext v16, gross_profit.py, GrossProfitGenerator.

## License

MIT. ERPNext itself remains under GNU GPLv3 — this app does not modify ERPNext's source; it patches a class at runtime within your own bench.

## Contributing / Issues

Open an issue or PR on the [GitHub repository](https://github.com/abdulrehman1937/erpnext-report-fix). When reporting a bug, please include:

- ERPNext / Frappe version
- Whether the Sales Invoice has `update_stock` checked
- Whether the Sales Invoice item has `delivery_note` / `dn_detail` populated
- Whether the SI item is linked to a Sales Order (`sales_order` / `so_detail`)
- The output of: `frappe.db.sql("SELECT voucher_no, voucher_detail_no, valuation_rate FROM \`tabStock Ledger Entry\` WHERE voucher_no = %s AND is_cancelled = 0", "<your DN name>", as_dict=1)`
