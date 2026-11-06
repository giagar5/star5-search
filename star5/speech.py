"""Read-aloud audio for finished answers: Azure neural voices through the foundry-proxy.

The browser splits the rendered answer into short chunks and asks for one chunk at a time, so
playback starts after a couple of seconds and only the part actually listened to is paid for.
Each chunk is cached on disk per turn (replays are free) and every turn has a character budget
so a buggy or hostile client cannot run up the bill.
"""

import asyncio
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

VOICES = {
    "it": ("it-IT", "it-IT-Isabella:DragonHDLatestNeural"),
    "fr": ("fr-FR", "fr-FR-Vivienne:DragonHDLatestNeural"),
    "en": ("en-US", "en-US-Ava:DragonHDLatestNeural"),
    "de": ("de-DE", "de-DE-Seraphina:DragonHDLatestNeural"),
    "es": ("es-ES", "es-ES-Ximena:DragonHDLatestNeural"),
    "nl": ("nl-NL", "nl-NL-FennaNeural"),
}
MAX_CHUNK = 3000
MAX_PARTS = 60
BUDGET_FLOOR = 4000
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TURN_ID = re.compile(r"[0-9a-f]{16,64}")


def clean_parts(parts):
    """Validate the client's chunk: a list of {"text", "heading"}; returns it normalized or None."""
    if not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS:
        return None
    out = []
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("text"), str):
            return None
        text = " ".join(CONTROL.sub(" ", part["text"]).split())
        if text:
            out.append({"text": text, "heading": bool(part.get("heading"))})
    if not out or sum(len(p["text"]) for p in out) > MAX_CHUNK:
        return None
    return out


def ssml(lang, parts):
    locale, voice = VOICES.get(lang, VOICES["it"])
    body = []
    for part in parts:
        text = escape(part["text"])
        body.append(f'<p>{text}</p><break time="450ms"/>' if part["heading"] else f"<p>{text}</p>")
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">'
            f'<voice name="{voice}">{"".join(body)}</voice></speak>')


async def synthesize(document):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10)) as client:
        response = await client.post(f"{endpoint}/speech/tts", content=document.encode("utf-8"), headers={
            "api-key": os.environ["AZURE_OPENAI_API_KEY"], "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"})
    if response.status_code != 200 or not response.content:
        raise RuntimeError(f"speech {response.status_code}")
    return response.content


class BudgetExceeded(Exception):
    pass


class Speech:
    def __init__(self, root, synth_fn=synthesize):
        self.root = Path(root)
        self.synth = synth_fn
        self.locks = {}

    def folder(self, turn_id):
        if not TURN_ID.fullmatch(str(turn_id)):
            raise ValueError("turn")
        return self.root / turn_id

    async def audio(self, turn, parts):
        """Path of the mp3 for this chunk of the turn's answer, synthesized on first request."""
        folder = self.folder(turn["id"])
        document = ssml(turn.get("lang") or "it", parts)
        path = folder / (hashlib.sha256(document.encode("utf-8")).hexdigest()[:32] + ".mp3")
        lock = self.locks.setdefault(turn["id"], asyncio.Lock())
        async with lock:
            if path.is_file():
                return path
            budget = folder / "budget.json"
            spent = json.loads(budget.read_text()).get("chars", 0) if budget.is_file() else 0
            size = sum(len(p["text"]) for p in parts)
            if spent + size > 2 * len(turn.get("answer") or "") + BUDGET_FLOOR:
                raise BudgetExceeded()
            data = await self.synth(document)
            folder.mkdir(parents=True, exist_ok=True)
            budget.write_text(json.dumps({"chars": spent + size}))
            tmp = path.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(path)
            return path

    def remove(self, turn_ids):
        for turn_id in turn_ids:
            self.locks.pop(turn_id, None)
            try:
                shutil.rmtree(self.folder(turn_id), ignore_errors=True)
            except ValueError:
                pass
