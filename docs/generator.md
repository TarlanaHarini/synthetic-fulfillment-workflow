# Generator and validation instructions

Run from the repository root with `python -m src.fulfillment.workflow`. Supported presets are `starter` and `full`; all dimensions are overrideable. `--seed` defaults to 20261022. A generated database is initialized from `src/fulfillment/schema.sql`; the baseline database is not opened for writes.

The generator uses deterministic IDs and a stable insertion order. IDs use `ORD-2026-000001`, `FUL-2026-000001`, `SHP-2026-000001`, `TRK-<shipment-id>-001`, and `PROM-ORD-2026-000001-01` conventions in business keys or export metadata. SQLite numeric IDs remain stable within a seed/configuration. `ground_truth.*` is kept outside the operational tables.

Run all checks with `python -m unittest discover -s tests -v`. Database checks can also be executed against a generated file using Python's sqlite3 module: `PRAGMA integrity_check; PRAGMA foreign_key_check;`. For reproducibility, run the same preset and seed into two separate directories and compare SHA-256 hashes of CSV exports and the ordered database table values. The report records per-file CSV hashes.
