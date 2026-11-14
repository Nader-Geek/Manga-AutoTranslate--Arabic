# -*- coding: utf-8 -*-
"""Discord embeds. Pure functions, so they can be tested without a connection."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import discord

from . import stats as st

KIND_TITLES = {
    "clean": "🧹 تنظيف الصفحات",
    "extract": "🔎 استخراج النص",
    "typer": "🧩 تصدير TypeR (تنظيف + إحداثيات)",
    "chapter": "📦 فصل (صور + chapter.json)",
    "translate": "🌐 ترجمة عربية",
}
STATUS_LABELS = {
    "pending": "⏳ في الانتظار", "running": "⚙️ قيد المعالجة", "done": "✅ اكتملت",
    "failed": "❌ فشلت", "cancelled": "🚫 أُلغيت",
}
COLORS = {
    "pending": 0x95A5A6, "running": 0x3498DB, "done": 0x2ECC71,
    "failed": 0xE74C3C, "cancelled": 0x7F8C8D,
}


def progress_bar(done: int, total: Optional[int], width: int = 12) -> str:
    if not total:
        return "░" * width
    frac = max(0.0, min(1.0, done / total))
    fill = int(round(frac * width))
    return "█" * fill + "░" * (width - fill) + f" {int(frac * 100)}%"


def _title(job: Dict[str, Any]) -> str:
    return f"{KIND_TITLES.get(job['kind'], job['kind'])} — مهمة #{job['id']}"


def queued_embed(job: Dict[str, Any], position: int) -> discord.Embed:
    e = discord.Embed(title=_title(job), color=COLORS["pending"],
                      description=f"📎 `{_safe(job['source_name'])}`")
    e.add_field(name="الحالة", value=STATUS_LABELS["pending"], inline=True)
    e.add_field(name="الترتيب في الطابور", value=str(position or 1), inline=True)
    if job.get("total_pages"):
        e.add_field(name="📄 الصفحات", value=str(job["total_pages"]), inline=True)
    e.set_footer(text="سأمنشنك عند الانتهاء • /status لمتابعة المهمة • /cancel للإلغاء")
    return e


WARN_IDLE_S = 120      # no output for this long  -> "slow step"
ALERT_IDLE_S = 600     # no output for this long  -> "may be stuck"


def health(idle: Optional[float]) -> str:
    """Working / slow / maybe-stuck indicator from seconds since manga.py's last output."""
    if idle is None or idle < WARN_IDLE_S:
        return "🟢 يعمل"
    if idle < ALERT_IDLE_S:
        return "🟡 خطوة طويلة (الترجمة/LaMa على CPU بطيئة — طبيعي)"
    return f"🔴 لا نشاط منذ {st.fmt_duration(idle)} — قد يكون عالقاً (جرّب /cancel وأعد المحاولة)"


def eta(elapsed: Optional[float], done: int, total: Optional[int]) -> Optional[str]:
    if not elapsed or not total or done < 1 or done >= total:
        return None
    return "≈ " + st.fmt_duration(elapsed / done * (total - done))


def running_embed(job: Dict[str, Any], text: str, lp: Optional[st.LogProgress] = None,
                  elapsed: Optional[float] = None, idle: Optional[float] = None) -> discord.Embed:
    total = job.get("total_pages")
    done = lp.pages_done if lp else job.get("pages_done", 0)
    bubbles = lp.bubbles_seen if lp else job.get("bubbles_seen", 0)
    e = discord.Embed(title=_title(job), color=COLORS["running"],
                      description=f"📎 `{_safe(job['source_name'])}`")
    e.add_field(name="الحالة", value=health(idle), inline=False)
    e.add_field(name="التقدم", value=progress_bar(done, total), inline=True)
    e.add_field(name="📄 الصفحات", value=f"{done}" + (f"/{total}" if total else ""), inline=True)
    e.add_field(name="💬 فقاعات مكتشفة", value=str(bubbles), inline=True)
    if elapsed is not None:
        e.add_field(name="⏱️ مضى", value=st.fmt_duration(elapsed), inline=True)
    left = eta(elapsed, done, total)
    if left:
        e.add_field(name="⏳ المتبقي تقريباً", value=left, inline=True)
    dev = st.device_text(lp) if lp else ""
    if dev or (lp and lp.monitor):
        e.add_field(name="🖥️ الجهاز", inline=False,
                    value=_safe((dev or "لم يُعلن المحرك بعد") + (f"\n{lp.monitor}" if lp and lp.monitor else ""), 200))
    if idle is not None:
        e.add_field(name="🕐 آخر نشاط", value=f"<t:{int(time.time() - idle)}:R>", inline=True)
    stage = text if text.startswith("⬆️") else ((lp.last_stage if lp else "") or "")
    if stage:
        e.add_field(name="المرحلة الحالية", value=f"`{_safe(stage, 100)}`", inline=False)
    e.timestamp = discord.utils.utcnow()   # footer shows when the bot last refreshed this message
    return e


def links_text(links: List[Dict[str, Any]]) -> str:
    lines = [f"[{_safe(l['name'], 40)} — {l['size'] / 1024 ** 2:.1f}MB]({l['url']})" for l in links]
    return "\n".join(lines)[:1000]


def done_embed(job: Dict[str, Any], stats: Dict[str, Any], notes: List[str],
               ttl_minutes: int) -> discord.Embed:
    e = discord.Embed(title=_title(job), color=COLORS["done"],
                      description=f"📎 `{_safe(job['source_name'])}`\n{STATUS_LABELS['done']}")
    for name, value, inline in st.stats_fields(job["kind"], stats):
        e.add_field(name=name, value=value[:1000] or "—", inline=inline)
    links = stats.get("external_links") or []
    if links:
        e.add_field(name="🔗 تحميل (الجودة الأصلية)", value=links_text(links), inline=False)
    if notes:
        e.add_field(name="ملاحظات", value="\n".join(notes)[:1000], inline=False)
    e.set_footer(text=(f"الملفات المحلية تُحذف بعد {ttl_minutes} دقيقة — الرابط على gofile "
                       f"(قد تنتهي صلاحيته حسب سياسة الخدمة)") if links
                 else f"الملفات تُحذف من السيرفر بعد {ttl_minutes} دقيقة")
    return e


def failed_embed(job: Dict[str, Any], error: str, tail: List[str]) -> discord.Embed:
    e = discord.Embed(title=_title(job), color=COLORS["failed"],
                      description=f"📎 `{_safe(job['source_name'])}`\n{STATUS_LABELS['failed']}")
    e.add_field(name="السبب", value=error[:900] or "—", inline=False)
    if tail:
        snippet = "\n".join(l[:160] for l in tail[-6:])
        e.add_field(name="آخر سطور السجل", value=f"```\n{snippet[:900]}\n```", inline=False)
    return e


def status_embed(job: Dict[str, Any], position: int = 0) -> discord.Embed:
    status = job["status"]
    e = discord.Embed(title=_title(job), color=COLORS.get(status, 0x95A5A6),
                      description=f"📎 `{_safe(job['source_name'])}`")
    e.add_field(name="الحالة", value=STATUS_LABELS.get(status, status), inline=True)
    if status == "pending":
        e.add_field(name="الترتيب في الطابور", value=str(position), inline=True)
    elif status == "running":
        now = datetime.now(timezone.utc)
        la, sa = job.get("last_activity_at"), job.get("started_at")
        idle = (now - la).total_seconds() if la else None
        e.add_field(name="الحالة", value=health(idle), inline=False)
        e.add_field(name="التقدم", value=progress_bar(
            job.get("pages_done", 0), job.get("total_pages")), inline=True)
        e.add_field(name="📄 الصفحات", value=f"{job.get('pages_done', 0)}"
                    + (f"/{job['total_pages']}" if job.get("total_pages") else ""), inline=True)
        e.add_field(name="💬 فقاعات مكتشفة", value=str(job.get("bubbles_seen", 0)), inline=True)
        if sa:
            e.add_field(name="⏱️ مضى", value=st.fmt_duration((now - sa).total_seconds()), inline=True)
            left = eta((now - sa).total_seconds(), job.get("pages_done", 0), job.get("total_pages"))
            if left:
                e.add_field(name="⏳ المتبقي تقريباً", value=left, inline=True)
        if la:
            e.add_field(name="🕐 آخر نشاط", value=f"<t:{int(la.timestamp())}:R>", inline=True)
    elif status == "done" and job.get("stats"):
        for name, value, inline in st.stats_fields(job["kind"], job["stats"]):
            e.add_field(name=name, value=value[:1000] or "—", inline=inline)
        if job["stats"].get("external_links"):
            e.add_field(name="🔗 تحميل (الجودة الأصلية)",
                        value=links_text(job["stats"]["external_links"]), inline=False)
        if job.get("workdir") is None:
            e.set_footer(text="ملفات هذه المهمة حُذفت من السيرفر")
    elif status == "failed" and job.get("error"):
        e.add_field(name="السبب", value=job["error"][:900], inline=False)
    return e


def history_embed(jobs: List[Dict[str, Any]], totals: Dict[str, Any]) -> discord.Embed:
    e = discord.Embed(title="📜 سجل مهامك", color=0x9B59B6)
    if not jobs:
        e.description = "لا توجد مهام بعد."
        return e
    lines = []
    for j in jobs:
        s = j.get("stats") or {}
        extra = ""
        if j["status"] == "done" and s:
            extra = f" — {s.get('pages', 0)} صفحة / {s.get('bubbles', 0)} فقاعة"
        lines.append(f"`#{j['id']}` {STATUS_LABELS.get(j['status'], j['status'])} "
                     f"{KIND_TITLES.get(j['kind'], j['kind']).split(' ', 1)[0]} "
                     f"`{_safe(j['source_name'], 28)}`{extra}")
    e.description = "\n".join(lines)
    e.add_field(name="✅ مكتملة", value=str(totals.get("jobs_done", 0)), inline=True)
    e.add_field(name="❌ فاشلة", value=str(totals.get("jobs_failed", 0)), inline=True)
    e.add_field(name="📄 إجمالي الصفحات", value=f"{totals.get('pages', 0):,}", inline=True)
    e.add_field(name="💬 إجمالي الفقاعات", value=f"{totals.get('bubbles', 0):,}", inline=True)
    return e


def help_embed(cfg: Any) -> discord.Embed:
    """/help — what each command does and how the newer features work. Reflects this bot's config."""
    e = discord.Embed(title="📖 دليل البوت", color=0x5865F2,
                      description="كل أمر يقبل **ملفاً مرفوعاً** (`file`) **أو رابطاً** (`link`) — واحداً فقط.")
    e.add_field(name="الأوامر", inline=False, value=(
        "🧹 `/clean` — يمسح النص من الفقاعات ويعيد صفحات نظيفة\n"
        "🔎 `/extract` — يستخرج النص الأصلي (txt + json)\n"
        "🧩 `/typer` — تنظيف + إحداثيات الفقاعات لاستيرادها في TypeR Web\n"
        "📦 `/chapter` — zip فيه مجلد `images/` + `chapter.json` (حزمة ستايلاتك `style_pack` (`/styles`)، خط مختلف لكل نوع فقاعة `tone_fonts`، ترجمة اختيارية بـ `translate:True`، المصدر `provider`: Ollama أو API)\n"
        "🌐 `/translate` — ترجمة عربية (Ollama) + كتابة النص على الصفحة\n"
        "📊 `/status` `/queue` `/history` `/cancel` `/ping` — متابعة المهام"))
    if getattr(cfg, "allow_links", True):
        gd = ("ملفات Drive **العامة** تعمل دائماً. " + (
            "المجلدات والملفات الخاصة مفعّلة ✅" if (getattr(cfg, "google_token_file", "")
                                                    or getattr(cfg, "google_api_key", ""))
            else "مجلدات Drive تحتاج ربط حساب Google (Colab) أو `GOOGLE_API_KEY` — غير مفعّل هنا."))
        e.add_field(name="🔗 الروابط بدل الرفع", inline=False, value=(
            f"الصق في `link` رابط **Google Drive** أو **Gofile** (ملف واحد ZIP/PDF/صورة، حتى "
            f"{cfg.max_link_mb}MB).\n{gd}\nمجلد صور في Drive يُضغط تلقائياً ZIP بترتيب الأسماء."))
    if getattr(cfg, "external_host", ""):
        e.add_field(name="⬆️ النتائج الكبيرة", inline=False, value=(
            "لو الناتج أكبر من حد ديسكورد يُرفع **بجودته الأصلية** على Gofile ويصلك الرابط "
            "(أي شخص معه الرابط يقدر يحمّله). لو فشل الرفع يُرسل مضغوطاً/مقسّماً عبر ديسكورد."))
    e.add_field(name="🧱 الصفحات", inline=False, value=(
        "الصفحات تُعالج **كما هي** — لا تُدمج في شرائط طويلة ولا تُلصق ببعضها، والناتج بنفس عدد صفحاتك."))
    e.add_field(name="⚙️ المحرك", inline=False, value=(
        "التنظيف والاستخراج وTypeR على المحرك الجديد؛ الترجمة العربية (Ollama) على المحرك العربي السابق."))
    e.add_field(name="📐 خيارات مفيدة", inline=False, value=(
        "`format`: jpg أخف بكثير من png. `quality`: `lama` أجود وأبطأ.\n"
        f"حدود: {cfg.max_pages} صفحة (ترجمة {cfg.max_pages_translate})، "
        f"{cfg.max_active_per_user} مهام نشطة لكل مستخدم."))
    return e


def _safe(text: str, limit: int = 60) -> str:
    t = (text or "").replace("`", "'").replace("\n", " ")
    return t if len(t) <= limit else t[: limit - 1] + "…"


def tone_label(tone: str) -> str:
    from .stats import TONE_LABELS
    return {**TONE_LABELS, "sfx": "مؤثر صوتي"}.get(tone, tone)
