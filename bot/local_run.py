# -*- coding: utf-8 -*-
"""Run clean / extract / typer / translate once, synchronously, without Discord or a database.

Used by the Kaggle and marimo notebooks (and handy from a terminal). It builds the exact
same manga.py command line as the bot (bot.runner.build_plan) and produces the same
statistics (bot.stats), so what you test here is what the bot will do.

    from bot.local_run import run_job
    res = run_job("clean", "chapter.zip", {"lama": False})
    print(res.stats)       # pages / bubbles / by_kind / cleanup ...
    print(res.files)       # files that would be sent to the user
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

from . import stats as st
from .config import Config, load_config
from .runner import build_plan, build_typer_parts, inspect_upload


class PipelineError(RuntimeError):
    """Raised when manga.py fails; .tail holds the last log lines."""

    def __init__(self, message: str, tail: Optional[List[str]] = None, log_path: Optional[Path] = None):
        super().__init__(message)
        self.tail = tail or []
        self.log_path = log_path


@dataclass
class RunResult:
    kind: str
    stats: Dict[str, Any]
    files: List[Path]
    workdir: Path
    log_path: Path
    typer_dir: Path
    elapsed_s: float
    progress: st.LogProgress = field(default_factory=st.LogProgress)

    def summary(self) -> str:
        lines = [f"{n}: {v}" for n, v, _ in st.stats_fields(self.kind, self.stats)]
        return "\n".join(lines)


def run_job(kind: str, input_path: "str | os.PathLike[str]", options: Optional[Dict[str, Any]] = None,
            *, cfg: Optional[Config] = None, workdir: Optional[Path] = None,
            on_line: Optional[Callable[[str], None]] = None,
            on_progress: Optional[Callable[[st.LogProgress], None]] = None,
            max_pages: Optional[int] = None) -> RunResult:
    cfg = cfg or load_config()
    src = Path(input_path)
    if not src.is_file():
        raise PipelineError(f"input file not found: {src}")
    limit = max_pages or (cfg.max_pages_translate if kind == "translate" else cfg.max_pages)
    total = inspect_upload(src, cfg, limit)          # raises UploadError with an Arabic message

    wd = Path(workdir) if workdir else cfg.work_dir / uuid.uuid4().hex
    wd.mkdir(parents=True, exist_ok=True)
    inp = wd / f"input{src.suffix.lower()}"
    shutil.copyfile(src, inp)

    job = {"kind": kind, "workdir": str(wd), "input_path": str(inp),
           "options": dict(options or {}), "total_pages": total}
    plan = build_plan(job, cfg)
    log_path = wd / "run.log"
    lp = st.LogProgress()
    tail: Deque[str] = deque(maxlen=40)
    timed_out = {"v": False}

    started = time.monotonic()
    proc = subprocess.Popen(
        plan.argv, cwd=str(cfg.repo_root), env=plan.env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
        text=True, encoding="utf-8", errors="replace", bufsize=1)

    def _kill() -> None:
        timed_out["v"] = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            proc.terminate()

    timer = threading.Timer(cfg.job_timeout_minutes * 60, _kill)
    timer.daemon = True
    timer.start()
    try:
        with open(log_path, "w", encoding="utf-8") as lf:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.rstrip("\r\n")
                lf.write(line + "\n")
                tail.append(line)
                if on_line:
                    on_line(line)
                if lp.feed(line) and on_progress:
                    on_progress(lp)
        rc = proc.wait()
    except KeyboardInterrupt:
        _kill()
        raise
    finally:
        timer.cancel()
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                proc.kill()
    elapsed = time.monotonic() - started

    if timed_out["v"]:
        raise PipelineError(f"timeout after {cfg.job_timeout_minutes} minutes", list(tail), log_path)
    if rc != 0:
        raise PipelineError(f"manga.py exited with code {rc}", list(tail), log_path)

    job_json = plan.typer_dir / "typer_job.json"
    try:
        base: Optional[Dict[str, Any]] = st.stats_from_typer_job(job_json)
    except (FileNotFoundError, ValueError, OSError):
        base = None

    if kind == "extract":
        if base is None:
            raise PipelineError("no typer_job.json was produced", list(tail), log_path)
        files = st.build_extract_files(job_json, wd / "extract", src.name)
    elif kind == "typer":
        if base is None:
            raise PipelineError("no typer_job.json was produced", list(tail), log_path)
        files, _ = build_typer_parts(plan.typer_dir, wd / "typer_out", 10 ** 12)  # local: no size limit
    else:
        files = list(plan.deliver)
    missing = [f.name for f in files if not f.is_file()]
    if missing or not files:
        raise PipelineError(f"missing outputs: {', '.join(missing) or 'none'}", list(tail), log_path)

    size = sum(f.stat().st_size for f in files)
    stats = (st.combine(base, lp, elapsed_s=elapsed, output_bytes=size) if base
             else st.fallback_from_log(lp, elapsed_s=elapsed, output_bytes=size))
    return RunResult(kind, stats, files, wd, log_path, plan.typer_dir, elapsed, lp)


def first_pages(result: RunResult, n: int = 3) -> List[Path]:
    """Cleaned page images of a finished job (from the typer export folder) for previews."""
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    pages = sorted(p for p in result.typer_dir.glob("*") if p.suffix.lower() in exts)
    return pages[:n]


# ----------------------------------------------------------------------- previews
_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _zip_images(zip_path: Path, dest: Path, n: int) -> List[Path]:
    import zipfile
    dest.mkdir(parents=True, exist_ok=True)
    out: List[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(x for x in zf.namelist() if Path(x).suffix.lower() in _IMG_EXTS)
        for i, name in enumerate(names[:n]):
            target = dest / f"{i:03d}_{Path(name).name}"
            target.write_bytes(zf.read(name))
            out.append(target)
    return out


def result_pages(result: RunResult, n: int = 2) -> List[Path]:
    """First pages of the delivered result (cleaned for clean/typer, translated for translate)."""
    for f in result.files:
        if f.suffix.lower() == ".zip":
            return _zip_images(f, result.workdir / "preview_result", n)
        if f.suffix.lower() == ".pdf":
            return _pdf_pages(f, result.workdir / "preview_result", n)
    return []


def original_pages(result: RunResult, n: int = 2) -> List[Path]:
    inp = next(iter(sorted(result.workdir.glob("input.*"))), None)
    if inp is None:
        return []
    if inp.suffix.lower() == ".zip":
        return _zip_images(inp, result.workdir / "preview_orig", n)
    if inp.suffix.lower() == ".pdf":
        return _pdf_pages(inp, result.workdir / "preview_orig", n)
    return [inp]


def _pdf_pages(pdf: Path, dest: Path, n: int) -> List[Path]:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    dest.mkdir(parents=True, exist_ok=True)
    out: List[Path] = []
    with fitz.open(pdf) as doc:
        for i in range(min(n, doc.page_count)):
            p = dest / f"{i:03d}_{pdf.stem}.png"
            doc[i].get_pixmap(dpi=100).save(str(p))
            out.append(p)
    return out


def side_by_side(result: RunResult, n: int = 2, height: int = 900):
    """PIL image: original page(s) on the left, result page(s) on the right (RGB)."""
    from PIL import Image
    a, b = original_pages(result, n), result_pages(result, n)
    if not b:
        b = first_pages(result, n)
    tiles = []
    for path in list(a[:n]) + list(b[:n]):
        im = Image.open(path).convert("RGB")
        w = max(1, int(im.width * height / im.height))
        tiles.append(im.resize((w, height)))
    if not tiles:
        raise PipelineError("no preview images were produced")
    gap = 12
    canvas = Image.new("RGB", (sum(t.width for t in tiles) + gap * (len(tiles) - 1), height), (40, 40, 40))
    x = 0
    for t in tiles:
        canvas.paste(t, (x, 0))
        x += t.width + gap
    return canvas
