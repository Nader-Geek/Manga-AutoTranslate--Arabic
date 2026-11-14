# -*- coding: utf-8 -*-
"""Translate extracted bubble texts to Arabic with a local Ollama model (used by /chapter).

Works on the *texts only* (the engine already found the bubbles), so it is independent of
which cleaning engine produced the pages. Batches of numbered lines go to /api/chat with
format=json; a bad/short reply is retried once and then falls back to one line at a time.
Lines that still fail stay untranslated ("") and are counted as such.
"""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable, Dict, List, Optional

import aiohttp

SRC_NAMES = {"en": "English", "ko": "Korean", "ja": "Japanese", "ch": "Chinese", "zh": "Chinese",
             "ar": "Arabic"}
DIALECTS = {
    "msa": "Modern Standard Arabic (فصحى مبسّطة)",
    "egyptian": "Egyptian Arabic (عامية مصرية)",
}


def system_prompt(src: str, dialect: str) -> str:
    return (
        f"You translate manga/manhwa speech-bubble text from {SRC_NAMES.get(src, src)} to "
        f"{DIALECTS.get(dialect, DIALECTS['msa'])}.\n"
        "Rules: keep the meaning, tone and character voice; keep each line short enough for a "
        "speech bubble; keep names consistent; keep sound effects as short Arabic equivalents; "
        "do not add notes or explanations; leave numbers/symbols as they are.\n"
        'Reply with ONLY JSON: {"translations": ["...", ...]} — exactly one string per input '
        "line, in the same order.")


def _extract_json(text: str):
    """API models sometimes wrap JSON in prose/```; take the outermost {...}."""
    try:
        return json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a < 0 or b <= a:
            raise
        return json.loads(text[a:b + 1])


async def _chat(session: aiohttp.ClientSession, url: str, model: str, system: str, lines: List[str],
                num_ctx: int, timeout_s: float, api_key: str = "") -> Optional[List[str]]:
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"lines": lines}, ensure_ascii=False)}]
    tmo = aiohttp.ClientTimeout(total=timeout_s)
    try:
        if api_key:   # hosted OpenAI-compatible API
            hdr = {"Authorization": f"Bearer {api_key}"}
            body = {"model": model, "temperature": 0.2, "messages": msgs,
                    "response_format": {"type": "json_object"}}
            async with session.post(f"{url}/chat/completions", json=body, headers=hdr,
                                    timeout=tmo) as r:
                if r.status == 400:   # some providers reject response_format: retry without it
                    body.pop("response_format")
                    async with session.post(f"{url}/chat/completions", json=body, headers=hdr,
                                            timeout=tmo) as r2:
                        if r2.status >= 400:
                            return None
                        data = await r2.json(content_type=None)
                elif r.status >= 400:
                    return None
                else:
                    data = await r.json(content_type=None)
            out = _extract_json(data["choices"][0]["message"]["content"])["translations"]
        else:         # local Ollama
            body = {"model": model, "stream": False, "format": "json",
                    "options": {"temperature": 0.2, "num_ctx": num_ctx}, "messages": msgs}
            async with session.post(f"{url}/api/chat", json=body, timeout=tmo) as r:
                if r.status >= 400:
                    return None
                data = await r.json(content_type=None)
            out = json.loads(data["message"]["content"])["translations"]
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, IndexError, ValueError, TypeError):
        return None
    if not isinstance(out, list) or len(out) != len(lines):
        return None
    return [str(x).strip() for x in out]


async def translate_texts(texts: List[str], *, url: str, model: str, src: str = "en",
                          dialect: str = "msa", num_ctx: int = 8192, batch: int = 8,
                          timeout_s: float = 300, api_key: str = "",
                          on_progress: Optional[Callable[[int, int], Awaitable[None]]] = None
                          ) -> List[str]:
    """Returns one Arabic string per input text ('' when it could not be translated)."""
    system = system_prompt(src, dialect)
    out: List[str] = [""] * len(texts)
    todo = [i for i, t in enumerate(texts) if t and t.strip()]
    done = 0
    async with aiohttp.ClientSession() as s:
        for start in range(0, len(todo), batch):
            idx = todo[start:start + batch]
            lines = [texts[i].strip() for i in idx]
            res = await _chat(s, url.rstrip("/"), model, system, lines, num_ctx, timeout_s, api_key)
            if res is None:                       # retry once, then one line at a time
                res = await _chat(s, url.rstrip("/"), model, system, lines, num_ctx, timeout_s, api_key)
            if res is None:
                res = []
                for ln in lines:
                    one = await _chat(s, url.rstrip("/"), model, system, [ln], num_ctx, timeout_s, api_key)
                    res.append(one[0] if one else "")
            for i, t in zip(idx, res):
                out[i] = t
            done += len(idx)
            if on_progress:
                await on_progress(done, len(todo))
    return out
