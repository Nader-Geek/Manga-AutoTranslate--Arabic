# -*- coding: utf-8 -*-
"""Download a chapter from a link (Google Drive public file / Gofile) instead of a Discord upload.

Safety: only a small allow-list of hosts is ever contacted (also on every redirect), the body is
streamed to disk with a hard size cap, and the file type is checked by extension AND by magic
bytes. Nothing from the reply is executed.

Supported:
  * Google Drive file shared as "Anyone with the link":  drive.google.com/file/d/<id>/view,
    /open?id=<id>, /uc?id=<id>   (folders are NOT supported — zip the chapter into one file)
  * Gofile content link:  gofile.io/d/<id>  (guest token + content listing; if the folder has
    exactly one usable file it is taken)

Written from the services' public behaviour and tested against local mock servers only:
verify once with   python -m bot.fetch "<link>"
"""
from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import aiohttp

ALLOWED_EXTS = {".zip", ".pdf", ".jpg", ".jpeg", ".png", ".webp"}
DRIVE_DOWNLOAD = "https://drive.usercontent.google.com/download"
GOFILE_API = "https://api.gofile.io"
# hosts we are willing to talk to (suffix match); tests extend this with 127.0.0.1
ALLOWED_HOSTS = ["gofile.io", "drive.google.com", "drive.usercontent.google.com",
                 "docs.google.com", "googleusercontent.com"]


class FetchError(RuntimeError):
    """User-presentable (Arabic) reason the link could not be used."""


@dataclass
class Fetched:
    path: Path
    filename: str
    size: int
    source: str


def _host_ok(url: str, extra: Tuple[str, ...] = ()) -> bool:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme == "http" and host in extra:        # tests only (explicit opt-in)
        return True
    if p.scheme != "https":
        return False
    return any(host == h or host.endswith("." + h) for h in list(ALLOWED_HOSTS) + list(extra))


def classify(link: str) -> Tuple[str, str]:
    """-> ("drive", file_id) | ("gofile", content_id). Raises FetchError for anything else."""
    link = (link or "").strip()
    p = urlparse(link)
    host = (p.hostname or "").lower()
    if p.scheme not in ("https", "http") or not host:
        raise FetchError("الرابط غير صالح. الصق رابط Google Drive أو Gofile كاملاً.")
    if host == "gofile.io" or host.endswith(".gofile.io"):
        m = re.match(r"^/d/([A-Za-z0-9]+)/?$", p.path)
        if not m:
            raise FetchError("رابط Gofile غير مفهوم. المتوقع شكل `https://gofile.io/d/xxxxxx`.")
        return "gofile", m.group(1)
    if host in ("drive.google.com", "docs.google.com"):
        if "/folders/" in p.path:
            raise FetchError("روابط **مجلدات** Drive غير مدعومة. اضغط الفصل في ملف ZIP واحد وشاركه.")
        m = re.search(r"/file/d/([A-Za-z0-9_-]{10,})", p.path)
        fid = m.group(1) if m else (parse_qs(p.query).get("id") or [""])[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{10,}", fid or ""):
            return "drive", fid
        raise FetchError("لم أجد معرّف الملف في رابط Drive.")
    raise FetchError("المسموح فقط روابط Google Drive و Gofile.")


def _sniff(head: bytes) -> str:
    if head.startswith(b"PK\x03\x04"):
        return ".zip"
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return ""


def _name_from_headers(resp: aiohttp.ClientResponse, fallback: str) -> str:
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd, re.I)
    if m:
        return Path(unquote(m.group(1).strip().strip('"'))).name or fallback
    m = re.search(r'filename="?([^";]+)"?', cd, re.I)
    return (Path(m.group(1)).name if m else "") or fallback


async def _stream(session: aiohttp.ClientSession, url: str, dest_dir: Path, max_bytes: int,
                  fallback_name: str, extra: Tuple[str, ...], headers: Optional[dict] = None,
                  hops: int = 5) -> Fetched:
    for _ in range(hops):
        if not _host_ok(url, extra):
            raise FetchError("الرابط يحوّل إلى موقع غير مسموح.")
        async with session.get(url, headers=headers or {}, allow_redirects=False) as r:
            if r.status in (301, 302, 303, 307, 308):
                url = urljoin(url, r.headers.get("Location", ""))
                continue
            if r.status in (401, 403):
                raise FetchError("الملف غير مشارك للعامة. اجعله «أي شخص لديه الرابط».")
            if r.status == 404:
                raise FetchError("الرابط غير موجود أو محذوف.")
            if r.status >= 400:
                raise FetchError(f"الموقع رد بخطأ HTTP {r.status}.")
            ctype = r.headers.get("Content-Type", "")
            if "text/html" in ctype:
                raise FetchError("الرابط أعاد صفحة ويب بدل الملف (غير مشارك للعامة أو يحتاج تأكيداً).")
            clen = int(r.headers.get("Content-Length") or 0)
            if clen > max_bytes:
                raise FetchError(f"الملف ({clen / 1024 ** 2:.0f}MB) أكبر من الحد "
                                 f"({max_bytes / 1024 ** 2:.0f}MB).")
            name = _name_from_headers(r, fallback_name)
            dest_dir.mkdir(parents=True, exist_ok=True)
            tmp = dest_dir / "download.part"
            total, head = 0, b""
            with open(tmp, "wb") as fh:
                async for chunk in r.content.iter_chunked(1 << 20):
                    if len(head) < 16:
                        head += chunk[: 16 - len(head)]
                    total += len(chunk)
                    if total > max_bytes:
                        fh.close(); tmp.unlink(missing_ok=True)
                        raise FetchError(f"الملف أكبر من الحد ({max_bytes / 1024 ** 2:.0f}MB).")
                    fh.write(chunk)
            ext = Path(name).suffix.lower()
            sniffed = _sniff(head)
            if not sniffed:
                tmp.unlink(missing_ok=True)
                raise FetchError("الملف ليس ZIP/PDF/صورة صالحة.")
            if not (ext == ".jpeg" and sniffed == ".jpg") and ext != sniffed:
                name = Path(name).stem + sniffed      # trust the content, not the name
            return Fetched(tmp, name, total, url)
    raise FetchError("تحويلات كثيرة جداً في الرابط.")


async def fetch_link(link: str, dest_dir: Path, max_bytes: int, *, timeout_s: float = 1800,
                     extra_hosts: Tuple[str, ...] = (), drive_url: str = "",
                     gofile_api: str = "") -> Fetched:
    kind, ident = classify(link)
    drive_url = drive_url or DRIVE_DOWNLOAD
    gofile_api = (gofile_api or GOFILE_API).rstrip("/")
    timeout = aiohttp.ClientTimeout(total=timeout_s, sock_connect=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as s:
            if kind == "drive":
                url = f"{drive_url}?id={ident}&export=download&confirm=t"
                return await _stream(s, url, dest_dir, max_bytes, f"{ident}.bin", extra_hosts)
            # gofile: guest account token -> content listing -> file link
            async with s.post(f"{gofile_api}/accounts") as r:
                data = await r.json(content_type=None)
            token = (data.get("data") or {}).get("token") if data.get("status") == "ok" else None
            if not token:
                raise FetchError("تعذّر الحصول على إذن من Gofile (قد يكون تغيّر الـ API). "
                                 "جرّب رابط Google Drive أو ارفع الملف مباشرة.")
            auth = {"Authorization": f"Bearer {token}", "Cookie": f"accountToken={token}"}
            async with s.get(f"{gofile_api}/contents/{ident}", headers=auth) as r:
                if r.status >= 400:
                    raise FetchError(f"Gofile لم يعرض محتوى الرابط (HTTP {r.status}). "
                                     f"قد يكون محمياً بكلمة سر أو منتهياً.")
                listing = await r.json(content_type=None)
            d = listing.get("data") or {}
            kids = d.get("children") or {}
            files = [c for c in kids.values() if isinstance(c, dict) and c.get("type") == "file"]
            if not files and d.get("type") == "file":
                files = [d]
            good = [c for c in files if Path(str(c.get("name", ""))).suffix.lower() in ALLOWED_EXTS]
            if len(good) != 1:
                raise FetchError("رابط Gofile يجب أن يحتوي **ملفاً واحداً** (ZIP أو PDF). "
                                 f"وجدت {len(good)}. اضغط الفصل في ZIP واحد.")
            f = good[0]
            return await _stream(s, str(f.get("link", "")), dest_dir, max_bytes,
                                 Path(str(f.get("name", "file"))).name, extra_hosts, headers=auth)
    except FetchError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError) as e:
        raise FetchError(f"تعذّر تحميل الرابط ({type(e).__name__}).")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -m bot.fetch "<link>"')
    import tempfile
    out = Path(tempfile.mkdtemp(prefix="fetch_"))
    f = asyncio.run(fetch_link(sys.argv[1], out, 2 * 1024 ** 3))
    print(f"OK {f.size} bytes, name={f.filename}, saved at {f.path}")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        raise SystemExit(f"FAILED: {e}")
