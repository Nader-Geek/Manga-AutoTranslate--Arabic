"""Stats parsing for the Discord bot. Run: python3 tests/test_bot_stats.py"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import stats as st

SAMPLE_JOB = {
    "format": "manga-autotranslate/typer-job", "version": 1, "reading_order": "rtl",
    "target_lang": "ar", "translated": True,
    "pages": [
        {"index": 0, "file": "page_001.png", "regions": [
            {"id": 1, "kind": "dialogue", "tone": "normal", "source": "HELLO", "text": "مرحبا", "rect": [1, 2, 3, 4]},
            {"id": 2, "kind": "dialogue", "tone": "shout", "source": "STOP!!", "text": "قف!!", "rect": [1, 2, 3, 4]},
            {"id": 3, "kind": "sfx", "tone": "", "source": "DON", "text": "", "rect": [1, 2, 3, 4]},
        ]},
        {"index": 1, "file": "page_002.png", "regions": []},
        {"index": 2, "file": "page_003.png", "regions": [
            {"id": 1, "kind": "dialogue", "tone": "whisper", "source": "hm", "text": "", "rect": [0, 0, 1, 1]},
            {"id": 2, "kind": "promo", "tone": "", "source": "read at site", "text": "", "rect": [0, 0, 1, 1]},
        ]},
    ],
}
LOG = """\
-------------------- بدء عملية جديدة --------------------
[المرحلة 1 - اكتشاف الفقاعات + OCR] 'a.jpg'...
[المرحلة 1 ✓] اكتمل الاستخراج — 3 فقاعة (الحوار=2) → يمكن بدء الصفحة التالية
  - Cleanup: {'flat': 1, 'LaMa': 2, 'OpenCV': 0}
-------------------- بدء عملية جديدة --------------------
- تم التخطي (صفحة فارغة): 'b.jpg'
-------------------- بدء عملية جديدة --------------------
[المرحلة 1 ✓] اكتمل الاستخراج — 2 فقاعة (الحوار=1) → يمكن بدء الصفحة التالية
  - Cleanup: {'flat': 0, 'LaMa': 1, 'OpenCV': 1}
  [*] حماية جدران الفقاعات/الإطارات: 120 بكسل
"""

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    (td / "typer_job.json").write_text(json.dumps(SAMPLE_JOB, ensure_ascii=False), encoding="utf-8")
    s = st.stats_from_typer_job(td / "typer_job.json")
    assert s["pages"] == 3 and s["blank_pages"] == 1 and s["pages_with_text"] == 2, s
    assert s["bubbles"] == 5 and s["dialogue"] == 3 and s["translated"] == 2, s
    assert s["by_kind"] == {"dialogue": 3, "sfx": 1, "promo": 1}, s
    assert s["by_tone"] == {"normal": 1, "shout": 1, "whisper": 1}, s
    assert s["busiest_page"] == 1 and s["busiest_page_bubbles"] == 3, s
    assert s["avg_bubbles_per_page"] == 1.7, s
    assert s["source_chars"] == len("HELLO") + len("STOP!!") + len("DON") + len("hm") + len("read at site")

    files = st.build_extract_files(td / "typer_job.json", td / "x", "ch1.zip")
    txt = files[0].read_text(encoding="utf-8")
    assert "=== صفحة 1 — 3 فقاعة ===" in txt and "(حوار) HELLO" in txt and "(مؤثرات صوتية) DON" in txt
    ex = json.loads(files[1].read_text(encoding="utf-8"))
    assert len(ex["items"]) == 5 and ex["items"][0]["page"] == 1 and ex["items"][4]["page"] == 3

    # bad inputs
    try:
        st.stats_from_typer_job(td / "nope.json"); raise SystemExit("expected FileNotFoundError")
    except FileNotFoundError:
        pass
    (td / "bad.json").write_text('{"pages": 5}'); 
    try:
        st.stats_from_typer_job(td / "bad.json"); raise SystemExit("expected ValueError")
    except ValueError:
        pass

lp = st.parse_log(LOG.splitlines())
assert (lp.pages_started, lp.pages_done, lp.bubbles_seen, lp.blank_skipped) == (3, 3, 5, 1), lp
assert lp.cleanup == {"flat": 1, "LaMa": 3, "OpenCV": 1} and lp.walls_protected_px == 120, lp
assert "الصفحة 3/10" in st.progress_text(lp, 10)

full = st.combine(s, lp, elapsed_s=125.4, output_bytes=3_500_000)
fields = dict((n, v) for n, v, _ in st.stats_fields("clean", full))
assert fields["📄 الصفحات"].startswith("3") and "1 فارغة" in fields["📄 الصفحات"]
assert fields["🧹 فقاعات/نصوص تم مسحها"] == "5" and fields["⏱️ المدة"] == "2 د 5 ث"
tr = dict((n, v) for n, v, _ in st.stats_fields("translate", full))
assert tr["🌐 حوارات مترجمة"] == "2/3"
fb = st.fallback_from_log(lp, elapsed_s=3, output_bytes=10)
assert fb["bubbles"] == 5 and fb["approximate"]
print("test_bot_stats OK")
