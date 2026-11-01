#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.174 — تستِ NNAPI از داخلِ اپ (فایلِ nnapi.txt) + نشانِ کرش:
(v1.14.175: به مکانیزمِ ترکیبیِ پیشفرض بهروز شد — تورنمنتِ NNAPI+XNNPACK
پیشفرض؛ نشانِ کرش نسخهآگاه؛ فالبکِ کرش = XNNPACK نه CPU.)

گلایهٔ سازنده: «ببینم با من لج داری؟ میگم nnapi بزار تست بزنم Xnnpack
میزاری جاش؟ همچنین nnapi برداشتی؟» — ریشه: تستِ NNAPI در 1.14.173 فقط با
envِ MANGA_MOBILE_OCR_EP بود که رویِ APK دستِ کاربر نیست → از نگاهِ
سازنده NNAPI «برداشته شده» بود و پروب هم فقط XNNPACK میگرفت.

۱) rapidocr_mobile/_ep_plan: فایلِ «nnapi.txt» کنارِ فایلهایِ مدل (0 بایت)
   = تورنمنتِ NNAPI+XNNPACK با گیتِ پروبِ پروسهٔ جدا؛ NNAPIِ سالمِ سریعتر
   برنده، پروبِ شکستخورده → فالبکِ XNNPACK.
۲) نشانِ «.ep_nnapi_last»: شروعِ اجرایِ NNAPI نوشته میشود؛ نشان از اجرایِ
   «قبلی» مانده باشد (کرشِ نیتیوِ اینفرنسِ واقعی که پروب نمیبیند) →
   اجرایِ بعدِ CPU + پیامِ راهنما؛ اولین کراپِ سالم (پوشِ ocr →
   _ocr_k3 → _nnapi_guard_clear) نشان را پاک میکند.
۳) پیشفرض (بدونِ فایل/env) همانِ 1.14.173 = فقط XNNPACK + پیامِ راهنمایِ
   «چطور NNAPI را تست کنم». envِ cpu/nnapi سرِ جایش (env بر فایل مقدم).
۴) تایم‌اوتِ پروب 90→180 (لاگِ گوشیِ 1.14.173: «Xnnpack=timeout» در بارِ
   اولِ بعد از آپدیت).
۵) عملی: _ep_plan با monkeypatch (env/فایل/گیتِ قلابی) — ۹ سناریو.
۶) نسخه — APP_VER↔versionName↔versionCode (مستقل از شماره — الگویِ 171) + نردبانِ K3 و لامبداِ 172 دستنخورده.
"""
import ast
import contextlib
import importlib.util
import io
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "android", "app", "src", "main", "python",
                  "rapidocr_mobile", "__init__.py")


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
rsrc = io.open(RP, encoding="utf-8").read()

# ۰) نسخه — سازگاریِ APP_VER با VERSION (مستقل از شماره — الگویِ 171)
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_vn = re.search(r"versionName=([\d.]+)", _ver)
_vc = re.search(r"versionCode=(\d+)", _ver)
if not _m or not _vn or not _vc:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")
if not re.match(r"^\d+$", _vc.group(1) or ""):
    fail("versionCode عددی نیست")
ok(f"نسخه {_m.group(1)}/{_vc.group(1)} (APP_VER↔versionName↔versionCode)")

# ۱) گیتهایِ مبدأِ rapidocr_mobile
rtree = ast.parse(rsrc)
for s in ("_nnapi_switch_path", "_nnapi_guard_path", "_nnapi_guard_write",
          "_nnapi_guard_clear", "_LAUNCH_TOKEN",
          '_LAUNCH_TOKEN = "%d:%.6f" % (os.getpid(),'):
    if s not in rsrc:
        fail(f"مکانیزمِ نشانِ کرش ناقص است: {s!r}")
cls_mob = None
for n in ast.walk(rtree):
    if isinstance(n, ast.ClassDef) and n.name == "RapidOcrMobile":
        cls_mob = n
        break
if cls_mob is None:
    fail("RapidOcrMobile پیدا نشد")
_meths = {}
for n in cls_mob.body:
    if isinstance(n, ast.FunctionDef):
        _meths[n.name] = ast.get_source_segment(rsrc, n) or ""
for want in ("ocr", "_ocr_k3"):
    if want not in _meths:
        fail(f"متودِ {want} در RapidOcrMobile نیست")
if "self._ocr_k3(image_bgr" not in _meths["ocr"] or \
        "_nnapi_guard_clear()" not in _meths["ocr"]:
    fail("پوشِ ocr باید _ocr_k3 را صدا و بعد نشان را پاک کند")
if _meths["ocr"].find("_nnapi_guard_clear()") < \
        _meths["ocr"].find("self._ocr_k3(image_bgr"):
    fail("پاککردنِ نشان باید بعدِ کراپِ کامل باشد")
if "def ocr(self" not in rsrc or rsrc.count("def ocr(self") != 1:
    fail("نقطهٔ ورودِ ocr باید تکمجمونه (پوش + _ocr_k3)")
if "MANGA_EP_PROBE_TIMEOUT\", \"180\"" not in rsrc:
    fail("تایم‌اوتِ پروب باید پیشفرضِ 180 باشد")
ok("پوشِ ocr → پاککردنِ نشان بعدِ کراپِ سالم؛ تایم‌اوتِ پروب 180")

epf = None
for n in ast.walk(rtree):
    if isinstance(n, ast.FunctionDef) and n.name == "_ep_plan":
        epf = n
        break
if epf is None:
    fail("_ep_plan نیست")
ep_src = ast.get_source_segment(rsrc, epf) or ""
for s in ('os.path.isfile(_nnapi_switch_path(_mdir))',
          '_wanted = ["NnapiExecutionProvider", "XnnpackExecutionProvider"]',
          '_nnapi_guard_stale(',
          '_nnapi_guard_write(_nnapi_guard_path(_mdir))',
          '_e == "nnapi"', '_e == "cpu"', "_x86_machine()",
          "MANGA_EP_NO_PROBE", "return None, {}"):
    if s not in ep_src:
        fail(f"_ep_plan ناقص است: {s!r}")
ok("گیتِ فایلِ nnapi.txt + نشانِ کرش در _ep_plan")

# ۲) تستِ عملیِ _ep_plan — ۹ سناریو با گیتِ قلابی
spec = importlib.util.spec_from_file_location("rpm_chk174", RP)
rpm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rpm)

rpm._android_env = lambda: True
rpm._x86_machine = lambda: False
rpm._avail_eps = lambda: {"CPUExecutionProvider", "XnnpackExecutionProvider",
                          "NnapiExecutionProvider"}
rpm._xnn_threads = lambda: 4

STATE = {"nnapi_ok": True, "gate_calls": 0}
SEEN = {}


def fake_gate(mdir, det, rec, wanted, threads):
    STATE["gate_calls"] += 1
    SEEN["wanted"] = list(wanted)
    out = {}
    for n in wanted:
        if n == "NnapiExecutionProvider" and not STATE["nnapi_ok"]:
            out[n] = {"ok": False, "why": "fake-nnapi-fail"}
        else:
            out[n] = {"ok": True,
                      "ms": 900.0 if n == "NnapiExecutionProvider"
                      else 2500.0}
    return out


rpm._ep_gate_ensure = fake_gate
TMP = tempfile.mkdtemp(prefix="ep174_")
DET = os.path.join(TMP, "det.onnx")
REC = os.path.join(TMP, "rec.onnx")
for _p in (DET, REC):
    with open(_p, "wb") as _f:
        _f.write(b"x")
SW = rpm._nnapi_switch_path(TMP)
GD = rpm._nnapi_guard_path(TMP)


def reset(nnapi=None, guard=None, switch=False, env=None):
    for p in (SW, GD):
        try:
            os.remove(p)
        except OSError:
            pass
    if switch:
        with open(SW, "w", encoding="utf-8") as f:
            f.write("")
    if guard is not None:
        with open(GD, "w", encoding="utf-8") as f:
            f.write(guard)
    rpm._EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
    rpm._NNAPI_HINT = False
    os.environ.pop("MANGA_MOBILE_OCR_EP", None)
    if env is not None:
        os.environ["MANGA_MOBILE_OCR_EP"] = env


def plan():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _p = rpm._ep_plan(DET, REC)
    return _p, buf.getvalue()


# S1 — پیشفرض (v1.14.175): تورنمنتِ ترکیبی — برندهِ NNAPI + نشان
reset()
plan1, out1 = plan()
if plan1 != ("NnapiExecutionProvider", {}) or \
        SEEN["wanted"] != ["NnapiExecutionProvider",
                           "XnnpackExecutionProvider"]:
    fail(f"S1 پیشفرضِ ترکیبی خراب: {plan1} / {SEEN['wanted']}")
if "ترکیبی" not in out1 or not os.path.isfile(GD):
    fail("S1 پیامِ ترکیبی/نوشتنِ نشان خراب")
ok("S1 پیشفرض = تورنمنتِ ترکیبی، برنده NNAPI + نشان")

# S2 — فایلِ nnapi.txt + NNAPI سالم → برندهِ NNAPI + نشان نوشته میشود
reset(switch=True)
plan2, out2 = plan()
if plan2 != ("NnapiExecutionProvider", {}) or \
        SEEN["wanted"] != ["NnapiExecutionProvider",
                           "XnnpackExecutionProvider"]:
    fail(f"S2 تورنمنت خراب: {plan2} / {SEEN['wanted']}")
_gc2 = (io.open(GD, encoding="utf-8").read() or "") \
    if os.path.isfile(GD) else ""
if rpm._LAUNCH_TOKEN not in _gc2:
    fail("S2 نشانِ .ep_nnapi_last با شناسهٔ اجرا نوشته نشد")
if "تستِ NNAPI (فایلِ nnapi.txt)" not in out2:
    fail("S2 پیامِ تستِ NNAPI (فایل) ندارد")
ok("S2 nnapi.txt → تورنمنت، برنده NNAPI، نشان نوشته شد")

# S3 — اجرایِ بعد (نشانِ اجرایِ قبلی مانده = کرش) → CPU + پیام
_prev_token = io.open(GD, encoding="utf-8").read()
rpm._LAUNCH_TOKEN = "launch-2"
reset(switch=True, guard=_prev_token)
plan3, out3 = plan()
if plan3 != ("XnnpackExecutionProvider",
             {"intra_op_num_threads": "4"}) or \
        SEEN["wanted"] != ["XnnpackExecutionProvider"]:
    fail(f"S3 فالبکِ بعد از کرش خراب: {plan3} / {SEEN['wanted']}")
if "کرشِ احتمالی" not in out3 or ".ep_nnapi_last" not in out3:
    fail("S3 پیامِ «کرشِ احتمالی → بدونِ NNAPI» ندارد")
ok("S3 نشانِ اجرایِ قبلی مانده → بدونِ NNAPI (XNNPACK) + پیام")

# S4 — پاککردنِ دستیِ نشان → تستِ دوبارهٔ NNAPI
os.remove(GD)
rpm._EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
plan4, _ = plan()
if plan4 != ("NnapiExecutionProvider", {}):
    fail(f"S4 تستِ دوباره خراب: {plan4}")
if "launch-2" not in (io.open(GD, encoding="utf-8").read() or ""):
    fail("S4 نشان باید با شناسهٔ اجرایِ فعلی دوباره نوشته میشد")
ok("S4 حذفِ نشان → NNAPI دوباره؛ نشان با شناسهٔ تازه")

# S5 — پروبِ NNAPI شکست → فالبکِ XNNPACK (CPUِ خالی نمیماند)
STATE["nnapi_ok"] = False
os.remove(GD)
rpm._EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
plan5, _ = plan()
if plan5[0] != "XnnpackExecutionProvider":
    fail(f"S5 فالبکِ XNNPACK خراب: {plan5}")
STATE["nnapi_ok"] = True
ok("S5 پروبِ NNAPI شکست → فالبکِ XNNPACK")

# S6 — env=cpu مقدم بر فایل → CPU؛ گیت صدا نمیشود
_n0 = STATE["gate_calls"]
reset(switch=True, env="cpu")
plan6, _ = plan()
if plan6 != (None, {}) or STATE["gate_calls"] != _n0:
    fail(f"S6 env=cpu خراب: {plan6}")
ok("S6 env=cpu مقدم بر فایل → CPU بدونِ پروب")

# S7 — env=nnapi (بدونِ فایل) → فقط NNAPI
reset(env="nnapi")
plan7, out7 = plan()
if plan7 != ("NnapiExecutionProvider", {}) or \
        SEEN["wanted"] != ["NnapiExecutionProvider"]:
    fail(f"S7 env=nnapi خراب: {plan7} / {SEEN['wanted']}")
ok("S7 env=nnapi → تستِ صریحِ فقط NNAPI")

# S8 — پاککردنِ نشان بعدِ کراپِ سالم
reset(switch=True)
rpm._EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
plan8, _ = plan()
if plan8[0] != "NnapiExecutionProvider" or not os.path.isfile(GD):
    fail(f"S8 پیشنیازِ پاککردن خراب: {plan8}")
rpm._nnapi_guard_clear()
if os.path.exists(GD) or rpm._NNAPI_ACTIVE or rpm._NNAPI_GUARD:
    fail("S8 _nnapi_guard_clear نشان را پاک نکرد")
rpm._nnapi_guard_clear()  # دوباره = بیاثر و بیدردسر
ok("S8 _nnapi_guard_clear بعدِ کراپِ سالم نشان را پاک میکند")

# S9 — تایم‌اوتِ پیشفرض
os.environ.pop("MANGA_EP_PROBE_TIMEOUT", None)
if rpm._ep_probe_timeout() != 180.0:
    fail("S9 تایم‌اوتِ پیشفرض باید 180 باشد")
ok("S9 تایم‌اوتِ پیشفرضِ پروب = 180s")

# ۳) نردبانِ K3 و لامبداِ 172 دستنخورده
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
lad = cls.get("K3LadderOCR")
lad_src = ast.get_source_segment(src, lad) or ""
for s in ("cov1 >= 0.70", "conf1 >= 0.55", "conf2 >= 0.80"):
    if s not in lad_src:
        fail(f"نردبانِ K3 تغییر کرده: {s!r}")
rb = cls.get("RapidOCRBackend")
rb_src = ast.get_source_segment(src, rb) or ""
if not re.search(r"lambda small(?:=False, tiny=False)?:\s*"
                 r"self\._build_mobile_onnx\(\s*lang,\s*"
                 r"small=\(True if _emu171 else small\)"
                 r"(?:,\s*tiny=tiny)?\)", rb_src):
    fail("لامبداِ wiringِ 172 عوض شده")
ok("نردبانِ K3 + لامبداِ کلیدواژهای (با tinyِ 179) سرِ جایش")

# ۴) سبزِ detector (173) هم سرِ جایش
dd = cls.get("MangaTranslator")
dd_src = ast.get_source_segment(src, dd) or ""
erb = re.search(r"def _extract_regions_from_bubbles.*?(?=\n    def )",
                dd_src, re.S).group(0)
for s in ("_raw_det_dbg = []", "det_raw = _raw_det_dbg"):
    if s not in erb:
        fail(f"det_raw در استخراج نیست: {s!r}")
ok("سبزِ detector رویِ DEBUGِ صفحه (173) دستنخورده")

print("[✓] همهٔ گیتهایِ v1.14.174 PASS")
