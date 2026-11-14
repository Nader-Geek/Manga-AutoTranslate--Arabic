# -*- coding: utf-8 -*-
"""Statistics for finished jobs.

Two sources, both produced by manga.py:
  * typer_job.json (--export-typer): per page, every detected region with its kind,
    tone, OCR source text and translated text.  This is the authoritative source.
  * the log (stdout): cleanup method counters and live per-page progress lines.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

KIND_LABELS = {"dialogue": "حوار", "sfx": "مؤثرات صوتية", "promo": "إعلانات", "junk": "شوائب"}
TONE_LABELS = {
    "normal": "عادي", "shout": "صراخ", "comedy_shout": "صراخ كوميدي", "whisper": "همس",
    "thought": "تفكير", "sun_thought": "تفكير شمسي", "free_text": "نص حر",
    "system": "نظام", "monster": "وحش", "cry": "بكاء", "fear": "خوف",
    "broadcast": "بث", "letter": "رسالة", "narrator": "راوي",
    "square_thought": "فكرة مربعة", "black": "داكن",
}


# --------------------------------------------------------------------- typer job
def stats_from_typer_job(job_path: Path) -> Dict[str, Any]:
    """Summarise typer_job.json. Raises FileNotFoundError / ValueError when unusable."""
    data = json.loads(Path(job_path).read_text(encoding="utf-8"))
    pages = data.get("pages")
    if not isinstance(pages, list):
        raise ValueError("typer_job.json has no 'pages' list")

    by_kind: Dict[str, int] = {}
    by_tone: Dict[str, int] = {}
    bubbles = dialogue = translated = source_chars = 0
    blank_pages = 0
    busiest = (0, 0)  # (bubbles, page number)

    for pg in pages:
        regions = pg.get("regions") or []
        if not regions:
            blank_pages += 1
        n = len(regions)
        if n > busiest[0]:
            busiest = (n, int(pg.get("index", 0)) + 1)
        for r in regions:
            bubbles += 1
            kind = r.get("kind") or "dialogue"
            by_kind[kind] = by_kind.get(kind, 0) + 1
            src = (r.get("source") or "").strip()
            source_chars += len(src)
            if kind == "dialogue":
                dialogue += 1
                tone = r.get("tone") or "normal"
                by_tone[tone] = by_tone.get(tone, 0) + 1
                if (r.get("text") or "").strip():
                    translated += 1

    n_pages = len(pages)
    return {
        "pages": n_pages,
        "blank_pages": blank_pages,
        "pages_with_text": n_pages - blank_pages,
        "bubbles": bubbles,
        "dialogue": dialogue,
        "translated": translated,
        "by_kind": by_kind,
        "by_tone": by_tone,
        "source_chars": source_chars,
        "avg_bubbles_per_page": round(bubbles / n_pages, 1) if n_pages else 0.0,
        "busiest_page": busiest[1] if busiest[0] else None,
        "busiest_page_bubbles": busiest[0],
        "target_lang": data.get("target_lang"),
        "reading_order": data.get("reading_order"),
    }


# --------------------------------------------------------------------------- log
_RE_NEW_PAGE = re.compile(r"-{5,}\s*بدء عملية جديدة")
_RE_PAGE_DONE = re.compile(r"\[المرحلة 1 ✓\].*?—\s*(\d+)\s*فقاعة")
_RE_SKIPPED = re.compile(r"تم التخطي \(صفحة فارغة\)")
_RE_NO_TEXT = re.compile(r"لم يُعثر على أي نص/فقاعة")
_RE_CLEANUP = re.compile(r"Cleanup:\s*(\{.*?\})")
# new engine (manga_sections): per-page progress lines
_RE_X_EXTRACT = re.compile(r"\[\*\] استخراج متن:\s*(\d+)/(\d+)")
_RE_X_CLEAN = re.compile(r"\[\*\] پاکسازی متن:\s*(\d+)/(\d+)")
_RE_X_FIN = re.compile(r"\[TIME\] page#(\d+) clean\+render=")
_RE_EP = re.compile(r"EP=(\w+)")
_RE_DEV = re.compile(r"(LaMa|PaddleOCR|OCR)[^\n]*?device=(\w+)", re.I)
_GPU_EPS = ("CUDA", "Tensorrt", "Dml", "ROCM", "CoreML", "WebGpu", "OpenVINO")


def _dev_label(name: str) -> str:
    return "GPU" if any(g.lower() in name.lower() for g in _GPU_EPS) or name.lower() in ("cuda", "gpu", "mps") else "CPU"


_RE_WALLS = re.compile(r"حماية جدران الفقاعات/الإطارات:\s*(\d+)")


@dataclass
class LogProgress:
    """Incremental parser: feed it lines as they arrive."""
    pages_started: int = 0
    pages_done: int = 0          # extraction finished (or blank page skipped)
    bubbles_seen: int = 0
    blank_skipped: int = 0
    cleanup: Dict[str, int] = field(default_factory=dict)
    walls_protected_px: int = 0
    last_stage: str = ""
    devices: Dict[str, str] = field(default_factory=dict)   # what the engine REPORTED using
    monitor: str = ""        # latest "cpu=.. ram=.. gpu=.." snapshot (set by the worker)
    _extract_n: int = 0
    _clean_n: int = 0
    _fin: set = field(default_factory=set)

    def feed(self, line: str) -> bool:
        """Returns True when the progress numbers changed."""
        changed = False
        if _RE_NEW_PAGE.search(line):
            self.pages_started += 1
            changed = True
        m = _RE_PAGE_DONE.search(line)
        if m:
            self.pages_done += 1
            self.bubbles_seen += int(m.group(1))
            changed = True
        elif _RE_SKIPPED.search(line):
            self.pages_done += 1
            self.blank_skipped += 1
            changed = True
        elif _RE_NO_TEXT.search(line):
            self.pages_done += 1
            changed = True
        if "EP=" in line:
            m = _RE_EP.search(line)
            if m:
                self.devices["OCR" if "OCR" in line or "RapidOCR" in line else "ONNX"] = _dev_label(m.group(1))
                changed = True
        m = _RE_DEV.search(line)
        if m:
            key = "LaMa" if m.group(1).lower() == "lama" else "OCR"
            self.devices[key] = _dev_label(m.group(2))
            changed = True
        m = _RE_X_EXTRACT.search(line)
        if m:
            self._extract_n = max(self._extract_n, int(m.group(1)))
            self.last_stage = f"استخراج النص {m.group(1)}/{m.group(2)}"
            changed = True
        m = _RE_X_CLEAN.search(line)
        if m:
            self._clean_n = max(self._clean_n, int(m.group(1)))
            self.last_stage = f"تنظيف النص {m.group(1)}/{m.group(2)}"
            changed = True
        m = _RE_X_FIN.search(line)
        if m:
            self._fin.add(int(m.group(1)))
            changed = True
        if self._extract_n or self._clean_n or self._fin:
            # new engine: a page counts as done once it is cleaned/finished
            done = max(self._clean_n, len(self._fin), self._extract_n)
            if done > self.pages_done:
                self.pages_done = done
                changed = True
        m = _RE_CLEANUP.search(line)
        if m:
            try:
                d = ast.literal_eval(m.group(1))
                for k, v in d.items():
                    self.cleanup[str(k)] = self.cleanup.get(str(k), 0) + int(v)
            except Exception:
                pass
        m = _RE_WALLS.search(line)
        if m:
            self.walls_protected_px += int(m.group(1))
        if line.startswith("[المرحلة"):
            self.last_stage = line.strip()[:120]
            changed = True
        return changed


def parse_log(lines: Iterable[str]) -> LogProgress:
    lp = LogProgress()
    for ln in lines:
        lp.feed(ln)
    return lp


def device_text(lp: "LogProgress") -> str:
    """'OCR: CPU • LaMa: GPU' from what the engine printed, or '' until it has said anything."""
    return " • ".join(f"{k}: {v}" for k, v in lp.devices.items())


def progress_text(lp: LogProgress, total_pages: Optional[int]) -> str:
    total = f"/{total_pages}" if total_pages else ""
    txt = f"الصفحة {lp.pages_done}{total} — فقاعات مكتشفة: {lp.bubbles_seen}"
    if lp.last_stage:
        txt += f"\n{lp.last_stage}"
    return txt


# ----------------------------------------------------------------- extract files
def build_extract_files(job_path: Path, out_dir: Path, source_name: str = "") -> List[Path]:
    """Create extract.txt (human readable) and extract.json (structured) from typer_job.json."""
    data = json.loads(Path(job_path).read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    rows: List[Dict[str, Any]] = []
    if source_name:
        lines.append(f"# {source_name}")
    for pg in data.get("pages", []):
        num = int(pg.get("index", 0)) + 1
        regions = pg.get("regions") or []
        lines.append("")
        lines.append(f"=== صفحة {num} — {len(regions)} فقاعة ===")
        for r in regions:
            kind = r.get("kind") or "dialogue"
            src = (r.get("source") or "").replace("\n", " ").strip()
            lines.append(f"[{r.get('id')}] ({KIND_LABELS.get(kind, kind)}) {src}")
            rows.append({
                "page": num, "id": r.get("id"), "kind": kind,
                "tone": r.get("tone") or "", "text": src,
                "rect": r.get("rect"),
            })
    txt = out_dir / "extract.txt"
    js = out_dir / "extract.json"
    txt.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    js.write_text(json.dumps(
        {"reading_order": data.get("reading_order"), "items": rows},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return [txt, js]


# ------------------------------------------------------------------- final merge
def combine(job_stats: Dict[str, Any], lp: LogProgress, *, elapsed_s: float,
            output_bytes: int) -> Dict[str, Any]:
    out = dict(job_stats)
    out["elapsed_s"] = round(elapsed_s, 1)
    out["output_bytes"] = int(output_bytes)
    if lp.cleanup:
        out["cleanup"] = dict(lp.cleanup)
    if lp.walls_protected_px:
        out["walls_protected_px"] = lp.walls_protected_px
    return out


def fallback_from_log(lp: LogProgress, *, elapsed_s: float, output_bytes: int) -> Dict[str, Any]:
    """Used when typer_job.json is missing (the run still produced output)."""
    return combine({
        "pages": lp.pages_done, "blank_pages": lp.blank_skipped,
        "pages_with_text": max(0, lp.pages_done - lp.blank_skipped),
        "bubbles": lp.bubbles_seen, "dialogue": 0, "translated": 0,
        "by_kind": {}, "by_tone": {}, "source_chars": 0,
        "avg_bubbles_per_page": round(lp.bubbles_seen / lp.pages_done, 1) if lp.pages_done else 0.0,
        "busiest_page": None, "busiest_page_bubbles": 0,
        "approximate": True,
    }, lp, elapsed_s=elapsed_s, output_bytes=output_bytes)


# ---------------------------------------------------------------------- display
def fmt_duration(seconds: float) -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s} ث"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m} د {s} ث"
    h, m = divmod(m, 60)
    return f"{h} س {m} د"


def fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


def stats_fields(kind: str, st: Dict[str, Any]) -> List[tuple]:
    """(name, value, inline) tuples for a Discord embed, tailored per command."""
    f: List[tuple] = []
    pages = st.get("pages", 0)
    f.append(("📄 الصفحات", f"{pages}" + (f" (منها {st['blank_pages']} فارغة)"
                                          if st.get("blank_pages") else ""), True))
    bubbles = st.get("bubbles", 0)
    if kind in ("clean", "typer", "chapter"):
        f.append(("🧹 فقاعات/نصوص تم مسحها", str(bubbles), True))
    elif kind == "extract":
        f.append(("🔎 نصوص مستخرجة", str(bubbles), True))
    else:
        f.append(("💬 فقاعات", str(bubbles), True))
    if kind == "translate":
        f.append(("🌐 حوارات مترجمة", f"{st.get('translated', 0)}/{st.get('dialogue', 0)}", True))
    if pages and bubbles:
        f.append(("📊 متوسط الفقاعات/صفحة", str(st.get("avg_bubbles_per_page", 0)), True))
    if st.get("busiest_page"):
        f.append(("🔝 أكثر صفحة نصاً",
                  f"صفحة {st['busiest_page']} ({st['busiest_page_bubbles']} فقاعة)", True))
    if kind == "extract" and st.get("source_chars"):
        f.append(("🔤 عدد الحروف", f"{st['source_chars']:,}", True))
    bk = st.get("by_kind") or {}
    if bk:
        f.append(("🏷️ حسب النوع", " • ".join(
            f"{KIND_LABELS.get(k, k)}: {v}" for k, v in sorted(bk.items(), key=lambda x: -x[1])),
            False))
    bt = st.get("by_tone") or {}
    if bt and kind in ("translate", "extract", "typer", "chapter"):
        top = sorted(bt.items(), key=lambda x: -x[1])[:5]
        f.append(("🎭 النبرات", " • ".join(f"{TONE_LABELS.get(k, k)}: {v}" for k, v in top), False))
    cl = st.get("cleanup") or {}
    if cl and kind in ("clean", "typer", "translate", "chapter"):
        names = {"flat": "تعبئة لونية", "color": "لون", "LaMa": "LaMa", "OpenCV": "OpenCV"}
        f.append(("🖌️ طريقة المسح (مجموعات)", " • ".join(
            f"{names.get(k, k)}: {v}" for k, v in cl.items() if v), False))
    if st.get("elapsed_s") is not None:
        f.append(("⏱️ المدة", fmt_duration(st["elapsed_s"]), True))
    if st.get("output_bytes"):
        f.append(("📦 حجم الناتج", fmt_size(st["output_bytes"]), True))
    if st.get("approximate"):
        f.append(("⚠️ ملاحظة", "الأرقام تقريبية (من السجل) لأن ملف typer_job.json غير متاح", False))
    return f
