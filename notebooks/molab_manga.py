# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "numpy",
#     "opencv-python-headless",
#     "onnxruntime",
#     "pillow",
#     "requests",
#     "arabic-reshaper",
#     "python-bidi",
#     "huggingface_hub",
#     "pymupdf",
#     "rapidocr",
#     "openai",
#     "asyncpg",
#     "discord.py",
#     "aiohttp",
#     "python-dotenv",
#     "pixeltable-pgserver",
# ]
# ///
"""مترجم المانجا العربي — بيئة تجربة marimo / molab.

يجرّب الأوامر الأربعة (clean / extract / typer / translate) على صفحاتك، ويعرض الإحصائيات
(الصفحات، الفقاعات، النوع، النبرة، طريقة المسح) ومعاينة قبل/بعد، ويشغّل اختبارات منطق البوت.

molab بيئة CPU قصيرة الجلسة: التنظيف والاستخراج يعملان محلياً، أما الترجمة فتحتاج عنوان Ollama
شغّال في مكان آخر (مثلاً من نوتبوك Kaggle أو جهازك). بوت ديسكورد نفسه لا يناسب molab (جلسات قصيرة)
فشغّله من نوتبوك Kaggle أو من جهازك.
"""

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import io
    import os
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    import marimo as mo

    return Path, io, mo, os, subprocess, sys, tempfile


@app.cell
def _(mo):
    mo.md(
        "# 🈶 مترجم المانجا العربي — تجربة على molab\n\n"
        "**الخطوات:** ١) جهّز المشروع ← ٢) ارفع صفحة/ZIP/PDF واختر الأمر ← ٣) شغّل.\n\n"
        "الجلسة الأولى تنزّل موديلات الكشف/OCR (دقائق)، وبعدها يصير التشغيل أسرع."
    )
    return


@app.cell
def _(mo):
    repo_url = mo.ui.text(
        value="https://github.com/Nader-Geek/Manga-AutoTranslate--Arabic",
        label="رابط الريبو", full_width=True)
    branch = mo.ui.text(value="discord-bot", label="الفرع")
    ollama_url = mo.ui.text(
        value="", label="عنوان Ollama (للترجمة فقط)", placeholder="http://host:11434", full_width=True)
    ollama_model = mo.ui.text(value="qwen2.5:7b-instruct", label="نموذج Ollama")
    setup_btn = mo.ui.run_button(label="١) جهّز المشروع والاعتماديات", kind="success")
    mo.vstack([repo_url, mo.hstack([branch, ollama_model], justify="start"), ollama_url, setup_btn])
    return branch, ollama_model, ollama_url, repo_url, setup_btn


@app.cell
def _(Path, branch, mo, os, repo_url, setup_btn, subprocess, sys):
    mo.stop(not setup_btn.value, mo.md("⬆️ اضغط زر التجهيز أولاً."))

    _existing = os.environ.get("MANGA_REPO", "")
    REPO = Path(_existing) if _existing else Path("/tmp/manga_repo")

    def _run(cmd, **kw):
        return subprocess.run(cmd, capture_output=True, text=True, **kw)

    def _pip(*args):
        _err = ""
        for cmd in ([sys.executable, "-m", "pip", "install", "-q", *args],
                    ["uv", "pip", "install", "-q", "--python", sys.executable, *args]):
            try:
                r = _run(cmd)
            except FileNotFoundError:
                continue
            if r.returncode == 0:
                return True, ""
            _err = (r.stderr or r.stdout)[-800:]
        return False, _err

    _log = []
    if not (REPO / "manga.py").exists():
        _r = _run(["git", "clone", "--depth", "1", "-b", branch.value, repo_url.value, str(REPO)])
        if _r.returncode:
            mo.stop(True, mo.md(f"❌ فشل `git clone`:\n```\n{_r.stderr[-800:]}\n```\n"
                                "لو الريبو خاص اضبط متغير البيئة `MANGA_REPO` على مجلد المشروع."))
    _log.append(f"المشروع: `{REPO}`")

    _ok, _err = _pip("-r", str(REPO / "requirements.txt"))
    _log.append("الاعتماديات: " + ("✅" if _ok else f"⚠️ {_err}"))

    sys.path.insert(0, str(REPO))
    _warm = _run([sys.executable, str(REPO / "manga.py"), "--help"], timeout=1800)
    _log.append("manga.py: " + ("✅" if _warm.returncode == 0 else f"❌\n```\n{(_warm.stdout + _warm.stderr)[-800:]}\n```"))
    mo.md("\n\n".join(_log))
    return (REPO,)


@app.cell
def _(mo):
    upload = mo.ui.file(
        filetypes=[".png", ".jpg", ".jpeg", ".webp", ".zip", ".pdf"], kind="area",
        label="ارفع صورة أو ZIP أو PDF")
    mode = mo.ui.dropdown(
        {"🧹 clean — تنظيف": "clean", "🔎 extract — استخراج النص": "extract",
         "🧩 typer — تنظيف + إحداثيات": "typer", "🌐 translate — ترجمة عربية": "translate"},
        value="🧹 clean — تنظيف", label="الأمر")
    quality = mo.ui.dropdown({"سريع (OpenCV)": "fast", "جودة أعلى (LaMa — أبطأ)": "lama"},
                             value="سريع (OpenCV)", label="جودة المسح")
    ocr = mo.ui.dropdown({"إنجليزي": "en", "ياباني": "ja", "كوري": "ko", "صيني": "zh"},
                         value="إنجليزي", label="لغة النص الأصلي")
    order = mo.ui.dropdown({"مانجا: يمين←يسار": "rtl", "ويبتون: يسار←يمين": "ltr"},
                           value="مانجا: يمين←يسار", label="ترتيب القراءة")
    dialect = mo.ui.dropdown({"فصحى مبسّطة": "msa", "لهجة مصرية": "egyptian"},
                             value="فصحى مبسّطة", label="أسلوب العربية (للترجمة)")
    run_btn = mo.ui.run_button(label="٢) شغّل", kind="success")
    mo.vstack([upload, mo.hstack([mode, quality], justify="start"),
               mo.hstack([ocr, order, dialect], justify="start"), run_btn])
    return dialect, mode, ocr, order, quality, run_btn, upload


@app.cell
def _(REPO, Path, dialect, io, mo, mode, ocr, ollama_model, ollama_url, order, os, quality, run_btn, tempfile, upload):
    mo.stop(not run_btn.value, mo.md("⬆️ ارفع ملفاً ثم اضغط **شغّل**."))
    mo.stop(not upload.value, mo.md("⚠️ لم يُرفع أي ملف."))

    from bot.local_run import PipelineError, run_job, side_by_side
    from bot.runner import UploadError

    _f = upload.value[0]
    _src = Path(tempfile.mkdtemp(prefix="up_")) / _f.name
    _src.write_bytes(_f.contents)

    os.environ["OLLAMA_MODEL"] = ollama_model.value
    if ollama_url.value.strip():
        os.environ["OLLAMA_URL"] = ollama_url.value.strip().rstrip("/")
    os.environ.setdefault("BOT_WORK_DIR", "/tmp/bot_work")
    if mode.value == "translate" and not ollama_url.value.strip():
        mo.stop(True, mo.md("⚠️ الترجمة تحتاج **عنوان Ollama** (الحقل أعلى). "
                            "جرّب clean / extract / typer بدونه."))

    _opts = {"lama": quality.value == "lama", "ocr": ocr.value, "reading_order": order.value,
             "img_format": "jpg"}
    if mode.value == "translate":
        _opts.update({"dialect": dialect.value, "format": "zip", "model": ollama_model.value})

    try:
        with mo.status.spinner(title="جارٍ المعالجة... (أول مرة تنزّل الموديلات)"):
            result = run_job(mode.value, _src, _opts)
    except (UploadError, PipelineError) as _e:
        _tail = "\n".join(getattr(_e, "tail", [])[-12:])
        mo.stop(True, mo.md(f"❌ **{_e}**\n\n```\n{_tail}\n```"))

    from bot import stats as _st
    _rows = [{"المؤشر": n, "القيمة": v} for n, v, _ in _st.stats_fields(mode.value, result.stats)]
    _buf = io.BytesIO()
    try:
        side_by_side(result, 2, 800).save(_buf, "PNG")
        _preview = mo.image(_buf.getvalue(), caption="يسار: الأصل — يمين: الناتج")
    except Exception as _e:  # no preview (e.g. extract on a PDF) is not an error
        _preview = mo.md(f"_لا توجد معاينة: {_e}_")
    _downloads = mo.hstack([
        mo.download(data=f.read_bytes(), filename=f.name, label=f"⬇️ {f.name}") for f in result.files
    ], justify="start")
    mo.vstack([mo.md("### ✅ تمّت المعالجة"), mo.ui.table(_rows, selection=None, pagination=False),
               _preview, _downloads])
    return PipelineError, UploadError, result, run_job, side_by_side


@app.cell
def _(mo, mode, result):
    # عرض نص الاستخراج مباشرة عند اختيار extract
    mo.stop(mode.value != "extract")
    mo.md("### 🔎 النص المستخرج\n```\n" +
          (result.workdir / "extract" / "extract.txt").read_text(encoding="utf-8")[:4000] + "\n```")
    return


@app.cell
def _(mo):
    tests_btn = mo.ui.run_button(label="٣) شغّل الاختبارات")
    mo.vstack([mo.md("---\n### 🧪 اختبارات منطق البوت (طابور PostgreSQL، الأوامر، الإحصائيات)"), tests_btn])
    return (tests_btn,)


@app.cell
def _(REPO, mo, os, subprocess, sys, tests_btn):
    mo.stop(not tests_btn.value)
    from bot import devpg

    _pg = devpg.start("/tmp/mangabot_pg_test")
    _env = {**os.environ, "TEST_DATABASE_URL": _pg.dsn}
    _lines = []
    for _t in ["test_wall_protect", "test_bot_stats", "test_bot_runner", "test_bot_localrun",
               "test_bot_worker", "test_bot_ui"]:
        _r = subprocess.run([sys.executable, "-I", f"tests/{_t}.py"], cwd=REPO, env=_env,
                            capture_output=True, text=True, timeout=900)
        _lines.append(("✅ " if _r.returncode == 0 else "❌ ") + _t +
                      ("" if _r.returncode == 0 else f"\n```\n{(_r.stdout + _r.stderr)[-700:]}\n```"))
    _pg.stop()
    mo.md("\n\n".join(_lines))
    return


if __name__ == "__main__":
    app.run()
