# Synthetic Fulfillment Workflow

This project extends the Milestone 1 SQLite schema with deterministic synthetic data generation, constrained node allocation, service and zone selection, business-day delivery promises, shipment and tracking records, sidecar ground truth, CSV/JSON/SQL exports, and validation reports.

## Quick start

Use Python 3.10+; the implementation uses only the standard library.

```powershell
python -m src.fulfillment.workflow --dataset starter --database generated/starter.sqlite3 --output generated/starter
python -m unittest discover -s tests -v
```

The default seed is `20261022`. Choose `--dataset full` for 50,000 orders, 500 SKUs, 20 nodes, 10 carriers, and 100,000 tracking events. Any dimension can be overridden using `--orders`, `--skus`, `--nodes`, `--carriers`, or `--tracking-events`. The output database is separate from the Milestone 1 `fulfillment.sqlite3` baseline.

## Outputs

The output directory contains a CSV and JSON export for every operational entity, `ground_truth.csv/json`, `seed.sql`, `validation_summary.json`, and `evaluation_report.json`. Operational tables contain only valid generated records; explicitly labeled anomaly cases are isolated in the ground-truth sidecar. `fulfillment.generated.sqlite3` is the CLI default database.

## Allocation and timing

The generator creates master records first. For each line it ranks eligible active nodes by current same-day capacity usage and then node ID; it requires unreserved stock and capacity, matching node coverage, and a carrier/service/zone combination. Partial quantities can split across nodes; unallocatable units remain unallocated and are reflected in the order state. Generated promises use UTC timestamps, weekday transit days, and the synthetic holiday calendar. Tracking events are append-only rows ordered by shipment sequence. A deterministic carrier-based 0–2 day delay is applied to delivery outcomes.

## Data and provenance

All records, names, zones, dates, holidays, carrier identities, inventory values, and outcomes are synthetic, generated locally with Python's `random.Random` seeded by the configured integer. No external data is used. See [docs/data_dictionary.md](docs/data_dictionary.md), [docs/entity_relationships.md](docs/entity_relationships.md), and [docs/business_rules.md](docs/business_rules.md).


## Project Documentation

- [Design and Technical Decisions](docs/DESIGN_AND_DECISIONS.md)
- [AI Usage and Prompt History](docs/AI_USAGE_AND_PROMPT_HISTORY.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Business Rules](docs/business_rules.md)
- [Entity Relationships](docs/entity_relationships.md)
- [Generator Guide](docs/generator.md)
