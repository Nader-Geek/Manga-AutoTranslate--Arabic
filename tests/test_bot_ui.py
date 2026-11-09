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
assert ui.progress_bar(0, 0).count("░") == 12 and "100%" in ui.progress_bar(9, 3) and "0%" in ui.progress_bar(0, 10)
print("test_bot_ui OK")
