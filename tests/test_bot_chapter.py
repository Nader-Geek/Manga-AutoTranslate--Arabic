"""chapter.zip builder + optional Ollama translation. Run: python3 tests/test_bot_chapter.py"""
import asyncio, json, os, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aiohttp import web
from PIL import Image
from bot.chapter_export import make_chapter, fit_font_size

def make_dir(d):
    regs = [{"id": 1, "kind": "dialogue", "rect": [10, 10, 120, 60], "tone": "normal", "source": "HELLO", "text": "",
             "srcstyle": {"fill": "#ffffff", "stroke": {"color": "#000000", "width": 3.0}, "glow": None,
                          "gradient": {"from": "#ff0000", "to": "#0000ff", "angle": 90}}},
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
            assert tx[0]["computed"]["fontFamily"].startswith("Vazirmatn") and tx[1]["computed"]["fontFamily"].startswith("Lalezar")
            assert tx[0]["stroke"] == {"width": 3.0, "color": "#000000"} and tx[0]["color"]["outline"] == "#000000"
            assert tx[0]["color"]["fill"] == "#ffffff" and tx[0]["gradient"]["to"] == "#0000ff" and "glow" not in tx[0]
            assert tx[0]["sourceStyle"]["stroke"]["width"] == 3.0 and tx[1]["sourceStyle"] is None
            assert tx[0]["box"] == {"x": 10, "y": 10, "w": 120, "h": 60} and tx[1]["style"] == ["shout"]
            assert data["pages"][0]["imageFilename"] == "page-001.jpg"
    # hosted API (OpenAI-compatible): bearer key, 400 on response_format -> retried without it
    seen = {"auth": None, "rf400": 0}
    async def comp(req):
        seen["auth"] = req.headers.get("Authorization")
        body = await req.json()
        if "response_format" in body:
            seen["rf400"] += 1
            return web.Response(status=400, text="no response_format")
        lines = json.loads(body["messages"][1]["content"])["lines"]
        txt = "```json\n" + json.dumps({"translations": ["api:" + l for l in lines]}) + "\n```"
        return web.json_response({"choices": [{"message": {"content": txt}}]})
    app2 = web.Application(); app2.router.add_post("/v1/chat/completions", comp)
    r2 = web.AppRunner(app2); await r2.setup()
    s2 = web.TCPSite(r2, "127.0.0.1", 0); await s2.start()
    base2 = f"http://127.0.0.1:{s2._server.sockets[0].getsockname()[1]}/v1"
    from bot import providers
    providers.API_PROVIDERS["openai"]["base"] = base2
    os.environ["OPENAI_API_KEY"] = "sk-test"
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); d = t / "typer"; d.mkdir(); make_dir(d)
        ch = await make_chapter(d, t / "c.zip", title="x", opts={"translate": True, "provider": "openai"},
                                ollama_url="http://unused", model="qwen")
        assert ch["pages"][0]["texts"][0]["text"] == "api:HELLO" and seen["auth"] == "Bearer sk-test" and seen["rf400"] >= 1
    del os.environ["OPENAI_API_KEY"]
    assert providers.missing_key_message("openai") and providers.missing_key_message("ollama") is None
    await r2.cleanup()
    # tone_fonts off -> one font for all
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); d = t / "typer"; d.mkdir(); make_dir(d)
        ch = await make_chapter(d, t / "c.zip", title="x", opts={"tone_fonts": False}, ollama_url="http://x", model="m")
        assert all(x["computed"]["fontFamily"].startswith("Vazirmatn") for x in ch["pages"][0]["texts"])
    # unreachable Ollama + translate requested -> loud failure (never a silent untranslated zip)
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); d = t / "typer"; d.mkdir(); make_dir(d)
        try:
            await make_chapter(d, t / "c.zip", title="x", opts={"translate": True, "provider": "ollama"},
                               ollama_url="http://127.0.0.1:9", model="m")
            raise SystemExit("silent failure")
        except RuntimeError as e:
            assert "فشلت الترجمة" in str(e), e
    # auto -> the provider that has a key; none -> ollama
    for k in providers.KEY_ENV_NAMES: os.environ.pop(k, None)
    assert providers.resolve("auto") == "ollama"
    os.environ["GEMINI_API_KEY"] = "k"; assert providers.resolve("auto") == "gemini"
    del os.environ["GEMINI_API_KEY"]
    await pack_tests(url)
    await runner.cleanup()
    assert 8 <= fit_font_size("hello world", 100, 50) <= 50



# ---- style pack (real TypeR export when available, else skipped)
import glob
async def pack_tests(url):
    PACK = glob.glob("/tmp/fz/*.json")
    if PACK:
        import shutil
        from bot import style_pack as sp
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); zp = t / "p.zip"
            with zipfile.ZipFile(zp, "w") as z:
                z.write(PACK[0], "styles.json")
                for f in glob.glob("/tmp/fz/fonts/*"): z.write(f, "fonts/" + Path(f).name)
            pack = sp.install_pack(zp, t / "pack")
            assert len(pack["styles"]) == 17 and pack["map"]["normal"] == "Speech" and pack["map"]["shout"] == "Shout"
            assert pack["map"]["thought"] == "Thinking" and all(s["arabic"] == 0 for s in pack["styles"])
            assert sp.set_mapping(t / "pack", "whisper", "Stress")["map"]["whisper"] == "Stress"
            try: sp.set_mapping(t / "pack", "whisper", "nope"); raise SystemExit("bad style accepted")
            except sp.PackError: pass
            d = t / "typer"; d.mkdir(); make_dir(d)
            async def go(translate):
                return await make_chapter(d, t / f"c{translate}.zip", title="x", ollama_url=url, model="m",
                                          opts={"translate": translate, "style_pack_dir": str(t / "pack")})
            ch = await go(False)      # source text: pack fonts + stroke + prefix, fonts shipped in the zip
            a, b = ch["pages"][0]["texts"]
            assert a["typerStyle"] == "Speech" and a["computed"]["fontFamily"].startswith("CCMildMannered") and a["stroke"]["width"] == 3
            assert a["computed"]["textTransform"] == "uppercase"
            assert b["typerStyle"] == "Hand letters" and b["computed"]["fontFamily"].startswith("SS Soapy")
            with zipfile.ZipFile(t / "cFalse.zip") as z:
                assert any(n.startswith("fonts/CCMildMannered") for n in z.namelist())
            ch = await go(True)       # Arabic: pack fonts lack glyphs -> fallback font, no pack fonts shipped
            a, b = ch["pages"][0]["texts"]
            assert a["computed"]["fontFamily"].startswith("Vazirmatn") and a["typerStyle"] == "Speech"
            with zipfile.ZipFile(t / "cTrue.zip") as z:
                assert not any(n.startswith("fonts/") for n in z.namelist())
            # hostile zips
            bad = t / "bad.zip"
            with zipfile.ZipFile(bad, "w") as z: z.writestr("x.json", "{}")
            try: sp.install_pack(bad, t / "p2"); raise SystemExit("accepted junk")
            except sp.PackError: pass
        print("style pack tests OK")


asyncio.run(main()); print("test_bot_chapter OK")

# ---- page notes (missing / failed pages are reported)
from bot.worker import Worker
with tempfile.TemporaryDirectory() as t:
    t = Path(t); (t / "typer").mkdir()
    (t / "typer" / "typer_job.json").write_text(json.dumps({"pages": [{"index": 0}, {"index": 1}]}))
    (t / "run.log").write_text("x\n    [!] PAGE_FAILED #2: boom\n")
    n = Worker._page_notes({"kind": "chapter", "total_pages": 4}, t, t / "typer" / "typer_job.json")
    assert any("2 صفحة من أصل 4" in x for x in n) and any("#2" in x for x in n), n
    assert Worker._page_notes({"kind": "translate", "total_pages": 4}, t, t / "typer" / "typer_job.json") == []
print("page notes OK")
