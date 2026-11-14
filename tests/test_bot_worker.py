"""PostgreSQL queue + worker end-to-end (fake manga.py, fake notifier).
Run: TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/mangabot_test python3 tests/test_bot_worker.py"""
import asyncio, json, os, shutil, sys, tempfile, time, zipfile
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot.config import Config
from bot.db import Database
from bot.worker import Worker

DSN = os.environ.get("TEST_DATABASE_URL")
if not DSN:
    print("SKIP: set TEST_DATABASE_URL to run the PostgreSQL tests"); sys.exit(0)
os.environ["DISCORD_TOKEN"] = "must-not-leak"; os.environ["DATABASE_URL"] = "postgresql://must-not-leak"


class FakeNotifier:
    def __init__(self, limit=10 * 1024 * 1024):
        self.limit = limit; self.events = []
    def upload_limit(self, job): return self.limit
    async def progress(self, job, text, lp, elapsed, idle): self.events.append(("progress", job["id"], lp.pages_done, idle, elapsed))
    async def done(self, job, stats, files, notes): self.events.append(("done", job["id"], stats, files, notes))
    async def failed(self, job, error, tail): self.events.append(("failed", job["id"], error, tail))
    def last(self, kind): return [e for e in self.events if e[0] == kind][-1]


async def main():
    work = Path(tempfile.mkdtemp(prefix="botwork_"))
    cfg = Config(work_dir=work, repo_root=ROOT, manga_script=ROOT / "tests" / "fake_manga.py", legacy_script=ROOT / "tests" / "fake_manga.py",
                 python=sys.executable, progress_interval=0.1, poll_seconds=0.2, file_ttl_minutes=20,
                 allowed_models=("qwen2.5:7b-instruct",))
    db = await Database.connect(DSN)
    await db.apply_schema()  # idempotent: second apply must not fail
    await db.pool.execute("TRUNCATE jobs RESTART IDENTITY")

    async def mkjob(kind, user=1, pages=3, ext=".zip", **opts):
        import uuid
        wd = work / uuid.uuid4().hex; wd.mkdir()
        inp = wd / f"input{ext}"
        if ext == ".zip":
            with zipfile.ZipFile(inp, "w") as z:
                for i in range(pages): z.writestr(f"{i}.jpg", b"x")
        else:
            inp.write_bytes(b"x")
        return await db.create_job(user_id=user, guild_id=None, channel_id=5, kind=kind, source_name="ch1.zip",
                                   workdir=str(wd), input_path=str(inp), total_pages=pages, options=opts)

    # ------------------------------------------------------------- queue / DB
    jobs = [await mkjob("clean", user=1 + i % 2) for i in range(6)]
    assert await db.queue_position(jobs[0]["id"]) == 1 and await db.queue_position(jobs[3]["id"]) == 4
    assert await db.count_active(1) == 3 and await db.count_active(99) == 0
    assert (await db.queue_summary()) == {"pending": 6, "running": 0}
    got = await asyncio.gather(*[db.claim_job() for _ in range(10)])
    ids = [g["id"] for g in got if g]
    assert sorted(ids) == sorted(j["id"] for j in jobs) and len(set(ids)) == 6, ids   # no double-claims
    assert sum(1 for g in got if g is None) == 4
    assert (await db.queue_summary()) == {"pending": 0, "running": 6}
    assert (await db.get_job(ids[0]))["attempts"] == 1

    # crash recovery: attempts<2 -> requeued; attempts>=2 -> failed
    await db.pool.execute("UPDATE jobs SET attempts=2 WHERE id=$1", jobs[0]["id"])
    n = await db.requeue_stale(max_attempts=2)
    assert n == 5 and (await db.get_job(jobs[0]["id"]))["status"] == "failed"
    assert (await db.queue_summary()) == {"pending": 5, "running": 0}

    # cancel permissions
    pend = await db.claim_job()
    assert await db.cancel_job(pend["id"], user_id=777, ttl_minutes=20) is None          # not the owner
    assert await db.cancel_job(pend["id"], user_id=777, ttl_minutes=20, is_admin=True) == "running"
    assert await db.cancel_job(pend["id"], user_id=pend["user_id"], ttl_minutes=20) is None  # already cancelled
    assert await db.finish_job(pend["id"], stats={}, result_files=[], ttl_minutes=1) is False  # can't finish a cancelled job
    await db.pool.execute("TRUNCATE jobs RESTART IDENTITY")

    # ------------------------------------------------------------- worker e2e
    nt = FakeNotifier(); w = Worker(cfg, db, nt)

    async def run_one(job):
        claimed = await db.claim_job(); assert claimed["id"] == job["id"]
        await w.process(claimed); return await db.get_job(job["id"])

    os.environ["FAKE_MODE"] = "ok"
    # clean
    j = await mkjob("clean", lama=True, img_format="png"); r = await run_one(j)
    assert r["status"] == "done", r["error"]
    s = r["stats"]
    assert (s["pages"], s["blank_pages"], s["bubbles"]) == (3, 1, 4), s
    assert s["by_kind"] == {"dialogue": 2, "sfx": 2} and s["cleanup"] == {"flat": 2, "LaMa": 2, "OpenCV": 0}, s
    assert s["elapsed_s"] > 0 and s["output_bytes"] > 0 and r["expires_at"] is not None
    ev = nt.last("done"); assert ev[3][0].name == "result.zip" and ev[3][0].is_file()
    assert any(e[0] == "progress" for e in nt.events), "no live progress was reported"
    called = json.loads((Path(j["workdir"]) / "argv.json").read_text())
    assert called["leaked"] == [], "secrets reached the manga.py subprocess"
    assert "--lama" in called["argv"] and "--clean-only" in called["argv"] and called["target_lang"] == "ar"
    assert (Path(j["workdir"]) / "run.log").read_text(encoding="utf-8").count("بدء عملية جديدة") == 3

    # heartbeat: manga.py goes silent for 3s -> the status keeps refreshing and "idle" grows
    os.environ["FAKE_MODE"] = "slow"
    w.cfg = replace(cfg, heartbeat_seconds=0.5, monitor_seconds=0.5)
    j = await mkjob("clean"); r = await run_one(j); w.cfg = cfg
    assert r["status"] == "done", r["error"]
    ev = [e for e in nt.events if e[0] == "progress" and e[1] == j["id"]]
    assert len(ev) >= 4, f"heartbeat missing: only {len(ev)} refreshes"
    assert max(e[3] for e in ev) >= 1.5, "idle time did not grow during the silent step"
    assert max(e[4] for e in ev) >= 2.5 and ev[-1][4] >= ev[0][4], "elapsed time not reported"
    assert r["last_activity_at"] is not None
    # run.log captures the hardware header, live CPU/RAM/GPU lines, the engine output and a footer
    logtxt = (Path(j["workdir"]) / "run.log").read_text(encoding="utf-8")
    assert logtxt.startswith("[bot] start"), logtxt[:80]
    assert "requested device: CPU (--cpu)" in logtxt and "[bot] argv:" in logtxt and "GPU:" in logtxt
    assert logtxt.count("[monitor] cpu=") >= 2, logtxt
    assert "EP=CPUExecutionProvider" in logtxt and "[bot] finished rc=0" in logtxt
    assert "devices=OCR: CPU • LaMa: CPU" in logtxt, logtxt[-300:]
    os.environ["FAKE_MODE"] = "ok"

    # extract -> txt + json only
    j = await mkjob("extract"); r = await run_one(j); assert r["status"] == "done", r["error"]
    assert sorted(f.name for f in nt.last("done")[3]) == ["extract.json", "extract.txt"]
    assert "TEXT 0" in (Path(j["workdir"]) / "extract" / "extract.txt").read_text(encoding="utf-8")

    # typer -> the export zip with typer_job.json
    j = await mkjob("typer"); r = await run_one(j); assert r["status"] == "done", r["error"]
    f = nt.last("done")[3][0]; assert f.name == "typer.zip" and "typer_job.json" in zipfile.ZipFile(f).namelist()

    # translate (pdf output) -> translated counters
    j = await mkjob("translate", dialect="egyptian", format="pdf", model="qwen2.5:7b-instruct")
    r = await run_one(j); assert r["status"] == "done", r["error"]
    assert r["stats"]["dialogue"] == 2 and r["stats"]["translated"] == 2 and nt.last("done")[3][0].suffix == ".pdf"

    # missing typer_job.json: clean still delivers with approximate stats, extract fails
    os.environ["FAKE_MODE"] = "noexport"
    j = await mkjob("clean"); r = await run_one(j)
    assert r["status"] == "failed" or r["stats"].get("approximate"), r   # typer.zip missing only matters for typer
    assert r["status"] == "done" and r["stats"]["approximate"] and r["stats"]["bubbles"] == 4, r
    j = await mkjob("extract"); r = await run_one(j); assert r["status"] == "failed", r

    # manga.py crashes
    os.environ["FAKE_MODE"] = "fail"
    j = await mkjob("clean"); r = await run_one(j)
    assert r["status"] == "failed" and "كود 3" in r["error"] and any("boom" in l for l in nt.last("failed")[3])

    # timeout kills the process tree
    os.environ["FAKE_MODE"] = "hang"
    t0 = time.monotonic(); j = await mkjob("clean")
    w.cfg = replace(cfg, job_timeout_minutes=0.03)
    r = await run_one(j); assert r["status"] == "failed" and "مهلة" in r["error"] and time.monotonic() - t0 < 30
    w.cfg = cfg

    # /cancel on a running job
    j = await mkjob("clean"); claimed = await db.claim_job()
    task = asyncio.create_task(w.process(claimed)); await asyncio.sleep(1.5)
    assert claimed["id"] in w.handles
    assert await db.cancel_job(j["id"], j["user_id"], 20) == "running"
    assert await w.cancel_running(j["id"]); await asyncio.wait_for(task, 20)
    assert (await db.get_job(j["id"]))["status"] == "cancelled" and j["id"] not in w.handles

    # a single huge image (tall PNG strip) is recompressed/sliced instead of failing
    os.environ["FAKE_MODE"] = "hugeimg"; nt.limit = 1_000_000
    j = await mkjob("clean", pages=3, img_format="png"); r = await run_one(j)
    assert r["status"] == "done", r["error"]
    done = nt.last("done"); fl = done[3]
    assert fl and all(f.stat().st_size <= 1_000_000 for f in fl), [f.stat().st_size for f in fl]
    assert any("🗜️" in n for n in done[4]), done[4]
    assert not any(n.endswith(".png") for f in fl for n in zipfile.ZipFile(f).namelist()), "big png should have become jpg"
    nt.limit = 10 * 1024 * 1024

    # oversized output: clean zip is split, typer zip / pdf fail with advice
    os.environ["FAKE_MODE"] = "huge"
    nt.limit = 1_000_000
    j = await mkjob("clean", pages=3); r = await run_one(j)
    assert r["status"] == "done", r["error"]
    files = nt.last("done")[3]; assert len(files) >= 2 and all(f.stat().st_size <= 1_000_000 for f in files), files
    assert any("قُسّم" in n for n in nt.last("done")[4])
    # typer: too big for one message -> several independent TypeR jobs instead of failing
    j = await mkjob("typer", pages=3); r = await run_one(j)
    assert r["status"] == "done", r["error"]
    tf = nt.last("done")[3]
    assert len(tf) >= 2 and all(f.stat().st_size <= 1_000_000 for f in tf) and all(f.suffix == ".zip" for f in tf), tf
    assert sorted(i for f in tf for pg in json.loads(zipfile.ZipFile(f).read("typer_job.json"))["pages"] for i in [pg["index"]]) == [0, 1, 2]
    assert any("مستقلة" in n for n in nt.last("done")[4])
    # a PNG page that can't fit is refused with advice
    os.environ["FAKE_MODE"] = "hugeimg"
    j = await mkjob("typer", pages=2, img_format="png"); r = await run_one(j)
    assert r["status"] == "failed" and "JPG" in r["error"], r["error"]
    nt.limit = 10 * 1024 * 1024

    # ------------------------------------------------------------- external host (gofile)
    import dataclasses, bot.worker as bw
    from bot.hosting import Uploaded, UploadFailed
    ups = []
    async def fake_up(path, **kw):
        ups.append((Path(path).name, Path(path).stat().st_size, kw.get("token")))
        return Uploaded(Path(path).name, "https://gofile.io/d/xyz", Path(path).stat().st_size)
    real_up = bw.upload_gofile; bw.upload_gofile = fake_up
    cfg_ext = dataclasses.replace(cfg, external_host="gofile", gofile_token="T")
    wx = Worker(cfg_ext, db, nt)
    async def run_x(job):
        c = await db.claim_job(); assert c["id"] == job["id"]
        await wx.process(c); return await db.get_job(job["id"])
    # typer export of ~170MB-like size > limit: one full, unmodified zip is uploaded, nothing sent to Discord
    os.environ["FAKE_MODE"] = "huge"; nt.limit = 300_000
    j = await mkjob("typer", pages=3, img_format="png"); r = await run_x(j)
    assert r["status"] == "done", r["error"]
    ev = nt.last("done"); assert ev[3] == [], "files should not go to Discord"
    L = r["stats"]["external_links"]; assert L and L[0]["url"].startswith("https://gofile.io/"), L
    assert ups[-1][2] == "T" and ups[-1][1] > 300_000 and r["stats"]["pages"] == 3
    # fits Discord -> no external upload
    os.environ["FAKE_MODE"] = "ok"; nt.limit = 10 * 1024 * 1024; n = len(ups)
    j = await mkjob("clean"); r = await run_x(j)
    assert r["status"] == "done" and len(ups) == n and "external_links" not in r["stats"]
    # too big + clean zip -> external link of the original result
    os.environ["FAKE_MODE"] = "hugeimg"; nt.limit = 1_000_000
    j = await mkjob("clean", pages=2, img_format="png"); r = await run_x(j)
    assert r["status"] == "done" and r["stats"].get("external_links") and nt.last("done")[3] == []
    # upload failure -> falls back to shrink/split over Discord, with a note, job still succeeds
    async def bad_up(path, **kw): raise UploadFailed("boom")
    bw.upload_gofile = bad_up
    j = await mkjob("clean", pages=2, img_format="png"); r = await run_x(j)
    ev = nt.last("done")
    assert r["status"] == "done" and ev[3] and any("تعذّر الرفع" in x for x in ev[4]), ev[4]
    assert all(f.stat().st_size <= 1_000_000 for f in ev[3])
    bw.upload_gofile = real_up; nt.limit = 10 * 1024 * 1024

    # ------------------------------------------------------------- cleanup
    os.environ["FAKE_MODE"] = "ok"
    j = await mkjob("clean"); r = await run_one(j); wd = Path(j["workdir"]); assert wd.exists()
    outside = Path(tempfile.mkdtemp(prefix="outside_")); (outside / "keep.txt").write_text("x")
    evil = await mkjob("clean"); await db.pool.execute("UPDATE jobs SET status='done', workdir=$2, expires_at=now()-interval '1 min' WHERE id=$1", evil["id"], str(outside))
    assert await w.cleanup_once() == 0 and wd.exists(), "not expired yet"
    await db.pool.execute("UPDATE jobs SET expires_at = now() - interval '1 minute' WHERE id=$1", j["id"])
    assert await w.cleanup_once() == 1 and not wd.exists()
    assert (outside / "keep.txt").exists(), "cleanup deleted a directory outside the work dir!"
    assert (await db.get_job(j["id"]))["workdir"] is None
    # history totals
    tot = await db.user_totals(j["user_id"]); assert tot["jobs_done"] >= 4 and tot["pages"] >= 12 and tot["bubbles"] >= 16, tot

    # a pending job whose workdir vanished fails cleanly instead of crashing the worker
    ghost = await mkjob("clean"); await db.pool.execute("UPDATE jobs SET workdir=NULL WHERE id=$1", ghost["id"])
    r = await run_one(ghost); assert r["status"] == "failed" and "مجلد" in r["error"], r

    # run_forever picks jobs up by itself
    w2 = Worker(cfg, db, FakeNotifier()); t = asyncio.create_task(w2.run_forever())
    j = await mkjob("clean"); w2.notify_new_job()
    for _ in range(100):
        if (await db.get_job(j["id"]))["status"] == "done": break
        await asyncio.sleep(0.1)
    assert (await db.get_job(j["id"]))["status"] == "done"; w2.stop(); await asyncio.wait_for(t, 5)

    await db.close(); shutil.rmtree(work, ignore_errors=True); shutil.rmtree(outside, ignore_errors=True)
    print("test_bot_worker OK")

asyncio.run(main())
