#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.173 — DEBUGِ سبزِ detector رویِ همان DEBUGِ صفحه +
NNAPI فقط با تستِ صریح (v1.14.174: گیتِ NNAPI به فایلِ nnapi.txt بهروز شد):

درخواستِ سازنده: «عکس جدا نشون نده رو همون عکس اصلی دیباگ بزاره با یک
رنگ دیگ سبز نشون بده» + «استخراج کنده هنوز تو گوشی ولی EP=Nnapi وقتی
رفت اونجا سریعتر شد میشه ولی کرش کرد فعلا رو همون بیاد — nnapi میخوام
تست کنم نه xnnpack».

۱) manga.py: مکانیزمِ عکسِ جدا (<صفحه>_det.jpg/_save_det_debug/_DET_TLS/
   _dbg_cache_*) کامل حذف؛ باکسهایِ خامِ detector-v4-s با det_raw رویِ
   ناحیهها سوار و در _draw_debug_regions با سبزِ (0,255,0) و برچسبِ
   D## رویِ همان DEBUGِ صفحه کشیده میشوند (نقطهٔ واحد — مسیرِ استخراج
   و مسیرِ clean-only هر دو).
۲) rapidocr_mobile/_ep_plan: پیشفرض/auto = فقط XNNPACK — NNAPI از
   تورنمنتِ خودکار حذف شد (پروبِ OK ولی کرشِ نیتیو در اینفرنسِ واقعی —
   لاگِ گوشیِ 1.14.172)؛ تستِ NNAPI فقط با MANGA_MOBILE_OCR_EP=nnapi؛
   گیتِ PC/x86 و MANGA_EP_NO_PROBE دستنخورده.
۳) نسخه — APP_VER↔versionName.
"""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

# ۰) نسخه
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)",
                io.open(os.path.join(ROOT, "VERSION"),
                        encoding="utf-8").read())
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")
ok(f"نسخه {_m.group(1)} (APP_VER↔versionName)")

# ۱) مکانیزمِ سبزِ رویِ DEBUGِ صفحه
dd = cls.get("MangaTranslator")
dd_src = ast.get_source_segment(src, dd) or ""
for gone in ("def _save_det_debug", "_DET_TLS = threading.local()",
             "self._dbg_cache_dir = cache_dir",
             "_DET_TLS.base = os.path.splitext(basename)[0]"):
    if gone in src:
        fail(f"مکانیزمِ عکسِ جدا حذف نشده: {gone!r}")
erb = re.search(r"def _extract_regions_from_bubbles.*?(?=\n    def )",
                dd_src, re.S)
if not erb:
    fail("_extract_regions_from_bubbles پیدا نشد")
erb_src = erb.group(0)
for s in ("_raw_det_dbg = []", "if self.debug:", "det_raw = _raw_det_dbg"):
    if s not in erb_src:
        fail(f"استفادهٔ det_raw در استخراج ناقص است: {s!r}")
i_stash = erb_src.find("_raw_det_dbg = [")
i_drop = erb_src.find("boxes = self._drop_contained_boxes(")
if i_stash < 0 or i_drop < 0 or i_stash > i_drop:
    fail("stashِ باکسِ خام باید قبلِ حذفِ تودرتو باشد")
ddr = re.search(r"def _draw_debug_regions.*?(?=\n    @|\n    def )",
                dd_src, re.S)
if not ddr:
    fail("_draw_debug_regions پیدا نشد")
ddr_src = ddr.group(0)
for s in ('getattr(_r0, "det_raw", None)', "(0, 255, 0)",
          'f"D{_di:02d} {_dcls}"', "cv2.rectangle(vis"):
    if s not in ddr_src:
        fail(f"پوششِ سبز در _draw_debug_regions ناقص است: {s!r}")
if ddr_src.rfind("return vis") < ddr_src.find("det_raw"):
    fail("پوششِ سبز باید قبل از return vis باشد")
ok("باکسهایِ خامِ detector = سبزِ D## رویِ همان DEBUGِ صفحه")

# ۲) EPِ موبایل — پیشفرض فقط XNNPACK؛ NNAPI فقط تستِ صریح
rp = os.path.join(ROOT, "android", "app", "src", "main", "python",
                  "rapidocr_mobile", "__init__.py")
rsrc = io.open(rp, encoding="utf-8").read()
rtree = ast.parse(rsrc)
epf = None
for n in ast.walk(rtree):
    if isinstance(n, ast.FunctionDef) and n.name == "_ep_plan":
        epf = n
        break
if epf is None:
    fail("_ep_plan در rapidocr_mobile نیست")
ep_src = ast.get_source_segment(rsrc, epf) or ""
# v1.14.174 — NNAPI دیگر حذف نیست ولی باید «فقط» پشتِ فایلِ nnapi.txt
# بیاید (env رویِ APK دستِ کاربر نیست)؛ مسیرِ پیشفرض همچنان XNNPACK-only
_i_sw = ep_src.find("nnapi.txt")
_i_both = ep_src.find('_wanted = ["NnapiExecutionProvider", '
                      '"XnnpackExecutionProvider"]')
if _i_sw < 0 or _i_both < 0 or _i_sw > _i_both:
    fail("تورنمنتِ NNAPI+XNNPACK باید پشتِ گیتِ فایلِ nnapi.txt باشد")
if "elif _switch:" not in ep_src or "_nnapi_switch_path(_mdir)" not in ep_src:
    fail("گیتِ فایلِ nnapi.txt در _ep_plan نیست")
if ".ep_nnapi_last" not in rsrc:
    fail("نشانِ کرشِ .ep_nnapi_last نیست")
# شاخهٔ تستِ صریحِ nnapi
if '_e == "nnapi"' not in ep_src or \
        '_wanted = ["NnapiExecutionProvider"]' not in ep_src:
    fail("شاخهٔ تستِ صریحِ MANGA_MOBILE_OCR_EP=nnapi نیست")
if "تستِ NNAPI" not in ep_src:
    fail("پیامِ تستِ NNAPI نیست")
# پیشفرض فقط XNNPACK
if '_wanted = ["XnnpackExecutionProvider"]' not in ep_src:
    fail("پیشفرضِ XNNPACK-only نیست")
if "v1.14.173" not in ep_src:
    fail("نشانِ v1.14.173 در _ep_plan نیست")
# گیتِ PC/x86 + پروبِ اجباری سرِ جایش
for s in ("_x86_machine()", "MANGA_EP_NO_PROBE", "_ep_gate_ensure(",
          "return None, {}"):
    if s not in ep_src:
        fail(f"گیتِ _ep_plan شکسته است: {s!r}")
ok("EP: پیشفرض فقط XNNPACK — NNAPI با فایلِ nnapi.txt یا MANGA_MOBILE_OCR_EP=nnapi")

# ۳) نردبانِ K3 و لامبداِ 172 سرِ جایش
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

print("[✓] همهٔ گیتهایِ v1.14.173 PASS")
