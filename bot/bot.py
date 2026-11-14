# -*- coding: utf-8 -*-
"""Discord bot: /clean /extract /typer /chapter /translate /status /history /cancel /queue /ping."""
from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import discord
from discord import app_commands

from . import ui
from . import stats as st
from .config import Config, load_config
from .db import Database, Job
from .fetch import FetchError, classify, fetch_link
from .runner import ALLOWED_EXTS, UploadError, batch_by_size, inspect_upload
from .worker import Worker

log = logging.getLogger("mangabot")

OCR_CHOICES = [
    app_commands.Choice(name="إنجليزي", value="en"),
    app_commands.Choice(name="ياباني + إنجليزي", value="ja"),
    app_commands.Choice(name="كوري + إنجليزي", value="ko"),
    app_commands.Choice(name="صيني + إنجليزي", value="zh"),
]
ORDER_CHOICES = [
    app_commands.Choice(name="من اليمين لليسار (مانجا)", value="rtl"),
    app_commands.Choice(name="من اليسار لليمين (ويبتون/كوميكس)", value="ltr"),
]
QUALITY_CHOICES = [
    app_commands.Choice(name="سريع (OpenCV)", value="fast"),
    app_commands.Choice(name="جودة أعلى (LaMa — أبطأ)", value="lama"),
]
FORMAT_CHOICES = [
    app_commands.Choice(name="JPG (أصغر)", value="jpg"),
    app_commands.Choice(name="PNG (أعلى جودة)", value="png"),
    app_commands.Choice(name="WEBP", value="webp"),
]
DIALECT_CHOICES = [
    app_commands.Choice(name="فصحى مبسّطة", value="msa"),
    app_commands.Choice(name="لهجة مصرية", value="egyptian"),
]
OUTFMT_CHOICES = [
    app_commands.Choice(name="ZIP (صور)", value="zip"),
    app_commands.Choice(name="PDF", value="pdf"),
]


class GuardedTree(app_commands.CommandTree):
    """Optional allow-list of servers."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cfg: Config = self.client.cfg  # type: ignore[attr-defined]
        if cfg.allowed_guild_ids and interaction.guild_id not in cfg.allowed_guild_ids:
            await interaction.response.send_message(
                "هذا البوت غير مفعّل في هذا السيرفر.", ephemeral=True)
            return False
        return True


class DiscordNotifier:
    def __init__(self, client: "MangaBot"):
        self.client = client

    def upload_limit(self, job: Job) -> int:
        cfg = self.client.cfg
        if cfg.reply_limit_mb:
            return cfg.reply_limit_mb * 1024 * 1024
        guild = self.client.get_guild(job["guild_id"]) if job.get("guild_id") else None
        limit = guild.filesize_limit if guild else 10 * 1024 * 1024
        return int(limit * 0.95)

    def _status_message(self, job: Job):
        if not job.get("message_id"):
            return None
        ch = self.client.get_partial_messageable(job["channel_id"])
        return ch.get_partial_message(job["message_id"])

    async def _edit(self, job: Job, embed: discord.Embed) -> None:
        msg = self._status_message(job)
        if msg is None:
            return
        try:
            await msg.edit(embed=embed)
        except discord.HTTPException as e:
            log.debug("edit failed for job %s: %s", job["id"], e)

    async def _send(self, job: Job, **kwargs: Any) -> None:
        mention = discord.AllowedMentions(users=[discord.Object(job["user_id"])])
        ch = self.client.get_partial_messageable(job["channel_id"])
        try:
            await ch.send(allowed_mentions=mention, **kwargs)
        except discord.HTTPException:
            # channel not writable → fall back to a DM
            try:
                user = await self.client.fetch_user(job["user_id"])
                await user.send(**kwargs)
            except discord.HTTPException:
                log.warning("could not deliver result of job %s", job["id"])

    async def progress(self, job: Job, text: str, lp: st.LogProgress,
                       elapsed: float, idle: float) -> None:
        await self._edit(job, ui.running_embed(job, text, lp, elapsed=elapsed, idle=idle))

    async def done(self, job: Job, stats: Dict[str, Any], files: List[Path],
                   notes: List[str]) -> None:
        embed = ui.done_embed(job, stats, notes, self.client.cfg.file_ttl_minutes)
        await self._edit(job, embed)
        # ≤10 attachments per message and the combined size of a message must fit the limit too
        if not files:   # delivered as external link(s): just ping the user with the embed
            await self._send(job, content=f"<@{job['user_id']}> مهمتك #{job['id']} جاهزة ✅ — "
                                          f"رابط التحميل في الرسالة", embed=embed, files=[])
            return
        for i, chunk in enumerate(batch_by_size(files, self.upload_limit(job))):
            await self._send(
                job,
                content=f"<@{job['user_id']}> مهمتك #{job['id']} جاهزة ✅" if i == 0 else None,
                embed=embed if i == 0 else None,
                files=[discord.File(str(f), filename=f.name) for f in chunk])

    async def failed(self, job: Job, error: str, tail: List[str]) -> None:
        embed = ui.failed_embed(job, error, tail)
        await self._edit(job, embed)
        await self._send(job, content=f"<@{job['user_id']}> فشلت مهمتك #{job['id']}",
                         embed=embed)


def _read_token(path: str) -> str:
    """Fresh Google access token written (and refreshed) by the Colab notebook, if any."""
    try:
        return Path(path).read_text().strip() if path else ""
    except OSError:
        return ""


class MangaBot(discord.Client):
    def __init__(self, cfg: Config):
        super().__init__(intents=discord.Intents.default())
        self.cfg = cfg
        self.tree = GuardedTree(self)
        self.db: Optional[Database] = None
        self.worker: Optional[Worker] = None
        self._tasks: List[asyncio.Task] = []
        self._register_commands()

    # ---------------------------------------------------------------- lifecycle
    async def setup_hook(self) -> None:
        self.cfg.work_dir.mkdir(parents=True, exist_ok=True)
        self.db = await Database.connect(self.cfg.database_url)
        n = await self.db.requeue_stale()
        if n:
            log.info("re-queued %d interrupted job(s)", n)
        self.worker = Worker(self.cfg, self.db, DiscordNotifier(self))
        for _ in range(self.cfg.workers):
            self._tasks.append(asyncio.create_task(self.worker.run_forever()))
        self._tasks.append(asyncio.create_task(self.worker.cleanup_forever()))
        if self.cfg.purge_old_commands:
            from .purge_commands import purge_commands
            res = await purge_commands(self, include_global=False, log=log.info)
            log.info("purged stale server commands: %s", res["guilds"] or "none")
        await self.tree.sync()

    async def close(self) -> None:
        if self.worker:
            self.worker.stop()
        for t in self._tasks:
            t.cancel()
        if self.db:
            await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("logged in as %s", self.user)

    # --------------------------------------------------------------- submission
    async def submit(self, interaction: discord.Interaction, kind: str,
                     attachment: Optional[discord.Attachment], options: Dict[str, Any],
                     link: Optional[str] = None) -> None:
        assert self.db is not None and self.worker is not None
        cfg = self.cfg
        if bool(attachment) == bool(link and link.strip()):
            await interaction.response.send_message(
                "أرفق ملفاً في `file` **أو** الصق رابطاً في `link` (واحد فقط).", ephemeral=True)
            return
        if link and not cfg.allow_links:
            await interaction.response.send_message("الروابط غير مفعّلة على هذا البوت.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)

        if await self.db.count_active(interaction.user.id) >= cfg.max_active_per_user:
            await interaction.followup.send(
                f"لديك {cfg.max_active_per_user} مهام قيد التنفيذ بالفعل. انتظر حتى تنتهي أو "
                f"استخدم `/cancel`.", ephemeral=True)
            return
        if attachment is not None:
            ext = Path(attachment.filename).suffix.lower()
            if ext not in ALLOWED_EXTS:
                await interaction.followup.send(
                    "الصيغة غير مدعومة. المسموح: صورة (jpg/png/webp) أو ZIP أو PDF.", ephemeral=True)
                return
            if attachment.size > cfg.max_upload_mb * 1024 * 1024:
                await interaction.followup.send(
                    f"الملف ({attachment.size / 1024 ** 2:.0f}MB) أكبر من الحد المسموح "
                    f"({cfg.max_upload_mb}MB). ارفعه على Google Drive/Gofile وأرسل الرابط في "
                    f"`link`، أو قسّم الفصل.", ephemeral=True)
                return
        else:
            try:   # fail fast on a bad link before creating anything
                classify(link or "")
            except FetchError as e:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
                return

        max_pages = cfg.max_pages_translate if kind == "translate" else cfg.max_pages
        workdir = cfg.work_dir / uuid.uuid4().hex
        workdir.mkdir(parents=True)
        try:
            if attachment is not None:
                input_path = workdir / f"input{ext}"
                source_name = attachment.filename
                await attachment.save(input_path)
            else:
                got = await fetch_link(link or "", workdir / "dl", cfg.max_link_mb * 1024 * 1024,
                                      google_api_key=cfg.google_api_key, max_files=max_pages,
                                      google_token=_read_token(cfg.google_token_file))
                ext = Path(got.filename).suffix.lower()
                input_path = workdir / f"input{ext}"
                got.path.replace(input_path)
                source_name = got.filename
            pages = await asyncio.to_thread(inspect_upload, input_path, cfg, max_pages)
            job = await self.db.create_job(
                user_id=interaction.user.id, guild_id=interaction.guild_id,
                channel_id=interaction.channel_id or 0, kind=kind,
                source_name=source_name, workdir=str(workdir),
                input_path=str(input_path), total_pages=pages, options=options)
        except (UploadError, FetchError) as e:
            shutil.rmtree(workdir, ignore_errors=True)
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception:
            shutil.rmtree(workdir, ignore_errors=True)
            log.exception("submit failed")
            await interaction.followup.send("❌ تعذّر استلام الملف، حاول مرة أخرى.", ephemeral=True)
            return

        pos = await self.db.queue_position(job["id"])
        msg = await interaction.followup.send(embed=ui.queued_embed(job, pos), wait=True)
        await self.db.set_message(job["id"], msg.id)
        self.worker.notify_new_job()

    # ----------------------------------------------------------------- commands
    def _register_commands(self) -> None:
        tree = self.tree

        @tree.command(name="clean", description="تنظيف الصفحات: مسح النص من الفقاعات وإرجاع صفحات نظيفة")
        @app_commands.describe(file="صورة أو ZIP أو PDF (أو استخدم link)", link="رابط Google Drive أو Gofile بدل الرفع", quality="جودة المسح",
                               format="صيغة الصور الناتجة", ocr="لغة النص الأصلي")
        @app_commands.choices(quality=QUALITY_CHOICES, format=FORMAT_CHOICES, ocr=OCR_CHOICES)
        async def clean(interaction: discord.Interaction, file: Optional[discord.Attachment] = None, link: Optional[str] = None,
                        quality: str = "fast", format: str = "jpg", ocr: str = "en"):
            await self.submit(interaction, "clean", file,
                              {"lama": quality == "lama", "img_format": format, "ocr": ocr}, link=link)

        @tree.command(name="extract", description="استخراج النصوص الأصلية من الصفحات (ملف txt + json)")
        @app_commands.describe(file="صورة أو ZIP أو PDF (أو استخدم link)", link="رابط Google Drive أو Gofile بدل الرفع", ocr="لغة النص الأصلي",
                               reading_order="ترتيب القراءة")
        @app_commands.choices(ocr=OCR_CHOICES, reading_order=ORDER_CHOICES)
        async def extract(interaction: discord.Interaction, file: Optional[discord.Attachment] = None, link: Optional[str] = None,
                          ocr: str = "en", reading_order: str = "rtl"):
            await self.submit(interaction, "extract", file,
                              {"ocr": ocr, "reading_order": reading_order}, link=link)

        @tree.command(name="typer", description="تنظيف + إحداثيات الفقاعات لاستيرادها في TypeR Web")
        @app_commands.describe(file="صورة أو ZIP أو PDF (أو استخدم link)", link="رابط Google Drive أو Gofile بدل الرفع", quality="جودة المسح",
                               ocr="لغة النص الأصلي", reading_order="ترتيب القراءة",
                               format="صيغة صور التصدير")
        @app_commands.choices(quality=QUALITY_CHOICES, ocr=OCR_CHOICES, reading_order=ORDER_CHOICES,
                              format=FORMAT_CHOICES)
        async def typer(interaction: discord.Interaction, file: Optional[discord.Attachment] = None, link: Optional[str] = None,
                        quality: str = "fast", ocr: str = "en", reading_order: str = "rtl",
                        format: str = "jpg"):
            await self.submit(interaction, "typer", file,
                              {"lama": quality == "lama", "ocr": ocr, "img_format": format,
                               "reading_order": reading_order}, link=link)

        @tree.command(name="chapter", description="ملف chapter.zip: مجلد الصور النظيفة + chapter.json (الترجمة اختيارية)")
        @app_commands.describe(file="صورة أو ZIP أو PDF (أو استخدم link)", link="رابط Google Drive أو Gofile بدل الرفع", translate="ترجمة النصوص للعربية داخل chapter.json (Ollama)",
                               dialect="أسلوب العربية", quality="جودة المسح", ocr="لغة النص الأصلي",
                               reading_order="ترتيب القراءة", format="صيغة الصور", model="نموذج Ollama")
        @app_commands.choices(dialect=DIALECT_CHOICES, quality=QUALITY_CHOICES, ocr=OCR_CHOICES,
                              reading_order=ORDER_CHOICES, format=FORMAT_CHOICES)
        async def chapter(interaction: discord.Interaction, file: Optional[discord.Attachment] = None, link: Optional[str] = None,
                          translate: bool = False, dialect: str = "msa", quality: str = "fast",
                          ocr: str = "en", reading_order: str = "rtl", format: str = "jpg",
                          model: Optional[str] = None):
            if model and model not in self.cfg.allowed_models:
                await interaction.response.send_message(
                    f"النموذج غير مسموح. المتاح: {', '.join(self.cfg.allowed_models)}", ephemeral=True)
                return
            await self.submit(interaction, "chapter", file, {
                "translate": translate, "dialect": dialect, "lama": quality == "lama", "ocr": ocr,
                "reading_order": reading_order, "img_format": format,
                "model": model or self.cfg.ollama_model}, link=link)

        @tree.command(name="translate", description="ترجمة المانجا إلى العربية (Ollama محلي) مع تنظيف وكتابة النص")
        @app_commands.describe(file="صورة أو ZIP أو PDF (أو استخدم link)", link="رابط Google Drive أو Gofile بدل الرفع", dialect="أسلوب العربية",
                               ocr="لغة النص الأصلي", reading_order="ترتيب القراءة",
                               output="صيغة الناتج", quality="جودة المسح",
                               model="نموذج Ollama")
        @app_commands.choices(dialect=DIALECT_CHOICES, ocr=OCR_CHOICES, reading_order=ORDER_CHOICES,
                              output=OUTFMT_CHOICES, quality=QUALITY_CHOICES)
        async def translate(interaction: discord.Interaction, file: Optional[discord.Attachment] = None, link: Optional[str] = None,
                            dialect: str = "msa", ocr: str = "en", reading_order: str = "rtl",
                            output: str = "zip", quality: str = "fast",
                            model: Optional[str] = None):
            if model and model not in self.cfg.allowed_models:
                await interaction.response.send_message(
                    f"النموذج غير مسموح. المتاح: {', '.join(self.cfg.allowed_models)}",
                    ephemeral=True)
                return
            await self.submit(interaction, "translate", file, {
                "dialect": dialect, "ocr": ocr, "reading_order": reading_order,
                "format": output, "lama": quality == "lama",
                "model": model or self.cfg.ollama_model}, link=link)

        @translate.autocomplete("model")
        async def _model_ac(interaction: discord.Interaction, current: str):
            return [app_commands.Choice(name=m, value=m)
                    for m in self.cfg.allowed_models if current.lower() in m.lower()][:25]

        @tree.command(name="status", description="حالة مهمة (آخر مهمة لك إن لم تحدد رقماً)")
        @app_commands.describe(job_id="رقم المهمة")
        async def status(interaction: discord.Interaction, job_id: Optional[int] = None):
            assert self.db is not None
            if job_id is None:
                rows = await self.db.user_history(interaction.user.id, 1)
                job = rows[0] if rows else None
            else:
                job = await self.db.get_job(job_id)
            if job is None or not self._can_see(interaction, job):
                await interaction.response.send_message("لا توجد مهمة بهذا الرقم.", ephemeral=True)
                return
            pos = await self.db.queue_position(job["id"]) if job["status"] == "pending" else 0
            await interaction.response.send_message(embed=ui.status_embed(job, pos), ephemeral=True)

        @tree.command(name="history", description="سجل مهامك وإجمالي الصفحات والفقاعات")
        async def history(interaction: discord.Interaction):
            assert self.db is not None
            jobs = await self.db.user_history(interaction.user.id, 10)
            totals = await self.db.user_totals(interaction.user.id)
            await interaction.response.send_message(
                embed=ui.history_embed(jobs, totals), ephemeral=True)

        @tree.command(name="cancel", description="إلغاء مهمة قيد الانتظار أو التنفيذ")
        @app_commands.describe(job_id="رقم المهمة")
        async def cancel(interaction: discord.Interaction, job_id: int):
            assert self.db is not None and self.worker is not None
            is_admin = interaction.user.id in self.cfg.admin_user_ids
            prev = await self.db.cancel_job(
                job_id, interaction.user.id, self.cfg.file_ttl_minutes, is_admin=is_admin)
            if prev is None:
                await interaction.response.send_message(
                    "لا يمكن إلغاء هذه المهمة (غير موجودة، أو ليست لك، أو انتهت).", ephemeral=True)
                return
            if prev == "running":
                await self.worker.cancel_running(job_id)
            await interaction.response.send_message(f"🚫 أُلغيت المهمة #{job_id}.", ephemeral=True)

        @tree.command(name="queue", description="حالة الطابور الحالية")
        async def queue(interaction: discord.Interaction):
            assert self.db is not None
            q = await self.db.queue_summary()
            await interaction.response.send_message(
                f"⚙️ قيد المعالجة: **{q['running']}** • ⏳ في الانتظار: **{q['pending']}**",
                ephemeral=True)

        @tree.command(name="help", description="شرح الأوامر والروابط والميزات الجديدة")
        async def help_cmd(interaction: discord.Interaction):
            await interaction.response.send_message(embed=ui.help_embed(self.cfg), ephemeral=True)

        @tree.command(name="ping", description="فحص البوت وقاعدة البيانات وOllama")
        async def ping(interaction: discord.Interaction):
            assert self.db is not None
            await interaction.response.defer(ephemeral=True)
            lines = [f"🏓 زمن الاستجابة: **{round(self.latency * 1000)}ms**"]
            try:
                await self.db.pool.fetchval("SELECT 1")
                lines.append("🗄️ PostgreSQL: ✅")
            except Exception:
                lines.append("🗄️ PostgreSQL: ❌")
            lines.append(await self._ollama_status())
            q = await self.db.queue_summary()
            lines.append(f"📋 الطابور: {q['running']} قيد التنفيذ / {q['pending']} منتظر")
            await interaction.followup.send("\n".join(lines), ephemeral=True)

    # ------------------------------------------------------------------ helpers
    def _can_see(self, interaction: discord.Interaction, job: Job) -> bool:
        return job["user_id"] == interaction.user.id or \
            interaction.user.id in self.cfg.admin_user_ids

    async def _ollama_status(self) -> str:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as s:
                async with s.get(f"{self.cfg.ollama_url}/api/tags") as r:
                    data = await r.json()
            names = {m.get("name") for m in data.get("models", [])}
            have = self.cfg.ollama_model in names
            return (f"🤖 Ollama: ✅ — النموذج `{self.cfg.ollama_model}` "
                    f"{'متوفر' if have else '**غير محمّل** (ollama pull)'}")
        except Exception:
            return "🤖 Ollama: ❌ غير متاح (الترجمة لن تعمل؛ التنظيف والاستخراج يعملان)"


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    if not cfg.discord_token:
        raise SystemExit("DISCORD_TOKEN is not set (see bot/.env.example)")
    MangaBot(cfg).run(cfg.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
