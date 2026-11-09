"""bot.local_run end-to-end with the fake manga.py. Run: python3 tests/test_bot_localrun.py"""
import os, sys, tempfile, zipfile
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DISCORD_TOKEN"] = "must-not-leak"
from bot.config import Config
from bot.local_run import PipelineError, first_pages, run_job, side_by_side, result_pages
from bot.runner import UploadError

td = Path(tempfile.mkdtemp(prefix="lr_"))
cfg = Config(work_dir=td / "w", repo_root=ROOT, manga_script=ROOT / "tests" / "fake_manga.py",
             python=sys.executable, allowed_models=("qwen2.5:7b-instruct",), ollama_url="http://gpu:11434")
inp = td / "ch.zip"
import io
from PIL import Image
_b = io.BytesIO(); Image.new("RGB", (60, 90), (255, 255, 255)).save(_b, "JPEG")
with zipfile.ZipFile(inp, "w") as z:
    for i in range(3): z.writestr(f"{i}.jpg", _b.getvalue())

os.environ["FAKE_MODE"] = "ok"
seen = []
r = run_job("clean", inp, {"lama": True}, cfg=cfg, on_progress=lambda lp: seen.append(lp.pages_done))
assert (r.stats["pages"], r.stats["bubbles"], r.stats["blank_pages"]) == (3, 4, 1), r.stats
assert r.files[0].name == "result.zip" and seen and seen[-1] == 3 and "الصفحات" in r.summary()
assert len(first_pages(r, 2)) == 2
im = side_by_side(r, 2, 300); assert im.height == 300 and im.width > 100 and len(result_pages(r, 2)) == 2
r = run_job("extract", inp, cfg=cfg); assert sorted(f.name for f in r.files) == ["extract.json", "extract.txt"]
r = run_job("typer", inp, cfg=cfg); assert r.files[0].name == "typer.zip"
r = run_job("translate", inp, {"dialect": "egyptian"}, cfg=cfg)
assert r.stats["translated"] == 2 and r.stats["dialogue"] == 2
import json; called = json.loads((r.workdir / "argv.json").read_text())
assert called["leaked"] == [] and called["dialect"] == "egyptian"

os.environ["FAKE_MODE"] = "fail"
try: run_job("clean", inp, cfg=cfg); raise SystemExit("expected PipelineError")
except PipelineError as e: assert "code 3" in str(e) and any("boom" in l for l in e.tail)
os.environ["FAKE_MODE"] = "hang"
try: run_job("clean", inp, cfg=replace(cfg, job_timeout_minutes=0.03)); raise SystemExit("expected timeout")
except PipelineError as e: assert "timeout" in str(e)
os.environ["FAKE_MODE"] = "ok"
(td / "x.exe").write_bytes(b"MZ")
try: run_job("clean", td / "x.exe", cfg=cfg); raise SystemExit("expected UploadError")
except UploadError: pass
print("test_bot_localrun OK")
