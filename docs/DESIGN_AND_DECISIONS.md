# Design and Technical Decisions

## 1. Problem Overview

The Synthetic Fulfillment Workflow simulates how an order fulfillment system selects warehouse locations, allocates inventory, calculates delivery promises, and tracks shipments.

The main objective is to allocate orders while respecting inventory availability, warehouse capacity, carrier service compatibility, delivery cutoffs, and holiday calendars.

The project also generates controlled anomaly examples to demonstrate how invalid fulfillment scenarios can be identified.

## 2. Architecture and Workflow

The project follows this processing sequence:

1. Generate master data such as SKUs, fulfillment nodes, carriers, and service levels.
2. Generate operational data such as orders, order lines, inventory, and warehouse capacity.
3. Allocate order quantities to eligible fulfillment nodes.
4. Select compatible carrier services for destination zones.
5. Calculate delivery promise dates using transit days, weekdays, cutoffs, and holidays.
6. Generate shipments and tracking events.
7. Validate relationships, business rules, and operational outcomes.
8. Export data and evaluation reports in CSV, JSON, and SQL formats.

## 3. Key Design Decisions

### Deterministic Data Generation

A fixed random seed of `20261022` is used to generate repeatable synthetic datasets.

This makes it possible to compare multiple runs and verify whether the generator produces consistent outputs.

### Database Design

SQLite is used to store the fulfillment data and relationships.

Primary keys and foreign keys help maintain record identity and referential integrity. Constraints and indexes support data validation and query access.

### Fulfillment Node Selection

The allocation process considers active nodes, inventory availability, remaining warehouse capacity, node coverage, and carrier service compatibility.

Eligible nodes are ranked by current same-day capacity usage and then by node ID.

This provides a deterministic selection method.

### Partial Allocation and Split Shipments

A single order line may be fulfilled from multiple nodes when one node cannot satisfy the complete requested quantity.

If inventory or capacity is insufficient, the remaining quantity stays unallocated rather than exceeding available resources.

### Delivery Promise Calculation

Delivery promises use UTC timestamps, weekday transit days, carrier service rules, cutoff times, and a synthetic holiday calendar.

This avoids treating every calendar day as a working delivery day.

### Shipment Tracking

Tracking events are stored as ordered, append-only records for each shipment.

Delivery outcomes include deterministic carrier-based delays of zero to two days.

### Ground Truth and Anomaly Separation

Five deliberately invalid anomaly examples are stored separately from normal operational data.

This keeps the generated operational records separate from the labeled examples used for validation and evaluation.

## 4. Assumptions

- All generated operational data is synthetic.
- Carrier names, service behavior, zones, holidays, and delivery outcomes are simulated.
- Warehouse capacity records represent the capacity available to the allocation workflow.
- Delivery promise calculations follow the business rules implemented in the project.
- Carrier delays are simulated and do not represent actual carrier performance.
- The fixed seed is used for reproducibility.

## 5. Testing and Validation

The project includes automated schema and workflow tests.

The local test command is:

```powershell
python -m unittest discover -s tests -v
```

The six tests passed during the reported local run.

The full generated dataset contains:

- 50,000 orders
- 64,096 order lines
- 500 SKUs
- 20 fulfillment nodes
- 10 carriers
- 40,010 shipments
- 100,000 tracking events

Reported database validation results:

- SQLite integrity check: `ok`
- Foreign key violations: `0`
- Inventory allocation compliance: `100%`
- Warehouse capacity compliance: `100%`
- Carrier compatibility: `100%`
- Promise calculation accuracy: `100%`
- Tracking lifecycle validity: `100%`
- Order-level status accuracy: `100%`

Two same-seed full generation runs were also reported to produce matching entity counts and CSV checksums.

## 6. Trade-offs

- SQLite keeps the project lightweight and easy to run locally, but it is not intended to demonstrate a distributed production database.
- Synthetic data makes testing repeatable and safe, but cannot represent every real-world fulfillment condition.
- Deterministic node ranking improves reproducibility, but more advanced optimization algorithms could produce different allocation decisions.
- Simulated carrier delays allow delivery scenarios to be tested, but actual carrier integrations would be needed for production use.

## 7. Limitations and Future Improvements

- Carrier information and delivery behavior are synthetic.
- The project does not connect to live warehouse management or carrier systems.
- The allocation strategy uses deterministic ranking rather than a global cost or optimization solver.
- The generated dataset represents selected business scenarios, not every possible operational condition.

Possible future improvements include live carrier integrations, configurable allocation strategies, more advanced optimization, and performance testing with larger datasets.

## 8. Conclusion

The project demonstrates an end-to-end synthetic fulfillment workflow with constrained inventory allocation, delivery promise calculation, shipment tracking, anomaly examples, reproducible data generation, and automated validation.

Its correctness is evaluated through database integrity checks, automated tests, cross-record validation, and operational metrics.