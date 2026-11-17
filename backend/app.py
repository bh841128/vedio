"""Zero-dependency HTTP API server (stdlib http.server) for the video platform.

Serves both the JSON API and the static H5 frontend from one process.

API (prefix /api/v1):
  GET    /health                -> {"status":"ok"}
  POST   /generations           -> 202 {"task_id", "status":"queued"}
  GET    /generations/{id}      -> task detail
  GET    /generations           -> paginated history
  DELETE /generations/{id}      -> 204
  POST   /prompts/enhance       -> {"enhanced"}
Static:
  GET    /                      -> frontend/index.html
  GET    /style.css, /app.js    -> frontend assets
  GET    /media/*               -> generated media (if present)
"""
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import config
from .store import Store
from .xai_client import XAIClient

store = Store(config.DATA_DIR)
xai = XAIClient()
executor = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(_ROOT, "frontend")
MEDIA_DIR = os.path.join(_ROOT, "media")

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".ico": "image/x-icon",
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_generation(task_id):
    """Background worker: create task on xAI, poll, write result back to store."""
    try:
        store.update(task_id, status="processing", progress=10)
        task = store.get(task_id)
        remote = xai.generate_video(task["prompt"], **(task.get("params") or {}))
        store.update(task_id, xai_task_id=remote.get("xai_task_id"), progress=30)

        for _ in range(config.MAX_POLL):
            time.sleep(config.POLL_INTERVAL)
            result = xai.get_video(remote.get("xai_task_id"))
            if result.get("status") == "succeeded":
                store.update(
                    task_id,
                    status="succeeded",
                    progress=100,
                    video_url=result.get("video_url"),
                    cover_url=result.get("cover_url"),
                )
                return
            if result.get("status") == "failed":
                store.update(
                    task_id,
                    status="failed",
                    error={"code": "XAI_ERROR", "message": result.get("error", "generation failed")},
                )
                return
            cur = store.get(task_id) or {}
            if cur.get("status") == "processing":
                store.update(task_id, progress=min(95, (cur.get("progress") or 30) + 5))

        store.update(task_id, status="failed",
                     error={"code": "TIMEOUT", "message": "generation timed out"})
    except Exception as exc:  # normalize any error to task state
        store.update(task_id, status="failed",
                     error={"code": "INTERNAL", "message": str(exc)})


class Handler(BaseHTTPRequestHandler):
    server_version = "vedio/1.0"

    def log_message(self, fmt, *args):
        return

    def _send(self, code, obj):
        body = b"" if code == 204 else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_bytes(self, code, body, content_type, extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        if path.startswith("/media/"):
            base = MEDIA_DIR
            rel = path[len("/media/"):]
        else:
            base = FRONTEND_DIR
            rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(base, rel))
        if not full.startswith(base) or not os.path.isfile(full):
            return self._send(404, {"code": "NOT_FOUND", "message": "route not found"})
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            body = f.read()
        self._send_bytes(200, body, _MIME.get(ext, "application/octet-stream"),
                         {"Cache-Control": "no-cache"})

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)

        if path == "/api/v1/health":
            return self._send(200, {"status": "ok"})
        if path == "/api/v1/generations":
            try:
                page = int(query.get("page", ["1"])[0])
                page_size = int(query.get("page_size", ["20"])[0])
            except ValueError:
                return self._send(400, {"code": "BAD_REQUEST", "message": "invalid page"})
            page_size = max(1, min(page_size, 100))
            items, total = store.list(page, page_size)
            return self._send(200, {"items": items, "total": total, "page": page})
        if path.startswith("/api/v1/generations/"):
            task_id = path.rsplit("/", 1)[-1]
            task = store.get(task_id)
            if not task:
                return self._send(404, {"code": "NOT_FOUND", "message": "task not found"})
            return self._send(200, task)
        if path.startswith("/api/"):
            return self._send(404, {"code": "NOT_FOUND", "message": "route not found"})
        return self._serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._body()
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"code": "BAD_REQUEST", "message": "invalid json"})

        if path == "/api/v1/generations":
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                return self._send(400, {"code": "BAD_REQUEST", "message": "prompt required"})
            enhance = bool(payload.get("enhance"))
            final_prompt = xai.enhance_prompt(prompt) if enhance else prompt
            params = {k: payload[k] for k in
                      ("model", "duration", "resolution", "aspect_ratio") if k in payload}
            task_id = uuid.uuid4().hex
            task = {
                "id": task_id,
                "prompt": final_prompt,
                "original_prompt": prompt,
                "enhanced": enhance,
                "params": params,
                "status": "queued",
                "progress": 0,
                "video_url": None,
                "cover_url": None,
                "error": None,
                "xai_task_id": None,
                "created_at": _now(),
                "updated_at": _now(),
            }
            store.create(task)
            executor.submit(run_generation, task_id)
            return self._send(202, {"task_id": task_id, "status": "queued"})

        if path == "/api/v1/prompts/enhance":
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                return self._send(400, {"code": "BAD_REQUEST", "message": "prompt required"})
            return self._send(200, {"enhanced": xai.enhance_prompt(prompt)})

        return self._send(404, {"code": "NOT_FOUND", "message": "route not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/v1/generations/"):
            task_id = path.rsplit("/", 1)[-1]
            if store.delete(task_id):
                return self._send(204, {})
            return self._send(404, {"code": "NOT_FOUND", "message": "task not found"})
        return self._send(404, {"code": "NOT_FOUND", "message": "route not found"})


def build_server(host=None, port=None):
    return ThreadingHTTPServer((host or config.HOST, port if port is not None else config.PORT), Handler)


def main():
    server = build_server()
    mode = "MOCK" if xai.mock else "LIVE"
    print(f"vedio backend listening on {config.HOST}:{config.PORT} [{mode} mode]", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
