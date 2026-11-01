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
if "versionCode=182" not in ver or "versionName=1.14.177" not in ver:
    fail("VERSION باید 182/1.14.177 باشد")
else:
    ok("VERSION: 182/1.14.177")
manga_src = read("manga.py")
m = re.search(r'APP_VER\s*=\s*"([^"]+)"', manga_src)
if not m or m.group(1) != "1.14.177":
    fail("APP_VER باید 1.14.177 باشد")
else:
    ok("APP_VER = 1.14.177")

# ------------------------------------------------------- K) اندروید collect
kt = read("android/app/src/main/java/com/amirwolf/mangatranslator/MainActivity.kt")
m = re.search(r"private fun collect\(\): JSONObject \{.*?\n    \}", kt, re.S)
if not m:
    fail("collect() در MainActivity.kt پیدا نشد")
else:
    blk = m.group(0)
    if 'listOf("ocr_ep", "ocr_ladder", "ocr_detcap")' not in blk:
        fail("collect(): پاسِ ocr_ep/ocr_ladder/ocr_detcap غایب است")
    if "map.put(\"ocr_threads\", o.optInt(\"ocr_threads\", 0))" not in blk:
        fail("collect(): ocr_threads با optInt پاس داده نمیشود")
    if "map.put(\"ocr_boost\", o.optBoolean(\"ocr_boost\", true))" not in blk:
        fail("collect(): ocr_boost با optBoolean پاس داده نمیشود")
    pos_val = blk.find('if (id !in o.keysIteratorAsList())')
    pos_lab = blk.find('listOf("ocr_ep", "ocr_ladder", "ocr_detcap")')
    if pos_val < 0 or pos_lab < 0 or pos_lab < pos_val:
        fail("collect(): بلوکِ lab باید بعد از بازیابیِ values باشد")
    if not FAILS:
        ok("collect(): هر ۵ کلیدِ lab با نوعِ درست، بعد از بازیابیِ values")

# -------------------------------------------------------------- P) PC سیمکشی
app = read("manga_app.py")
sig = re.search(r"def run_translation\(.*?\*tone_args\):", app, re.S)
if not sig:
    fail("امضای run_translation پیدا نشد")
else:
    miss = [k for k in ("ocr_ep_v", "ocr_ladder_v", "ocr_threads_v",
                        "ocr_detcap_v", "ocr_boost_v")
            if k not in sig.group(0)]
    if miss:
        fail("run_translation: پارامترهایِ غایب: %s" % miss)
    else:
        ok("run_translation: هر ۵ پارامترِ lab در امضا")

mm = re.search(r"inputs=\[session_id.*?\] \+ tone_uploads \+ tone_enables,",
               app, re.S)
if not mm:
    fail("inputsِ گرادیو پیدا نشد")
elif "ocr_ep, ocr_ladder, ocr_threads, ocr_detcap, ocr_boost" \
        not in mm.group(0):
    fail("inputsِ گرادیو: ۵ ویجتِ lab غایب")
else:
    ok("inputsِ گرادیو: ۵ ویجتِ lab بعد از api_base")

env_blk = re.search(
    r"_env = os\.environ\.copy\(\).*?_env\[\"MANGA_LIVE_DIR\"\] = live_dir",
    app, re.S)
if not env_blk:
    fail("بلوکِ _env پیدا نشد")
else:
    b = env_blk.group(0)
    need = ["MANGA_MOBILE_OCR_EP", "MANGA_K3_MODE", "MANGA_OCR_THREADS",
            "MANGA_XNN_THREADS", "MANGA_CROP_DET_CAP", "MANGA_CROP_ENH_SCALE"]
    bad = [n for n in need
           if ('_env["%s"]' % n) not in b and ('_env.pop("%s"' % n) not in b]
    if bad:
        fail("_env: envهایِ غایب: %s" % bad)
    elif '"fast", "mlkit", "rapid", "paddle"' not in b \
            or '"nnapi", "xnnpack", "cpu"' not in b \
            or '"640", "1280"' not in b:
        fail("_env: فالبکِ نامعتبرها ناقص است")
    else:
        ok("_env: هر ۶ env + فالبکِ امنِ نامعتبرها (پیشفرض = pop)")
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
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.getcwd())
import manga
out = {}
keys = ("MANGA_MOBILE_OCR_EP","MANGA_K3_MODE","MANGA_OCR_THREADS",
        "MANGA_XNN_THREADS","MANGA_CROP_DET_CAP","MANGA_CROP_ENH_SCALE")
def clean():
    for k in keys: os.environ.pop(k, None)
clean()
out["E1_line"] = manga.speed_lab_env({
    "ocr_ep": "nnapi", "ocr_ladder": "mlkit", "ocr_threads": 3,
    "ocr_detcap": "640", "ocr_boost": False})
out["E1_env"] = {k: os.environ.get(k) for k in keys}
clean(); os.environ["MANGA_K3_MODE"] = "fast"  # الودگیِ باقیمانده
out["E2_line"] = manga.speed_lab_env({})
out["E2_env"] = {k: os.environ.get(k) for k in keys}
clean()
manga.speed_lab_env({"ocr_ep": "blah", "ocr_ladder": "hmm",
                     "ocr_threads": 99, "ocr_detcap": "12", "ocr_boost": 0})
out["E3_env"] = (os.environ.get("MANGA_MOBILE_OCR_EP"),
                 os.environ.get("MANGA_K3_MODE"),
                 os.environ.get("MANGA_OCR_THREADS"),
                 os.environ.get("MANGA_CROP_DET_CAP"))
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
        want1 = {"MANGA_MOBILE_OCR_EP": "nnapi", "MANGA_K3_MODE": "mlkit",
                 "MANGA_OCR_THREADS": "3", "MANGA_XNN_THREADS": "3",
                 "MANGA_CROP_DET_CAP": "640", "MANGA_CROP_ENH_SCALE": "1.0"}
        if d["E1_env"] != want1 or "روشِ استخراج=mlkit" not in d["E1_line"]:
            fail("E1: env/لاگِ اشتباه: %r" % d["E1_env"])
        else:
            ok("E1: dictِ collect → هر ۶ env درست + لاگِ روش=mlkit")
        e2 = d["E2_env"]
        if any(e2[k] is not None for k in e2) \
                or "روشِ استخراج=full" not in d["E2_line"]:
            fail("E2: dictِ خالی باید همهٔ envها را پاک کند + لاگِ full: %r"
                 % e2)
        else:
            ok("E2: dictِ خالی → پاکسازیِ کامل + لاگِ full (رفتارِ قبل)")
        if tuple(d["E3_env"]) != (None, None, "8", None):
            fail("E3: فالبکِ نامعتبرها غلط: %r" % (d["E3_env"],))
        else:
            ok("E3: نامعتبر → فالبکِ امن (auto/full/clamp8/960)")
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
    miss = [k for k in LAB_KEYS if k not in found]
    if miss:
        fail("U: extract_ui این فیلدها را نمیدهد: %s (دارد: %s)"
             % (miss, list(found)))
    else:
        t_ok = (found["ocr_ep"].get("type") == "select"
                and found["ocr_ladder"].get("type") == "select"
                and found["ocr_threads"].get("type") == "slider"
                and found["ocr_detcap"].get("type") == "select"
                and found["ocr_boost"].get("type") == "bool")
        d_lad = found["ocr_ladder"].get("default")
        d_lad = d_lad.get("default") if isinstance(d_lad, dict) else d_lad
        d_ep = found["ocr_ep"].get("default")
        d_ep = d_ep.get("default") if isinstance(d_ep, dict) else d_ep
        if not t_ok:
            fail("U: نوعِ فیلدها غلط: %s"
                 % {k: v.get("type") for k, v in found.items()})
        elif d_lad != "full" or d_ep != "auto":
            fail("U: پیشفرضها باید full/auto باشد (نه %r/%r)"
                 % (d_ep, d_lad))
        else:
            ok("U: extract_ui هر ۵ فیلد را با نوع/پیشفرضِ درست میدهد")
except Exception as e:
    fail("U: %s: %s" % (type(e).__name__, e))

# W) پیامِ «تستِ دوباره» در infoِ پنل و پیامِ گارد
if "تستِ دوبارهٔ NNAPI" not in app:
    fail("W: infoِ ocr_ep باید «تستِ دوبارهٔ NNAPI» را بگوید")
elif "«فقط NNAPI» را از پنلِ اپ انتخاب کن" not in \
        read("android/app/src/main/python/rapidocr_mobile/__init__.py"):
    fail("W: پیامِ گارد باید راهنمایِ پنل را بگوید")
else:
    ok("W: راهنمایِ تستِ دوباره در infoِ پنل + پیامِ گارد")

print()
if FAILS:
    print("[x] %d گیتِ v1.14.177 شکست خورد" % len(FAILS))
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.177 PASS")
