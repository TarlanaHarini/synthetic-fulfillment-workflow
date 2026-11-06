import sqlite3, tempfile, unittest
from pathlib import Path
from src.fulfillment.db import initialize_database
class SchemaTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.conn=initialize_database(Path(self.tmp.name)/"x.sqlite")
 def tearDown(self):
  self.conn.close(); self.tmp.cleanup()
 def test_required_entities(self):
  names={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  self.assertTrue({"orders","order_lines","skus","fulfillment_nodes","inventory","warehouse_capacity","carriers","service_levels","shipments","tracking_events","order_delivery_promises","shipment_delivery_promises","inventory_transactions","shipment_lines","carrier_service_levels","service_zones","node_service_zones","zones","holidays"} <= names)
 def test_foreign_keys(self):
  names={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  for table in names:
   for fk in self.conn.execute('PRAGMA foreign_key_list("'+table+'")'): self.assertIn(fk["table"],names)
  self.assertEqual([],list(self.conn.execute("PRAGMA foreign_key_check")))
  with self.assertRaises(sqlite3.IntegrityError):
   self.conn.execute("INSERT INTO orders(order_number,ordered_at,destination_zone_id,status,currency,created_at) VALUES('O','2026-01-01T00:00:00Z',999,'pending','USD','2026-01-01T00:00:00Z')")
 def test_checks_and_indexes(self):
  with self.assertRaises(sqlite3.IntegrityError):
   self.conn.execute("INSERT INTO skus(sku_code,description,unit_weight_kg) VALUES('S','sample',-1)")
  ix={r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
  self.assertIn("idx_tracking_shipment_time",ix); self.assertIn("idx_inventory_tx_stock_time",ix)
  self.assertIn("idx_orders_destination_zone",ix)
 def test_cutoff_local_time_check(self):
  self.conn.execute("INSERT INTO holiday_calendars VALUES('HC','Calendar','R')")
  valid=["00:00","09:05","23:59"]
  invalid=["24:00","29:00","12:60","1:00","ab:cd","12-30","12:000"]
  for i,value in enumerate(valid):
   self.conn.execute("INSERT INTO fulfillment_nodes(node_code,name,timezone,cutoff_local_time,holiday_calendar_code) VALUES(?,?,?,?,?)",(f"V{i}","Node","UTC",value,"HC"))
  for i,value in enumerate(invalid):
   with self.subTest(value=value), self.assertRaises(sqlite3.IntegrityError):
    self.conn.execute("INSERT INTO fulfillment_nodes(node_code,name,timezone,cutoff_local_time,holiday_calendar_code) VALUES(?,?,?,?,?)",(f"I{i}","Node","UTC",value,"HC"))
if __name__=="__main__": unittest.main()
