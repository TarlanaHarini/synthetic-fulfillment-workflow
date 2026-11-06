import tempfile
import unittest
from pathlib import Path

from src.fulfillment.config import DatasetConfig, SEED
from src.fulfillment.db import connect
from src.fulfillment.validation import validate
from src.fulfillment.workflow import generate


class WorkflowTests(unittest.TestCase):
    def test_small_generation_and_exports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = DatasetConfig("test", 12, 8, 3, 2, 24)
            result = generate(root / "a.sqlite3", root / "out", cfg, SEED)
            self.assertEqual(result["counts"]["orders"], 12)
            self.assertEqual(result["counts"]["tracking_events"], 24)
            self.assertEqual(len(result["ground_truth"]), 5)
            self.assertTrue((root / "out" / "ground_truth.json").exists())
            conn = connect(root / "a.sqlite3")
            self.assertEqual(validate(conn), [])
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            conn.close()

    def test_same_seed_is_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = DatasetConfig("test", 10, 6, 2, 2, 20)
            a = generate(root / "a.sqlite3", root / "a", cfg, SEED)
            b = generate(root / "b.sqlite3", root / "b", cfg, SEED)
            self.assertEqual(a["counts"], b["counts"])
            self.assertEqual(a["checksums"], b["checksums"])
            self.assertEqual(a["ground_truth"], b["ground_truth"])


if __name__ == "__main__":
    unittest.main()
