# -*- coding: utf-8 -*-
"""Upload big results to an external file host (Gofile) instead of squeezing them into Discord.

Gofile guest uploads need no account: POST a multipart form with a `file` field and read
`data.downloadPage` from the JSON reply. A token (optional, GOFILE_TOKEN) is sent as a Bearer
header so files land in your own account. The upload URL is configurable (GOFILE_UPLOAD_URL)
in case the service changes it.

NOTE: this was written from Gofile's documented behaviour and tested against a local mock
server only. Verify against the real service once:   python -m bot.hosting some_file.zip

Anyone who has the returned link can download the file (that is how Gofile guest links work).
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

import aiohttp

DEFAULT_UPLOAD_URL = "https://upload.gofile.io/uploadfile"
ALLOWED_LINK_HOSTS = ("gofile.io",)


class UploadFailed(RuntimeError):
    """The external host rejected or could not receive the file."""


class _Retryable(Exception):
    pass


@dataclass
class Uploaded:
    name: str
    url: str
    size: int


def _check_link(link: str, allowed: Tuple[str, ...]) -> str:
    """Only accept an https link on the expected host (the reply is untrusted input that we
    paste into a Discord message)."""
    p = urlparse(link)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not any(host == h or host.endswith("." + h) for h in allowed):
        raise UploadFailed(f"unexpected download link from host: {link[:80]!r}")
    return link


async def upload_gofile(path: Path, *, url: str = DEFAULT_UPLOAD_URL, token: str = "",
                        retries: int = 2, backoff: float = 3.0, timeout_s: float = 3600,
                        allowed_hosts: Tuple[str, ...] = ALLOWED_LINK_HOSTS) -> Uploaded:
    path = Path(path)
    size = path.stat().st_size
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    last: Exception = UploadFailed("upload failed")
    for attempt in range(retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_s, sock_connect=30)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                with open(path, "rb") as fh:
                    form = aiohttp.FormData()
                    form.add_field("file", fh, filename=path.name,
                                   content_type="application/octet-stream")
                    async with session.post(url, data=form) as r:
                        body = await r.text()
                        if r.status >= 500 or r.status == 429:
                            raise _Retryable(f"HTTP {r.status}")
                        if r.status >= 400:
                            raise UploadFailed(f"HTTP {r.status}: {body[:160]}")
            try:
                data = json.loads(body)
            except ValueError:
                raise UploadFailed(f"non-JSON reply: {body[:120]!r}")
            if data.get("status") != "ok":
                raise UploadFailed(f"service said: {str(data.get('status'))[:80]}")
            link = (data.get("data") or {}).get("downloadPage")
            if not link:
                raise UploadFailed("reply has no downloadPage")
            return Uploaded(path.name, _check_link(str(link), allowed_hosts), size)
        except UploadFailed:
            raise
        except (_Retryable, aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            last = UploadFailed(f"{type(e).__name__}: {e}"[:200])
            if attempt < retries:
                await asyncio.sleep(backoff * (attempt + 1))
    raise last


def main() -> None:
    import os
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m bot.hosting FILE")
    up = asyncio.run(upload_gofile(
        Path(sys.argv[1]), url=os.environ.get("GOFILE_UPLOAD_URL", DEFAULT_UPLOAD_URL),
        token=os.environ.get("GOFILE_TOKEN", "")))
    print(f"OK {up.size} bytes -> {up.url}")


if __name__ == "__main__":
    try:
        main()
    except UploadFailed as e:
        raise SystemExit(f"FAILED: {e}")
