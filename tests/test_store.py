import os
import tempfile
import unittest

from backend.store import Store


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = Store(self.d)

    def _task(self, tid, created):
        return {"id": tid, "prompt": "p", "status": "queued", "created_at": created}

    def test_create_get(self):
        self.store.create(self._task("a", "2026-01-01T00:00:00Z"))
        self.assertEqual(self.store.get("a")["status"], "queued")
        self.assertIsNone(self.store.get("missing"))

    def test_update(self):
        self.store.create(self._task("a", "2026-01-01T00:00:00Z"))
        self.store.update("a", status="succeeded", progress=100)
        t = self.store.get("a")
        self.assertEqual(t["status"], "succeeded")
        self.assertEqual(t["progress"], 100)
        self.assertIn("updated_at", t)

    def test_persistence_across_instances(self):
        self.store.create(self._task("a", "2026-01-01T00:00:00Z"))
        other = Store(self.d)
        self.assertIsNotNone(other.get("a"))

    def test_list_sorted_and_paginated(self):
        self.store.create(self._task("a", "2026-01-01T00:00:00Z"))
        self.store.create(self._task("b", "2026-01-02T00:00:00Z"))
        items, total = self.store.list(1, 1)
        self.assertEqual(total, 2)
        self.assertEqual(items[0]["id"], "b")

    def test_delete(self):
        self.store.create(self._task("a", "2026-01-01T00:00:00Z"))
        self.assertTrue(self.store.delete("a"))
        self.assertFalse(self.store.delete("a"))
        self.assertIsNone(self.store.get("a"))


if __name__ == "__main__":
    unittest.main()
