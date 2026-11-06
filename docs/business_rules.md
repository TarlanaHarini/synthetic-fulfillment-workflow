# Business rules and implementation status

The deterministic generator and validators implement the rules below for generated baseline records. Invalid examples are emitted separately in `anomaly_inputs.*` and labeled in `ground_truth.*`; they are excluded from operational tables.

1. Inventory eligibility: on-hand minus active reservations must cover requested units; record reserve/release/consume/restock/adjustment as new transaction rows.
2. Capacity: node/date handling usage cannot exceed warehouse capacity.
3. Node selection: eligible active stock, node-zone coverage, and capacity, with documented deterministic rank/tie-break.
4. Split shipments: line allocation may span shipments; valid baseline sums to requested units and never exceeds them.
5. Carrier and service: pair must exist in CarrierServiceLevel and destination in ServiceZone.
6. Dispatch schedule uses local timezone/cutoff, weekends and node holiday calendar.
7. Promise derives from order time, allocation readiness, dispatch, transit duration, and business calendars; revisions append. Order promise reflects complete split-order delivery under the selected policy.
8. Tracking transitions: label_created -> picked_up -> in_transit -> out_for_delivery -> delivered. Exception may interrupt picked_up/in_transit/out_for_delivery; exception_cleared resumes a valid in-progress state. return_initiated -> returned. Delivered, returned, cancelled are terminal. Sequence timestamps are nondecreasing. Exception status requires exception code. Event counts vary per shipment; aggregate requested event count is exact.
9. Actual outcome and lateness derive from tracking and applicable promise.
10. Order status derives from line quantities and shipment outcomes; split order is delivered only after all required quantity and shipments complete.
11. Ground truth is stored separately from operational features; validators detect invalid cases without relying on labels.
12. Inject five invalid scenarios only after valid baseline: promise before order, over-allocation, unsupported service zone, delivery before dispatch, wrong split-shipment rollup.

Daily capacity and stock are deliberately finite; allocation across eligible nodes is partial when a line cannot be completed at one node. Numeric reservation records reconcile to the inventory reserved quantity. Dispatch dates apply the node cutoff, weekends, and calendar holidays. Carrier delivery outcomes apply a deterministic carrier delay profile of zero to two working days. Promise and tracking timestamps are stored in UTC.

Row-level structural checks are SQLite constraints. Cross-row arithmetic, transitions, and temporal ordering are later rule/validator implementation. No generation, allocation, promise calculation, tracking, anomaly injection, metrics, or pipeline is implemented now.
