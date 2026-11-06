# -*- coding: utf-8 -*-
"""تستِ v1.14.224 — (۱) کشِ صفحه با لینکِ بلند در وبِ PC/لینوکس: خطِ
مشخصاتِ مدلِ ذخیرهشده (#manga_cm_info) با overflow-wrap:anywhere میشکند
و دیگر صفحه را پهن نمیکند — دستورِ سازنده: «تو وب لینوکس پی سی لینک مدل
بزرگ باشه صفحه بزرگ تر میشه اینو درست کن بعد قسمت میگن لینک بلند باشه
کش میده» + (۲) ریشهٔ «وقتی دکمه ویرایش میزنم شکل نمایش کلید نمیاد تو
Gemini میاد ولی تو کاستوم خودم نمیاد»: gradio وقتی ردیفِ کلید پنهان/
آشکار میشود (انتخابِ مدلِ ذخیرهشده → ✎ ویرایش) فیلد را از DOM میبرد و
دوباره میسازد؛ آبسرورِ چسبیدهبه خودِ فیلد با فیلدِ قدیمی میمیرد → حالا
آبسرور همیشه به body وصل است (هرگز از DOM نمیافتد) — گوشیِ اندروید
طبقِ سازنده اوکیه و دست نخورده."""
import json
import os
import re
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
    print(("  OK " if cond else "  XX ") + name
          + ((" — " + str(extra)[:200]) if extra and not cond else ""))


SRC = open(os.path.join(ROOT, "manga_app.py"), encoding="utf-8").read()

print("== 1) source: لینکِ بلند صفحه را کش نمیدهد (CSS) ==")
chk("overflow-wrap:anywhere رویِ #manga_cm_info و .hint",
    "overflow-wrap: anywhere !important" in SRC
    and "#manga_cm_info, #manga_cm_info *" in SRC
    and ".hint, .hint *" in SRC)
chk("word-break:break-word همراهِ anywhere",
    "word-break: break-word !important" in SRC)
chk("max-width:100% برایِ جلوگیری از پهناشدن",
    "max-width: 100% !important" in SRC)
chk("code با white-space:normal (لینک داخلِ <code> میشکند)",
    "#manga_cm_info code, .hint code { white-space: normal !important; }"
    in SRC)
# نظمِ CSS: قانونِ تازه بعد از تعریفِ .hint باشد
i_hint = SRC.find(".hint { color:")
i_wrap = SRC.find("overflow-wrap: anywhere !important")
chk("قانونِ تازه در بخشِ CSSِ همین صفحه (بعدِ .hint)", 0 < i_hint < i_wrap)

print("== 2) source: ریشهٔ 👁ِ گمشده در ویرایش (آبسرورِ body) ==")
chk("آبسرور همیشه به document.body وصل است",
    "window.__mangaEyeObs.observe(document.body," in SRC)
chk("رصدِ subtree کاملِ body",
    "{ childList: true, subtree: true }" in SRC)
chk("رشتهٔ قدیمیِ ریشهٔ فیلدی فقط در بلوکِ چشم حذف شد (observeِ لاگِ زنده مستقل است)",
    'document.getElementById("manga_api_keys") || document.body'
    not in SRC)
chk("debounce با requestAnimationFrame (بدونِ قفلشدنِ مرورگر)",
    "requestAnimationFrame" in SRC and "let pend = false;" in SRC)
chk("attachEye هنوز همان میزبانِ input-container است",
    'inp.closest(".input-container")' in SRC)
chk("تایمرهایِ اتصالِ اولیه سرِ جایشان",
    "[300, 800, 1500, 3000, 5000].forEach((t) => setTimeout(attachEye, t))"
    in SRC)

print("== 3) source: رگرسیونِ ۲۲۳ (ویرایش + کلیدِ مخفی + ✖) ==")
chk("api_keys هنوز type=password سمتِ سرور", 'type="password", scale=3,' in SRC)
chk("cm_edit / cm_save_edits سرِ جایشان",
    'api_name="cm_edit"' in SRC and 'api_name="cm_save_edits"' in SRC)
chk("قابِ .styler شفاف (فیکسِ ✖ِ کشیده)",
    "div.styler{background:transparent !important" in SRC)
chk("✖ همچنان ۳۰×۳۰",
    "width:30px !important;height:30px !important" in SRC
    and "max-height:30px !important" in SRC)

print("== 4) version ==")
chk("APP_VER = 1.14.224", 'APP_VER = "1.14.224"' in SRC)
chk("VERSION file 1.14.224 / 228", "versionName=1.14.224" in open(
    os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
    and "versionCode=228" in open(os.path.join(ROOT, "VERSION"),
                                  encoding="utf-8").read())
GRADLE = open(os.path.join(ROOT, "android/app/build.gradle.kts"),
              encoding="utf-8").read()
chk("gradle 1.14.224 / 228",
    'versionName = "1.14.224"' in GRADLE and "versionCode = 228" in GRADLE)

print("== 5) node --check رویِ client_restore_js (شاملِ آبسرورِ تازه) ==")
try:
    m = re.search(r'client_restore_js = f"""\n(.*?)\n"""', SRC, re.S)
    tpl = m.group(1)
    tpl = tpl.replace('{JOB_KEY}', 'manga_job_v1')
    tpl = tpl.replace('{LS_KEY}', 'manga_autotranslate_form_v2')
    tpl = tpl.replace('{SESSION_TTL * 1000}', '1800000')
    tpl = tpl.replace('{_perm_js}', 'const PERM=1;')
    js = tpl.replace('{{', '{').replace('}}', '}')
    open("/tmp/cr224.js", "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", "--check", "/tmp/cr224.js"],
                       capture_output=True, timeout=30)
    chk("client_restore_js سالم است (node --check)", r.returncode == 0,
        r.stderr.decode()[:200])
except Exception as e:
    chk("client_restore_js سالم است (node --check)", False, e)

print("== 6) boot + real API (رگرسیونِ ویرایش/ذخیره با لینکِ بلند) ==")

MODELS_PATH = os.path.join(ROOT, "workspace", "manga_models.json")
LONG_URL = ("https://api.cloudflare.com/client/v4/accounts/"
            "587bd99e8413d8bc59b05082a6e667a6/ai/v1/chat/completions")
SEED = [{"name": "deepseek-v4.1-flash:free", "api_base": LONG_URL,
         "api_key": "thk_live_11char-9JYS", "model": "deepseek-v4.1-flash:free"}]


def boot(port):
    proc = subprocess.Popen(
        [sys.executable, "manga_app.py"],
        env={**os.environ, "MANGA_APP_PORT": str(port), "MANGA_NO_BROWSER": "1"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 90:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/",
                                        timeout=3) as r:
                return proc, r.read()
        except Exception:
            time.sleep(1)
    proc.kill()
    print(proc.stdout.read().decode("utf-8", "ignore")[-3000:])
    sys.exit(1)


def call_api(name, payload, port, timeout_req=25):
    body = json.dumps({"data": payload}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/gradio_api/call/{name}",
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_req) as r:
        ev = json.loads(r.read()).get("event_id")
    with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/gradio_api/call/{name}/{ev}",
            timeout=40) as r:
        txt = r.read().decode("utf-8", "ignore")
    for ln in txt.splitlines():
        if ln.startswith("data:"):
            try:
                return json.loads(ln[5:].strip())
            except Exception:
                return ln[5:].strip()
    return None


os.makedirs(os.path.dirname(MODELS_PATH), exist_ok=True)
json.dump(SEED, open(MODELS_PATH, "w", encoding="utf-8"),
          ensure_ascii=False)
port = 7932
proc, page = boot(port)
try:
    out = call_api("toggle_custom_base",
                   ["deepseek-v4.1-flash:free", SEED,
                    {"_last": "gemini"}, "", "", ""], port)
    ok = isinstance(out, list) and len(out) == 11
    chk("toggle رویِ مدلِ لینکبلند: ۱۱ خروجی", ok, out)
    if ok:
        info = str(out[6].get("value", ""))
        chk("خطِ مشخصات: لینکِ بلند داخلش هست", LONG_URL in info, info[:160])
        chk("خطِ مشخصات: کلیدِ ماسکشده", "thk_l…9JYS" in info
            or "…" in info, info[:160])
        chk("ویرایش رویِ مدلِ خودت دیده میشود", out[9].get("visible") is True)

    out = call_api("cm_edit", ["deepseek-v4.1-flash:free", SEED], port)
    ok = isinstance(out, list) and len(out) == 8
    chk("cm_edit: ۸ خروجی", ok, out)
    if ok:
        chk("cm_edit: لینکِ بلند در فیلد پیشپر میشود",
            out[0].get("value") == LONG_URL, out[0])
        chk("cm_edit: کلید برایِ ویرایش میآید",
            out[2].get("value") == "thk_live_11char-9JYS", out[2])

    out = call_api("cm_save_edits",
                   ["deepseek-v4.1-flash:free", SEED, LONG_URL,
                    "thk_new_9999", "deepseek-v4.1-flash:free"], port)
    ok = isinstance(out, list) and len(out) == 14
    chk("cm_save_edits: ۱۴ خروجی", ok, out)
    if ok:
        chk("cm_save_edits: پیامِ ✅ با لینکِ بلند",
            "ذخیره شد" in str(out[13].get("value", ""))
            and LONG_URL in str(out[13].get("value", "")), out[13])
        chk("cm_save_edits: مشخصاتِ تازه زیرِ منو",
            LONG_URL in str(out[4].get("value", "")), out[4])
finally:
    proc.kill()
    proc.wait(timeout=10)
    try:
        os.remove(MODELS_PATH)
    except Exception:
        pass

print(f"\nresult: {len(PASS)} green / {len(FAIL)} red")
if FAIL:
    print("reds:", FAIL)
    sys.exit(1)
print("all green")
