"""Settings, read from the .env file in the project root (or real environment variables)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


def env(name, default=""):
    return os.environ.get(name, default)


# Sarvam AI (speech-to-text, text-to-speech and, by default, the chat model)
SARVAM_API_KEY = env("SARVAM_API_KEY")
SARVAM_STT_MODEL = env("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_STT_MODE = env("SARVAM_STT_MODE", "translit")  # translit = Hinglish in Latin script
SARVAM_TTS_MODEL = env("SARVAM_TTS_MODEL", "bulbul:v4-flash")
SARVAM_TTS_SPEAKER = env("SARVAM_TTS_SPEAKER", "")  # empty = the model's default voice
SARVAM_TTS_LANG = env("SARVAM_TTS_LANG", "hi-IN")

# Brain: "auto" uses the LLM when a key is set and falls back to rules if a call fails.
#        "llm" forces the LLM, "rules" forces the offline rule-based brain.
BRAIN = env("BRAIN", "saver").lower()  # saver: fast path for routine asks, AI for the rest | llm | rules

# Any OpenAI-compatible chat API with tool calling. Defaults to Sarvam's own chat model.
LLM_BASE_URL = env("LLM_BASE_URL", "https://api.sarvam.ai/v1")
LLM_API_KEY = env("LLM_API_KEY", SARVAM_API_KEY)
LLM_MODEL = env("LLM_MODEL", "sarvam-105b")

# Prices for the cost-per-case meter (rupees). Check your plan's current prices.
PRICE_LLM_IN_PER_M = float(env("PRICE_LLM_IN_PER_M", "15"))
PRICE_LLM_OUT_PER_M = float(env("PRICE_LLM_OUT_PER_M", "60"))
PRICE_STT_PER_MIN = float(env("PRICE_STT_PER_MIN", "0.49"))
PRICE_TTS_PER_1K_CHARS = float(env("PRICE_TTS_PER_1K_CHARS", "1"))
PRICE_LLM_CACHED_IN_PER_M = float(env("PRICE_LLM_CACHED_IN_PER_M", "5"))
# What one support contact costs when a person solves it (outsourced Indian contact centre, ~₹100 per resolution).
HUMAN_COST_PER_CASE = float(env("HUMAN_COST_PER_CASE", "100"))

# Demo behaviour
STEP_DELAY = float(env("STEP_DELAY", "0.7"))  # seconds between agent steps, so people can follow
REFUND_APPROVAL_LIMIT = int(env("REFUND_APPROVAL_LIMIT", "2000"))
UNDO_WINDOW_MIN = int(env("UNDO_WINDOW_MIN", "30"))
DEMO_MERCHANT = env("DEMO_MERCHANT", "M1001")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "munim.db"
TTS_CACHE = DATA_DIR / "tts_cache"
TTS_CACHE.mkdir(exist_ok=True)
