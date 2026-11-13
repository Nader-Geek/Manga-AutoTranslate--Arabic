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
from .hosting import UploadFailed, upload_gofile
from .config import Config
from .db import Database, Job
from .runner import (ProcessHandle, UploadError, build_plan, build_typer_parts, retry_options,
                     run_plan, shrink_oversized_images, split_zip)

log = logging.getLogger("mangabot.worker")


class Notifier(Protocol):
    """Everything the worker needs from the chat platform (Discord implements this)."""

    def upload_limit(self, job: Job) -> int: ...
    async def progress(self, job: Job, text: str, lp: st.LogProgress,
                       elapsed: float, idle: float) -> None: ...
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

        started = time.monotonic()
        act = {"t": started}          # monotonic time of manga.py's last output line

        def on_line(line: str) -> None:
            act["t"] = time.monotonic()
            if lp.feed(line):
                dirty["v"] = True

        async def reporter() -> None:
            # Push when something changed, and at least every heartbeat_seconds even when
            # manga.py is silent (a long translation/LaMa step) so the message never looks frozen.
            last_push = 0.0
            while True:
                await asyncio.sleep(self.cfg.progress_interval)
                now = time.monotonic()
                if not dirty["v"] and now - last_push < self.cfg.heartbeat_seconds:
                    continue
                dirty["v"] = False
                last_push = now
                idle = now - act["t"]
                text = st.progress_text(lp, job.get("total_pages"))
                try:
                    await self.db.update_progress(
                        jid, text=text, pages_done=lp.pages_done,
                        bubbles_seen=lp.bubbles_seen, idle_s=idle)
                    await self.notifier.progress(job, text, lp, now - started, idle)
                except Exception:
                    log.exception("progress update failed")

        retry_note: List[str] = []
        rep = asyncio.create_task(reporter())
        try:
            res = await run_plan(
                plan, cwd=self.cfg.repo_root, log_path=wd / "run.log",
                timeout_s=self.cfg.job_timeout_minutes * 60, on_line=on_line, handle=handle)
            # a known layout error (pages chained too long / no text-safe cut) -> retry once
            # with the fix manga.py itself suggests, and tell the user
            fix = None
            if res.returncode not in (0, None) and not res.cancelled and not res.timed_out:
                fix = retry_options(job.get("options") or {}, res.tail)
            if fix:
                new_opts, note = fix
                log.info("job %s: retrying (%s)", jid, note[:40])
                retry_note.append(note)
                job = {**job, "options": new_opts}
                plan = build_plan(job, self.cfg)
                shutil.rmtree(plan.typer_dir, ignore_errors=True)
                lp = st.LogProgress()
                dirty["v"] = False
                act["t"] = time.monotonic()
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

        await self._finish(job, plan, lp, elapsed, res.tail, retry_note)

    async def _finish(self, job: Job, plan, lp: st.LogProgress, elapsed: float,
                      tail: List[str], pre_notes: Optional[List[str]] = None) -> None:
        wd = Path(job["workdir"])
        job_json = plan.typer_dir / "typer_job.json"

        files: List[Path] = list(plan.deliver)
        notes: List[str] = list(pre_notes or [])
        try:
            base = st.stats_from_typer_job(job_json)
        except (FileNotFoundError, ValueError, OSError) as e:
            log.warning("job %s: no usable typer_job.json (%s)", job["id"], e)
            base = None

        # Too big for Discord? Upload the ORIGINAL, full-quality result to the external host
        # and send a link; if that is off or fails, fall through to compress/split below.
        limit = self.notifier.upload_limit(job)
        if self.cfg.external_host == "gofile" and job["kind"] in ("clean", "translate", "typer") \
                and (job["kind"] != "typer" or base is not None):
            links, ext_notes = await self._try_external(job, plan, wd, lp, elapsed, limit)
            notes.extend(ext_notes)
            if links:
                return await self._complete(job, base, lp, elapsed, [], notes, links)

        if job["kind"] == "extract":
            if base is None:
                return await self._fail(job, "لم يُنتج الاستخراج أي نتيجة (لا يوجد typer_job.json).", tail)
            files = st.build_extract_files(job_json, wd / "extract", job.get("source_name", ""))
        elif job["kind"] == "typer":
            if base is None:
                return await self._fail(job, "لم يُنتج التصدير أي نتيجة (لا يوجد typer_job.json).", tail)
            try:   # one zip, or several independent TypeR jobs when it exceeds the upload limit
                files, typer_notes = await asyncio.to_thread(
                    build_typer_parts, plan.typer_dir, wd / "typer_out",
                    self.notifier.upload_limit(job))
            except (ValueError, OSError) as e:
                return await self._fail(job, str(e), tail)
            notes.extend(f"🗜️ {n}" for n in typer_notes)

        missing = [f.name for f in files if not f.is_file()]
        if missing or not files:
            return await self._fail(
                job, f"المخرجات غير موجودة: {', '.join(missing) or 'لا شيء'}", tail)

        # fit under the platform upload limit
        final: List[Path] = []
        for f in files:
            if f.stat().st_size <= limit:
                final.append(f)
            elif f.suffix == ".zip" and job["kind"] in ("clean", "translate"):
                try:
                    # a single image (e.g. a tall PNG strip) can exceed the limit by itself
                    f2, shrink_notes = await asyncio.to_thread(shrink_oversized_images, f, limit)
                    parts = await asyncio.to_thread(split_zip, f2, limit)
                except Exception as e:
                    return await self._fail(job, f"الناتج كبير ولا يمكن تقليله: {e}", tail)
                notes.extend(f"🗜️ {n}" for n in shrink_notes)
                if len(parts) > 1:
                    notes.append(f"الناتج أكبر من حد الرفع فقُسّم إلى {len(parts)} ملفات.")
                final.extend(parts)
            else:
                mb = f.stat().st_size / 1024 ** 2
                hint = "جرّب صيغة zip أو ملفاً بصفحات أقل." if f.suffix == ".pdf" \
                    else "جرّب ملفاً بصفحات أقل."
                return await self._fail(
                    job, f"الناتج ({mb:.1f}MB) أكبر من حد الرفع ({limit / 1024 ** 2:.0f}MB). {hint}",
                    tail)

        await self._complete(job, base, lp, elapsed, final, notes, [])

    async def _try_external(self, job: Job, plan, wd: Path, lp: st.LogProgress, elapsed: float,
                            limit: int):
        """Returns ([{"name","url","size"}...], notes). Empty links = use the Discord path."""
        notes: List[str] = []
        try:
            if job["kind"] == "typer":   # one complete, unmodified export (no size limit)
                raw, _ = await asyncio.to_thread(
                    build_typer_parts, plan.typer_dir, wd / "typer_full", 10 ** 12)
            else:
                raw = list(plan.deliver)
            raw = [f for f in raw if f.is_file()]
            if not raw or all(f.stat().st_size <= limit for f in raw):
                return [], notes                      # fits Discord as it is
            links: List[Dict[str, Any]] = []
            for i, f in enumerate(raw, 1):
                try:
                    await self.notifier.progress(
                        job, f"⬆️ رفع {f.name} ({f.stat().st_size / 1024 ** 2:.0f}MB) "
                             f"إلى gofile ({i}/{len(raw)})", lp, elapsed, 0.0)
                except Exception:
                    pass
                up = await upload_gofile(f, url=self.cfg.gofile_upload_url,
                                         token=self.cfg.gofile_token)
                links.append({"name": f.name, "url": up.url, "size": up.size})
            return links, notes
        except Exception as e:   # UploadFailed or anything unexpected: never lose the job
            log.warning("job %s: external upload failed: %s", job["id"], e)
            notes.append(f"⚠️ تعذّر الرفع الخارجي ({str(e)[:120]}) — سأرسل عبر ديسكورد "
                         f"بعد الضغط/التقسيم.")
            return [], notes

    async def _complete(self, job: Job, base, lp: st.LogProgress, elapsed: float,
                        final: List[Path], notes: List[str], links: List[Dict[str, Any]]) -> None:
        size = sum(f.stat().st_size for f in final) + sum(l["size"] for l in links)
        stats = (st.combine(base, lp, elapsed_s=elapsed, output_bytes=size) if base
                 else st.fallback_from_log(lp, elapsed_s=elapsed, output_bytes=size))
        if links:
            stats["external_links"] = links

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
