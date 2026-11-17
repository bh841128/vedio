"""End-to-end API test: spins up the real HTTP server in a thread."""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["MOCK_MODE"] = "1"
        os.environ["POLL_INTERVAL"] = "0.01"
        os.environ["DATA_DIR"] = tempfile.mkdtemp()
        from backend import config
        # reload-dependent singletons read config at import time
        from backend.app import build_server
        cls.srv = build_server("127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}/api/v1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method,
                                   headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, (json.loads(raw) if raw else None)

    def test_health(self):
        s, b = self.req("GET", "/health")
        self.assertEqual(s, 200)
        self.assertEqual(b["status"], "ok")

    def test_full_generation_flow(self):
        s, b = self.req("POST", "/generations", {"prompt": "a robot surfing", "enhance": True})
        self.assertEqual(s, 202)
        tid = b["task_id"]
        self.assertTrue(tid)

        status = None
        for _ in range(200):
            s, task = self.req("GET", "/generations/" + tid)
            status = task["status"]
            if status in ("succeeded", "failed"):
                break
            time.sleep(0.05)
        self.assertEqual(status, "succeeded", task)
        self.assertEqual(task["progress"], 100)
        self.assertTrue(task["video_url"])

    def test_enhance(self):
        s, b = self.req("POST", "/prompts/enhance", {"prompt": "a dog"})
        self.assertEqual(s, 200)
        self.assertIn("enhanced", b)

    def test_empty_prompt_rejected(self):
        s, b = self.req("POST", "/generations", {"prompt": "   "})
        self.assertEqual(s, 400)
        self.assertEqual(b["code"], "BAD_REQUEST")

    def test_history_and_delete(self):
        s, b = self.req("POST", "/generations", {"prompt": "mountains"})
        tid = b["task_id"]
        s, hist = self.req("GET", "/generations?page=1&page_size=10")
        self.assertEqual(s, 200)
        self.assertGreaterEqual(hist["total"], 1)
        self.assertIn("items", hist)
        s, _ = self.req("DELETE", "/generations/" + tid)
        self.assertEqual(s, 204)
        s, _ = self.req("GET", "/generations/" + tid)
        self.assertEqual(s, 404)


if __name__ == "__main__":
    unittest.main()
