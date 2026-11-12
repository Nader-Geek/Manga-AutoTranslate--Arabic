import asyncio, io, sys, tempfile, zipfile
from pathlib import Path
from aiohttp import web
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.fetch import fetch_link, classify, FetchError

ZIP = io.BytesIO(); 
with zipfile.ZipFile(ZIP, "w") as z: z.writestr("1.jpg", b"x" * 1000)
ZIP = ZIP.getvalue()


async def main():
    seen = {}
    async def drive(req):
        seen["q"] = dict(req.query)
        fid = req.query["id"]
        if fid == "privateprivate": return web.Response(text="<html>sign in</html>", content_type="text/html")
        if fid == "hugehugehuge": return web.Response(body=b"PK\x03\x04" + b"0" * 3_000_000, content_type="application/zip")
        if fid == "textfiletext": return web.Response(body=b"hello world, not a zip", content_type="application/octet-stream")
        if fid == "redirredirr": raise web.HTTPFound("https://evil.example.com/x")
        return web.Response(body=ZIP, content_type="application/octet-stream",
                            headers={"Content-Disposition": "attachment; filename*=UTF-8''%D9%81%D8%B5%D9%84.zip"})
    async def accounts(req): return web.json_response({"status": "ok", "data": {"token": "TKN"}})
    async def contents(req):
        seen["auth"] = req.headers.get("Authorization")
        cid = req.match_info["cid"]
        base = f"http://127.0.0.1:{port}"
        if cid == "multi": kids = {"a": {"type": "file", "name": "a.zip", "link": base + "/f/a"}, "b": {"type": "file", "name": "b.zip", "link": base + "/f/b"}}
        else: kids = {"a": {"type": "file", "name": "ch1.zip", "link": base + "/f/a"}, "n": {"type": "file", "name": "notes.txt", "link": base + "/f/n"}}
        return web.json_response({"status": "ok", "data": {"type": "folder", "children": kids}})
    async def f(req):
        seen["cookie"] = req.headers.get("Cookie")
        return web.Response(body=ZIP, content_type="application/zip")
    app = web.Application(); app.router.add_get("/download", drive); app.router.add_post("/accounts", accounts)
    app.router.add_get("/contents/{cid}", contents); app.router.add_get("/f/{x}", f)
    runner = web.AppRunner(app); await runner.setup(); site = web.TCPSite(runner, "127.0.0.1", 0); await site.start()
    port = site._server.sockets[0].getsockname()[1]
    kw = dict(extra_hosts=("127.0.0.1",), drive_url=f"http://127.0.0.1:{port}/download", gofile_api=f"http://127.0.0.1:{port}")
    out = lambda: Path(tempfile.mkdtemp())

    # classification
    assert classify("https://drive.google.com/file/d/1AbCdEfGhIjKlMn/view?usp=sharing") == ("drive", "1AbCdEfGhIjKlMn")
    assert classify("https://drive.google.com/open?id=1AbCdEfGhIjKlMn") == ("drive", "1AbCdEfGhIjKlMn")
    assert classify("https://gofile.io/d/aB3xYz") == ("gofile", "aB3xYz")
    for bad in ("https://evil.com/x.zip", "ftp://gofile.io/d/abc", "https://gofile.io.evil.com/d/abc",
                "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMn", "not a url", "http://127.0.0.1/x",
                "https://gofile.io/d/../../etc"):
        try: classify(bad); raise SystemExit(f"should reject {bad}")
        except FetchError: pass

    r = await fetch_link("https://drive.google.com/file/d/1AbCdEfGhIjKlMn/view", out(), 10**8, **kw)
    assert r.filename == "فصل.zip" and r.size == len(ZIP) and r.path.read_bytes() == ZIP and seen["q"]["id"] == "1AbCdEfGhIjKlMn"
    r = await fetch_link("https://gofile.io/d/aB3xYz", out(), 10**8, **kw)
    assert r.filename == "ch1.zip" and r.path.read_bytes() == ZIP and seen["auth"] == "Bearer TKN" and "TKN" in seen["cookie"]
    for link, why in (("https://gofile.io/d/multi", "واحد"),
                      ("https://drive.google.com/file/d/privateprivate/view", "صفحة ويب"),
                      ("https://drive.google.com/file/d/hugehugehuge/view", "أكبر"),
                      ("https://drive.google.com/file/d/textfiletext/view", "ليس ZIP"),
                      ("https://drive.google.com/file/d/redirredirr/view", "غير مسموح")):
        mx = 1_000_000 if "huge" in link else 10**8
        try: await fetch_link(link, out(), mx, **kw); raise SystemExit(f"should fail: {link}")
        except FetchError as e: assert why in str(e), (link, str(e))
    # an unreachable server gives a clean FetchError, not a traceback
    try: await fetch_link("https://gofile.io/d/aB3xYz", out(), 10**6, extra_hosts=("127.0.0.1",), gofile_api="http://127.0.0.1:1")
    except FetchError: pass
    else: raise SystemExit("should fail")
    await runner.cleanup(); print("PASS test_bot_fetch")

asyncio.run(main())
