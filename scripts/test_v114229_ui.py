#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ بوتِ UIِ v1.14.229 — دراپ‌داونِ مدل + دکمهٔ ↻ بدون اجرای سرور.
gr.Blocks.launch موقتاً no-op میشود؛ run_web کلِ رابط را میسازد و
ساختار (دراپ‌داون/دکمه/api) از دموگرِ ساختهشده چک میشود."""
import contextlib
import io as _io
import os
import sys

ROOT = "/home/z/my-project/Manga-AutoTranslate"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ["MANGA_WEB"] = "1"
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

PASS = FAIL = 0


def chk(name, cond, extra=""):
    global PASS, FAIL
    print(("  ✔ " if cond else "  ✘ ") + name + (f"  {extra}" if not cond else ""))
    if cond:
        PASS += 1
    else:
        FAIL += 1


src = open(os.path.join(ROOT, "manga_app.py"), encoding="utf-8").read()
chk("A: دراپ‌داونِ مدل با allow_custom_value", "allow_custom_value=True" in src
    and 'elem_id="manga_model"' in src and "gr.Dropdown(" in src)
chk("B: دکمهٔ ↻ مدلها هست", 'elem_id="manga_model_ref"' in src)
chk("C: api_name refresh_models ثبت شده", 'api_name="refresh_models"' in src)
chk("D: list_provider_models از manga میآید",
    "from manga import list_provider_models" in src)
chk("E: resolve_ai_named با ۴ خروجی آنپک میشود", "_p, _b, _k, _m = _nm" in src)
chk("F: فونتِ سیستم = Sahel-Bold",
    '("system",       "Sahel-Bold.ttf"' in src or
    '("system", "Sahel-Bold.ttf"' in src)
_n_vc = src.count("Vazir-Code")
chk("G: Vazir-Code فقط در کامنتِ توضیح (نه باندل/نه پیشفرض)", _n_vc <= 2,
    f"count={_n_vc}")

# ── بوتِ واقعی: launch → no-op؛ run_web همهٔ رابط را میسازد ──
import gradio as gr  # noqa: E402

CAPTURED = {}


def _fake_launch(self, *a, **k):
    CAPTURED["demo"] = self
    # prevent_event_loop: هیچ سروری بالا نمیآید
    return (None, None, None)


gr.Blocks.launch = _fake_launch

import manga_app  # noqa: E402

err = ""
try:
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        manga_app.run_web()
except SystemExit:
    pass
except Exception as e:
    err = f"{type(e).__name__}: {str(e)[:140]}"

demo = CAPTURED.get("demo")
chk("H: Blocks بدونِ خطا ساخته شد", demo is not None and not err, err)
if demo is not None:
    try:
        deps = (getattr(demo, "config", None) or {}).get("dependencies", [])
        names = {str((b or {}).get("api_name") or "") for b in deps}
        chk("I: apiهایِ refresh_models ثبت شد", "refresh_models" in names,
            f"found={sorted(n for n in names if n and not n.startswith('lambda'))[:14]}")
    except Exception as e:
        chk("I: apiها خوانده نشد (نادیده)", False, str(e)[:100])
else:
    chk("I: apiها (دمو نیست)", False, "")

print(f"\n═══ ui-boot: {PASS} ✔ / {FAIL} ✘ ═══")
sys.exit(1 if FAIL else 0)
