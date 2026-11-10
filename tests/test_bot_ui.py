"""Discord embed limits. Run: python3 tests/test_bot_ui.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import ui

def check(e):
    d = e.to_dict()
    total = len(d.get("title", "")) + len(d.get("description", "")) + len(d.get("footer", {}).get("text", ""))
    assert len(d.get("title", "")) <= 256 and len(d.get("description", "")) <= 4096
    fields = d.get("fields", [])
    assert len(fields) <= 25, len(fields)
    for f in fields:
        assert 0 < len(f["name"]) <= 256 and 0 < len(f["value"]) <= 1024, f
        total += len(f["name"]) + len(f["value"])
    assert total <= 6000, total

big = {"pages": 60, "blank_pages": 3, "bubbles": 900, "dialogue": 700, "translated": 650,
       "by_kind": {"dialogue": 700, "sfx": 150, "promo": 30, "junk": 20},
       "by_tone": {t: 10 for t in ["normal", "shout", "whisper", "thought", "system", "monster", "cry"]},
       "cleanup": {"flat": 100, "color": 5, "LaMa": 700, "OpenCV": 50}, "elapsed_s": 5400.5,
       "output_bytes": 80_000_000, "avg_bubbles_per_page": 15.0, "busiest_page": 12, "busiest_page_bubbles": 40,
       "source_chars": 12345, "approximate": True}
nasty = "`" * 30 + "x" * 200 + "\n" + "ملف" * 40 + ".zip"
for kind in ("clean", "extract", "typer", "translate"):
    job = {"id": 123456, "kind": kind, "source_name": nasty, "status": "done", "total_pages": 60,
           "pages_done": 7, "bubbles_seen": 99, "stats": big, "workdir": None, "error": "e" * 5000}
    check(ui.queued_embed(job, 3)); check(ui.running_embed(job, "x"))
    check(ui.done_embed(job, big, ["n" * 400] * 5, 20))
    check(ui.failed_embed(job, "e" * 5000, ["l" * 500] * 10))
    for st in ("pending", "running", "done", "failed", "cancelled"):
        check(ui.status_embed({**job, "status": st}, 4))
check(ui.history_embed([{"id": i, "kind": "clean", "status": "done", "source_name": nasty, "stats": big}
                        for i in range(10)], {"jobs_done": 9, "jobs_failed": 1, "pages": 123456, "bubbles": 999999}))
check(ui.history_embed([], {}))

# --- live progress / health indicator
from datetime import datetime, timedelta, timezone
from bot import stats as st
lp = st.LogProgress(pages_done=7, bubbles_seen=42, last_stage="[المرحلة 1 - اكتشاف الفقاعات + OCR] 'x.jpg'...")
job = {"id": 5, "kind": "translate", "source_name": "ch.zip", "total_pages": 30}
assert "🟢" in ui.health(5) and "🟢" in ui.health(None) and "🟡" in ui.health(300) and "🔴" in ui.health(1200)
assert "عالق" in ui.health(1200) and "/cancel" in ui.health(1200)
assert ui.eta(70, 7, 30).startswith("≈") and ui.eta(70, 0, 30) is None and ui.eta(70, 30, 30) is None and ui.eta(None, 3, 30) is None
for idle in (3, 300, 5000):
    e = ui.running_embed(job, "x", lp, elapsed=700, idle=idle); check(e)
    d = {f["name"]: f["value"] for f in e.to_dict()["fields"]}
    assert d["📄 الصفحات"] == "7/30" and "<t:" in d["🕐 آخر نشاط"] and d["⏱️ مضى"] == "11 د 40 ث"
    assert "⏳ المتبقي تقريباً" in d and "المرحلة الحالية" in d and e.timestamp is not None
check(ui.running_embed(job, "x"))                      # old call style still works
now = datetime.now(timezone.utc)
for la in (now - timedelta(seconds=20), now - timedelta(minutes=30), None):
    e = ui.status_embed({**job, "status": "running", "pages_done": 7, "bubbles_seen": 42,
                         "started_at": now - timedelta(minutes=5), "last_activity_at": la}, 0); check(e)
    d = {f["name"]: f["value"] for f in e.to_dict()["fields"]}
    assert ("🔴" in d["الحالة"]) == (la is not None and (now - la).total_seconds() > 600), d["الحالة"]
assert ui.progress_bar(0, 0).count("░") == 12 and "100%" in ui.progress_bar(9, 3) and "0%" in ui.progress_bar(0, 10)
print("test_bot_ui OK")
