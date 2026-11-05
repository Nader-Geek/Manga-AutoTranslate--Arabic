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
chk("چیپها: کلاس cm-chips در CSS", ".cm-chips{" in page)
chk("چیپ: کلاس cm-chip + نامِ بولد (cm-chip-n)", "cm-chip-n" in page)
chk("ضربدرِ ✖ با data-name (رویدادِ حذف)", "cm-x" in page and "data-name" in page)
chk("جدولِ قدیمیِ cm-table کلاً حذف شد", "cm-table" not in page)
chk("لیستِ مدلها elem_id=manga_cm_list (زیرِ منوی AI)", "manga_cm_list" in page)
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
    chk("کانالِ حذفِ ✖ (manga_cm_del_box) در config", "manga_cm_del_box" in deps)
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
    chk("cm_add مدل را ثبت کرد (چیپِ رندرشده برگشت)",
        "تستA" in outs and "cm-chip" in outs, outs[:200])
    out = call_api("cm_del_row", ["تستA", [], "auto"])
    outs = json.dumps(out, ensure_ascii=False)
    chk("cm_del_row حذف کرد (تستA دیگر در چیپها نیست)",
        "تستA" not in outs and "cm-chip" in outs, outs[:200])
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
html = ma._render_models_html([{"name": "الف", "model": "m", "api_base": "b", "api_key": "x"}])
chk("چیپِ رندرشده شاملِ نام + ✖ کنارِ هم است",
    "cm-chip" in html and "cm-x" in html and "الف" in html and "✖" in html, html[:150])
chk("در چیپ، ضربدر بعد از نام میآید (کنارِ هم)",
    html.find("الف") < html.find("cm-x"))

proc.kill()
proc.wait(timeout=10)

print(f"\nنتیجه: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
print("همه سبز ✅")
