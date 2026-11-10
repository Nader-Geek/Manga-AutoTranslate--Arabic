"""Command building, upload validation and zip splitting. Run: python3 tests/test_bot_runner.py"""
import io, os, sys, tempfile, zipfile
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.config import Config
from bot.runner import UploadError, build_plan, inspect_upload, split_zip

cfg = Config(work_dir=Path("/tmp/w"), allowed_models=("qwen2.5:7b-instruct",))
os.environ["DISCORD_TOKEN"] = "secret"; os.environ["DATABASE_URL"] = "postgresql://x"

def job(kind, **opts):
    return {"kind": kind, "workdir": "/tmp/w/abc", "input_path": "/tmp/w/abc/input.zip", "options": opts}

def flag(argv, name, n=1):
    i = argv.index(name); return argv[i + 1:i + 1 + n]

# --- clean
p = build_plan(job("clean", lama=True, img_format="png", ocr="ja"), cfg)
assert "--clean-only" in p.argv and "--lama" in p.argv and "--cpu" in p.argv
assert flag(p.argv, "--ocr-lang", 2) == ["ja", "en"] and flag(p.argv, "--img-format") == ["png"]
assert flag(p.argv, "--export-typer") == ["/tmp/w/abc/typer"] and p.deliver == [Path("/tmp/w/abc/result.zip")]
assert "DISCORD_TOKEN" not in p.env and "DATABASE_URL" not in p.env, "secrets leaked into subprocess env"
assert p.env["MANGA_TARGET_LANG"] == "ar"
# --- typer delivers the export zip
p = build_plan(job("typer"), cfg); assert p.deliver == [Path("/tmp/w/abc/typer.zip")] and "--clean-only" in p.argv
# --- extract builds its own files later
p = build_plan(job("extract"), cfg); assert p.deliver == [] and "--clean-only" in p.argv
# --- translate
p = build_plan(job("translate", dialect="egyptian", format="pdf", model="qwen2.5:7b-instruct"), cfg)
assert "--clean-only" not in p.argv and p.out_path.suffix == ".pdf"
assert flag(p.argv, "--ar-dialect") == ["egyptian"] and flag(p.argv, "--provider") == ["ollama"]
assert flag(p.argv, "--bubbles-per-request") == ["4"] and p.env["MANGA_AR_DIALECT"] == "egyptian"
assert p.env["OLLAMA_BASE_URL"] == "http://localhost:11434/v1"
assert build_plan(job("translate"), replace(cfg, ollama_url="http://gpu-box:11434/")).env["OLLAMA_BASE_URL"] == "http://gpu-box:11434/v1"
# --- hostile options fall back to safe values / are rejected, never reach argv raw
p = build_plan(job("clean", img_format="; rm -rf /", ocr="$(x)", reading_order="up"), cfg)
assert flag(p.argv, "--img-format") == ["jpg"] and flag(p.argv, "--ocr-lang") == ["en"] and flag(p.argv, "--reading-order") == ["rtl"]
try:
    build_plan(job("translate", model="evil:latest"), cfg); raise SystemExit("model allow-list not enforced")
except ValueError: pass
try:
    build_plan(job("rm"), cfg); raise SystemExit("unknown kind accepted")
except ValueError: pass
# --- gpu flag
assert "--gpu" in build_plan(job("clean"), replace(cfg, use_gpu=True)).argv

# --- upload inspection
def mkzip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in entries: z.writestr(n, data)
def expect_err(path, c=cfg, pages=10, text=""):
    try:
        inspect_upload(path, c, pages); raise SystemExit(f"expected UploadError: {text}")
    except UploadError as e:
        assert text in str(e), (text, str(e))

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    mkzip(td / "ok.zip", [("1.jpg", b"x"), ("2.png", b"x"), ("notes.txt", b"x")])
    assert inspect_upload(td / "ok.zip", cfg, 10) == 2
    mkzip(td / "slip.zip", [("../evil.jpg", b"x")]); expect_err(td / "slip.zip", text="غير آمنة")
    mkzip(td / "abs.zip", [("/etc/x.jpg", b"x")]); expect_err(td / "abs.zip", text="غير آمنة")
    mkzip(td / "none.zip", [("a.txt", b"x")]); expect_err(td / "none.zip", text="لم أجد")
    mkzip(td / "many.zip", [(f"{i}.jpg", b"x") for i in range(11)]); expect_err(td / "many.zip", text="يتجاوز الحد")
    mkzip(td / "bomb.zip", [("a.jpg", b"\0" * (3 * 1024 * 1024))])
    expect_err(td / "bomb.zip", replace(cfg, max_unzipped_mb=1), text="بعد الفك")
    (td / "bad.zip").write_bytes(b"not a zip"); expect_err(td / "bad.zip", text="تالف")
    (td / "x.exe").write_bytes(b"MZ"); expect_err(td / "x.exe", text="غير مدعومة")
    (td / "a.jpg").write_bytes(b"x"); assert inspect_upload(td / "a.jpg", cfg, 10) == 1
    (td / "bad.pdf").write_bytes(b"nope"); expect_err(td / "bad.pdf", text="PDF")
    import fitz
    d = fitz.open(); [d.new_page() for _ in range(3)]; d.save(td / "ok.pdf")
    assert inspect_upload(td / "ok.pdf", cfg, 10) == 3

    # --- split_zip
    big = td / "big.zip"
    with zipfile.ZipFile(big, "w", zipfile.ZIP_STORED) as z:
        for i in range(10): z.writestr(f"p{i}.png", os.urandom(100_000))
    assert split_zip(big, 5_000_000) == [big]
    parts = split_zip(big, 350_000)
    assert len(parts) >= 3 and all(x.stat().st_size <= 350_000 for x in parts), [x.stat().st_size for x in parts]
    names = sorted(n for x in parts for n in zipfile.ZipFile(x).namelist())
    assert names == sorted(f"p{i}.png" for i in range(10)), names
    try:
        split_zip(big, 50_000); raise SystemExit("expected ValueError for oversize entry")
    except ValueError: pass

# --- layout option
assert "--stitch-max-height" not in build_plan(job("clean"), cfg).argv
assert flag(build_plan(job("clean", layout="original"), cfg).argv, "--stitch-max-height") == ["0"]
assert "--stitch-max-height" not in build_plan(job("clean", layout="; rm"), cfg).argv

# --- single oversized images (tall PNG strips)
import io, numpy as np
from PIL import Image
from bot.runner import batch_by_size, shrink_image, shrink_oversized_images

def png(arr):
    b = io.BytesIO(); Image.fromarray(arr).save(b, "PNG"); return b.getvalue()
def jpg_size(arr, q):
    b = io.BytesIO(); Image.fromarray(arr).save(b, "JPEG", quality=q, optimize=True); return len(b.getvalue())

# 1) smooth artwork: a JPEG at some quality fits -> one piece, same dimensions, .jpg name
yy, xx = np.mgrid[0:3000, 0:600]
smooth = np.stack([(xx * 255 // 600), (yy * 255 // 3000), ((xx + yy) % 256)], -1).astype(np.uint8)
data = png(smooth); budget = (len(data) + jpg_size(smooth, 95)) // 2
pieces, note = shrink_image(data, "strip_001.png", budget)
assert len(pieces) == 1 and pieces[0][0] == "strip_001.jpg" and len(pieces[0][1]) <= budget, (len(pieces), note)
assert Image.open(io.BytesIO(pieces[0][1])).size == (600, 3000) and "JPEG" in note

# 2) incompressible page: must be sliced, and the cut snaps to the blank band between "panels"
rng = np.random.RandomState(1)
noisy = rng.randint(0, 256, (3000, 600, 3), dtype=np.uint8)
noisy[1480:1520] = 255                                   # blank gutter around the middle
budget = int(jpg_size(noisy, 80) * 0.7)
pieces, note = shrink_image(png(noisy), "dir/strip_002.png", budget)
assert len(pieces) == 2 and [p[0] for p in pieces] == ["dir/strip_002_p1.jpg", "dir/strip_002_p2.jpg"], [p[0] for p in pieces]
assert all(len(p[1]) <= budget for p in pieces)
ims = [Image.open(io.BytesIO(p[1])) for p in pieces]
assert all(i.width == 600 for i in ims) and sum(i.height for i in ims) == 3000, [i.size for i in ims]
assert 1480 <= ims[0].height <= 1520, f"cut at {ims[0].height}, not in the blank gutter"
try:
    shrink_image(png(noisy), "x.png", budget, allow_slice=False); raise SystemExit("expected ValueError")
except ValueError: pass

# 3) inside a zip: only the oversized image is touched; untouched zips are returned as-is
with tempfile.TemporaryDirectory() as td:
    td = Path(td); small = png(rng.randint(0, 256, (20, 20, 3), dtype=np.uint8))
    z = td / "result.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("a_small.png", small); zf.writestr("notes.txt", "hello"); zf.writestr("strip_001.png", png(noisy))
    same, notes = shrink_oversized_images(z, 10_000_000); assert same == z and notes == []
    limit = int(jpg_size(noisy, 80) * 0.7 / 0.9)
    out, notes = shrink_oversized_images(z, limit)
    assert out != z and out.is_file() and len(notes) == 1 and "strip_001.png" in notes[0]
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert zf.read("a_small.png") == small and zf.read("notes.txt") == b"hello", "untouched files must be byte-identical"
        assert "strip_001.png" not in names and any(n.startswith("strip_001_p") for n in names), names
    parts = split_zip(out, limit)
    assert all(p.stat().st_size <= limit for p in parts), [p.stat().st_size for p in parts]
    # 4) message batching by combined size and count
    fs = []
    for i, n in enumerate([400, 400, 400, 100, 900, 50, 50]):
        p = td / f"f{i}.bin"; p.write_bytes(b"x" * n); fs.append(p)
    b = batch_by_size(fs, 1000, max_count=10)
    assert [[x.name for x in g] for g in b] == [["f0.bin", "f1.bin"], ["f2.bin", "f3.bin"], ["f4.bin", "f5.bin", "f6.bin"]], b
    assert all(sum(x.stat().st_size for x in g) <= 1000 for g in b) and sum(len(g) for g in b) == 7, b
    assert max(len(g) for g in batch_by_size(fs, 10 ** 9, max_count=3)) == 3
print("test_bot_runner OK")
