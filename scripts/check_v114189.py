#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.189 — چهار مشکلِ دستورِ سازنده.

گیتها:
  A. نسخه = 1.14.189 / versionCode=194 در manga.py + VERSION + gradle.
  B. مشکل۲ — پرامپتهایِ اسنیفشده: untitled.py → FLASH_PROMPT،
     untitled2.py → FLASH_LITE_PROMPT، SYSTEM_INSTRUCTION_PROTOCOL،
     temperature 0.7 + topP 0.9 در هر چهار مسیرِ ارسال؛ بدونِ URLِ فیکِ
     کپچر؛ بدونِ هیچ آپلودِ تصویر؛ classic جدای خودش؛ غیرِGemini → lite.
  C. مشکل۳ — حبابِ خالی ممنوع: نجاتِ تکآیتمیِ نهایی + fallback؛
     دستورِ «هرگز رشتهٔ خالی» در پرامپت.
  D. مشکل۱ — استخراجِ img6: گاردِ ضدِ ادغامِ دو متنِ جدا + نجاتِ
     نیمههایِ کراپِ کشیده + ترمیمِ «77,I» → «I».
  E. مشکل۴ — ONNXِ باندل حذف: OcrModelStore (دانلودِ زمانِ اجرا به
     حسابِ زبانِ انتخابی) + ModelSource (assets/filesDir) + پلِ
     زبان‌آگاه + build.ymlِ بدونِ مدل (فلگِ تستِ شبیهساز پابرجا).
  F. py_compile + YAML + تستهایِ عملیِ گارد/ترمیم/سبکِ پرامپت.
"""

import ast
import io
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FAILS = []


def ok(msg):
    print(f"[✓] {msg}")


def fail(msg):
    FAILS.append(msg)
    print(f"[✗] {msg}")


def gate(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)
    return cond


_manga = io.open("manga.py", encoding="utf-8").read()
_gradle = io.open("android/app/build.gradle.kts", encoding="utf-8").read()
_bridge_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/PaddleOcrBridge.kt",
    encoding="utf-8").read()
_store_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/OcrModelStore.kt",
    encoding="utf-8").read()
_msrc_kt = io.open(
    "android/ppocr-sdk/src/main/java/com/paddle/ocr/util/ModelSource.kt",
    encoding="utf-8").read()
_build_yml = io.open(".github/workflows/build.yml", encoding="utf-8").read()

# ── A. نسخه ──────────────────────────────────────────────────────────
gate('APP_VER = "1.14.189"' in _manga, "A: APP_VERِ manga.py = 1.14.189")
_v = {}
try:
    for ln in open("VERSION", encoding="utf-8"):
        if "=" in ln:
            k, val = ln.strip().split("=", 1)
            _v[k] = val
    gate(_v.get("versionCode") == "194"
         and _v.get("versionName") == "1.14.189",
         "A: VERSION = 1.14.189 / versionCode=194")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")
gate('versionCode = 194' in _gradle
     and 'versionName = "1.14.189"' in _gradle,
     "A: build.gradle.kts = 194 / 1.14.189")

# ── B. مشکل۲ — پرامپتها ─────────────────────────────────────────────
gate("FLASH_PROMPT = r'''" in _manga
     and "FLASH_LITE_PROMPT = r'''" in _manga
     and "SYSTEM_INSTRUCTION_PROTOCOL = r'''" in _manga,
     "B: سه ثابتِ پرامپت = رشتهٔ خامِ اسنیفشده")
for frag in ("TASK: Translate the sequential dialogue blocks",
             "فرایند پردازش و ترجمه", "بومی‌سازی هوشمندانه"):
    gate(frag in _manga.split("FLASH_LITE_PROMPT")[0].split("FLASH_PROMPT")[-1],
         f"B: FLASH_PROMPT = متنِ کپچرِ untitled.py ({frag[:26]}…)")
for frag in ("قوانین ترجمه", "لحن کتابی، رسمی و عبارات ماشینی پرهیز کن"):
    gate(frag in _manga.split("SYSTEM_INSTRUCTION_PROTOCOL")[0]
         .split("FLASH_LITE_PROMPT")[-1],
         f"B: FLASH_LITE_PROMPT = متنِ کپچرِ untitled2.py ({frag[:24]}…)")
for frag in ("SYSTEM BEHAVIOR PROTOCOL", "[CENSORED]",
             "NEVER skip, merge, reorder"):
    gate(frag in _manga.split("SYSTEM_INSTRUCTION_PROTOCOL", 1)[1]
         .split("'''", 1)[1].split("'''", 1)[0],
         f"B: SYSTEM_INSTRUCTION_PROTOCOL = کپچر ({frag[:22]}…)")
gate("تو مترجم حرفه‌ای مانگا" in _manga,
     "B: classic = دستورِ فارسیِ خودش (جدا و مستقل)")
gate("no-filter-gemini" not in _manga and "khalilkhko" not in _manga,
     "B: URLِ فیکِ کپچر هیچ‌جای کد نیست")
gate("inline_data" not in _manga and "inlineData" not in _manga
     and "X-Goog-Upload" not in _manga,
     "B: هیچ مسیرِ آپلودِ تصویر وجود ندارد (فقط متن)")
gate("translation_temperature: float = 0.7" in _manga
     and 'p.add_argument("--temperature", type=float, default=0.7)' in _manga,
     "B: temperatureِ پیشفرض = 0.7 (کپچر)")
gate('config_args["top_p"] = 0.9' in _manga
     and 'kwargs["top_p"] = 0.9' in _manga
     and '**({"top_p": 0.9} if structured else {})' in _manga
     and '**({"topP": 0.9} if structured else {})' in _manga,
     "B: topP 0.9 در هر چهار مسیر (gemini/openai/anthropic/google)")
gate("if mode == \"classic\":" in _manga
     and "return SYSTEM_INSTRUCTION_PROTOCOL" in _manga,
     "B: سبکهای flash → پروتکلِ سیستمیِ کپچر؛ classic → دستورِ خودش")
gate("style_head" in _manga
     and "INPUT PAGES AND DIALOGUES (JSON):" in _manga,
     "B: سرِ کپچر + برچسبِ داده در user prompt")
# route: غیرِGemini → lite
gate('if prov != "gemini":\n        return "lite"' in _manga,
     "B: resolve_prompt_mode — هر سرویسِ غیرِGemini → سبکِ lite")

# ── C. مشکل۳ — حبابِ خالی ممنوع ─────────────────────────────────────
gate("def _force_translate_missing_1189(" in _manga,
     "C: نجاتِ نهاییِ تکآیتمی تعریف شده")
gate(_manga.count("self._force_translate_missing_1189(regions)") >= 2,
     "C: نجات در مسیرِ موفق و مسیرِ تلاشِ نهایی هر دو صدا زده میشود")
gate("هرگز رشتهٔ خالی برنگردان" in _manga,
     "C: پرامپت دیگر اجازهٔ رشتهٔ خالی نمیدهد")
gate("متنِ مبدأ جایگزین شد" in _manga,
     "C: آخرین fallback = خودِ متنِ مبدأ (حبابِ سفیدِ خالی ممنوع)")

# ── D. مشکل۱ — استخراجِ img6 ────────────────────────────────────────
gate("def _incoherent_lines_1189(" in _manga
     and ">= 1.35" in _manga,
     "D: گاردِ ضدِ ادغام (دو فونتِ ناهماهنگ = دو ناحیه)")
_merge_body = _manga.split("def _merge_overlapping_regions")[1]
gate("elif _incoherent_lines_1189(cur, b):" in _merge_body
     and "def _incoherent_lines_1189(a, b):" in _merge_body,
     "D: گارد داخلِ شاخهٔ joinِ merge")
gate("[🔍189] شکافِ خط" in _manga
     and "half-top" in _manga and "half-bot" in _manga
     and "_maxgap189 > 2.0 * _med189" in _manga,
     "D: نجاتِ نیمههایِ کراپِ کشیده (خطِ جامانده)")
gate('return "I"' in _manga
     and 'all(c in "Iil" for c in _alpha188)' in _manga
     and "_fix188 or len(_keep188) != len(entries)" in _manga,
     "D: ترمیمِ «77,I» → «I» بهجایِ حذف (I'llِ ناخوانا)")

# ── E. مشکل۴ — حذفِ باندل + دانلودِ زبان‌آگاه ───────────────────────
for frag in ("https://github.com/amirwolf512k/Manga-AutoTranslate/releases/download/models/",
             '"models/det/inference.onnx"', '"models/rec/inference.onnx"',
             '"models/rec_ja/inference.onnx"', '"models/rec_ko/inference.onnx"',
             "PP-OCRv6_medium_rec_onnx.onnx", "ppocrv6_chars.txt",
             "fun pathsForLang", "fun ensure("):
    gate(frag in _store_kt, f"E: OcrModelStore — {frag[:44]}")
gate("fun init(numThreads: Int, primaryLang: String?)" in _bridge_kt
     and "OcrModelStore.ensure(context, OcrModelStore.pathsForLang(primaryLang))" in _bridge_kt
     and "listOf(variant.first, variant.second)" in _bridge_kt,
     "E: پل — initِ زبان‌آگاه + ensureِ واریانت در تعویضِ زبان")
gate("object ModelSource" in _msrc_kt
     and "context.filesDir" in _msrc_kt,
     "E: ModelSource — assets یا filesDir")
_sdk = ""
for f in ("android/ppocr-sdk/src/main/java/com/paddle/ocr/model/ModelConfig.kt",
          "android/ppocr-sdk/src/main/java/com/paddle/ocr/engine/RapidOcrEngine.kt",
          "android/ppocr-sdk/src/main/java/com/paddle/ocr/engine/ORTSessionManager.kt"):
    _sdk += io.open(f, encoding="utf-8").read()
gate(_sdk.count("ModelSource.") >= 3,
     "E: هر سه محلِ خواندنِ مدل در SDK از ModelSource میخوانند")
gate('self._bridge.init(_intra, str(self.lang or "en"))' in _manga
     and "except TypeError:" in _manga,
     "E: manga.py — init با زبانِ انتخابی (سازگارِ APKِ قدیمی)")
gate('github.event_name == \'workflow_dispatch\' && inputs.bundle_ocr_models' in _build_yml
     and "bundle_ocr_models:" in _build_yml
     and "default: false" in _build_yml,
     "E: build.yml — باندل فقط با فلگِ تست؛ پیشفرض = APKِ سبک")
gate("korean_PP-OCRv4_rec_mobile.onnx" in _build_yml,
     "E: مسیرِ باندلِ تستِ شبیهساز پابرجاست")

# ── F. کامپایل + تستهایِ عملی ───────────────────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    ok("F: py_compileِ manga.py")
except Exception as e:
    fail(f"F: py_compile: {e}")
try:
    import yaml
    yaml.safe_load(io.open(".github/workflows/build.yml", encoding="utf-8"))
    ok("F: build.yml — YAML سالم")
except Exception as e:
    fail(f"F: YAML: {e}")

try:
    sys.argv = ["manga.py"]
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import manga as M
    import numpy as np

    # سبکِ پرامپت: غیرِGemini → lite؛ متنِ کپچر بارگذاری شده
    assert M.resolve_prompt_mode("auto", "openai", "") == "lite"
    assert "TASK: Translate" in M.PROMPT_PRESETS["professional"]
    assert "قوانین ترجمه" in M.PROMPT_PRESETS["lite"]
    assert "تو مترجم حرفه‌ای مانگا" in M.PROMPT_PRESETS["classic"]
    assert M.SYSTEM_INSTRUCTION_PROTOCOL.startswith("SYSTEM BEHAVIOR PROTOCOL")
    ok("F: سبکهای پرامپت — lite/openai + متنِ کپچر + classicِ جدا")

    # گاردِ ضدِ ادغام — سناریوی img6ِ گوشی
    TR = M.TextRegion

    def _mk(rid, rect, text, dims):
        polys = []
        y = rect[1] + 6
        x = rect[0] + 6
        for d in dims:
            polys.append(np.array([[x, y], [x + d * 5, y], [x + d * 5, y + d],
                                   [x, y + d]], dtype=np.int32))
            y += d + 4
        return TR(id=rid, boxes=[polys[0]], source_text=text, rect=rect,
                  ocr_polys=polys)

    A = _mk(2, (6, 34, 350, 640), "THEN PULL THE FLOAT FOR YOU!", [50, 48, 49, 51])
    B = _mk(4, (6, 414, 151, 224), "You're the real attraction here.", [70, 72, 73, 70])
    out = M.MangaTranslator._merge_overlapping_regions([A, B])
    assert len(out) == 2, "two-text regions must stay separate"
    C = _mk(1, (100, 100, 300, 160), "HELLO THERE FRIEND", [48, 46])
    Dd = _mk(2, (130, 115, 140, 30), "WORLD MY FRIEND", [47, 49])
    assert len(M.MangaTranslator._merge_overlapping_regions([C, Dd])) == 1, \
        "legit same-height merge must still work"
    ok("F: گاردِ ضدِ ادغام — img6 جدا میماند؛ ادغامِ سالم سر جایش")

    # ترمیمِ خطِ آشغال
    assert M._latin_junk_line188("77,I") == "I"
    assert M._latin_junk_line188("FL") is True
    assert M._latin_junk_line188("GO!") is False
    ok("F: ترمیمِ I'llِ ناخوانا — «77,I» → «I»")
except SystemExit:
    raise
except Exception as e:
    fail(f"F: تستهایِ عملی: {e}")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ v1.14.189 شکست خورد")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.189 PASS — پرامپتهایِ کپچری + حبابِ بدونِ خالی "
      "+ استخراجِ کاملِ img6 + مدلِ دانلودیِ زبان‌آگاه")
