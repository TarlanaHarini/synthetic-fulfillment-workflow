"""Deterministic synthetic fulfillment data and workflow implementation.

The generator writes a fresh database and exports operational tables separately
from anomaly labels. All timestamps are UTC ISO-8601 strings.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sqlite3
import tempfile
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .config import FULL, SEED, STARTER, DatasetConfig
from .db import initialize_database
from .validation import validate

BASE_TIME = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
TABLES = ["zones", "holiday_calendars", "holidays", "skus", "fulfillment_nodes", "carriers", "service_levels", "carrier_service_levels", "service_zones", "node_service_zones", "inventory", "warehouse_capacity", "orders", "order_lines", "order_delivery_promises", "shipments", "shipment_lines", "shipment_delivery_promises", "inventory_transactions", "tracking_events"]
ISSUES = ["promise_before_order", "allocation_exceeds_stock", "unsupported_carrier_zone", "delivery_before_dispatch", "split_status_rollup"]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def add_business_days(start: date, days: int, holidays: set[date]) -> date:
    d, added = start, 0
    while added < days:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            added += 1
    return d


SYNTHETIC_HOLIDAYS = {date(2026, 1, 1), date(2026, 7, 4), date(2026, 12, 25)}


def dispatch_date(ordered_at: datetime, cutoff: time, holidays: set[date] = SYNTHETIC_HOLIDAYS) -> date:
    """Return the next open dispatch date after applying the node's local cutoff."""
    candidate = ordered_at.date()
    if ordered_at.timetz().replace(tzinfo=None) >= cutoff:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate += timedelta(days=1)
    return candidate


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript((Path(__file__).with_name("schema.sql")).read_text(encoding="utf8"))
    conn.commit()


def _insert(conn, table, columns, rows):
    if rows:
        q = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
        conn.executemany(q, rows)


def generate(database: Path, out_dir: Path, cfg: DatasetConfig = STARTER, seed: int = SEED, anomalies: bool = True) -> dict:
    """Generate a reproducible dataset in a new SQLite database and exports."""
    rng = random.Random(seed)
    database.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = initialize_database(database)
    try:
        # Master/reference entities first.
        _insert(conn, "zones", ["zone_id", "zone_code", "name", "region_code"], [(i, f"Z{i:02}", f"Zone {i}", f"R{(i-1)//5+1}") for i in range(1, 11)])
        _insert(conn, "holiday_calendars", ["holiday_calendar_code", "calendar_name", "region_code"], [(f"HC{i:02}", f"Calendar {i}", f"R{i}") for i in range(1, 5)])
        holidays = []
        for i in range(1, 5):
            for day in (date(2026, 1, 1), date(2026, 7, 4), date(2026, 12, 25)):
                holidays.append((f"HC{i:02}", day.isoformat(), "Synthetic public holiday"))
        _insert(conn, "holidays", ["holiday_calendar_code", "holiday_date", "holiday_name"], holidays)
        _insert(conn, "skus", ["sku_id", "sku_code", "description", "unit_weight_kg"], [(i, f"SKU-{i:05}", f"Synthetic item {i}", round(rng.uniform(.1, 12), 3)) for i in range(1, cfg.skus+1)])
        _insert(conn, "fulfillment_nodes", ["node_id", "node_code", "name", "timezone", "cutoff_local_time", "holiday_calendar_code"], [(i, f"FUL-2026-{i:06}", f"Fulfillment Node {i}", "UTC", "17:00", f"HC{(i-1)%4+1:02}") for i in range(1, cfg.nodes+1)])
        _insert(conn, "carriers", ["carrier_id", "carrier_code", "name"], [(i, f"CAR{i:02}", f"Synthetic Carrier {i}") for i in range(1, cfg.carriers+1)])
        services = [(1, "GROUND", "Ground", 3), (2, "EXPRESS", "Express", 1), (3, "ECONOMY", "Economy", 5)]
        _insert(conn, "service_levels", ["service_level_id", "service_code", "name", "transit_business_days"], services)
        _insert(conn, "carrier_service_levels", ["carrier_id", "service_level_id"], [(c, s) for c in range(1, cfg.carriers+1) for s in (1, 2, 3)])
        _insert(conn, "service_zones", ["service_level_id", "zone_id"], [(s, z) for s in (1, 2, 3) for z in range(1, 11)])
        _insert(conn, "node_service_zones", ["node_id", "zone_id"], [(n, z) for n in range(1, cfg.nodes+1) for z in range(1, 11)])
        stock_rows = []
        stock = {}
        for n in range(1, cfg.nodes+1):
            for s in range(1, cfg.skus+1):
                qty = rng.randint(0, 20)
                stock[n, s] = qty
                stock_rows.append((n, s, qty, 0))
        _insert(conn, "inventory", ["node_id", "sku_id", "on_hand_quantity", "reserved_quantity"], stock_rows)
        daily_capacity = max(3, cfg.orders//cfg.nodes//200)
        cap = [(n, (BASE_TIME.date()+timedelta(days=d)).isoformat(), daily_capacity) for n in range(1, cfg.nodes+1) for d in range(370)]
        _insert(conn, "warehouse_capacity", ["node_id", "capacity_date", "capacity_units"], cap)

        # Orders and lines. Allocation uses a deterministic score among nodes with stock, coverage and capacity.
        order_rows, line_rows, allocations, promise_rows, ship_rows, shipline_rows = [], [], [], [], [], []
        shipment_id = 0
        capacity_used = Counter()
        available = dict(stock)
        line_id = 0
        for oid in range(1, cfg.orders+1):
            ordered = BASE_TIME + timedelta(minutes=oid*7 + rng.randrange(60))
            zone = (oid-1) % 10 + 1
            order_rows.append((oid, f"ORD-2026-{oid:06}", iso(ordered), zone, "pending", "USD", iso(ordered)))
            line_count = 1 if rng.random() < .72 else 2
            total_promised = ordered.date()
            incomplete = False
            for ln in range(1, line_count+1):
                line_id += 1
                sku = rng.randint(1, cfg.skus)
                qty = rng.choices([1, 2, 3, 4], [60, 25, 12, 3])[0]
                line_rows.append((line_id, oid, ln, sku, qty, round(rng.uniform(5, 200), 2)))
                candidates = []
                for n in range(1, cfg.nodes+1):
                    day = ordered.date().isoformat()
                    cap_key = (n, day)
                    cap_limit = daily_capacity
                    free_capacity = cap_limit - capacity_used[cap_key]
                    allocatable = min(available[n, sku], free_capacity)
                    if allocatable > 0:
                        candidates.append((capacity_used[cap_key], n, allocatable))
                remaining = qty
                for _, node, allocatable in sorted(candidates):
                    if remaining <= 0:
                        break
                    portion = min(remaining, allocatable)
                    available[node, sku] -= portion
                    capacity_used[(node, ordered.date().isoformat())] += portion
                    shipment_id += 1
                    sid = shipment_id
                    service = (1, 2, 3)[(oid + ln) % 3]
                    carrier = (oid-1) % cfg.carriers + 1
                    ship_rows.append((sid, f"SHP-2026-{sid:06}", oid, node, carrier, service, zone, "allocated", iso(ordered)))
                    shipline_rows.append((sid, oid, line_id, portion))
                    allocations.append((node, sku, oid, line_id, sid, portion, ordered))
                    transit = next(x[3] for x in services if x[0] == service)
                    eta = add_business_days(dispatch_date(ordered, time(17)), transit, SYNTHETIC_HOLIDAYS)
                    total_promised = max(total_promised, eta)
                    remaining -= portion
                incomplete = incomplete or remaining > 0
            if incomplete:
                total_promised = max(total_promised, add_business_days(ordered.date(), 7, SYNTHETIC_HOLIDAYS))
            promised_at = datetime.combine(total_promised, time(23, 59), timezone.utc)
            if promised_at < ordered:
                promised_at = ordered + timedelta(hours=1)
            promise_rows.append((oid, 1, iso(promised_at), iso(ordered), "calendar-v1", "Synthetic calendar, transit, and constrained-stock estimate"))
        _insert(conn, "orders", ["order_id","order_number","ordered_at","destination_zone_id","status","currency","created_at"], order_rows)
        _insert(conn, "order_lines", ["order_line_id","order_id","line_number","sku_id","quantity","unit_price"], line_rows)
        _insert(conn, "order_delivery_promises", ["order_id","revision","promised_at","calculated_at","rule_version","reason"], promise_rows)
        _insert(conn, "shipments", ["shipment_id","shipment_number","order_id","node_id","carrier_id","service_level_id","destination_zone_id","status","created_at"], ship_rows)
        _insert(conn, "shipment_lines", ["shipment_id","order_id","order_line_id","allocated_quantity"], shipline_rows)
        _insert(conn, "shipment_delivery_promises", ["shipment_id","revision","promised_at","calculated_at","rule_version","reason"], [(s[0], 1, iso(datetime.combine(add_business_days(dispatch_date(datetime.fromisoformat(s[8].replace('Z','+00:00')), time(17)), next(x[3] for x in services if x[0]==s[5]), SYNTHETIC_HOLIDAYS), time(23, 59), timezone.utc)), s[8], "calendar-v1", "Synthetic carrier calendar and cutoff") for s in ship_rows])
        _insert(conn, "inventory_transactions", ["inventory_transaction_id","transaction_key","node_id","sku_id","order_id","order_line_id","shipment_id","transaction_type","quantity","occurred_at","note"], [(i, f"TX-{i:09}", n, sku, oid, lid, sid, "reserve", qty, iso(dt), "Generated allocation") for i,(n,sku,oid,lid,sid,qty,dt) in enumerate(allocations,1)])
        for (node_id, sku_id), initial in stock.items():
            conn.execute("UPDATE inventory SET reserved_quantity=? WHERE node_id=? AND sku_id=?", (initial-available[node_id,sku_id], node_id, sku_id))

        # Create a deterministic exact tracking-event budget with append-only event history.
        event_budget = cfg.tracking_events
        tracking = []
        if ship_rows and event_budget:
            base, rem = divmod(event_budget, len(ship_rows))
            event_counts = [base] * len(ship_rows)
            for i in range(rem):
                event_counts[i] += 1
            # With the full preset, distribute surplus evenly after guaranteeing
            # one first scan per shipment, so a substantial cohort reaches delivery.
            if event_budget >= 4 * len(ship_rows):
                event_counts = [4] * len(ship_rows)
                for i in range(event_budget - 4 * len(ship_rows)):
                    event_counts[i % len(event_counts)] += 1
            elif event_budget >= len(ship_rows):
                surplus = event_budget - len(ship_rows)
                event_counts = [1] * len(ship_rows)
                for i in range(surplus // 3):
                    event_counts[i] += 3
                for i in range(surplus % 3):
                    event_counts[surplus // 3 + i] += 1
            teid = 0
            for i, s in enumerate(ship_rows):
                count = event_counts[i]
                created = datetime.fromisoformat(s[8].replace("Z", "+00:00"))
                carrier_delay_days = (s[4] - 1) % 3
                dispatch_day = dispatch_date(created, time(17))
                dispatch_at = max(created + timedelta(hours=3), datetime.combine(dispatch_day, time(9), timezone.utc))
                transit_days = next(x[3] for x in services if x[0] == s[5])
                planned_delivery_date = add_business_days(dispatch_day, transit_days, SYNTHETIC_HOLIDAYS)
                actual_delivery_date = add_business_days(planned_delivery_date, carrier_delay_days, SYNTHETIC_HOLIDAYS)
                in_transit_at = datetime.combine(add_business_days(dispatch_day, 1, SYNTHETIC_HOLIDAYS), time(9), timezone.utc)
                delivery_at = datetime.combine(actual_delivery_date, time(17), timezone.utc)
                sequence = [("label_created", "label_created", created), ("picked_up", "picked_up", created+timedelta(hours=3))]
                sequence[1] = ("picked_up", "picked_up", dispatch_at)
                if count == 3:
                    sequence.append(("in_transit", "in_transit", in_transit_at))
                elif count == 4:
                    sequence.extend([("in_transit", "in_transit", in_transit_at), ("delivered", "delivered", delivery_at)])
                elif count >= 5:
                    sequence.extend(("in_transit", "in_transit", in_transit_at+timedelta(minutes=k)) for k in range(count-4))
                    sequence.extend([("out_for_delivery", "out_for_delivery", delivery_at-timedelta(minutes=30)), ("delivered", "delivered", delivery_at)])
                sequence = sequence[:count]
                for j, (typ, stat, when) in enumerate(sequence):
                    teid += 1
                    tracking.append((teid, s[0], j+1, typ, stat, iso(when), "Synthetic Hub", None, None, f"TRK-{s[0]:06}-{j+1:03}"))
            _insert(conn, "tracking_events", ["tracking_event_id","shipment_id","event_sequence","event_type","event_status","event_at","location","exception_code","exception_detail","source_event_id"], tracking)
        # Update operational statuses based on generated allocations and delivered tracking.
        conn.execute("UPDATE shipments SET status=CASE (SELECT event_status FROM tracking_events e WHERE e.shipment_id=shipments.shipment_id ORDER BY event_sequence DESC LIMIT 1) WHEN 'delivered' THEN 'delivered' WHEN 'in_transit' THEN 'in_transit' WHEN 'picked_up' THEN 'dispatched' WHEN 'label_created' THEN 'label_created' ELSE 'allocated' END")
        conn.execute("UPDATE orders SET status=CASE WHEN NOT EXISTS(SELECT 1 FROM shipments s WHERE s.order_id=orders.order_id) THEN 'exception' WHEN EXISTS(SELECT 1 FROM order_lines ol WHERE ol.order_id=orders.order_id AND COALESCE((SELECT SUM(sl.allocated_quantity) FROM shipment_lines sl WHERE sl.order_line_id=ol.order_line_id),0)<ol.quantity) THEN 'partially_fulfilled' WHEN EXISTS(SELECT 1 FROM shipments s WHERE s.order_id=orders.order_id AND s.status<>'delivered') THEN 'fulfilled' ELSE 'delivered' END")

        ground_truth = []
        if anomalies and cfg.orders >= 5 and ship_rows:
            # Invalid records are explicitly isolated in a sidecar so normal operational inputs remain clean.
            examples = [
                ("ANOM-001", "promise_before_order", "promised_at precedes ordered_at", {"ordered_at":"2026-01-02T08:00:00Z","promised_at":"2026-01-01T20:00:00Z"}),
                ("ANOM-002", "allocation_exceeds_stock", "requested allocation exceeds available stock", {"node_id":1,"sku_id":1,"available_quantity":2,"allocated_quantity":3}),
                ("ANOM-003", "unsupported_carrier_zone", "carrier service-zone combination is unsupported", {"carrier_id":1,"service_level_id":1,"destination_zone_id":99}),
                ("ANOM-004", "delivery_before_dispatch", "delivered event timestamp precedes pickup", {"picked_up_at":"2026-01-03T12:00:00Z","delivered_at":"2026-01-03T10:00:00Z"}),
                ("ANOM-005", "split_status_rollup", "order marked delivered while a required shipment is not delivered", {"order_status":"delivered","shipment_statuses":["delivered","in_transit"]}),
            ]
            anomaly_inputs = [{"case_id": rid, "record": payload} for rid, _, _, payload in examples]
            ground_truth = [{"case_id": rid, "issue_type": issue, "description": desc, "ground_truth": "expected_invalid"} for rid, issue, desc, _ in examples]
        conn.commit()

        # Export every table to CSV and JSON, plus reproducibility manifest.
        counts, checksums = {}, {}
        for table in TABLES:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
            if table == "order_delivery_promises":
                for row in rows:
                    row["promise_number"] = f"PROM-ORD-2026-{row['order_id']:06}-{row['revision']:02}"
            counts[table] = len(rows)
            csv_path = out_dir / f"{table}.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                if rows:
                    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
                else:
                    f.write("\n")
            (out_dir / f"{table}.json").write_text(json.dumps(rows, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            checksums[csv_path.name] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        (out_dir / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        (out_dir / "anomaly_inputs.json").write_text(json.dumps(anomaly_inputs if anomalies and cfg.orders >= 5 and ship_rows else [], indent=2, sort_keys=True)+"\n", encoding="utf-8")
        with (out_dir / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["case_id","issue_type","description","ground_truth"]); w.writeheader(); w.writerows(ground_truth)
        # SQLite text dump is portable seed SQL.
        (out_dir / "seed.sql").write_text("\n".join(conn.iterdump())+"\n", encoding="utf-8")
        violations = list(conn.execute("PRAGMA foreign_key_check"))
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        report = {"seed": seed, "dataset": cfg.name, "counts": counts, "ground_truth_count": len(ground_truth), "integrity_check": integrity, "foreign_key_violations": len(violations), "validation_errors": validate(conn), "checksums": checksums}
        (out_dir / "validation_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        metrics = evaluate(conn)
        (out_dir / "evaluation_report.json").write_text(json.dumps(metrics, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        (out_dir / "source_manifest.json").write_text(json.dumps({"provenance":"Entirely synthetic; generated locally; no external datasets or carrier systems used.","generator":"src.fulfillment.workflow","schema":"src.fulfillment/schema.sql","seed":seed,"dataset":cfg.name,"database":str(database)}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        (out_dir / "acceptance_report.md").write_text("# Acceptance report\n\n"+f"- Dataset: `{cfg.name}`; seed `{seed}`.\n- Orders: {counts.get('orders',0)}; order lines: {counts.get('order_lines',0)}; shipments: {counts.get('shipments',0)}; tracking events: {counts.get('tracking_events',0)}.\n- SQLite integrity: `{integrity}`; foreign key violations: {len(violations)}.\n- Ground-truth cases: {len(ground_truth)} (5 required anomaly types listed in sidecar).\n- Evaluation metrics: see `evaluation_report.json`.\n- Generated inputs and exports contain synthetic data only.\n", encoding="utf-8")
        return report | {"metrics": metrics, "ground_truth": ground_truth}
    finally:
        conn.close()


def evaluate(conn: sqlite3.Connection) -> dict:
    lines = conn.execute("SELECT COALESCE(SUM(quantity),0) FROM order_lines").fetchone()[0]
    assigned = conn.execute("SELECT COALESCE(SUM(allocated_quantity),0) FROM shipment_lines").fetchone()[0]
    tx_bad = conn.execute("SELECT COUNT(*) FROM inventory i WHERE i.reserved_quantity>i.on_hand_quantity").fetchone()[0]
    cap_bad = conn.execute("SELECT COUNT(*) FROM (SELECT s.node_id,date(s.created_at) d,SUM(sl.allocated_quantity) q FROM shipments s JOIN shipment_lines sl USING(shipment_id) GROUP BY s.node_id,d HAVING q>(SELECT capacity_units FROM warehouse_capacity c WHERE c.node_id=s.node_id AND c.capacity_date=date(s.created_at)))").fetchone()[0]
    carrier_bad = conn.execute("SELECT COUNT(*) FROM shipments s LEFT JOIN carrier_service_levels c USING(carrier_id,service_level_id) LEFT JOIN service_zones z ON z.service_level_id=s.service_level_id AND z.zone_id=s.destination_zone_id WHERE c.carrier_id IS NULL OR z.zone_id IS NULL").fetchone()[0]
    delivered = conn.execute("SELECT COUNT(*) FROM shipments WHERE status='delivered'").fetchone()[0]
    ontime = conn.execute("SELECT COUNT(*) FROM shipments s JOIN shipment_delivery_promises p USING(shipment_id) JOIN tracking_events t ON t.shipment_id=s.shipment_id AND t.event_status='delivered' WHERE t.event_at<=p.promised_at").fetchone()[0]
    delivered_events = conn.execute("SELECT COUNT(*) FROM tracking_events WHERE event_status='delivered'").fetchone()[0]
    bad_time = conn.execute("SELECT COUNT(*) FROM tracking_events d JOIN tracking_events p USING(shipment_id) WHERE d.event_status='delivered' AND p.event_status='picked_up' AND d.event_at<p.event_at").fetchone()[0]
    zero_stock_positions = conn.execute("SELECT COUNT(*) FROM inventory WHERE on_hand_quantity=0").fetchone()[0]
    capacity_units = conn.execute("SELECT COALESCE(SUM(capacity_units),0) FROM warehouse_capacity").fetchone()[0]
    errs = validate(conn)
    n_orders = max(1, conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0])
    promises = {r["order_id"]: r["promised_at"] for r in conn.execute("SELECT order_id,promised_at FROM order_delivery_promises WHERE revision=(SELECT MAX(p2.revision) FROM order_delivery_promises p2 WHERE p2.order_id=order_delivery_promises.order_id)")}
    order_info = {r["order_id"]: datetime.fromisoformat(r["ordered_at"].replace("Z", "+00:00")) for r in conn.execute("SELECT order_id,ordered_at FROM orders")}
    shipment_etas = {oid: [] for oid in order_info}
    for r in conn.execute("SELECT s.order_id,s.created_at,sl.transit_business_days FROM shipments s JOIN service_levels sl USING(service_level_id)"):
        created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        ready = dispatch_date(created, time(17))
        shipment_etas[r["order_id"]].append(add_business_days(ready, r["transit_business_days"], SYNTHETIC_HOLIDAYS))
    incomplete_orders = {r["order_id"] for r in conn.execute("SELECT ol.order_id FROM order_lines ol LEFT JOIN (SELECT order_line_id,SUM(allocated_quantity) allocated FROM shipment_lines GROUP BY order_line_id) a USING(order_line_id) GROUP BY ol.order_id HAVING SUM(COALESCE(a.allocated,0))<SUM(ol.quantity)")}
    matches = 0
    for oid, ordered in order_info.items():
        days = shipment_etas[oid]
        expected = max(days) if days else ordered.date()
        if oid in incomplete_orders:
            expected = max(expected, add_business_days(ordered.date(), 7, SYNTHETIC_HOLIDAYS))
        expected_at = datetime.combine(expected, time(23, 59), timezone.utc)
        if expected_at < ordered:
            expected_at = ordered + timedelta(hours=1)
        if promises.get(oid) == iso(expected_at):
            matches += 1
    promise_accuracy = matches / n_orders
    return {"inventory_allocation_compliance": 1.0 if not tx_bad else 0.0, "zero_stock_positions": zero_stock_positions, "warehouse_capacity_compliance": round(1-cap_bad/max(1,conn.execute("SELECT COUNT(DISTINCT node_id||':'||date(created_at)) FROM shipments").fetchone()[0]),6), "warehouse_capacity_utilization": round(assigned/max(1,capacity_units),6), "promise_calculation_accuracy": round(promise_accuracy,6), "carrier_compatibility": round(1-carrier_bad/max(1,conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]),6), "on_time_delivery_rate": round(ontime/max(1,delivered_events),6), "split_shipment_rate": round(conn.execute("SELECT COUNT(*) FROM (SELECT order_id FROM shipments GROUP BY order_id HAVING COUNT(*)>1)").fetchone()[0]/n_orders,6), "exception_rate": round(conn.execute("SELECT COUNT(*) FROM orders WHERE status='exception'").fetchone()[0]/n_orders,6), "tracking_lifecycle_validity": round(1-bad_time/max(1,delivered_events),6), "order_level_status_accuracy": 1.0 if not any("status" in e for e in errs) else 0.0, "allocated_unit_rate": round(assigned/max(1,lines),6), "unallocated_units": lines-assigned, "unallocated_lines": conn.execute("SELECT COUNT(*) FROM order_lines ol WHERE COALESCE((SELECT SUM(allocated_quantity) FROM shipment_lines sl WHERE sl.order_line_id=ol.order_line_id),0)<ol.quantity").fetchone()[0]}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",choices=["starter","full"],default="starter")
    p.add_argument("--orders",type=int); p.add_argument("--skus",type=int); p.add_argument("--nodes",type=int); p.add_argument("--carriers",type=int); p.add_argument("--tracking-events",type=int)
    p.add_argument("--seed",type=int,default=SEED); p.add_argument("--database",type=Path,default=Path("fulfillment.generated.sqlite3")); p.add_argument("--output",type=Path,default=Path("generated")); p.add_argument("--no-anomalies",action="store_true")
    a=p.parse_args(argv); base=FULL if a.dataset=="full" else STARTER
    cfg=DatasetConfig(a.dataset,a.orders or base.orders,a.skus or base.skus,a.nodes or base.nodes,a.carriers or base.carriers,a.tracking_events or base.tracking_events)
    print(json.dumps(generate(a.database,a.output,cfg,a.seed,not a.no_anomalies),indent=2,sort_keys=True))

if __name__ == "__main__": main()
