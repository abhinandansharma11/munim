"""Sarvam AI: speech-to-text (Saaras) and text-to-speech (Bulbul).

STT: POST https://api.sarvam.ai/speech-to-text  (multipart: file, model, mode; header api-subscription-key)
     Up to 30 seconds per request; WAV/MP3/AAC/FLAC/OGG.
TTS: POST https://api.sarvam.ai/text-to-speech  (JSON; response {"audios": [base64 WAV]})
"""
import base64
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from . import config

BASE = "https://api.sarvam.ai"


class SarvamError(Exception):
    pass


def enabled():
    return bool(config.SARVAM_API_KEY)


def _headers():
    return {"api-subscription-key": config.SARVAM_API_KEY}


def to_wav(data: bytes, filename: str) -> bytes:
    """Phones may upload m4a/webm. Convert to 16 kHz mono WAV with ffmpeg when it is installed."""
    if filename.lower().endswith(".wav") or not shutil.which("ffmpeg"):
        return data
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / ("in" + Path(filename).suffix)
        dst = Path(d) / "out.wav"
        src.write_bytes(data)
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000",
                            "-t", "29", str(dst)], capture_output=True)
        return dst.read_bytes() if r.returncode == 0 else data


async def stt(audio: bytes, filename: str = "voice.wav"):
    """Returns (transcript, seconds_of_audio)."""
    if not enabled():
        raise SarvamError("No SARVAM_API_KEY set. Type the message instead, or add the key to .env")
    audio = to_wav(audio, filename)
    name = filename if filename.lower().endswith(".wav") else "voice.wav"
    seconds = max(1.0, (len(audio) - 44) / 32000) if audio[:4] == b"RIFF" else 10.0
    files = {"file": (name, audio, "audio/wav")}
    data = {"model": config.SARVAM_STT_MODEL, "mode": config.SARVAM_STT_MODE}
    async with httpx.AsyncClient(timeout=40) as c:
        r = await c.post(f"{BASE}/speech-to-text", headers=_headers(), files=files, data=data)
        if r.status_code >= 400 and data.get("mode"):
            # Older models do not take 'mode'; try once without it.
            r = await c.post(f"{BASE}/speech-to-text", headers=_headers(), files=files,
                             data={"model": config.SARVAM_STT_MODEL})
    if r.status_code >= 400:
        raise SarvamError(f"Sarvam speech-to-text error {r.status_code}: {r.text[:200]}")
    return (r.json().get("transcript") or "").strip(), seconds


def _cache_path(text, lang):
    key = hashlib.sha1(f"{config.SARVAM_TTS_MODEL}|{config.SARVAM_TTS_SPEAKER}|{lang}|{text}".encode()).hexdigest()
    return config.TTS_CACHE / f"{key}.wav"


# Request shapes to try, cheapest voice first. Bulbul v4 Flash costs a third of Bulbul v3 (₹1 vs ₹3 per 1,000 characters).
# The first shape that works is remembered, so later calls make one request only.
V4_SPEAKER = {"hi-IN": "aparna_hi_customer", "en-IN": "simran_en_sales"}
_working_shape = {}


def _shapes(text, lang):
    model = config.SARVAM_TTS_MODEL
    spk = config.SARVAM_TTS_SPEAKER
    out = []
    if model.startswith("bulbul:v4"):
        v4spk = spk or V4_SPEAKER.get(lang)
        out += [("v4", {"text": text, "model": model, "language_code": lang, **({"speaker": v4spk} if v4spk else {})}),
                ("v4-target", {"text": text, "model": model, "target_language_code": lang, **({"speaker": v4spk} if v4spk else {})}),
                ("v4-plain", {"text": text, "model": model, "language_code": lang})]
    v3 = model if not model.startswith("bulbul:v4") else "bulbul:v3"
    out += [("v3", {"text": text, "target_language_code": lang, "model": v3, **({"speaker": spk} if spk and not model.startswith("bulbul:v4") else {})}),
            ("v3-inputs", {"inputs": [text], "target_language_code": lang, "model": v3})]
    return out


async def tts(text: str, lang: str = ""):
    """Returns (wav_bytes, characters_billed). Cached on disk, so repeated lines cost nothing."""
    text = (text or "").strip()[:1500]
    if not text:
        raise SarvamError("Nothing to say")
    lang = lang or config.SARVAM_TTS_LANG
    p = _cache_path(text, lang)
    if p.exists():
        return p.read_bytes(), 0
    if not enabled():
        raise SarvamError("No SARVAM_API_KEY set")
    shapes = _shapes(text, lang)
    if lang in _working_shape:
        shapes.sort(key=lambda s: s[0] != _working_shape[lang])
    last = None
    async with httpx.AsyncClient(timeout=40) as c:
        for name, body in shapes:
            r = await c.post(f"{BASE}/text-to-speech", headers=_headers(), json=body)
            if r.status_code < 400 and (r.json().get("audios") or []):
                _working_shape[lang] = name
                wav = base64.b64decode(r.json()["audios"][0])
                p.write_bytes(wav)
                return wav, len(text)
            last = r
            if r.status_code in (401, 403, 402, 429):
                break  # bad key, no credits or rate limit: another shape won't help
    raise SarvamError(f"Sarvam text-to-speech error {last.status_code}: {last.text[:200]}")
