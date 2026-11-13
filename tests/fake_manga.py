"""Stand-in for manga.py used by the bot tests. Mimics its CLI, log lines and output files.
FAKE_MODE: ok | fail | hang | noexport | huge"""
import argparse, json, os, sys, time, zipfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("-i"); p.add_argument("-o"); p.add_argument("--font")
p.add_argument("--clean-only", action="store_true"); p.add_argument("--export-typer")
p.add_argument("--cpu", action="store_true"); p.add_argument("--gpu", action="store_true")
p.add_argument("--lama", action="store_true"); p.add_argument("--provider")
p.add_argument("--reading-order"); p.add_argument("--ocr-lang", nargs="+")
p.add_argument("--img-format"); p.add_argument("--workers"); p.add_argument("--model")
p.add_argument("--target-lang"); p.add_argument("--ar-dialect")
p.add_argument("--stitch-max-height"); p.add_argument("--no-seam-repair", action="store_true"); p.add_argument("--no-resume", action="store_true"); p.add_argument("--bubbles-per-request"); p.add_argument("--batch-workers")
a = p.parse_args()

mode = os.environ.get("FAKE_MODE", "ok")
# record what we were called with and whether secrets leaked into our environment
Path(a.o).parent.joinpath("argv.json").write_text(json.dumps({
    "argv": sys.argv[1:], "leaked": [k for k in ("DISCORD_TOKEN", "DATABASE_URL") if k in os.environ],
    "target_lang": os.environ.get("MANGA_TARGET_LANG"), "dialect": os.environ.get("MANGA_AR_DIALECT"),
}))
if a.i.lower().endswith(".zip"):
    with zipfile.ZipFile(a.i) as z:
        n = sum(1 for x in z.namelist() if x.lower().endswith((".jpg", ".png", ".webp")))
else:
    n = 1
if mode == "hang":
    print("starting", flush=True); time.sleep(600)
if mode == "fail":
    print("[المرحلة 1 - اكتشاف الفقاعات + OCR] ...", flush=True)
    print("Traceback: boom", file=sys.stderr, flush=True); sys.exit(3)

translate = not a.clean_only
pages = []
d = Path(a.export_typer)
d.mkdir(parents=True, exist_ok=True)
for i in range(n):
    print("-------------------- بدء عملية جديدة --------------------", flush=True)
    time.sleep(0.15)
    blank = (i == 1)
    regions = [] if blank else [
        {"id": 1, "kind": "dialogue", "tone": "normal", "source": f"TEXT {i}", "text": "نص" if translate else "", "rect": [1, 2, 3, 4], "polys": []},
        {"id": 2, "kind": "sfx", "tone": "", "source": "DON", "text": "", "rect": [1, 2, 3, 4], "polys": []},
    ]
    if blank:
        print("- تم التخطي (صفحة فارغة): 'p.jpg'", flush=True)
    else:
        print(f"[المرحلة 1 ✓] اكتمل الاستخراج — {len(regions)} فقاعة (الحوار=1) → يمكن بدء الصفحة التالية", flush=True)
        print("  - Cleanup: {'flat': 1, 'LaMa': 1, 'OpenCV': 0}", flush=True)
    if mode == "slow" and i == 0:
        time.sleep(3)   # a long silent step (e.g. CPU translation)
    name = f"page_{i+1:03d}.png"
    _png = __import__("io").BytesIO(); __import__("PIL.Image", fromlist=["Image"]).new("RGB", (80, 120), (200, 220, 255)).save(_png, "PNG")
    if mode == "hugeimg":   # a genuinely big, incompressible page (like a tall PNG strip)
        import numpy as _np
        _png = __import__("io").BytesIO()
        __import__("PIL.Image", fromlist=["Image"]).fromarray(
            _np.random.RandomState(i).randint(0, 256, (1500, 600, 3), dtype=_np.uint8)).save(_png, "PNG")
    (d / name).write_bytes(_png.getvalue() + (os.urandom(400_000) if mode == "huge" else b""))
    pages.append({"index": i, "file": name, "width": 10, "height": 10, "origin": "x", "regions": regions})
if mode != "noexport":
    (d / "typer_job.json").write_text(json.dumps({"format": "manga-autotranslate/typer-job", "version": 1,
        "reading_order": a.reading_order, "target_lang": "ar", "translated": translate, "pages": pages}, ensure_ascii=False))
    with zipfile.ZipFile(str(d).rstrip("/") + ".zip", "w") as z:
        z.write(d / "typer_job.json", "typer_job.json")
        for pg in pages: z.write(d / pg["file"], pg["file"])
out = Path(a.o)
if out.suffix == ".pdf":
    out.write_bytes(b"%PDF-1.4 fake")
else:
    with zipfile.ZipFile(out, "w") as z:
        for pg in pages: z.write(d / pg["file"], pg["file"])
print(f"[✓] تم حفظ ملف zip النهائي في: {out}", flush=True)
