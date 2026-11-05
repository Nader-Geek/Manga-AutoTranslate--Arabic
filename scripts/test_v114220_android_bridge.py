# -*- coding: utf-8 -*-
"""تستِ سمتِ اندرویدِ v1.14.220 — resolveِ auto/مدلِ نامی در bridge +
ساختارِ manifest (منویِ provider با auto، بکاپِ بومی، چیپها)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "android", "app", "src", "main", "python"))
sys.path.insert(0, ROOT)
os.environ.setdefault("MANGA_FILES_DIR", "/tmp/manga_files_test_220")
os.makedirs(os.environ["MANGA_FILES_DIR"], exist_ok=True)

PASS, FAIL = [], []


def chk(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + ((" — " + str(extra)[:150]) if extra and not cond else ""))


import bridge  # noqa: E402

print("== ۱) resolveِ «مدلِ نامی» ==")
p = {"provider": "Kk", "keys": "pagekey", "model": "pagemodel",
     "api_base": "pagebase",
     "custom_models": json.dumps([{"name": "Kk", "api_base": "https://x/v1",
                                   "api_key": "kk-key", "model": "ds-flash"}])}
keys = bridge._resolve_auto_or_named(p, ["pagekey"], lambda m: None)
chk("provider → custom", p["provider"] == "custom", p)
chk("api_base از خودِ مدل", p["api_base"] == "https://x/v1", p)
chk("کلید از خودِ مدل", keys == ["kk-key"], keys)
chk("مدل از خودِ مدل", p["model"] == "ds-flash", p)

print("== ۲) resolveِ «auto» با probeِ ساختگی ==")
calls = []


def fake_probe(key, prov, base, model=None):
    calls.append((prov, base, model))
    if prov == "custom":
        return [{"ok": True}]
    return [{"ok": False, "error": "no gemini key"}]


bridge._manga = lambda: types.SimpleNamespace(test_api_keys=fake_probe)
import types  # noqa: E402
p2 = {"provider": "auto", "keys": "", "model": "", "api_base": "",
      "custom_models": [{"name": "مدل۲", "api_base": "https://y/v1",
                         "api_key": "y-key", "model": "m2"}]}
lines = []
keys2 = bridge._resolve_auto_or_named(p2, [], lambda m: lines.append(str(m)))
chk("auto: gemini رد شد → مدلِ کاربر انتخاب شد",
    p2["provider"] == "custom" and p2["api_base"] == "https://y/v1", p2)
chk("auto: لاگِ مراحل آمده", any("auto" in l for l in lines), lines)

print("== ۳) resolveِ «auto» بدونِ هیچ مدلی ==")
p3 = {"provider": "auto", "keys": "", "model": "", "api_base": "",
      "custom_models": "[]"}


def probe3(key, prov, base, model=None):
    return [{"ok": False, "error": "x"}]


bridge._manga = lambda: types.SimpleNamespace(test_api_keys=probe3)
bridge._resolve_auto_or_named(p3, [], lambda m: None)
chk("autoِ خالی → geminiِ فالبک (نه providerِ «auto»)",
    p3["provider"] == "gemini", p3)

print("== ۴) مدلِ نامیِ غایب ==")
p4 = {"provider": "ناموجود", "keys": "k", "model": "", "api_base": "",
      "custom_models": "[]"}
bridge._resolve_auto_or_named(p4, ["k"], lambda m: None)
chk("ناموجود → gemini با کلیدِ صفحه", p4["provider"] == "gemini", p4)

print("== ۵) manifestِ اندروید ==")
mf = json.loads(bridge.manifest())
chk("app_ver = 1.14.220", mf.get("app_ver") == "1.14.220", mf.get("app_ver"))
prov = None
bak = None
for s in mf.get("sections", []):
    for f in s.get("fields", []):
        if f.get("id") == "provider":
            prov = f
        if "بکاپ" in s.get("title", ""):
            bak = s
chk("منویِ provider: auto اول است",
    prov and prov.get("choices") and prov["choices"][0][0] == "auto", prov)
chk("منویِ provider: ترتیبِ auto|gemini|custom (مدلها را MainActivity میگذارد)",
    prov and [c[0] for c in prov["choices"]] == ["auto", "gemini", "custom"], prov)
# v1.14.221 — پیشفرضِ provider پویا شد (مدل داشته باشی = auto، نباشد =
# gemini)؛ در MainActivity هم refreshProviderBtn همین را نرمال میکند.
chk("پیشفرضِ provider پویاست (None/«auto»/«gemini») و نرمالسازی با MainActivity",
    prov and prov.get("default") in (None, "auto", "gemini"),
    (prov or {}).get("default"))
chk("api_base فقط رویِ custom دیده شود",
    any(f.get("id") in ("manga_api_base", "api_base")
        and f.get("visible_if", {}).get("equals") == "custom"
        for s in mf.get("sections", []) for f in s.get("fields", [])))
chk("بخشِ بکاپ: باکسِ بزرگِ manga_import_file در manifest نیست (UploadButton استخراج نمیشود)",
    bak is not None and all(f.get("id") != "manga_import_file"
                            for f in bak.get("fields", [])), bak)

print(f"\nنتیجه: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
print("همه سبز ✅")
