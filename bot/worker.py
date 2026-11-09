# -*- coding: utf-8 -*-
"""Job worker: claims jobs from PostgreSQL, runs manga.py, reports back through a Notifier."""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from . import stats as st
from .config import Config
from .db import Database, Job
from .runner import ProcessHandle, UploadError, build_plan, run_plan, split_zip

log = logging.getLogger("mangabot.worker")


class Notifier(Protocol):
    """Everything the worker needs from the chat platform (Discord implements this)."""

    def upload_limit(self, job: Job) -> int: ...
    async def progress(self, job: Job, text: str, lp: st.LogProgress) -> None: ...
    async def done(self, job: Job, stats: Dict[str, Any], files: List[Path],
                   notes: List[str]) -> None: ...
    async def failed(self, job: Job, error: str, tail: List[str]) -> None: ...


class Worker:
    def __init__(self, cfg: Config, db: Database, notifier: Notifier):
        self.cfg = cfg
        self.db = db
        self.notifier = notifier
        self.wake = asyncio.Event()
        self.handles: Dict[int, ProcessHandle] = {}
        self._stop = False

    # ------------------------------------------------------------------ control
    def notify_new_job(self) -> None:
        self.wake.set()

    def stop(self) -> None:
        self._stop = True
        self.wake.set()

    async def cancel_running(self, job_id: int) -> bool:
        h = self.handles.get(job_id)
        if h is None:
            return False
        await h.cancel()
        return True

    # --------------------------------------------------------------------- loops
    async def run_forever(self) -> None:
        while not self._stop:
            try:
                job = await self.db.claim_job()
            except Exception:
                log.exception("claim_job failed")
                await asyncio.sleep(self.cfg.poll_seconds)
                continue
            if job is None:
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), self.cfg.poll_seconds)
                except asyncio.TimeoutError:
                    pass
                continue
            try:
                await self.process(job)
            except Exception as e:  # never let one job kill the loop
                log.exception("job %s crashed", job["id"])
                await self._fail(job, f"خطأ داخلي: {e}", [])

    async def cleanup_forever(self, every: float = 60.0) -> None:
        while not self._stop:
            try:
                await self.cleanup_once()
            except Exception:
                log.exception("cleanup failed")
            await asyncio.sleep(every)

    async def cleanup_once(self) -> int:
        root = self.cfg.work_dir.resolve()
        removed = 0
        for row in await self.db.take_expired_workdirs():
            p = Path(row["workdir"]).resolve()
            # safety: only ever delete inside the bot's own work dir
            if root in p.parents:
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
            await self.db.mark_workdir_removed(row["id"])
        return removed

    # ------------------------------------------------------------------- one job
    async def _fail(self, job: Job, error: str, tail: List[str]) -> None:
        await self.db.fail_job(job["id"], error, self.cfg.file_ttl_minutes)
        try:
            await self.notifier.failed(job, error, tail)
        except Exception:
            log.exception("notifier.failed")

    async def process(self, job: Job) -> None:
        jid = job["id"]
        if not job.get("workdir"):
            return await self._fail(job, "مجلد المهمة غير موجود (ربما حُذف).", [])
        wd = Path(job["workdir"])
        try:
            plan = build_plan(job, self.cfg)
        except ValueError as e:
            return await self._fail(job, str(e), [])
        if not Path(job["input_path"]).is_file():
            return await self._fail(job, "ملف الإدخال لم يعد موجوداً.", [])
        if not self.cfg.manga_script.is_file():
            return await self._fail(job, "manga.py غير موجود على السيرفر.", [])

        lp = st.LogProgress()
        dirty = {"v": False}
        handle = ProcessHandle()
        self.handles[jid] = handle

        def on_line(line: str) -> None:
            if lp.feed(line):
                dirty["v"] = True

        async def reporter() -> None:
            while True:
                await asyncio.sleep(self.cfg.progress_interval)
                if not dirty["v"]:
                    continue
                dirty["v"] = False
                text = st.progress_text(lp, job.get("total_pages"))
                await self.db.update_progress(
                    jid, text=text, pages_done=lp.pages_done, bubbles_seen=lp.bubbles_seen)
                try:
                    await self.notifier.progress(job, text, lp)
                except Exception:
                    log.exception("notifier.progress")

        rep = asyncio.create_task(reporter())
        started = time.monotonic()
        try:
            res = await run_plan(
                plan, cwd=self.cfg.repo_root, log_path=wd / "run.log",
                timeout_s=self.cfg.job_timeout_minutes * 60, on_line=on_line, handle=handle)
        finally:
            rep.cancel()
            self.handles.pop(jid, None)
        elapsed = time.monotonic() - started

        if res.cancelled:
            return  # /cancel already updated the row and told the user
        if res.timed_out:
            return await self._fail(
                job, f"انتهت مهلة المعالجة ({self.cfg.job_timeout_minutes} دقيقة).", res.tail)
        if res.returncode != 0:
            return await self._fail(
                job, f"manga.py انتهى بخطأ (كود {res.returncode}).", res.tail)

        await self._finish(job, plan, lp, elapsed, res.tail)

    async def _finish(self, job: Job, plan, lp: st.LogProgress, elapsed: float,
                      tail: List[str]) -> None:
        wd = Path(job["workdir"])
        job_json = plan.typer_dir / "typer_job.json"

        files: List[Path] = list(plan.deliver)
        notes: List[str] = []
        try:
            base = st.stats_from_typer_job(job_json)
        except (FileNotFoundError, ValueError, OSError) as e:
            log.warning("job %s: no usable typer_job.json (%s)", job["id"], e)
            base = None

        if job["kind"] == "extract":
            if base is None:
                return await self._fail(job, "لم يُنتج الاستخراج أي نتيجة (لا يوجد typer_job.json).", tail)
            files = st.build_extract_files(job_json, wd / "extract", job.get("source_name", ""))

        missing = [f.name for f in files if not f.is_file()]
        if missing or not files:
            return await self._fail(
                job, f"المخرجات غير موجودة: {', '.join(missing) or 'لا شيء'}", tail)

        # fit under the platform upload limit
        limit = self.notifier.upload_limit(job)
        final: List[Path] = []
        for f in files:
            if f.stat().st_size <= limit:
                final.append(f)
            elif f.suffix == ".zip" and job["kind"] in ("clean", "translate"):
                try:
                    parts = split_zip(f, limit)
                except ValueError as e:
                    return await self._fail(job, f"الناتج كبير ولا يمكن تقسيمه: {e}", tail)
                notes.append(f"الناتج أكبر من حد الرفع فقُسّم إلى {len(parts)} ملفات.")
                final.extend(parts)
            else:
                mb = f.stat().st_size / 1024 ** 2
                hint = "جرّب صيغة zip أو ملفاً بصفحات أقل." if f.suffix == ".pdf" \
                    else "جرّب ملفاً بصفحات أقل."
                return await self._fail(
                    job, f"الناتج ({mb:.1f}MB) أكبر من حد الرفع ({limit / 1024 ** 2:.0f}MB). {hint}",
                    tail)

        size = sum(f.stat().st_size for f in final)
        stats = (st.combine(base, lp, elapsed_s=elapsed, output_bytes=size) if base
                 else st.fallback_from_log(lp, elapsed_s=elapsed, output_bytes=size))

        if job["kind"] == "translate" and stats.get("dialogue") and \
                stats.get("translated", 0) < stats["dialogue"]:
            left = stats["dialogue"] - stats["translated"]
            notes.append(f"⚠️ {left} حوار لم يُترجم (قد يكون نموذج Ollama فشل أو انقطع).")

        ok = await self.db.finish_job(
            job["id"], stats=stats, result_files=[str(f) for f in final],
            ttl_minutes=self.cfg.file_ttl_minutes)
        if not ok:
            return  # cancelled while finishing
        try:
            await self.notifier.done(job, stats, final, notes)
        except Exception:
            log.exception("notifier.done")
