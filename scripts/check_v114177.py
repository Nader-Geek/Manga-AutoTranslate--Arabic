# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.177 — «تنظیمهایِ آزمایشگاهِ سرعت حالا واقعاً اعمال میشوند»

باگِ 176: پنلِ «🧪 آزمایشگاه سرعت استخراج» نمایش داده میشد ولی:
  • اندروید: collect() در MainActivity.kt فقط کلیدهایِ هاردکدِ قدیمی را
    به پایتون میفرستاد → هر ۵ کلیدِ جدید (ocr_ep/ocr_ladder/ocr_threads/
    ocr_detcap/ocr_boost) دور ریخته میشد → speed_lab_env همیشه پیشفرض
    (لاگِ سازنده: «عوض میکنم عوض نمیکنه — میزارم رو ml kit بازم full»).
  • PC: run_translation این ۵ مقدار را نمیگرفت و _env هیچ envی ست
    نمیکرد → زیرپروسهِ manga.py بیخبر بود.

ساختارِ چک: گیتهایِ استاتیک در همین پروسه (فایل/AST — سبک)؛ تستهایِ
دینامیک (importِ manga و rapidocr_mobile) در «زیرپروسه» اجرا میشوند تا
هیچ وحشِ وارداتیِ سنگین پروسهٔ چک را در خروج نگه ندارد.
"""
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FAILS = []


def fail(msg):
    FAILS.append(msg)
    print("[x] %s" % msg)


def ok(msg):
    print("[+] %s" % msg)


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


LAB_KEYS = ["ocr_ep", "ocr_ladder", "ocr_threads", "ocr_detcap", "ocr_boost"]

# ---------------------------------------------------------------- V) نسخه
ver = read("VERSION")
manga_src = read("manga.py")
mcode = re.search(r"versionCode=(\d+)", ver)
mname = re.search(r"versionName=([\d.]+)", ver)
m = re.search(r'APP_VER\s*=\s*"([^"]+)"', manga_src)
if not (mcode and mname and m):
    fail("VERSION/APP_VER ناقص است")
elif m.group(1) != mname.group(1):
    fail("APP_VER(%s) != versionName(%s)" % (m.group(1), mname.group(1)))
else:
    ok("نسخه: %s / versionCode=%s (سازگار)"
       % (mname.group(1), mcode.group(1)))
# ------------------------------------------------------- K) اندروید collect
kt = read("android/app/src/main/java/com/amirwolf/mangatranslator/MainActivity.kt")
m = re.search(r"private fun collect\(\): JSONObject \{.*?\n    \}", kt, re.S)
if not m:
    fail("collect() در MainActivity.kt پیدا نشد")
else:
    blk = m.group(0)
    if 'map.put("ocr_speedtest", optBool(o, "ocr_speedtest"))' not in blk:
        fail("collect(): پاسِ ocr_speedtest غایب است")
    oldk = [k for k in LAB_KEYS if ('"%s"' % k) in blk]
    if oldk:
        fail("collect(): کلیدهایِ کهنهٔ lab هنوز هستند: %s" % oldk)
    pos_val = blk.find('if (id !in o.keysIteratorAsList())')
    pos_st = blk.find('map.put("ocr_speedtest"')
    if pos_val < 0 or pos_st < 0 or pos_st < pos_val:
        fail("collect(): پاسِ ocr_speedtest باید بعد از بازیابیِ values باشد")
    if 'speedTestSent = p.optBoolean("ocr_speedtest", false)' not in kt:
        fail("onStartJob: ضبطِ speedTestSent غایب است")
    if 'values.remove("ocr_speedtest")' not in kt \
            or 'putString("ocr_speedtest", "false")' not in kt:
        fail("پایانِ کار: خاموشیِ خودکارِ کلید نیست")
    if not FAILS:
        ok("collect(): فقط ocr_speedtest + خاموشیِ خودکار بعد از done")
# -------------------------------------------------------------- P) PC سیمکشی
app = read("manga_app.py")
sig = re.search(r"def run_translation\(.*?\*tone_args\):", app, re.S)
if not sig:
    fail("امضای run_translation پیدا نشد")
else:
    if "ocr_speedtest_v" not in sig.group(0):
        fail("run_translation: پارامترِ ocr_speedtest_v غایب است")
    else:
        ok("run_translation: ocr_speedtest_v در امضا")
mm = re.search(r"inputs=\[session_id.*?\] \+ tone_uploads \+ tone_enables,",
               app, re.S)
if not mm:
    fail("inputsِ گرادیو پیدا نشد")
elif "ocr_speedtest" not in mm.group(0):
    fail("inputsِ گرادیو: ocr_speedtest غایب")
else:
    ok("inputsِ گرادیو: ocr_speedtest بعد از api_base")
env_blk = re.search(
    r"_env = os\.environ\.copy\(\).*?_env\[\"MANGA_LIVE_DIR\"\] = live_dir",
    app, re.S)
if not env_blk:
    fail("بلوکِ _env پیدا نشد")
else:
    b = env_blk.group(0)
    if '_env["MANGA_SPEED_TEST"] = "1"' not in b \
            or '_env.pop("MANGA_SPEED_TEST"' not in b:
        fail("_env: MANGA_SPEED_TEST set/pop غایب است")
    elif "ocr_speedtest_v" not in b:
        fail("_env: شرطِ ocr_speedtest_v غایب است")
    else:
        ok("_env: فقط MANGA_SPEED_TEST (برنده در speed_test.json اعمال میشود)")
    pos_env = app.find(env_blk.group(0))
    if app.find("proc = subprocess.Popen(", pos_env) < 0:
        fail("Popen بعد از _env پیدا نشد")
    else:
        ok("_env قبل از Popen ساخته میشود")

# X) قراردادِ env↔پنل در مبدأِ manga.py
mmode = re.search(r"_K3_MODES = \(([^)]*)\)", manga_src)
modes = [x.strip().strip('"\'') for x in mmode.group(1).split(",")] \
    if mmode else []
if modes != ["full", "fast", "mlkit", "rapid", "paddle"]:
    fail("X: _K3_MODES تغییر کرده: %r" % modes)
else:
    ok("X: _K3_MODES = ۵ حالتِ پنل (قراردادِ env↔پنل)")
mep = re.search(r'_SPEED_LAB_EP = \(([^)]*)\)', manga_src)
eps = [x.strip().strip('"\'') for x in mep.group(1).split(",")] if mep else []
if eps != ["auto", "nnapi", "xnnpack", "cpu"]:
    fail("X: _SPEED_LAB_EP تغییر کرده: %r" % eps)
elif 'MANGA_MOBILE_OCR_EP' not in manga_src:
    fail("X: MANGA_MOBILE_OCR_EP در manga.py نیست")
else:
    ok("X: _SPEED_LAB_EP = ۴ حالتِ پنل")

# ------------------------------------------- E) عملیِ پایتون — زیرپروسه
PY = sys.executable
e_code = r'''
import json, os, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.getcwd())
import manga
out = {}
keys = ("MANGA_MOBILE_OCR_EP", "MANGA_K3_MODE", "MANGA_OCR_THREADS",
        "MANGA_XNN_THREADS", "MANGA_CROP_DET_CAP", "MANGA_CROP_ENH_SCALE")
tmp = tempfile.mkdtemp(prefix="lab177_")
os.environ["MANGA_FILES_DIR"] = tmp
stf = os.path.join(tmp, "speed_test.json")


def clean():
    for k in keys:
        os.environ.pop(k, None)


def nofile():
    try:
        os.remove(stf)
    except OSError:
        pass


# E1 — بدونِ نتیجه → پیشفرض + پاکسازی (کلیدهایِ کهنهٔ سوییچها هم)
clean()
os.environ["MANGA_OCR_THREADS"] = "8"
os.environ["MANGA_CROP_ENH_SCALE"] = "1.0"
nofile()
out["E1_line"] = manga.speed_lab_env({})
out["E1_env"] = {k: os.environ.get(k) for k in keys}
# E2 — برندهٔ فایل → env
clean()
with open(stf, "w", encoding="utf-8") as f:
    json.dump({"ladder": "mlkit", "ep": "cpu",
               "ladder_ms": {"mlkit": 90}}, f)
out["E2_line"] = manga.speed_lab_env({})
out["E2_env"] = {k: os.environ.get(k) for k in keys}
# E3 — نامعتبر → فالبکِ امن
clean()
with open(stf, "w", encoding="utf-8") as f:
    json.dump({"ladder": "hmm", "ep": "blah"}, f)
out["E3_line"] = manga.speed_lab_env({})
out["E3_env"] = (os.environ.get("MANGA_MOBILE_OCR_EP"),
                 os.environ.get("MANGA_K3_MODE"))
print("JSON_BEGIN" + json.dumps(out, ensure_ascii=False) + "JSON_END")
'''
try:
    r = subprocess.run([PY, "-c", e_code], capture_output=True, text=True,
                       timeout=240, cwd=ROOT)
    mm2 = re.search(r"JSON_BEGIN(.*)JSON_END", r.stdout, re.S)
    if mm2 is None:
        fail("E: زیرپروسه خروجی JSON نداد. stderr انتهایی: "
             + (r.stderr or "")[-400:])
    else:
        d = json.loads(mm2.group(1))
        if any(d["E1_env"][k] is not None for k in d["E1_env"]) \
                or "پیشفرض" not in d["E1_line"]:
            fail("E1: بدونِ نتیجه باید پاکسازی + پیشفرض: %r" % d["E1_env"])
        else:
            ok("E1: بدونِ نتیجه → پاکسازیِ کامل + پیشفرض (کلیدهایِ کهنه هم)")
        if d["E2_env"]["MANGA_K3_MODE"] != "mlkit" \
                or d["E2_env"]["MANGA_MOBILE_OCR_EP"] != "cpu" \
                or "برندهٔ" not in d["E2_line"]:
            fail("E2: برندهٔ فایل باید env شود: %r / %s"
                 % (d["E2_env"], d["E2_line"]))
        else:
            ok("E2: برندهٔ speed_test.json → env + خطِ برنده")
        if tuple(d["E3_env"]) != (None, None) \
                or "برندهٔ" not in d["E3_line"]:
            fail("E3: نامعتبر باید فالبکِ امن شود: %r" % (d["E3_env"],))
        else:
            ok("E3: نامعتبر → فالبکِ امن (auto/full)")
except subprocess.TimeoutExpired:
    fail("E: زیرپروسه تایم‌اوت شد")
except Exception as e:
    fail("E: %s: %s" % (type(e).__name__, e))
# ------------------------------- N) گاردِ NNAPI — زیرپروسه
n_code = r'''
import json, os, sys, time, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), "android", "app", "src",
                                "main", "python"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "rpm177", os.path.join(os.getcwd(), "android", "app", "src", "main",
                           "python", "rapidocr_mobile", "__init__.py"))
rpm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rpm)

tmp = tempfile.mkdtemp(prefix="lab177_")
det = os.path.join(tmp, "det.onnx"); rec = os.path.join(tmp, "rec.onnx")
open(det, "wb").write(b"x"); open(rec, "wb").write(b"x")
gp = rpm._nnapi_guard_path(tmp)
out = {}

rpm._android_env = lambda: True
rpm._x86_machine = lambda: False
rpm._avail_eps = lambda: ["NnapiExecutionProvider",
                          "XnnpackExecutionProvider"]
rpm._ep_gate_ensure = lambda *a, **k: {
    "NnapiExecutionProvider": {"ok": True, "ms": 100.0},
    "XnnpackExecutionProvider": {"ok": True, "ms": 900.0}}
rpm._xnn_threads = lambda: 4

def fresh_token():
    rpm._LAUNCH_TOKEN = "%d:%.6f" % (os.getpid(), time.time())

def seed_stale():
    rpm._EP_PLAN_CACHE = {"key": None, "plan": None}
    rpm._NNAPI_HINT = False; rpm._NNAPI_ACTIVE = False
    rpm._NNAPI_GUARD = None
    if os.path.isfile(gp): os.remove(gp)
    for k in ("MANGA_MOBILE_OCR_EP", "MANGA_EP_NO_PROBE"):
        os.environ.pop(k, None)
    with open(gp, "w", encoding="utf-8") as f:
        json.dump({"launch": "OLD:1.0",
                   "ver": os.environ.get("MANGA_APP_VER", "")}, f)
    fresh_token()

# N1 — auto + نشانِ کهنه → بدونِ NNAPI؛ نشان دستنخورده
seed_stale()
plan = rpm._ep_plan(det, rec)
out["N1_plan"] = plan[0]
out["N1_marker"] = json.load(open(gp))["launch"] if os.path.isfile(gp) else None

# N2 — همان وضعیت + انتخابِ صریحِ nnapi → نشانِ کهنه پاک + NNAPI برنده
seed_stale()
os.environ["MANGA_MOBILE_OCR_EP"] = "nnapi"
plan2 = rpm._ep_plan(det, rec)
out["N2_plan"] = plan2[0]
out["N2_active"] = bool(rpm._NNAPI_ACTIVE)
out["N2_marker_launch"] = json.load(open(gp))["launch"] \
    if os.path.isfile(gp) else None
out["N2_token"] = rpm._LAUNCH_TOKEN
print("JSON_BEGIN" + json.dumps(out) + "JSON_END")
'''
try:
    r = subprocess.run([PY, "-c", n_code], capture_output=True, text=True,
                       timeout=240, cwd=ROOT)
    mm3 = re.search(r"JSON_BEGIN(.*)JSON_END", r.stdout, re.S)
    if mm3 is None:
        fail("N: زیرپروسه خروجی JSON نداد. stderr انتهایی: "
             + (r.stderr or "")[-400:])
    else:
        d = json.loads(mm3.group(1))
        if d["N1_plan"] == "NnapiExecutionProvider":
            fail("N1: auto با نشانِ کهنه نباید NNAPI بدهد")
        elif d["N1_marker"] != "OLD:1.0":
            fail("N1: auto نباید نشانِ کهنه را تغییر دهد: %r"
                 % d["N1_marker"])
        else:
            ok("N1: auto + نشانِ کهنه → بدونِ NNAPI، نشان میماند (ضدِ حلقه)")
        if d["N2_marker_launch"] == "OLD:1.0":
            fail("N2: انتخابِ صریحِ nnapi باید نشانِ کهنه را عوض کند")
        elif d["N2_marker_launch"] != d["N2_token"]:
            fail("N2: نشانِ تازه باید شناسهٔ همین اجرا باشد: %r != %r"
                 % (d["N2_marker_launch"], d["N2_token"]))
        elif d["N2_plan"] != "NnapiExecutionProvider" or not d["N2_active"]:
            fail("N2: NNAPI باید برنده و فعال باشد: %r"
                 % {k: d[k] for k in ("N2_plan", "N2_active")})
        else:
            ok("N2: «فقط NNAPI» از پنل → نشانِ کهنه پاک + NNAPI برنده"
               " + نشانِ تازه (دکمهٔ تستِ دوباره)")
except subprocess.TimeoutExpired:
    fail("N: زیرپروسه تایم‌اوت شد")
except Exception as e:
    fail("N: %s: %s" % (type(e).__name__, e))

# ---------------------------------------------- U) استخراجِ فرمِ گوشی
try:
    sys.path.insert(0, os.path.join(ROOT, "android", "app", "src",
                                    "main", "python"))
    import extract_ui as eu

    fields = eu.extract("manga_app.py")
    found = {}
    for sec in ((fields or {}).get("sections") or []):
        for f in (sec.get("fields") or []):
            if isinstance(f, dict) and str(f.get("id", "")).startswith("ocr_"):
                found[f["id"]] = f
    if list(found.keys()) != ["ocr_speedtest"]:
        fail("U: پنل باید فقط ocr_speedtest را داشته باشد (دارد: %s)"
             % list(found.keys()))
    elif found["ocr_speedtest"].get("type") != "bool":
        fail("U: ocr_speedtest باید bool باشد")
    else:
        ok("U: extract_ui فقط دکمهٔ «تستِ سرعت» را میدهد (سوییچها حذف)")
except Exception as e:
    fail("U: %s: %s" % (type(e).__name__, e))

# W) راهنمایِ تستِ دوبارهٔ NNAPI = دکمهٔ «تستِ سرعت» (همهٔ پیامها همراستا)
if "⚡ تستِ سرعت" not in app:
    fail("W: دکمهٔ «تستِ سرعت» در manga_app نیست")
elif "«تستِ سرعت» را از پنلِ اپ اجرا کن" not in \
        read("android/app/src/main/python/rapidocr_mobile/__init__.py"):
    fail("W: پیامِ گاردِ NNAPI باید به «تستِ سرعت» اشاره کند")
else:
    ok("W: پیامِ گاردِ NNAPI = اجرایِ «تستِ سرعت» از پنل")

print("[✓] همهٔ گیتهایِ v1.14.177 PASS")
