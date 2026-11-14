"""chapter.zip builder + optional Ollama translation. Run: python3 tests/test_bot_chapter.py"""
import asyncio, json, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aiohttp import web
from PIL import Image
from bot.chapter_export import make_chapter, fit_font_size

def make_dir(d):
    regs = [{"id": 1, "kind": "dialogue", "rect": [10, 10, 120, 60], "tone": "normal", "source": "HELLO", "text": ""},
            {"id": 2, "kind": "sfx", "rect": [150, 100, 80, 40], "tone": "shout", "source": "BOOM", "text": ""}]
    pages = []
    for i in range(2):
        Image.new("RGB", (300, 400), (250, 250, 250)).save(d / f"page_{i+1:03d}.jpg")
        pages.append({"index": i, "file": f"page_{i+1:03d}.jpg", "width": 300, "height": 400,
                      "origin": f"{i+1}.jpg", "regions": json.loads(json.dumps(regs)) if i == 0 else []})
    (d / "typer_job.json").write_text(json.dumps({"pages": pages}), encoding="utf-8")

calls = {"n": 0}
async def chat(req):
    calls["n"] += 1
    body = await req.json()
    lines = json.loads(body["messages"][1]["content"])["lines"]
    return web.json_response({"message": {"content": json.dumps({"translations": ["ar:" + l for l in lines]}, ensure_ascii=False)}})

async def main():
    app = web.Application(); app.router.add_post("/api/chat", chat)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0); await site.start()
    url = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
    for translate in (False, True):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); d = t / "typer"; d.mkdir(); make_dir(d)
            ch = await make_chapter(d, t / "chapter.zip", title="My Manga Ch 1",
                                    opts={"translate": translate, "ocr": "en"}, ollama_url=url, model="m")
            with zipfile.ZipFile(t / "chapter.zip") as z:
                names = z.namelist()
                assert "chapter.json" in names and "images/page-001.jpg" in names and "images/page-002.jpg" in names, names
                data = json.loads(z.read("chapter.json"))
            assert data["schema"] == "manhuarmtl-v1" and data["pageCount"] == 2 and data["stitchMode"] == "none"
            tx = data["pages"][0]["texts"]
            assert len(tx) == 2 and data["pages"][1]["texts"] == []
            assert data["translation"]["active"] is translate
            if translate:
                assert tx[0]["text"] == "ar:HELLO" and tx[0]["sourceText"] == "HELLO" and tx[0]["isTranslated"] and tx[0]["dir"] == "rtl"
                assert data["translation"]["translatedTexts"] == 2 and not data["translation"]["insufficient"]
            else:
                assert tx[0]["text"] == "HELLO" and not tx[0]["isTranslated"] and calls["n"] == 1 or calls["n"] == 0
            assert tx[0]["box"] == {"x": 10, "y": 10, "w": 120, "h": 60} and tx[1]["style"] == ["shout"]
            assert data["pages"][0]["imageFilename"] == "page-001.jpg"
    # unreachable Ollama: no crash, texts stay untranslated
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); d = t / "typer"; d.mkdir(); make_dir(d)
        ch = await make_chapter(d, t / "c.zip", title="x", opts={"translate": True}, ollama_url="http://127.0.0.1:9", model="m")
        assert ch["translation"]["translatedTexts"] == 0 and ch["translation"]["insufficient"]
    await runner.cleanup()
    assert 8 <= fit_font_size("hello world", 100, 50) <= 50

asyncio.run(main()); print("test_bot_chapter OK")
