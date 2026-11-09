# -*- coding: utf-8 -*-
"""Build manga.py command lines, validate uploads, and run the subprocess."""
from __future__ import annotations

import asyncio
import os
import re
import signal
import time
import zipfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Tuple

from .config import Config

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_EXTS = IMAGE_EXTS | {".zip", ".pdf"}
KINDS = ("clean", "extract", "typer", "translate")

# Environment variables that must never reach the manga.py subprocess.
_SECRET_ENV = ("DISCORD_TOKEN", "DATABASE_URL")

OCR_CHOICES = {"en": ["en"], "ja": ["ja", "en"], "ko": ["ko", "en"], "zh": ["zh", "en"]}


class UploadError(Exception):
    """Raised with a user-facing (Arabic) message when an upload is rejected."""


# ---------------------------------------------------------------- upload checks
def _natural_ok_name(name: str) -> bool:
    p = PurePosixPath(name.replace("\\", "/"))
    return not (p.is_absolute() or ".." in p.parts or name.startswith(("/", "\\")))


def inspect_upload(path: Path, cfg: Config, max_pages: int) -> int:
    """Validate the file on disk and return its page count. Raises UploadError."""
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise UploadError("الصيغة غير مدعومة. المسموح: صورة (jpg/png/webp) أو ZIP أو PDF.")
    if ext in IMAGE_EXTS:
        return 1

    if ext == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                infos = zf.infolist()
                total = 0
                pages = 0
                for zi in infos:
                    if not _natural_ok_name(zi.filename):
                        raise UploadError("ملف ZIP يحتوي مسارات غير آمنة.")
                    if zi.is_dir():
                        continue
                    total += zi.file_size
                    if total > cfg.max_unzipped_mb * 1024 * 1024:
                        raise UploadError(
                            f"حجم ZIP بعد الفك يتجاوز {cfg.max_unzipped_mb}MB.")
                    if Path(zi.filename).suffix.lower() in IMAGE_EXTS:
                        pages += 1
                if pages == 0:
                    raise UploadError("لم أجد أي صور (jpg/png/webp) داخل ملف ZIP.")
                if len(infos) > max(2000, max_pages * 20):
                    raise UploadError("ملف ZIP يحتوي عدداً كبيراً غير معقول من الملفات.")
        except zipfile.BadZipFile:
            raise UploadError("ملف ZIP تالف أو غير صالح.")
    else:  # pdf
        pages = _pdf_pages(path)

    if pages > max_pages:
        raise UploadError(f"عدد الصفحات {pages} يتجاوز الحد المسموح ({max_pages}). "
                          f"قسّم الفصل إلى أجزاء أصغر.")
    return pages


def _pdf_pages(path: Path) -> int:
    try:
        try:
            import pymupdf as fitz  # current import name
        except ImportError:
            import fitz  # older pymupdf releases
    except Exception:
        raise UploadError("دعم PDF غير متاح على السيرفر (pymupdf غير مثبّت).")
    try:
        with fitz.open(path) as doc:
            if doc.needs_pass:
                raise UploadError("ملف PDF محمي بكلمة مرور.")
            return int(doc.page_count)
    except UploadError:
        raise
    except Exception:
        raise UploadError("ملف PDF تالف أو غير قابل للقراءة.")


# ------------------------------------------------------------------ command line
@dataclass
class Plan:
    argv: List[str]
    env: Dict[str, str]
    out_path: Path            # file manga.py writes with -o
    typer_dir: Path           # --export-typer directory (stats + extract source)
    deliver: List[Path]       # files that go to the user ('extract' builds its own later)


def _safe_env(cfg: Config, extra: Dict[str, str]) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _SECRET_ENV}
    env.update({"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"})
    env.update(extra)
    return env


def build_plan(job: Dict[str, Any], cfg: Config) -> Plan:
    """Translate a job row into a manga.py invocation. Never builds a shell string."""
    kind = job["kind"]
    if kind not in KINDS:
        raise ValueError(f"unknown job kind {kind!r}")
    opts = job.get("options") or {}
    wd = Path(job["workdir"])
    typer_dir = wd / "typer"

    img_format = opts.get("img_format", "jpg")
    if img_format not in ("jpg", "png", "webp"):
        img_format = "jpg"
    ocr = OCR_CHOICES.get(opts.get("ocr", "en"), ["en"])
    order = opts.get("reading_order", "rtl")
    if order not in ("rtl", "ltr"):
        order = "rtl"

    if kind == "translate":
        fmt = opts.get("format", "zip")
        out_path = wd / ("result.pdf" if fmt == "pdf" else "result.zip")
    else:
        out_path = wd / "result.zip"

    argv = [cfg.python, str(cfg.manga_script),
            "-i", str(job["input_path"]), "-o", str(out_path),
            "--font", cfg.font,
            "--gpu" if cfg.use_gpu else "--cpu",
            "--provider", "ollama",
            "--reading-order", order,
            "--ocr-lang", *ocr,
            "--img-format", img_format,
            "--export-typer", str(typer_dir),
            "--workers", "1"]

    extra_env: Dict[str, str] = {"MANGA_TARGET_LANG": "ar"}

    if kind in ("clean", "extract", "typer"):
        argv.append("--clean-only")
        if opts.get("lama"):
            argv.append("--lama")
    else:  # translate
        model = opts.get("model") or cfg.ollama_model
        if model not in cfg.allowed_models:
            raise ValueError(f"model {model!r} is not allowed")
        dialect = opts.get("dialect", "msa")
        if dialect not in ("msa", "egyptian"):
            dialect = "msa"
        argv += ["--model", model, "--target-lang", "ar", "--ar-dialect", dialect,
                 "--bubbles-per-request", "4", "--batch-workers", "1"]
        extra_env.update({
            "OLLAMA_BASE_URL": cfg.ollama_url.rstrip("/") + "/v1",
            "MANGA_AR_DIALECT": dialect,
            "OLLAMA_CONTEXT_LENGTH": str(cfg.ollama_context),
        })
        if opts.get("lama"):
            argv.append("--lama")

    if kind == "clean":
        deliver = [out_path]
    elif kind == "typer":
        deliver = [Path(str(typer_dir) + ".zip")]
    elif kind == "translate":
        deliver = [out_path]
    else:
        deliver = []  # built from typer_job.json by the worker
    return Plan(argv, _safe_env(cfg, extra_env), out_path, typer_dir, deliver)


# ------------------------------------------------------------------- subprocess
@dataclass
class RunResult:
    returncode: int
    tail: List[str]
    timed_out: bool = False
    cancelled: bool = False


class ProcessHandle:
    """Lets /cancel stop a running job."""
    def __init__(self) -> None:
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.cancelled = False

    async def cancel(self) -> None:
        self.cancelled = True
        await _kill_tree(self.proc)


async def _kill_tree(proc: Optional[asyncio.subprocess.Process]) -> None:
    if proc is None or proc.returncode is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        await asyncio.wait_for(proc.wait(), 8)
    except asyncio.TimeoutError:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


async def run_plan(plan: Plan, *, cwd: Path, log_path: Path, timeout_s: float,
                   on_line: Callable[[str], None], handle: ProcessHandle,
                   tail_lines: int = 40) -> RunResult:
    """Run manga.py, streaming merged stdout/stderr to the log file and on_line()."""
    tail: Deque[str] = deque(maxlen=tail_lines)
    proc = await asyncio.create_subprocess_exec(
        *plan.argv, cwd=str(cwd), env=plan.env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        stdin=asyncio.subprocess.DEVNULL, start_new_session=True,
        limit=1024 * 1024)
    handle.proc = proc
    timed_out = False

    async def pump() -> None:
        with open(log_path, "w", encoding="utf-8", errors="replace") as lf:
            assert proc.stdout is not None
            while True:
                try:
                    raw = await proc.stdout.readline()
                except (asyncio.LimitOverrunError, ValueError):
                    raw = b"[line too long, skipped]\n"
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                lf.write(line + "\n")
                lf.flush()
                tail.append(line)
                try:
                    on_line(line)
                except Exception:
                    pass

    pump_task = asyncio.create_task(pump())
    try:
        await asyncio.wait_for(proc.wait(), timeout_s)
    except asyncio.TimeoutError:
        timed_out = True
        await _kill_tree(proc)
    try:
        await asyncio.wait_for(pump_task, 15)
    except asyncio.TimeoutError:
        pump_task.cancel()
    return RunResult(proc.returncode if proc.returncode is not None else -1,
                     list(tail), timed_out=timed_out, cancelled=handle.cancelled)


# --------------------------------------------------------------- result packaging
def split_zip(src: Path, limit_bytes: int) -> List[Path]:
    """Repack a zip of independent files into parts that each fit under limit_bytes.
    Returns [src] when it already fits. Raises ValueError when one entry alone is too big."""
    if src.stat().st_size <= limit_bytes:
        return [src]
    budget = int(limit_bytes * 0.97)
    parts: List[Path] = []
    with zipfile.ZipFile(src) as zin:
        entries = [zi for zi in zin.infolist() if not zi.is_dir()]
        cur: Optional[zipfile.ZipFile] = None
        cur_size = 0
        idx = 0
        for zi in entries:
            need = zi.compress_size + 200 + len(zi.filename) * 2
            if need > budget:
                if cur is not None:
                    cur.close()
                raise ValueError(f"{zi.filename} is larger than the upload limit")
            if cur is None or cur_size + need > budget:
                if cur is not None:
                    cur.close()
                idx += 1
                p = src.with_name(f"{src.stem}_part{idx}.zip")
                parts.append(p)
                cur = zipfile.ZipFile(p, "w", zipfile.ZIP_STORED)
                cur_size = 0
            cur.writestr(zi.filename, zin.read(zi))
            cur_size += need
        if cur is not None:
            cur.close()
    return parts
