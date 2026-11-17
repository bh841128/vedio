"""xAI Grok API client using only the standard library (urllib).

Supports Text Generation (prompt enhance), Video Generation (async), and
Image Generation (cover). Model names / endpoints are config-driven.
When MOCK_MODE is on (or no API key), calls are simulated so the full
platform flow can be exercised locally without credentials or cost.

Video API (per docs.x.ai/developers/model-capabilities/video/generation):
  POST /videos/generations  -> {"request_id": "..."}
  GET  /videos/{request_id} -> {"status": "done"|"failed"|..., "video": {"url": "..."}}
"""
import json
import uuid
import urllib.request

from . import config


class XAIClient:
    def __init__(self):
        self.key = config.XAI_API_KEY
        self.mock = config.MOCK_MODE or not self.key

    def _headers(self, json_body=True):
        h = {"Authorization": "Bearer " + self.key}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def _post(self, path, payload):
        req = urllib.request.Request(
            config.XAI_BASE_URL + path,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)

    def _get(self, path):
        req = urllib.request.Request(
            config.XAI_BASE_URL + path, headers=self._headers(json_body=False)
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)

    def enhance_prompt(self, prompt):
        if self.mock:
            return prompt + ", cinematic lighting, highly detailed, 4k, smooth motion"
        resp = self._post("/chat/completions", {
            "model": config.XAI_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": (
                    "Rewrite the user's idea into ONE concise, vivid paragraph describing "
                    "a short video (subject, setting, motion, style, lighting). "
                    "Output ONLY the plain prompt text. No headings, no markdown, "
                    "no labels, no quotes, no explanation."
                )},
                {"role": "user", "content": prompt},
            ],
        })
        try:
            text = resp["choices"][0]["message"]["content"].strip()
            return text or prompt
        except (KeyError, IndexError):
            return prompt

    def generate_cover(self, prompt):
        """Optional Image Generation for a cover/thumbnail."""
        if self.mock:
            return "/media/demo-cover.svg"
        resp = self._post("/images/generations", {
            "model": config.XAI_IMAGE_MODEL,
            "prompt": prompt,
            "n": 1,
        })
        try:
            return resp["data"][0].get("url")
        except (KeyError, IndexError):
            return None

    def generate_video(self, prompt, **params):
        if self.mock:
            return {"xai_task_id": "mock-" + uuid.uuid4().hex}
        resp = self._post("/videos/generations", {
            "model": params.get("model", config.XAI_VIDEO_MODEL),
            "prompt": prompt,
            "duration": params.get("duration", 5),
            "aspect_ratio": params.get("aspect_ratio", "16:9"),
            "resolution": params.get("resolution", "720p"),
        })
        request_id = resp.get("request_id") or resp.get("id")
        return {"xai_task_id": str(request_id or "")}

    def get_video(self, xai_task_id):
        if self.mock:
            return {
                "status": "succeeded",
                "video_url": "/media/demo-video.mp4",
                "cover_url": "/media/demo-cover.svg",
            }
        resp = self._get("/videos/" + str(xai_task_id))
        status = str(resp.get("status", "")).lower()
        if status in ("done", "succeeded", "completed"):
            video = resp.get("video") or {}
            return {
                "status": "succeeded",
                "video_url": video.get("url") if isinstance(video, dict) else resp.get("video_url"),
                "cover_url": resp.get("cover_url"),
            }
        if status in ("failed", "error", "cancelled"):
            return {"status": "failed", "error": resp.get("error", "generation failed")}
        return {"status": "processing"}
