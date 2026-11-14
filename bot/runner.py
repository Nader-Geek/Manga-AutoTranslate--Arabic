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

    # clean / extract / typer run on the new engine (manga.py + manga_sections/);
    # translate (Arabic via Ollama) runs on the previous Arabic engine.
    script = cfg.legacy_script if kind == "translate" else cfg.manga_script
    argv = [cfg.python, str(script),
            "-i", str(job["input_path"]), "-o", str(out_path),
            "--font", cfg.font,
            "--gpu" if cfg.use_gpu else "--cpu",
            "--provider", "ollama",
            "--reading-order", order,
            "--ocr-lang", *ocr,
            "--img-format", img_format,
            "--export-typer", str(typer_dir),
            "--workers", "1"]

    # The typer export dir is written by every job kind (stats / previews / TypeR); keep it
    # in the same compact format as the output instead of manga.py's default lossless PNG
    # (a chapter of tall strips was 170MB).
    extra_env: Dict[str, str] = {"MANGA_TARGET_LANG": "ar", "MANGA_TYPER_FORMAT": img_format}

    # Pages are never merged into tall strips and no seam "repair" chains pages together:
    # every page goes in and comes out as itself.
    argv += ["--stitch-max-height", "0", "--no-seam-repair"]

    if kind in ("clean", "extract", "typer"):
        argv += ["--clean-only", "--no-resume"]   # fresh run: the export must cover every page
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
        deliver = []   # built from the export folder by build_typer_parts (split to fit the limit)
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
        self.log: Callable[[str], None] = lambda _t: None   # appends a line to run.log

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
    if handle.cancelled:          # /cancel arrived while the process was being spawned
        await _kill_tree(proc)

    async def pump() -> None:
        with open(log_path, "a", encoding="utf-8", errors="replace") as lf:
            def _log(text: str) -> None:
                lf.write(text + "\n")
                lf.flush()
            handle.log = _log
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


# ------------------------------------------------------------- oversized single images
_JPEG_QUALITIES = (95, 90, 85, 80, 72, 65)


def _encode_jpeg(im, quality: int) -> bytes:
    import io
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _quiet_cut_rows(im, parts: int) -> List[int]:
    """Cut rows for splitting `im` into `parts` slices, snapped to the flattest nearby row
    (a gap between panels / empty background) so text and artwork are not cut through."""
    import numpy as np
    g = np.asarray(im.convert("L"), dtype=np.float32)
    h = g.shape[0]
    score = g.std(axis=1)
    cuts: List[int] = []
    for i in range(1, parts):
        target = round(h * i / parts)
        win = max(20, int(h / parts * 0.15))
        lo, hi = max(cuts[-1] + 50 if cuts else 50, target - win), min(h - 50, target + win)
        cuts.append(int(lo + np.argmin(score[lo:hi])) if hi > lo else target)
    return cuts


def shrink_image(data: bytes, name: str, budget: int, allow_slice: bool = True):
    """Make one image fit `budget` bytes. Returns ([(new_name, bytes)...], note).
    1) JPEG at the highest quality that fits  2) otherwise vertical slices cut at quiet rows."""
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    stem = str(PurePosixPath(name).with_suffix(""))
    mb = len(data) / 1024 ** 2

    for q in _JPEG_QUALITIES:
        out = _encode_jpeg(im, q)
        if len(out) <= budget:
            return [(f"{stem}.jpg", out)], f"{PurePosixPath(name).name}: {mb:.1f}MB → JPEG جودة {q}"
    if not allow_slice:
        raise ValueError(f"{name} cannot be made small enough without slicing")

    h = im.height
    parts = max(2, -(-len(_encode_jpeg(im, 80)) // max(1, int(budget * 0.85))))
    while parts <= 40:
        cuts = [0] + _quiet_cut_rows(im, parts) + [h]
        pieces = []
        for k in range(parts):
            piece = im.crop((0, cuts[k], im.width, cuts[k + 1]))
            for q in (88, 80, 72, 65):
                out = _encode_jpeg(piece, q)
                if len(out) <= budget:
                    break
            else:
                break
            pieces.append((f"{stem}_p{k + 1}.jpg", out))
        else:
            return pieces, f"{PurePosixPath(name).name}: {mb:.1f}MB → قُسّم إلى {parts} أجزاء (JPEG)"
        parts += 1
    raise ValueError(f"{name} cannot be split small enough")


def shrink_oversized_images(src: Path, limit_bytes: int, allow_slice: bool = True) -> Tuple[Path, List[str]]:
    """If any single image inside the zip is too big to upload, recompress/slice just those.
    Returns (zip path, notes). The original zip is returned untouched when nothing is oversized."""
    budget = int(limit_bytes * 0.9)
    with zipfile.ZipFile(src) as zin:
        infos = [zi for zi in zin.infolist() if not zi.is_dir()]
        big = [zi for zi in infos if zi.compress_size > budget
               and Path(zi.filename).suffix.lower() in IMAGE_EXTS]
        if not big:
            return src, []
        dst = src.with_name(f"{src.stem}_fit.zip")
        notes: List[str] = []
        big_names = {zi.filename for zi in big}
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as zout:
            for zi in infos:
                data = zin.read(zi)
                if zi.filename in big_names:
                    pieces, note = shrink_image(data, zi.filename, budget, allow_slice)
                    notes.append(note)
                    for nm, blob in pieces:
                        zout.writestr(nm, blob)
                else:
                    zout.writestr(zi.filename, data)
    return dst, notes


def batch_by_size(files: List[Path], limit_bytes: int, max_count: int = 10) -> List[List[Path]]:
    """Group files into messages so each message has <= max_count files AND a total size
    <= limit_bytes (Discord also limits the combined size of one message's attachments)."""
    batches: List[List[Path]] = []
    cur: List[Path] = []
    cur_size = 0
    for f in files:
        size = f.stat().st_size
        if cur and (len(cur) >= max_count or cur_size + size > limit_bytes):
            batches.append(cur)
            cur, cur_size = [], 0
        cur.append(f)
        cur_size += size
    if cur:
        batches.append(cur)
    return batches


# ------------------------------------------------------------------- TypeR export parts
def _recompress_in_place(path: Path, budget: int) -> bool:
    """Lower the quality of a .jpg/.webp page (same name, same pixel size) until <= budget."""
    from PIL import Image
    if path.suffix.lower() not in (".jpg", ".jpeg", ".webp"):
        return False
    im = Image.open(path)
    im.load()
    im = im.convert("RGB")
    fmt = "WEBP" if path.suffix.lower() == ".webp" else "JPEG"
    for q in (85, 78, 70, 62, 55):
        im.save(path, fmt, quality=q, optimize=(fmt == "JPEG"))
        if path.stat().st_size <= budget:
            return True
    return False


def build_typer_parts(typer_dir: Path, out_dir: Path, limit_bytes: int) -> Tuple[List[Path], List[str]]:
    """Package the TypeR export so every zip fits the upload limit.

    One zip (`typer.zip`) when it fits; otherwise `typer_part1.zip`, `typer_part2.zip`...: each
    part is a complete, independent job (its own typer_job.json with the pages it contains and
    their original `index`), so it can be imported into TypeR on its own. Pixel sizes and file
    names never change, so coordinates stay valid. Raises ValueError when one page alone
    cannot fit (advice in the message)."""
    import json
    job = json.loads((typer_dir / "typer_job.json").read_text(encoding="utf-8"))
    pages = job.get("pages") or []
    if not pages:
        raise ValueError("typer_job.json has no pages")
    budget = int(limit_bytes * 0.93)
    notes: List[str] = []

    for pg in pages:
        f = typer_dir / pg["file"]
        size = f.stat().st_size
        if size <= budget - 4000:
            continue
        if _recompress_in_place(f, budget - 4000):
            notes.append(f"{pg['file']}: {size / 1024 ** 2:.1f}MB → {f.stat().st_size / 1024 ** 2:.1f}MB (ضغط)")
            continue
        hint = ("اختر صيغة JPG" if f.suffix.lower() == ".png" else "جرّب ملفاً بصفحات أقل")
        raise ValueError(f"الصفحة {pg['file']} ({size / 1024 ** 2:.1f}MB) أكبر من حد الرفع "
                         f"({limit_bytes / 1024 ** 2:.0f}MB) حتى بعد الضغط. {hint}.")

    groups: List[List[dict]] = []
    cur: List[dict] = []
    cur_size = 0
    for pg in pages:
        sz = (typer_dir / pg["file"]).stat().st_size + 600 + len(json.dumps(pg, ensure_ascii=False))
        if cur and cur_size + sz > budget - 2000:
            groups.append(cur)
            cur, cur_size = [], 0
        cur.append(pg)
        cur_size += sz
    if cur:
        groups.append(cur)

    out_dir.mkdir(parents=True, exist_ok=True)
    files: List[Path] = []
    for gi, grp in enumerate(groups, 1):
        name = "typer.zip" if len(groups) == 1 else f"typer_part{gi}.zip"
        sub = dict(job)
        sub["pages"] = grp
        if len(groups) > 1:
            sub["part"], sub["parts"] = gi, len(groups)
        zp = out_dir / name
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
            z.writestr("typer_job.json", json.dumps(sub, ensure_ascii=False, indent=1))
            for pg in grp:
                z.write(typer_dir / pg["file"], pg["file"])
        files.append(zp)
    if len(groups) > 1:
        first, last = pages[0]["index"] + 1, pages[-1]["index"] + 1
        notes.append(f"الصفحات {first}–{last} قُسّمت إلى {len(groups)} ملفات TypeR مستقلة "
                     f"(استورد كل ملف على حدة).")
    return files, notes

