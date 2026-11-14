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


async def _chat(session: aiohttp.ClientSession, url: str, model: str, system: str, lines: List[str],
                num_ctx: int, timeout_s: float) -> Optional[List[str]]:
    body = {"model": model, "stream": False, "format": "json",
            "options": {"temperature": 0.2, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(
                             {"lines": lines}, ensure_ascii=False)}]}
    try:
        async with session.post(f"{url}/api/chat", json=body,
                                timeout=aiohttp.ClientTimeout(total=timeout_s)) as r:
            if r.status >= 400:
                return None
            data = await r.json(content_type=None)
        out = json.loads(data["message"]["content"])["translations"]
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError, TypeError):
        return None
    if not isinstance(out, list) or len(out) != len(lines):
        return None
    return [str(x).strip() for x in out]


async def translate_texts(texts: List[str], *, url: str, model: str, src: str = "en",
                          dialect: str = "msa", num_ctx: int = 8192, batch: int = 8,
                          timeout_s: float = 300,
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
            res = await _chat(s, url.rstrip("/"), model, system, lines, num_ctx, timeout_s)
            if res is None:                       # retry once, then one line at a time
                res = await _chat(s, url.rstrip("/"), model, system, lines, num_ctx, timeout_s)
            if res is None:
                res = []
                for ln in lines:
                    one = await _chat(s, url.rstrip("/"), model, system, [ln], num_ctx, timeout_s)
                    res.append(one[0] if one else "")
            for i, t in zip(idx, res):
                out[i] = t
            done += len(idx)
            if on_progress:
                await on_progress(done, len(todo))
    return out
