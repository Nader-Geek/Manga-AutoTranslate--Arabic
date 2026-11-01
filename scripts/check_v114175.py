#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.175 — تورنمنتِ ترکیبیِ NNAPI+XNNPACK «پیشفرض»:

دستورِ سازنده: «هرکوفتی یا هر کصشری چیزی ترکیبی nnapi nnpack و… فقط این
کوفتی سرعتش ببرع بالا گوشی به جهنم لگ شع فقط سریع استخراج بزنه» — یعنی
هیچ گیتِ دستیِ فایل/env برایِ سرعت نمیخواهد؛ NNAPI/ترکیبی باید خودکار
امتحان شود.

۱) auto/پیشفرض (بدونِ فایل/env) = تورنمنتِ ترکیبیِ NNAPI+XNNPACK —
   NNAPI مقدم (اولین سالمِ گیتِ پروب کافی — کوتاهبر).
۲) نشانِ کرشِ .ep_nnapi_last نسخهآگاه شد (JSON: launch + ver):
   نشانِ اجرایِ «قبلیِ» همان نسخه → NNAPI از تورنمنت حذف (حتی پروبِ
   دوباره نمیگیرد) → فالبکِ XNNPACK نه CPU؛ آپدیتِ اپ (MANGA_APP_VER —
   manga.py ست میکند) یا محتوایِ متنیِ قدیمیِ 1.14.174 = فرصتِ تازه.
۳) قفلِ فقط-XNNPACK از داخلِ اپ: فایلِ «no_nnapi.txt» کنارِ مدلها.
۴) env سرِ جایش: cpu (مقدم بر همه) | xnnpack | nnapi؛ nnapi.txt همان
   تورنمنت.
۵) عملی: _ep_plan با monkeypatch (۱۳ سناریو) + کوتاهبرِ _ep_gate_ensure
   با کَشِ واقعیِ فایلِ پروب.
۶) نسخه 180/1.14.175 + نردبانِ K3 + لامبداِ 172 + سبزِ 173 دستنخورده.
"""
import ast
import contextlib
import importlib.util
import io
import json
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

# ۰) نسخه — سازگاریِ APP_VER با VERSION (مستقل از شماره — الگویِ 171؛
#    از v1.14.176 به بعد شماره عوض میشود ولی مکانیزم سرِ جایش است)
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
if 'os.environ.setdefault("MANGA_APP_VER", APP_VER)' not in src:
    fail("manga.py باید MANGA_APP_VER را ست کند (نشانِ نسخهآگاهِ کرش)")
ok(f"نسخه {_m.group(1)}/{_vc.group(1)} (APP_VER↔versionName↔versionCode)")

# ۱) گیتهایِ مبدأ
for s in ("def _nnapi_guard_stale", '"ver": os.environ.get("MANGA_APP_VER"'
          ', "")', "no_nnapi.txt", "_LAUNCH_TOKEN"):
    if s not in rsrc:
        fail(f"مکانیزمِ 175 ناقص است: {s!r}")
rtree = ast.parse(rsrc)
gatef = None
epf = None
for n in ast.walk(rtree):
    if isinstance(n, ast.FunctionDef):
        if n.name == "_ep_gate_ensure":
            gatef = n
        elif n.name == "_ep_plan":
            epf = n
if gatef is None or epf is None:
    fail("‎_ep_plan/_ep_gate_ensure پیدا نشد")
gate_src = ast.get_source_segment(rsrc, gatef) or ""
ep_src = ast.get_source_segment(rsrc, epf) or ""
if gate_src.count('if _info.get("ok"):\n            break') + \
        gate_src.count('.get("ok"):\n                break') < 2:
    fail("کوتاهبرِ «اولین سالم» در _ep_gate_ensure نیست")
if "_nnapi_guard_stale(_nnapi_guard_path(_mdir))" not in ep_src:
    fail("فیلترِ نشانِ کرش در _ep_plan نیست")
ok("کوتاهبرِ پروب + فیلترِ نشانِ کرش در مبدأ")

# ۲) تستِ عملی — ماژولِ واقعی با گیتِ قلابی
spec = importlib.util.spec_from_file_location("rpm_chk175", RP)
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
TMP = tempfile.mkdtemp(prefix="ep175_")
DET = os.path.join(TMP, "det.onnx")
REC = os.path.join(TMP, "rec.onnx")
for _p in (DET, REC):
    with open(_p, "wb") as _f:
        _f.write(b"x")
SW = rpm._nnapi_switch_path(TMP)
GD = rpm._nnapi_guard_path(TMP)
NNO = os.path.join(TMP, "no_nnapi.txt")


def reset(switch=False, no_nnapi=False, guard=None, env=None):
    for p in (SW, GD, NNO):
        try:
            os.remove(p)
        except OSError:
            pass
    if switch:
        with open(SW, "w", encoding="utf-8") as f:
            f.write("")
    if no_nnapi:
        with open(NNO, "w", encoding="utf-8") as f:
            f.write("")
    if guard is not None:
        with open(GD, "w", encoding="utf-8") as f:
            f.write(guard)
    rpm._EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
    rpm._NNAPI_HINT = False
    os.environ.pop("MANGA_MOBILE_OCR_EP", None)
    os.environ.pop("MANGA_APP_VER", None)
    if env is not None:
        for k, v in env.items():
            os.environ[k] = v


def plan():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _p = rpm._ep_plan(DET, REC)
    return _p, buf.getvalue()


XNNPLAN = ("XnnpackExecutionProvider", {"intra_op_num_threads": "4"})

# S1 — پیشفرضِ ترکیبی: برندهِ NNAPI + نشانِ JSON با نسخه
reset(env={"MANGA_APP_VER": "1.14.175"})
plan1, out1 = plan()
if plan1 != ("NnapiExecutionProvider", {}) or \
        SEEN["wanted"] != ["NnapiExecutionProvider",
                           "XnnpackExecutionProvider"]:
    fail(f"S1 ترکیبی خراب: {plan1} / {SEEN['wanted']}")
if "ترکیبی" not in out1:
    fail("S1 پیامِ ترکیبی ندارد")
_g1 = json.loads(io.open(GD, encoding="utf-8").read())
if _g1.get("launch") != rpm._LAUNCH_TOKEN or \
        _g1.get("ver") != "1.14.175":
    fail(f"S1 نشانِ نسخهآگاه خراب: {_g1}")
ok("S1 پیشفرضِ ترکیبی → NNAPI + نشانِ JSON (launch+ver)")

# S2 — موتورِ دومِ همان اجرا: نشانِ خودش = تازه → NNAPI دوباره
rpm._EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
plan2, _ = plan()
if plan2 != ("NnapiExecutionProvider", {}):
    fail(f"S2 موتورِ دوم خراب: {plan2}")
ok("S2 نشانِ همین اجرا تازه است → NNAPI برایِ موتورِ دوم")

# S3 — نشانِ اجرایِ «قبلی» (همان نسخه) → بدونِ NNAPI؛ حتی پروب نمیگیرد
_prev = io.open(GD, encoding="utf-8").read()
rpm._LAUNCH_TOKEN = "launch-2"
reset(switch=True, guard=_prev, env={"MANGA_APP_VER": "1.14.175"})
_n0 = STATE["gate_calls"]
plan3, out3 = plan()
if plan3 != XNNPLAN or SEEN["wanted"] != ["XnnpackExecutionProvider"]:
    fail(f"S3 فالبکِ کرش خراب: {plan3} / {SEEN['wanted']}")
if "کرشِ احتمالی" not in out3 or "بدونِ NNAPI" not in out3:
    fail("S3 پیامِ «کرشِ احتمالی → بدونِ NNAPI» ندارد")
if STATE["gate_calls"] != _n0 + 1:
    fail("S3 گیت باید فقط برایِ XNNPACK صدا میشد")
ok("S3 نشانِ کرشِ همان نسخه → فقط XNNPACK (NNAPI پروبِ دوباره نمیگیرد)")

# S4 — آپدیتِ اپ (نسخهٔ نشان فرق دارد) → فرصتِ تازهٔ NNAPI
reset(switch=True,
      guard=json.dumps({"launch": "old-launch", "ver": "1.14.174"}),
      env={"MANGA_APP_VER": "1.14.175"})
plan4, _ = plan()
if plan4 != ("NnapiExecutionProvider", {}):
    fail(f"S4 فرصتِ تازه بعد از آپدیت خراب: {plan4}")
_g4 = json.loads(io.open(GD, encoding="utf-8").read())
if _g4.get("ver") != "1.14.175" or _g4.get("launch") != "launch-2":
    fail(f"S4 نشان باید با نسخهٔ جدید دوباره نوشته میشد: {_g4}")
ok("S4 آپدیتِ اپ = فرصتِ تازهٔ NNAPI + نشانِ نسخهٔ جدید")

# S5 — محتوایِ متنیِ قدیمیِ 1.14.174 = فرصتِ تازه
reset(switch=True, guard="12345:999.0",
      env={"MANGA_APP_VER": "1.14.175"})
plan5, _ = plan()
if plan5 != ("NnapiExecutionProvider", {}):
    fail(f"S5 نشانِ قدیمیِ 174 خراب: {plan5}")
ok("S5 نشانِ متنیِ 1.14.174 → NNAPI بلامانع")

# S6 — پروبِ NNAPI شکست → فالبکِ XNNPACK
STATE["nnapi_ok"] = False
reset(env={"MANGA_APP_VER": "1.14.175"})
plan6, _ = plan()
if plan6[0] != "XnnpackExecutionProvider":
    fail(f"S6 فالبکِ XNNPACK خراب: {plan6}")
STATE["nnapi_ok"] = True
ok("S6 پروبِ NNAPI شکست → XNNPACK")

# S7 — env=cpu مقدم بر همه → CPU بدونِ پروب
_n0 = STATE["gate_calls"]
reset(no_nnapi=True, env={"MANGA_MOBILE_OCR_EP": "cpu"})
plan7, _ = plan()
if plan7 != (None, {}) or STATE["gate_calls"] != _n0:
    fail(f"S7 env=cpu خراب: {plan7}")
ok("S7 env=cpu مقدم بر فایلها → CPU")

# S8 — env=xnnpack → فقط XNNPACK
reset(env={"MANGA_MOBILE_OCR_EP": "xnnpack"})
plan8, _ = plan()
if plan8 != XNNPLAN or SEEN["wanted"] != ["XnnpackExecutionProvider"]:
    fail(f"S8 env=xnnpack خراب: {plan8} / {SEEN['wanted']}")
ok("S8 env=xnnpack → فقط XNNPACK")

# S9 — env=nnapi → فقط NNAPI؛ با نشانِ کرشِ همان نسخه → CPU
reset(env={"MANGA_MOBILE_OCR_EP": "nnapi",
           "MANGA_APP_VER": "1.14.175"})
plan9, _ = plan()
if plan9 != ("NnapiExecutionProvider", {}) or \
        SEEN["wanted"] != ["NnapiExecutionProvider"]:
    fail(f"S9a env=nnapi خراب: {plan9} / {SEEN['wanted']}")
reset(env={"MANGA_MOBILE_OCR_EP": "nnapi", "MANGA_APP_VER": "1.14.175"},
      guard=json.dumps({"launch": "old", "ver": "1.14.175"}))
plan9b, out9b = plan()
_mk9b = None
try:
    with open(GD, encoding="utf-8") as _f:
        _mk9b = (json.load(_f) or {}).get("launch")
except Exception:
    pass
# v1.14.177 — انتخابِ صریحِ nnapi = «تستِ دوباره»: نشانِ کهنه پاک و
# NNAPI دوباره آزموده میشود (گاردِ ضدِ حلقه فقط برایِ auto است).
if plan9b != ("NnapiExecutionProvider", {}) or _mk9b == "old" \
        or "کرشِ احتمالی" in out9b or "کهنه پاک شد" not in out9b:
    fail(f"S9b env=nnapi + نشانِ کرش خراب: {plan9b} / {_mk9b}")
ok("S9 env=nnapi → فقط NNAPI؛ نشانِ کهنه = تستِ دوباره (177)")

# S10 — قفلِ no_nnapi.txt → فقط XNNPACK
reset(no_nnapi=True, env={"MANGA_APP_VER": "1.14.175"})
plan10, out10 = plan()
if plan10 != XNNPLAN or SEEN["wanted"] != ["XnnpackExecutionProvider"]:
    fail(f"S10 no_nnapi خراب: {plan10} / {SEEN['wanted']}")
if "no_nnapi.txt" not in out10:
    fail("S10 پیامِ no_nnapi.txt ندارد")
ok("S10 no_nnapi.txt → فقط XNNPACK (خاموشکردنِ NNAPI از داخلِ اپ)")

# S11 — nnapi.txt همان تورنمنت + پیامِ فایل
reset(switch=True, env={"MANGA_APP_VER": "1.14.175"})
plan11, out11 = plan()
if plan11 != ("NnapiExecutionProvider", {}) or \
        "تستِ NNAPI (فایلِ nnapi.txt)" not in out11:
    fail(f"S11 nnapi.txt خراب: {plan11}")
ok("S11 nnapi.txt → همان تورنمنت + پیامِ فایل")

# S12 — پاککردنِ نشان بعدِ کراپِ سالم
reset(env={"MANGA_APP_VER": "1.14.175"})
plan12, _ = plan()
if plan12[0] != "NnapiExecutionProvider" or not os.path.isfile(GD):
    fail(f"S12 پیشنیاز خراب: {plan12}")
rpm._nnapi_guard_clear()
if os.path.exists(GD) or rpm._NNAPI_ACTIVE or rpm._NNAPI_GUARD:
    fail("S12 _nnapi_guard_clear نشان را پاک نکرد")
ok("S12 کراپِ سالم → نشان پاک؛ NNAPI میماند")

# S13 — تایم‌اوتِ پیشفرضِ پروب
os.environ.pop("MANGA_EP_PROBE_TIMEOUT", None)
if rpm._ep_probe_timeout() != 180.0:
    fail("S13 تایم‌اوتِ پیشفرض باید 180 باشد")
ok("S13 تایم‌اوتِ پیشفرضِ پروب = 180s")

# S14 — کوتاهبرِ واقعیِ _ep_gate_ensure با کَشِ فایلِ پروب
# (ماژولِ تازه = گیتِ دستنخورده؛ سرویس رویِ PC شروع نمیشود)
spec2 = importlib.util.spec_from_file_location("rpm_chk175_real", RP)
rpm2 = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(rpm2)
os.environ.pop("MANGA_EP_PROBE_TIMEOUT", None)
KEY = rpm2._probe_key([DET, REC])
with open(rpm2._ep_flag_path(TMP), "w", encoding="utf-8") as _f:
    json.dump({"key": KEY,
               "eps": {"NnapiExecutionProvider":
                       {"ok": True, "ms": 900.0}}}, _f)
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    _res = rpm2._ep_gate_ensure(TMP, DET, REC,
                                ["NnapiExecutionProvider",
                                 "XnnpackExecutionProvider"], 4)
if list(_res.keys()) != ["NnapiExecutionProvider"] or \
        not _res["NnapiExecutionProvider"].get("ok"):
    fail(f"S14 کوتاهبر خراب — XNNPACK نباید پروب میگرفت: {_res}")
# NNAPI شکست در کَش → XNNPACK باید پروبِ دوباره بگیرد (سرویس رویِ PC
# شروع نمیشود → service-start-failed — ولی یعنی کوتاهبر رویِ شکست
# نمیایستد)
with open(rpm2._ep_flag_path(TMP), "w", encoding="utf-8") as _f:
    json.dump({"key": KEY,
               "eps": {"NnapiExecutionProvider":
                       {"ok": False, "why": "fake-fail"}}}, _f)
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    _res2 = rpm2._ep_gate_ensure(TMP, DET, REC,
                                 ["NnapiExecutionProvider",
                                  "XnnpackExecutionProvider"], 4)
if "XnnpackExecutionProvider" not in _res2:
    fail("S14 بعد از شکستِ NNAPI، XNNPACK باید پروب میگرفت")
ok("S14 کوتاهبرِ واقعی: اولین سالم کافی؛ شکست → ادامه")

# ۳) نردبانِ K3 و لامبداِ 172 و سبزِ 173 دستنخورده
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
lad = cls.get("K3LadderOCR")
lad_src = ast.get_source_segment(src, lad) or ""
for s in ("cov1 >= 0.70", "conf1 >= 0.55", "conf2 >= 0.80"):
    if s not in lad_src:
        fail(f"نردبانِ K3 تغییر کرده: {s!r}")
rb = cls.get("RapidOCRBackend")
rb_src = ast.get_source_segment(src, rb) or ""
if not re.search(r"lambda small: self\._build_mobile_onnx\(\s*lang, "
                 r"small=\(True if _emu171 else small\)\)", rb_src):
    fail("لامبداِ wiringِ 172 عوض شده")
dd = cls.get("MangaTranslator")
dd_src = ast.get_source_segment(src, dd) or ""
erb = re.search(r"def _extract_regions_from_bubbles.*?(?=\n    def )",
                dd_src, re.S).group(0)
for s in ("_raw_det_dbg = []", "det_raw = _raw_det_dbg"):
    if s not in erb:
        fail(f"det_raw در استخراج نیست: {s!r}")
ok("نردبانِ K3 + لامبدا + سبزِ detector سرِ جایش")

print("[✓] همهٔ گیتهایِ v1.14.175 PASS")
