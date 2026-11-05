# -*- coding: utf-8 -*-
"""تستِ واقعیِ بوتِ v1.14.220 — چیپهایِ «اسم + ✖»، دکمهٔ Importِ هماندازهٔ
بکاپ، دکمهٔ افزودنِ مستقل از custom، آکاردئونِ بستهٔ بکاپ."""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

PASS, FAIL = [], []


def chk(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✅ " if cond else "  ❌ ") + name + ((" — " + str(extra)[:120]) if extra and not cond else ""))


print("== ۱) بوتِ واقعیِ اپ ==")
port = 7921
proc = subprocess.Popen(
    [sys.executable, "manga_app.py"],
    env={**os.environ, "MANGA_APP_PORT": str(port), "MANGA_NO_BROWSER": "1"},
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
src = b""
t0 = time.time()
up = False
while time.time() - t0 < 90:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as r:
            src = r.read()
        up = True
        break
    except Exception:
        time.sleep(1)
chk("اپ بوت شد و صفحه بالا آمد", up)
if not up:
    proc.kill()
    print(proc.stdout.read().decode("utf-8", "ignore")[-3000:])
    sys.exit(1)

page = src.decode("utf-8", "ignore")
chk("APP_VER = 1.14.220 در صفحه", "1.14.220" in page)

print("== ۲) ساختارِ جدیدِ UI در HTMLِ رندرشده ==")
# v1.14.221 — ساختار عوض شد: ✖ِ حذف چسبیده به خودِ منویِ AI (بدونِ چیپ)
chk("ضربدرِ ✖ِ کنارِ منو (manga_cm_del_btn)", "manga_cm_del_btn" in page)
chk("چیپهایِ ۲۲۰ کلاً حذف شدند", ".cm-chips{" not in page and "cm-chip-n" not in page)
chk("جدولِ قدیمیِ cm-table کلاً حذف شد", "cm-table" not in page)
chk("لیستِ جداگانهٔ مدلها حذف شد (manga_cm_list) — ✖ فقط کنارِ منو",
    "manga_cm_list" not in page)
chk("منوی انتخاب AI (منوی انتخاب AI)", "منوی انتخاب AI" in page)
chk("دکمهٔ افزودن به لیست مدلها", "افزودن به لیست مدل\u200cها" in page or "افزودن به لیست مدل‌ها" in page)
chk("آکاردئونِ بستهٔ بکاپ", "بکاپ و بازیابی" in page)
chk("دکمهٔ بکاپ", "manga_backup_btn" in page)
chk("Import = UploadButton (manga_import_file)", "manga_import_file" in page)
chk("باکسِ بزرگِ قبلی (labelِ آپلودر) حذف شد",
    "بازیابیِ کامل از فایلِ بکاپ (JSON)" not in page)

print("== ۳) APIهایِ سرور (config) ==")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/config", timeout=10) as r:
        cfgp = json.loads(r.read())
    deps = json.dumps(cfgp.get("dependencies", []), ensure_ascii=False)
    api_names = set()
    for d in cfgp.get("dependencies", []):
        for ev in d.get("events", {}) or {}:
            for tr in (d["events"][ev] or []):
                if isinstance(tr, dict) and tr.get("js"):
                    continue
    # named routes در gradio 6 داخلِ config نیستند → از endpointها چک میکنیم
    chk("کانالِ cm_add (manga_cm_add_box) در config", "manga_cm_add_box" in deps)
    chk("کانالِ قدیمیِ حذف (manga_cm_del_box) حذف شد — ✖ حالا خودِ دکمه است",
        "manga_cm_del_box" not in deps)
    chk("کانالِ بازیابیِ localStorage (manga_cm_restore) در config", "manga_cm_restore" in deps)
    chk("دامنهٔ API (manga_api_base) در config", "manga_api_base" in deps)
except Exception as e:
    chk("خواندنِ config", False, e)

# فراخوانیِ واقعیِ APIهایِ نامدار
import hashlib

def call_api(name, payload):
    body = json.dumps({"data": payload}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/gradio_api/call/{name}",
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        ev = json.loads(r.read()).get("event_id")
    with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/gradio_api/call/{name}/{ev}", timeout=30) as r:
        txt = r.read().decode("utf-8", "ignore")
    # SSE: «event: complete\ndata: [...]» — یونی‌کد escapeشده؛ پارس میکنیم
    for ln in txt.splitlines():
        if ln.startswith("data:"):
            try:
                return json.loads(ln[5:].strip())
            except Exception:
                return ln[5:].strip()
    return txt

print("== ۴) سرورِ سمتِ مدلها ==")
# نکته: Stateِ سمتِ سرور در فراخوانیِ API از مقدارِ اولیهٔ خودش (دیسک)
# میآید — پس تست روی «دلتا» است: بعد از افزودن باید تستA باشد و بعد از
# حذف نباشد (بقیهٔ لیست مهم نیست).
try:
    out = call_api("cm_add", [json.dumps({"name": "تستA", "api_base": "https://x.example/v1",
                                          "api_key": "k12345678", "model": "m-1"},
                                         ensure_ascii=False), [], "auto"])
    outs = json.dumps(out, ensure_ascii=False)
    chk("cm_add مدل را ثبت کرد (JSONِ مرورگر برگشت)",
        "تستA" in outs, outs[:200])
    try:
        out = call_api("cm_del_row", ["تستA", [], "auto"])
        ok_del = False
    except Exception:
        ok_del = True
    chk("cm_del_row حذف شد — جایگزین: cm_del_sel (✖ِ کنارِ منو)", ok_del)
except Exception as e:
    chk("APIهایِ مدلها", False, str(e)[:200])

print("== ۵) منطقِ resolve (وبسمتِ پایتون) ==")
import importlib
ma = importlib.import_module("manga_app")
ch = ma._ai_choices([{"name": "مدلِ من"}, {"name": "auto"}, {"name": "gemini"}])
chk("ترتیبِ منو: auto|gemini|مدلها|custom",
    ch == ["auto", "gemini", "مدلِ من", "custom"], ch)
r = ma.resolve_ai_named([{"name": "مدلِ من", "api_base": "https://b/v1",
                          "api_key": "k", "model": "m"}], "مدلِ من", "pk", "pm")
chk("resolveِ مدلِ نامی → custom با فیلدهایِ خودش",
    r and r[0] == "custom" and r[1] == "https://b/v1" and r[2] == "k" and r[3] == "m", r)
chk("_render_models_html در ۲۲۱ حذف شد (✖ = دکمهٔ کنارِ منو، نه HTML)",
    not hasattr(ma, "_render_models_html"))
chk("_ai_choices بدونِ مدل: gemini|custom (بدونِ auto — دستورِ ۲۲۱)",
    ma._ai_choices([]) == ["gemini", "custom"], ma._ai_choices([]))

proc.kill()
proc.wait(timeout=10)

print(f"\nنتیجه: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
print("همه سبز ✅")
