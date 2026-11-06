# Data dictionary

Generated from the initialized SQLite schema. SQLite type, nullability, default, primary-key order, and foreign-key target are read from PRAGMA. CHECK and uniqueness details are included in each table DDL below. Timestamps use ISO-8601 text; dates use ISO YYYY-MM-DD.

## carrier_service_levels

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| carrier_id | INTEGER | no | ? | 1 | carriers.carrier_id |
| service_level_id | INTEGER | no | ? | 2 | service_levels.service_level_id |

DDL:

    CREATE TABLE carrier_service_levels(carrier_id INTEGER NOT NULL REFERENCES carriers,service_level_id INTEGER NOT NULL REFERENCES service_levels,PRIMARY KEY(carrier_id,service_level_id))

## carriers

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| carrier_id | INTEGER | no | ? | 1 | ? |
| carrier_code | TEXT | no | ? | 0 | ? |
| name | TEXT | no | ? | 0 | ? |
| active | INTEGER | no | 1 | 0 | ? |

DDL:

    CREATE TABLE carriers(carrier_id INTEGER PRIMARY KEY,carrier_code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)))

## fulfillment_nodes

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| node_id | INTEGER | no | ? | 1 | ? |
| node_code | TEXT | no | ? | 0 | ? |
| name | TEXT | no | ? | 0 | ? |
| timezone | TEXT | no | ? | 0 | ? |
| cutoff_local_time | TEXT | no, 24-hour HH:MM CHECK | ? | 0 | ? |
| holiday_calendar_code | TEXT | no | ? | 0 | holiday_calendars.holiday_calendar_code |
| active | INTEGER | no | 1 | 0 | ? |

DDL:

    CREATE TABLE fulfillment_nodes(node_id INTEGER PRIMARY KEY,node_code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,timezone TEXT NOT NULL,cutoff_local_time TEXT NOT NULL CHECK(length(cutoff_local_time)=5 AND (cutoff_local_time GLOB '[01][0-9]:[0-5][0-9]' OR cutoff_local_time GLOB '2[0-3]:[0-5][0-9]')),holiday_calendar_code TEXT NOT NULL REFERENCES holiday_calendars,active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)))

## holiday_calendars

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| holiday_calendar_code | TEXT | no | ? | 1 | ? |
| calendar_name | TEXT | no | ? | 0 | ? |
| region_code | TEXT | no | ? | 0 | ? |

DDL:

    CREATE TABLE holiday_calendars(holiday_calendar_code TEXT PRIMARY KEY,calendar_name TEXT NOT NULL,region_code TEXT NOT NULL)

## holidays

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| holiday_calendar_code | TEXT | no | ? | 1 | holiday_calendars.holiday_calendar_code |
| holiday_date | TEXT | no | ? | 2 | ? |
| holiday_name | TEXT | no | ? | 0 | ? |

DDL:

    CREATE TABLE holidays(holiday_calendar_code TEXT NOT NULL REFERENCES holiday_calendars,holiday_date TEXT NOT NULL CHECK(date(holiday_date) IS NOT NULL),holiday_name TEXT NOT NULL,PRIMARY KEY(holiday_calendar_code,holiday_date))

## inventory

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| node_id | INTEGER | no | ? | 1 | fulfillment_nodes.node_id |
| sku_id | INTEGER | no | ? | 2 | skus.sku_id |
| on_hand_quantity | INTEGER | no | ? | 0 | ? |
| reserved_quantity | INTEGER | no | 0 | 0 | ? |

DDL:

    CREATE TABLE inventory(node_id INTEGER NOT NULL REFERENCES fulfillment_nodes,sku_id INTEGER NOT NULL REFERENCES skus,on_hand_quantity INTEGER NOT NULL CHECK(on_hand_quantity>=0),reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK(reserved_quantity>=0),PRIMARY KEY(node_id,sku_id),CHECK(reserved_quantity<=on_hand_quantity))

## inventory_transactions

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| inventory_transaction_id | INTEGER | no | ? | 1 | ? |
| transaction_key | TEXT | no | ? | 0 | ? |
| node_id | INTEGER | no | ? | 0 | inventory.node_id |
| sku_id | INTEGER | no | ? | 0 | inventory.sku_id |
| order_id | INTEGER | yes | ? | 0 | orders.order_id |
| order_line_id | INTEGER | yes | ? | 0 | order_lines.order_line_id |
| shipment_id | INTEGER | yes | ? | 0 | shipments.shipment_id |
| transaction_type | TEXT | no | ? | 0 | ? |
| quantity | INTEGER | no | ? | 0 | ? |
| occurred_at | TEXT | no | ? | 0 | ? |
| note | TEXT | yes | ? | 0 | ? |

DDL:

    CREATE TABLE inventory_transactions(inventory_transaction_id INTEGER PRIMARY KEY,transaction_key TEXT NOT NULL UNIQUE,node_id INTEGER NOT NULL,sku_id INTEGER NOT NULL,order_id INTEGER REFERENCES orders,order_line_id INTEGER REFERENCES order_lines,shipment_id INTEGER REFERENCES shipments,transaction_type TEXT NOT NULL CHECK(transaction_type IN('reserve','release','consume','restock','adjustment')),quantity INTEGER NOT NULL CHECK(quantity>0),occurred_at TEXT NOT NULL CHECK(datetime(occurred_at) IS NOT NULL),note TEXT,FOREIGN KEY(node_id,sku_id) REFERENCES inventory(node_id,sku_id))

## node_service_zones

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| node_id | INTEGER | no | ? | 1 | fulfillment_nodes.node_id |
| zone_id | INTEGER | no | ? | 2 | zones.zone_id |

DDL:

    CREATE TABLE node_service_zones(node_id INTEGER NOT NULL REFERENCES fulfillment_nodes,zone_id INTEGER NOT NULL REFERENCES zones,PRIMARY KEY(node_id,zone_id))

## order_delivery_promises

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| order_promise_id | INTEGER | no | ? | 1 | ? |
| order_id | INTEGER | no | ? | 0 | orders.order_id |
| revision | INTEGER | no | ? | 0 | ? |
| promised_at | TEXT | no | ? | 0 | ? |
| calculated_at | TEXT | no | ? | 0 | ? |
| rule_version | TEXT | no | ? | 0 | ? |
| reason | TEXT | yes | ? | 0 | ? |

DDL:

    CREATE TABLE order_delivery_promises(order_promise_id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders,revision INTEGER NOT NULL CHECK(revision>0),promised_at TEXT NOT NULL CHECK(datetime(promised_at) IS NOT NULL),calculated_at TEXT NOT NULL CHECK(datetime(calculated_at) IS NOT NULL),rule_version TEXT NOT NULL,reason TEXT,UNIQUE(order_id,revision))

## order_lines

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| order_line_id | INTEGER | no | ? | 1 | ? |
| order_id | INTEGER | no | ? | 0 | orders.order_id |
| line_number | INTEGER | no | ? | 0 | ? |
| sku_id | INTEGER | no | ? | 0 | skus.sku_id |
| quantity | INTEGER | no | ? | 0 | ? |
| unit_price | REAL | no | ? | 0 | ? |

DDL:

    CREATE TABLE order_lines(order_line_id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders,line_number INTEGER NOT NULL CHECK(line_number>0),sku_id INTEGER NOT NULL REFERENCES skus,quantity INTEGER NOT NULL CHECK(quantity>0),unit_price REAL NOT NULL CHECK(unit_price>=0),UNIQUE(order_id,line_number),UNIQUE(order_line_id,order_id))

## orders

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| order_id | INTEGER | no | ? | 1 | ? |
| order_number | TEXT | no | ? | 0 | ? |
| ordered_at | TEXT | no | ? | 0 | ? |
| destination_zone_id | INTEGER | no | ? | 0 | zones.zone_id |
| status | TEXT | no | ? | 0 | ? |
| currency | TEXT | no | ? | 0 | ? |
| created_at | TEXT | no | ? | 0 | ? |

DDL:

    CREATE TABLE orders(order_id INTEGER PRIMARY KEY,order_number TEXT NOT NULL UNIQUE,ordered_at TEXT NOT NULL CHECK(datetime(ordered_at) IS NOT NULL),destination_zone_id INTEGER NOT NULL REFERENCES zones,status TEXT NOT NULL CHECK(status IN('pending','allocated','partially_fulfilled','fulfilled','delivered','cancelled','exception')),currency TEXT NOT NULL CHECK(length(currency)=3),created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL))

## service_levels

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| service_level_id | INTEGER | no | ? | 1 | ? |
| service_code | TEXT | no | ? | 0 | ? |
| name | TEXT | no | ? | 0 | ? |
| transit_business_days | INTEGER | no | ? | 0 | ? |
| active | INTEGER | no | 1 | 0 | ? |

DDL:

    CREATE TABLE service_levels(service_level_id INTEGER PRIMARY KEY,service_code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,transit_business_days INTEGER NOT NULL CHECK(transit_business_days>=0),active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)))

## service_zones

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| service_level_id | INTEGER | no | ? | 1 | service_levels.service_level_id |
| zone_id | INTEGER | no | ? | 2 | zones.zone_id |

DDL:

    CREATE TABLE service_zones(service_level_id INTEGER NOT NULL REFERENCES service_levels,zone_id INTEGER NOT NULL REFERENCES zones,PRIMARY KEY(service_level_id,zone_id))

## shipment_delivery_promises

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| shipment_promise_id | INTEGER | no | ? | 1 | ? |
| shipment_id | INTEGER | no | ? | 0 | shipments.shipment_id |
| revision | INTEGER | no | ? | 0 | ? |
| promised_at | TEXT | no | ? | 0 | ? |
| calculated_at | TEXT | no | ? | 0 | ? |
| rule_version | TEXT | no | ? | 0 | ? |
| reason | TEXT | yes | ? | 0 | ? |

DDL:

    CREATE TABLE shipment_delivery_promises(shipment_promise_id INTEGER PRIMARY KEY,shipment_id INTEGER NOT NULL REFERENCES shipments,revision INTEGER NOT NULL CHECK(revision>0),promised_at TEXT NOT NULL CHECK(datetime(promised_at) IS NOT NULL),calculated_at TEXT NOT NULL CHECK(datetime(calculated_at) IS NOT NULL),rule_version TEXT NOT NULL,reason TEXT,UNIQUE(shipment_id,revision))

## shipment_lines

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| shipment_id | INTEGER | no | ? | 1 | shipments.shipment_id |
| order_id | INTEGER | no | ? | 0 | shipments.order_id |
| order_line_id | INTEGER | no | ? | 2 | order_lines.order_line_id |
| allocated_quantity | INTEGER | no | ? | 0 | ? |

DDL:

    CREATE TABLE shipment_lines(shipment_id INTEGER NOT NULL,order_id INTEGER NOT NULL,order_line_id INTEGER NOT NULL,allocated_quantity INTEGER NOT NULL CHECK(allocated_quantity>0),PRIMARY KEY(shipment_id,order_line_id),FOREIGN KEY(shipment_id,order_id) REFERENCES shipments(shipment_id,order_id),FOREIGN KEY(order_line_id,order_id) REFERENCES order_lines(order_line_id,order_id))

## shipments

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| shipment_id | INTEGER | no | ? | 1 | ? |
| shipment_number | TEXT | no | ? | 0 | ? |
| order_id | INTEGER | no | ? | 0 | orders.order_id |
| node_id | INTEGER | no | ? | 0 | fulfillment_nodes.node_id |
| carrier_id | INTEGER | no | ? | 0 | carriers.carrier_id |
| service_level_id | INTEGER | no | ? | 0 | service_levels.service_level_id |
| destination_zone_id | INTEGER | no | ? | 0 | zones.zone_id |
| status | TEXT | no | ? | 0 | ? |
| created_at | TEXT | no | ? | 0 | ? |

DDL:

    CREATE TABLE shipments(shipment_id INTEGER PRIMARY KEY,shipment_number TEXT NOT NULL UNIQUE,order_id INTEGER NOT NULL REFERENCES orders,node_id INTEGER NOT NULL REFERENCES fulfillment_nodes,carrier_id INTEGER NOT NULL REFERENCES carriers,service_level_id INTEGER NOT NULL REFERENCES service_levels,destination_zone_id INTEGER NOT NULL REFERENCES zones,status TEXT NOT NULL CHECK(status IN('planned','allocated','label_created','dispatched','in_transit','delivered','exception','returned','cancelled')),created_at TEXT NOT NULL CHECK(datetime(created_at) IS NOT NULL),UNIQUE(shipment_id,order_id))

## skus

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| sku_id | INTEGER | no | ? | 1 | ? |
| sku_code | TEXT | no | ? | 0 | ? |
| description | TEXT | no | ? | 0 | ? |
| unit_weight_kg | REAL | no | ? | 0 | ? |
| active | INTEGER | no | 1 | 0 | ? |

DDL:

    CREATE TABLE skus(sku_id INTEGER PRIMARY KEY,sku_code TEXT NOT NULL UNIQUE,description TEXT NOT NULL,unit_weight_kg REAL NOT NULL CHECK(unit_weight_kg>=0),active INTEGER NOT NULL DEFAULT 1 CHECK(active IN(0,1)))

## tracking_events

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| tracking_event_id | INTEGER | no | ? | 1 | ? |
| shipment_id | INTEGER | no | ? | 0 | shipments.shipment_id |
| event_sequence | INTEGER | no | ? | 0 | ? |
| event_type | TEXT | no | ? | 0 | ? |
| event_status | TEXT | no | ? | 0 | ? |
| event_at | TEXT | no | ? | 0 | ? |
| location | TEXT | yes | ? | 0 | ? |
| exception_code | TEXT | yes | ? | 0 | ? |
| exception_detail | TEXT | yes | ? | 0 | ? |
| source_event_id | TEXT | yes | ? | 0 | ? |

DDL:

    CREATE TABLE tracking_events(tracking_event_id INTEGER PRIMARY KEY,shipment_id INTEGER NOT NULL REFERENCES shipments,event_sequence INTEGER NOT NULL CHECK(event_sequence>0),event_type TEXT NOT NULL CHECK(event_type IN('label_created','picked_up','in_transit','out_for_delivery','delivered','exception','exception_cleared','return_initiated','returned','cancelled')),event_status TEXT NOT NULL CHECK(event_status IN('label_created','picked_up','in_transit','out_for_delivery','delivered','exception','return_initiated','returned','cancelled')),event_at TEXT NOT NULL CHECK(datetime(event_at) IS NOT NULL),location TEXT,exception_code TEXT,exception_detail TEXT,source_event_id TEXT,UNIQUE(shipment_id,event_sequence),CHECK((event_status='exception' AND exception_code IS NOT NULL) OR (event_status<>'exception' AND exception_code IS NULL)))

## warehouse_capacity

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| node_id | INTEGER | no | ? | 1 | fulfillment_nodes.node_id |
| capacity_date | TEXT | no | ? | 2 | ? |
| capacity_units | INTEGER | no | ? | 0 | ? |

DDL:

    CREATE TABLE warehouse_capacity(node_id INTEGER NOT NULL REFERENCES fulfillment_nodes,capacity_date TEXT NOT NULL CHECK(date(capacity_date) IS NOT NULL),capacity_units INTEGER NOT NULL CHECK(capacity_units>=0),PRIMARY KEY(node_id,capacity_date))

## zones

| Column | SQLite type | Nullable | Default | PK order | FK target |
|---|---|---:|---|---:|---|
| zone_id | INTEGER | no | ? | 1 | ? |
| zone_code | TEXT | no | ? | 0 | ? |
| name | TEXT | no | ? | 0 | ? |
| region_code | TEXT | no | ? | 0 | ? |

DDL:

    CREATE TABLE zones(zone_id INTEGER PRIMARY KEY,zone_code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,region_code TEXT NOT NULL)

## Business meanings

Orders, inventory, shipments, tracking, service, and promise semantics are defined in business_rules.md and entity_relationships.md. Quantities are whole units; unit_weight_kg is kilograms; unit_price is in order currency; *_at fields are timestamps and *_date fields are dates. Flags use 0/1. Inventory transaction quantity is a positive magnitude interpreted using transaction_type. Tracking event_sequence orders events within a shipment.

## Additional index

| Index | Table and column | Purpose |
|---|---|---|
| idx_orders_destination_zone | orders(destination_zone_id) | Supports destination-zone filtering. |
