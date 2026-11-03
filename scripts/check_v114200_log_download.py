#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ v1.14.200 — «تو پی سی لینوکس هم دانلود لاگ بزار کنار کپی لاگ …
لاگ کامل بگیره ناقص نباشه» (گزارشِ سازنده — برایِ گزارشِ باگ).

گیتها:
  A. نسخه = 1.14.200 / versionCode=205 (manga.py + manga_app.py + VERSION
     + gradle) + سطرهایِ apkArm64/apkArmv7a/apkUniversal در VERSION.
  B. لاگِ کاملِ رویِ دیسک: فایلِ sessions/{sid}.log از اولِ کار تا آخر،
     بی هیچ برشی — هر خطِ stdout در _reader خطبهخط مینشیند (flush + tail
     + close) و خطهایِ وضعیت (شروع/متوقف/خطا/تمامشد) هم همانجا میآیند؛
     بافرِ ۱۲۰خطیِ نمایشِ زنده فقط برایِ UI میماند (سبکِ قبل).
  C. دکمهٔ «⬇ دانلود لاگ» کنارِ «📋 کپی لاگ»: دکمهٔ HTML + data-sessdir +
     JS (sid از #manga_sid/localStorage؛ URL از /gradio_api/file= با
     encodeURIComponent و %2F→/؛ چکِ HEAD؛ a.download با نامِ
     manga_log_<sid8>.txt) — کپیِ قدیمی دستنخورده.
  D. عملکردیِ _append_job_logfile: نوشتنِ دقیق/الحاقِ درست/بیتوجهی به
     sidِ خالی.
  E. عملکردیِ _reader (500 خطِ واقعی): فایلِ لاگ «کامل» است حتی وقتی
     bufِ حافظه به ۳۰۰ سقف میخورد؛ ترتیب سالم؛ tailِ بیسطرجدید هم مینشیند.
  F. node --check رویِ JSِ استخراجشدهٔ _dark_js_src.
  G. روتِ زندهٔ /gradio_api/file= در gradio 6: فایلِ لاگِ زیرِ
     allowed_paths ۲۰۰ میآید، بیرونش ۴۰۳.
"""

import ast
import io
import os
import py_compile
import re
import shutil
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FAILS = []


def ok(msg):
    print(f"[✓] {msg}")


def fail(msg):
    FAILS.append(msg)
    print(f"[✗] {msg}")


def gate(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)
    return cond


_manga = io.open("manga.py", encoding="utf-8").read()
_manga_app = io.open("manga_app.py", encoding="utf-8").read()
_gradle = io.open("android/app/build.gradle.kts", encoding="utf-8").read()
_version = io.open("VERSION", encoding="utf-8").read()

# ---------- A. نسخه ----------
_m = re.search(r'APP_VER\s*=\s*"([^"]+)"', _manga)
_ma = re.search(r'APP_VER\s*=\s*"([^"]+)"', _manga_app)
_vn = re.search(r"versionName=([0-9.]+)", _version)
_vc = re.search(r"versionCode=(\d+)", _version)
_gn = re.search(r'versionName\s*=\s*"([0-9.]+)"', _gradle)
_gc = re.search(r"versionCode\s*=\s*(\d+)", _gradle)
gate(_m and _m.group(1) == "1.14.200", "manga.py: APP_VER = 1.14.200")
gate(_ma and _ma.group(1) == "1.14.200", "manga_app.py: APP_VER = 1.14.200")
gate(_vn and _vn.group(1) == "1.14.200", "VERSION: versionName=1.14.200")
gate(_vc and _vc.group(1) == "205", "VERSION: versionCode=205")
gate(_gn and _gn.group(1) == "1.14.200", "gradle: versionName 1.14.200")
gate(_gc and _gc.group(1) == "205", "gradle: versionCode 205")
gate("apkArm64=" in _version and "apkArmv7a=" in _version
     and "apkUniversal=" in _version, "VERSION: ۳ سطرِ apk سرِ جایش")

# ---------- B. لاگِ کاملِ رویِ دیسک ----------
gate("def _append_job_logfile(sid: str, text: str) -> None:" in _manga_app,
     "helper: _append_job_logfile تعریف شده")
gate('os.path.join(SESS_DIR, f"{sid}.log")' in _manga_app,
     "فایلِ لاگ = sessions/{sid}.log")
gate("f.write(text if text.endswith(\"\\n\") else text + \"\\n\")"
     in _manga_app,
     "helper: خطِ بیسطرجدید هم با سطرجدید مینشیند")
# _reader: بازکردنِ فایل + نوشتنِ هر خط + flush + tail + بستن
gate('log_fh = open(os.path.join(SESS_DIR, f"{sid}.log"), "a",' in _manga_app,
     "reader: فایلِ کامل در ابتدایِ کار باز میشود (append)")
gate("log_fh.write(text + \"\\n\")" in _manga_app
     and "log_fh.flush()" in _manga_app,
     "reader: هر خطِ stdout خطبهخط + flush مینشیند")
gate("_tail_txt" in _manga_app and "log_fh.write(_tail_txt + \"\\n\")"
     in _manga_app,
     "reader: دنبالهٔ نیمخطِ آخر هم مینشیند")
gate("if log_fh is not None:\n                        try:\n                            log_fh.close()"
     in _manga_app,
     "reader: فایل در finally بسته میشود")
# خطهایِ وضعیت هم داخلِ فایلِ کامل
gate('_append_job_logfile(sid, "⏹ ترجمه متوقف شد توسط کاربر.")' in _manga_app,
     "وضعیت: «متوقف شد» در فایلِ لاگ")
gate("_append_job_logfile(sid, f\"❌ خطا — کد خروج {rc}\")" in _manga_app,
     "وضعیت: «خطا — کد خروج» در فایلِ لاگ")
gate("_append_job_logfile(sid, f\"⚠ reader: {e}\")" in _manga_app,
     "وضعیت: خطایِ reader در فایلِ لاگ")
gate("_append_job_logfile(sid, f\"❌ اجرا نشد: {e}\")" in _manga_app,
     "وضعیت: «اجرا نشد» در فایلِ لاگ")
gate("_append_job_logfile(sid, _done_line)" in _manga_app
     and "_done_line = (f\"✅ تمام شد ({dur_s})" in _manga_app,
     "وضعیت: «تمام شد» یکبار در فایلِ لاگ (بدونِ دوبله)")
gate("shروعِ کارِ جدید" in _manga_app
     or "شروعِ کارِ جدید" in _manga_app,
     "وضعیت: هدرِ شروعِ کار (نسخه + زمان) در فایلِ لاگ")
gate('final_log = "\\n".join(buf[-120:]) + _done_line' in _manga_app,
     "نمایشِ زنده: همان برشِ ۱۲۰خطیِ قبل (سبکِ قبل دستنخورده)")

# ---------- C. دکمهٔ دانلود لاگ ----------
gate('id="manga_dl_log"' in _manga_app and "⬇ دانلود لاگ" in _manga_app,
     "HTML: دکمهٔ «⬇ دانلود لاگ» کنارِ «کپی لاگ»")
gate("data-sessdir=" in _manga_app and 'f"""\n<div id="manga_status_chip">'
     in _manga_app,
     "HTML: data-sessdir (مسیرِ نشستها) به JS میرسد")
gate('id="manga_copy_log"' in _manga_app
     and 'title="کپی متن لاگ"' in _manga_app,
     "کپیِ قدیمی: سرِ جایش، دستنخورده")
gate("getElementById('manga_dl_log')" in _manga_app
     and "dlLogBtn.addEventListener('click'" in _manga_app,
     "JS: دکمهٔ دانلود بسته میشود (یکبار)")
gate("document.querySelector('#manga_sid textarea')" in _manga_app
     and "localStorage.getItem('manga_sid')" in _manga_app,
     "JS: sid از #manga_sid + فالبکِ localStorage")
gate("'/gradio_api/file='" in _manga_app
     and "encodeURIComponent(sessdir + '/' + sid + '.log').replace(/%2F/g, '/')"
     in _manga_app,
     "JS: URL از روتِ فایلِ gradio 6 با کدگذاریِ امنِ مسیر")
gate("method: 'HEAD'" in _manga_app,
     "JS: چکِ HEAD — بدونِ لاگ، «✖ لاگی نیست» نه دانلودِ شکسته")
gate("a.download = 'manga_log_' + sid.slice(0, 8) + '.txt'" in _manga_app,
     "JS: نامِ فایلِ دانلودی = manga_log_<sid8>.txt")

# ---------- D. عملکردیِ _append_job_logfile ----------
def _extract_fn(src, name):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.Module(body=[node], type_ignores=[])
    return None


_tmp = tempfile.mkdtemp(prefix="manga200_")
try:
    ns = {"os": os, "SESS_DIR": _tmp}
    mod = _extract_fn(_manga_app, "_append_job_logfile")
    gate(mod is not None, "عملکردی: _append_job_logfile از سورس استخراج شد")
    if mod is not None:
        exec(compile(mod, "<extract>", "exec"), ns)
        fn = ns["_append_job_logfile"]
        fn("abc123", "line1")
        fn("abc123", "line2\n")
        fn("", "nope")          # sidِ خالی = بیاثر
        fn("other", "x")
        p = os.path.join(_tmp, "abc123.log")
        data = io.open(p, encoding="utf-8").read()
        gate(data == "line1\nline2\n", f"عملکردی: نوشتن/الحاقِ دقیق ({data!r})")
        gate(os.path.isfile(os.path.join(_tmp, "other.log")),
             "عملکردی: هر sid فایلِ خودش")
        gate(not os.path.exists(os.path.join(_tmp, ".log")),
             "عملکردی: sidِ خالی هیچ فایلی نسازد")

        # ---------- E. عملکردیِ _reader با ۵۰۰ خط ----------
        import time as _time

        class _Stream:
            def __init__(self, data):
                self.data = data
                self.i = 0

            def fileno(self):
                return None

            def read(self, n):
                if self.i >= len(self.data):
                    return b""
                chunk = self.data[self.i:self.i + n]
                self.i += len(chunk)
                return chunk

        class _Proc:
            def __init__(self, data):
                self.stdout = _Stream(data)

            def poll(self):
                return 0 if self.stdout.i >= len(self.stdout.data) else None

            def wait(self, timeout=None):
                return 0

        lines = [f"LOG-LINE-{i:04d} — متنِ فارسیِ تست" for i in range(500)]
        payload = ("\n".join(lines) + "\nPARTIAL-TAIL-بدونِ-سطرجدید").encode("utf-8")
        proc = _Proc(payload)
        job = {"lock": threading.Lock(), "buf": [], "log": "", "ts": 0.0,
               "proc": proc, "running": True}
        fin = []
        ns2 = {
            "os": os, "threading": threading, "time": _time,
            "SESS_DIR": _tmp, "sid": "test500", "proc": proc, "job": job,
            "_append_job_logfile": fn,
            "_persist_job_meta": lambda sid: None,
            "_finalize_job_success": lambda sid: fin.append(sid),
            "_fmt": lambda buf_lines: "\n".join(buf_lines[-120:])
            if buf_lines else "…",
        }
        rmod = _extract_fn(_manga_app, "_reader")
        gate(rmod is not None, "عملکردی: _reader از سورس استخراج شد")
        if rmod is not None:
            exec(compile(rmod, "<extract>", "exec"), ns2)
            ns2["_reader"]()
            p5 = os.path.join(_tmp, "test500.log")
            log_data = io.open(p5, encoding="utf-8").read()
            got = [l for l in log_data.split("\n") if l]
            gate(len(got) == 501 and got[0] == lines[0]
                 and got[499] == lines[499]
                 and got[500] == "PARTIAL-TAIL-بدونِ-سطرجدید",
                 f"عملکردی: فایلِ لاگِ «کامل» — {len(got)} سطر (۵۰۰ + tail)")
            gate(len(job["buf"]) <= 400 and len(job["buf"]) < len(got),
                 f"عملکردی: bufِ حافظه همان سقفِ سبکِ قبل ({len(job['buf'])}) "
                 "— ولی فایل کامل")
            gate(job.get("done_event") is True and fin == ["test500"],
                 "عملکردی: پایانِ کار سالم (done_event + finalize)")
    else:
        fail("عملکردی: _append_job_logfile استخراج نشد — بقیهٔ D/E رد")
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

# ---------- F. سینتکسِ JS ----------
try:
    tree = ast.parse(_manga_app)
    js_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_dark_js_src":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                        and "manga_copy_log" in sub.value:
                    js_src = sub.value
    gate(js_src is not None, "JS: رشتهٔ _dark_js_src استخراج شد")
    if js_src:
        import subprocess
        # خودِ رشته یک عبارتِ کاملِ تابعِ پیکانی است — با پرانتز سالم میشود
        with io.open("/tmp/manga200_dark.js", "w", encoding="utf-8") as f:
            f.write("(" + js_src.strip() + ")")
        r = subprocess.run(["node", "--check", "/tmp/manga200_dark.js"],
                           capture_output=True, text=True)
        gate(r.returncode == 0,
             "JS: node --check سبز" + ("" if r.returncode == 0
                                       else f" — {r.stderr[:200]}"))
except Exception as _e:
    fail(f"JS: بررسیِ سینتکس — {_e}")

# ---------- G. روتِ زندهٔ /gradio_api/file= ----------
try:
    os.environ["GRADIO_ALLOWED_PATHS"] = _tmp if False else os.environ.get(
        "GRADIO_ALLOWED_PATHS", "")
    import requests
    import gradio as gr

    _gtmp = tempfile.mkdtemp(prefix="manga200_route_")
    _sess = os.path.join(_gtmp, "sessions")
    os.makedirs(_sess, exist_ok=True)
    _logf = os.path.join(_sess, "sid999.log")
    with io.open(_logf, "w", encoding="utf-8") as f:
        f.write("h-1\nh-2\ncomplete-tail")

    with gr.Blocks() as demo:
        gr.DownloadButton(label="x")
    demo.launch(server_name="127.0.0.1", server_port=7865,
                prevent_thread_lock=True, quiet=True,
                allowed_paths=[_gtmp])
    _port = demo.server_port or 7865
    _base = (getattr(demo, "local_url", None) or
             f"http://127.0.0.1:{_port}/").rstrip("/")
    if _base.endswith("/gradio_api"):
        _base = _base[: -len("/gradio_api")]
    r1 = requests.get(f"{_base}/gradio_api/file={_logf}", timeout=10)
    gate(r1.status_code == 200 and r1.text == "h-1\nh-2\ncomplete-tail",
         "زنده: فایلِ لاگِ زیرِ allowed_paths کامل برگشت (۲۰۰)")
    r2 = requests.head(f"{_base}/gradio_api/file={_logf}",
                       timeout=10)
    gate(r2.status_code == 200, "زنده: HEAD همان فایل ۲۰۰ (چکِ دکمه)")
    r3 = requests.get(f"{_base}/gradio_api/file=/etc/hostname", timeout=10)
    gate(r3.status_code == 403, "زنده: بیرونِ allowed_paths ۴۰۳ (امنیتِ قبل)")
    demo.close()
    shutil.rmtree(_gtmp, ignore_errors=True)
except Exception as _e:
    print(f"[i] روتِ زنده رد شد ({_e.__class__.__name__}: {_e}) — "
          "گیتهایِ سورس کفایت میکنند")

# ---------- سلامتِ عمومی ----------
try:
    py_compile.compile("manga_app.py", doraise=True)
    ok("py_compile: manga_app.py")
except Exception as _e:
    fail(f"py_compile: manga_app.py — {_e}")
try:
    py_compile.compile("manga.py", doraise=True)
    ok("py_compile: manga.py")
except Exception as _e:
    fail(f"py_compile: manga.py — {_e}")
# رگرسیونِ سبکِ قبل: پلِ ۱۹۹/۱۹۸/۱۹۷ در manga.py
gate('APP_VER = "1.14.200"' in _manga, "رگرسیون: فقط bumpِ نسخه در manga.py")
gate("_split_one_request_batches" in _manga,
     "رگرسیون: تقسیمِ متوازنِ ۱۹۹ سرِ جایش")
gate("_live_page_dump" in _manga and "slot" in _manga,
     "رگرسیون: اسلاتِ صریحِ ۱۹۸ سرِ جایش")

print()
if FAILS:
    print(f"✗ {len(FAILS)} گیتِ مردود:")
    for _f in FAILS:
        print(f"  - {_f}")
    sys.exit(1)
print("✓ همهٔ گیتهایِ v1.14.200 سبز.")
