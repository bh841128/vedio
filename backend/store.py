"""Thread-safe JSON-file backed task store (zero dependencies)."""
import json
import os
import threading
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "tasks.json")
        self.lock = threading.RLock()
        if not os.path.exists(self.path):
            self._write({})

    def _read(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _write(self, data):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def create(self, task):
        with self.lock:
            data = self._read()
            data[task["id"]] = task
            self._write(data)
        return task

    def get(self, task_id):
        with self.lock:
            return self._read().get(task_id)

    def list(self, page, page_size):
        with self.lock:
            items = list(self._read().values())
        items.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        total = len(items)
        start = max(0, (page - 1) * page_size)
        return items[start:start + page_size], total

    def update(self, task_id, **fields):
        with self.lock:
            data = self._read()
            task = data.get(task_id)
            if task is None:
                return None
            task.update(fields)
            task["updated_at"] = _now()
            self._write(data)
            return dict(task)

    def delete(self, task_id):
        with self.lock:
            data = self._read()
            if task_id not in data:
                return False
            del data[task_id]
            self._write(data)
            return True
