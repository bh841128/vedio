import os


def _load_dotenv(path):
    """Minimal stdlib .env loader. Existing environment variables win."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


# Load .env from project root (two levels up from this file) before reading.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_load_dotenv(os.path.join(_ROOT, ".env"))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Data / storage
DATA_DIR = os.getenv("DATA_DIR", os.path.join(_ROOT, "data"))

# xAI integration (all config-driven, never hardcode model names in code)
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
# Model IDs below reflect xAI's currently listed model names; override via .env.
XAI_VIDEO_MODEL = os.getenv("XAI_VIDEO_MODEL", "grok-imagine-video-1.5")
XAI_TEXT_MODEL = os.getenv("XAI_TEXT_MODEL", "grok-4.20-non-reasoning")
XAI_IMAGE_MODEL = os.getenv("XAI_IMAGE_MODEL", "grok-imagine-image-2.0")

# Mock mode: on by default, or when no API key is configured.
# Set MOCK_MODE=0 together with XAI_API_KEY to call the real xAI API.
MOCK_MODE = os.getenv("MOCK_MODE", "1").lower() not in ("0", "false", "no")

# Async worker (video generation is slow: default 5s x 120 = ~10 min ceiling)
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "5"))
MAX_POLL = int(os.getenv("MAX_POLL", "120"))
