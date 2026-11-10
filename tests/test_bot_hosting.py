import asyncio, sys, tempfile
from pathlib import Path
from aiohttp import web
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot.hosting import upload_gofile, UploadFailed


async def main():
    seen = {"n": 0, "auth": None, "size": 0, "name": None}
    mode = {"v": "ok"}

    async def h(req):
        seen["n"] += 1; seen["auth"] = req.headers.get("Authorization")
        if mode["v"] == "500once" and seen["n"] == 1:
            return web.Response(status=503, text="busy")
        if mode["v"] == "403":
            return web.Response(status=403, text="no")
        if mode["v"] == "html":
            return web.Response(text="<html>")
        if mode["v"] == "evil":
            return web.json_response({"status": "ok", "data": {"downloadPage": "https://evil.com/x"}})
        if mode["v"] == "http":
            return web.json_response({"status": "ok", "data": {"downloadPage": "http://gofile.io/d/x"}})
        r = await req.multipart(); part = await r.next()
        data = await part.read(); seen["size"] = len(data); seen["name"] = part.filename
        return web.json_response({"status": "ok", "data": {"downloadPage": "https://gofile.io/d/abc123"}})

    app = web.Application(client_max_size=1024**3); app.router.add_post("/uploadfile", h)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0); await site.start()
    url = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}/uploadfile"

    f = Path(tempfile.mkdtemp()) / "res.zip"; f.write_bytes(b"z" * 3_000_000)
    up = await upload_gofile(f, url=url, token="tok")
    assert up.url == "https://gofile.io/d/abc123" and up.size == 3_000_000
    assert seen["size"] == 3_000_000 and seen["name"] == "res.zip" and seen["auth"] == "Bearer tok"
    seen["n"] = 0; mode["v"] = "500once"
    up = await upload_gofile(f, url=url, backoff=0.01); assert seen["n"] == 2
    for m in ("403", "html", "evil", "http"):
        mode["v"] = m
        try: await upload_gofile(f, url=url, backoff=0.01); raise SystemExit(f"{m} should fail")
        except UploadFailed: pass
    try: await upload_gofile(f, url="http://127.0.0.1:1/x", retries=1, backoff=0.01); raise SystemExit("no fail")
    except UploadFailed: pass
    await runner.cleanup()
    print("PASS test_bot_hosting")

asyncio.run(main())
