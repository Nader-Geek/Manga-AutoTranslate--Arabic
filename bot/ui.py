# -*- coding: utf-8 -*-
"""Discord embeds. Pure functions, so they can be tested without a connection."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import discord

from . import stats as st

KIND_TITLES = {
    "clean": "🧹 تنظيف الصفحات",
    "extract": "🔎 استخراج النص",
    "typer": "🧩 تصدير TypeR (تنظيف + إحداثيات)",
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


def running_embed(job: Dict[str, Any], text: str, lp: Optional[st.LogProgress] = None) -> discord.Embed:
    total = job.get("total_pages")
    done = lp.pages_done if lp else job.get("pages_done", 0)
    bubbles = lp.bubbles_seen if lp else job.get("bubbles_seen", 0)
    e = discord.Embed(title=_title(job), color=COLORS["running"],
                      description=f"📎 `{_safe(job['source_name'])}`")
    e.add_field(name="الحالة", value=STATUS_LABELS["running"], inline=True)
    e.add_field(name="التقدم", value=progress_bar(done, total), inline=True)
    e.add_field(name="📄 الصفحات", value=f"{done}" + (f"/{total}" if total else ""), inline=True)
    e.add_field(name="💬 فقاعات مكتشفة", value=str(bubbles), inline=True)
    return e


def done_embed(job: Dict[str, Any], stats: Dict[str, Any], notes: List[str],
               ttl_minutes: int) -> discord.Embed:
    e = discord.Embed(title=_title(job), color=COLORS["done"],
                      description=f"📎 `{_safe(job['source_name'])}`\n{STATUS_LABELS['done']}")
    for name, value, inline in st.stats_fields(job["kind"], stats):
        e.add_field(name=name, value=value[:1000] or "—", inline=inline)
    if notes:
        e.add_field(name="ملاحظات", value="\n".join(notes)[:1000], inline=False)
    e.set_footer(text=f"الملفات تُحذف من السيرفر بعد {ttl_minutes} دقيقة")
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
        e.add_field(name="التقدم", value=progress_bar(
            job.get("pages_done", 0), job.get("total_pages")), inline=True)
        e.add_field(name="💬 فقاعات مكتشفة", value=str(job.get("bubbles_seen", 0)), inline=True)
    elif status == "done" and job.get("stats"):
        for name, value, inline in st.stats_fields(job["kind"], job["stats"]):
            e.add_field(name=name, value=value[:1000] or "—", inline=inline)
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


def _safe(text: str, limit: int = 60) -> str:
    t = (text or "").replace("`", "'").replace("\n", " ")
    return t if len(t) <= limit else t[: limit - 1] + "…"
