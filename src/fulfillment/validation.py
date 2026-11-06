"""Cross-row and lifecycle validation for generated fulfillment datasets."""
import sqlite3


def validate(conn: sqlite3.Connection) -> list[str]:
    errors = []
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        errors.append("SQLite integrity_check failed")
    if list(conn.execute("PRAGMA foreign_key_check")):
        errors.append("foreign key violations found")
    checks = {
        "order quantity reconciliation": """SELECT ol.order_line_id FROM order_lines ol LEFT JOIN shipment_lines sl USING(order_line_id) GROUP BY ol.order_line_id HAVING COALESCE(SUM(sl.allocated_quantity),0)>ol.quantity""",
        "carrier service compatibility": """SELECT s.shipment_id FROM shipments s LEFT JOIN carrier_service_levels c ON c.carrier_id=s.carrier_id AND c.service_level_id=s.service_level_id WHERE c.carrier_id IS NULL""",
        "service zone compatibility": """SELECT s.shipment_id FROM shipments s LEFT JOIN service_zones z ON z.service_level_id=s.service_level_id AND z.zone_id=s.destination_zone_id WHERE z.zone_id IS NULL""",
        "node zone compatibility": """SELECT s.shipment_id FROM shipments s LEFT JOIN node_service_zones z ON z.node_id=s.node_id AND z.zone_id=s.destination_zone_id WHERE z.node_id IS NULL""",
        "tracking sequence time order": """SELECT a.shipment_id FROM tracking_events a JOIN tracking_events b ON b.shipment_id=a.shipment_id AND b.event_sequence=a.event_sequence+1 WHERE b.event_at<a.event_at""",
        "delivery after pickup": """SELECT d.shipment_id FROM tracking_events d JOIN tracking_events p USING(shipment_id) WHERE d.event_status='delivered' AND p.event_status='picked_up' AND d.event_at<p.event_at""",
        "promise after order": """SELECT o.order_id FROM orders o JOIN order_delivery_promises p USING(order_id) WHERE p.promised_at<o.ordered_at""",
        "inventory reservation reconciliation": """SELECT i.node_id FROM inventory i WHERE i.reserved_quantity<>COALESCE((SELECT SUM(t.quantity) FROM inventory_transactions t WHERE t.node_id=i.node_id AND t.sku_id=i.sku_id AND t.transaction_type='reserve'),0) OR i.reserved_quantity>i.on_hand_quantity""",
        "warehouse daily capacity": """SELECT s.node_id FROM shipments s JOIN shipment_lines sl USING(shipment_id) GROUP BY s.node_id,date(s.created_at) HAVING SUM(sl.allocated_quantity)>COALESCE((SELECT c.capacity_units FROM warehouse_capacity c WHERE c.node_id=s.node_id AND c.capacity_date=date(s.created_at)),0)""",
        "shipment allocation reconciliation": """SELECT ol.order_line_id FROM order_lines ol LEFT JOIN shipment_lines sl USING(order_line_id) GROUP BY ol.order_line_id HAVING COALESCE(SUM(sl.allocated_quantity),0)>ol.quantity""",
        "order status rollup": """SELECT o.order_id FROM orders o WHERE (o.status='delivered')<>(EXISTS(SELECT 1 FROM shipments s WHERE s.order_id=o.order_id) AND NOT EXISTS(SELECT 1 FROM shipments s WHERE s.order_id=o.order_id AND s.status<>'delivered') AND NOT EXISTS(SELECT 1 FROM order_lines ol WHERE ol.order_id=o.order_id AND COALESCE((SELECT SUM(sl.allocated_quantity) FROM shipment_lines sl WHERE sl.order_line_id=ol.order_line_id),0)<ol.quantity))""",
    }
    for name, sql in checks.items():
        if conn.execute(sql+" LIMIT 1").fetchone():
            errors.append(name+" failed")
    return errors


def summary(conn: sqlite3.Connection) -> dict:
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    counts = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
    return {"counts": counts, "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0], "foreign_key_violations": len(list(conn.execute("PRAGMA foreign_key_check"))), "validation_errors": validate(conn)}
