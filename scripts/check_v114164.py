#!/usr/bin/env python3
# v1.14.164 — چکِ رگرسیونِ رگِ «متن پیدا نشد»ٔ 1.14.163.
# ریشه: def _ocr_impl(self, …) هنگامِ ویرایشِ نردبانِ K3 (1.14.157)
# ناخواسته داخلِ def _better_res تودرتو شد = کدِ مرده → کلاسِ
# RapidOcrMobile دیگر _ocr_impl نداشت → هر OCRِ کراپ رویِ گوشی
# AttributeError میداد و دو exceptِ بیصدا آن را قورت میداد →
# «Region [i] had no OCR text but has text-like ink» برایِ همهٔ نواحی.
# این چک بدونِ هیچ وابستگی (فقط ast):
#   ۱) _ocr_impl باید متدِ مستقیمِ RapidOcrMobile باشد.
#   ۲) هیچ تابعِ سطحِ ماژول نباید def ای با آرگومانِ اولِ self داشته باشد
#      (تنها استثنایِ مجاز: کلوزورهایِ عمدیِ bridge.py).
#   ۳) manga.py باید متدِ ocr با crop_mode و پرچمِ خطایِ بلند داشته باشد.
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILS = []


def nested_self_defs(fn, owner):
    out = []
    for child in ast.iter_child_nodes(fn):
        if isinstance(child, ast.FunctionDef):
            if child.args.args and child.args.args[0].arg == "self":
                out.append((owner, child.name, child.lineno))
            out += nested_self_defs(child, child.name)
        elif isinstance(child, ast.ClassDef):
            for m in child.body:
                if isinstance(m, ast.FunctionDef):
                    out += nested_self_defs(m, f"{child.name}.{m.name}")
        else:
            out += nested_self_defs(child, owner)
    return out


# ── ۱) rapidocr_mobile: _ocr_impl متدِ کلاس است ──
p = ROOT / "android/app/src/main/python/rapidocr_mobile/__init__.py"
tree = ast.parse(p.read_text(encoding="utf-8"))
cls = next(n for n in ast.walk(tree)
           if isinstance(n, ast.ClassDef) and n.name == "RapidOcrMobile")
methods = {m.name for m in cls.body if isinstance(m, ast.FunctionDef)}
for need in ("_ocr_impl", "ocr", "_detect", "_recognize", "_within_bounds"):
    if need not in methods:
        FAILS.append(f"{p.name}: متدِ {need} در کلاسِ RapidOcrMobile نیست")
mod_funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
for need in ("_k3_on", "_enh_scale_for", "_enhance_crop", "_lines_quality",
             "_low_quality", "_rescale_res", "_better_res"):
    if need not in mod_funcs:
        FAILS.append(f"{p.name}: تابعِ ماژولیِ {need} از دست رفت")

# ── ۲) هیچ def(self,…) تودرتویی در کلِ ریپو (بهجز کلوزورهایِ مجاز) ──
ALLOW = {("install_webp_guards", "_safe_save")}  # کلوزورِ عمدیِ bridge.py
for f in ROOT.rglob("*.py"):
    if ".git" in str(f):
        continue
    try:
        t = ast.parse(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    for n in t.body:
        if isinstance(n, ast.FunctionDef):
            for owner, name, ln in nested_self_defs(n, n.name):
                if (owner, name) in ALLOW:
                    continue
                FAILS.append(f"{f}: def {name}(self,…) تودرتو داخلِ "
                             f"{owner} (خط {ln}) — کدِ مرده؟")

# ── ۳) manga.py: مسیرِ OCRِ کراپ + لاگِ بلندِ خطا + سدِ دستهٔ ۱۶۵ ──
m = (ROOT / "manga.py").read_text(encoding="utf-8")
for needle in ("crop_mode=True",
               "خطایِ OCRِ موبایل",
               "OCRِ برش خطا داد",
               # v1.14.165 — نجاتِ تکه‌متنِ لبه + سدِ دسته
               "_edge_sides",
               "پاسِ ویژهٔ لبه",
               "_dense165",
               "_wait_batch_clean_barrier",
               "MANGA_CLEAN_PAR"):
    if needle not in m:
        FAILS.append(f"manga.py: رشتهٔ لازمِ «{needle}» پیدا نشد")

# ── ۴) rapidocr_mobile: قطعاتِ نردبانِ rec-only (v1.14.165) ──
for need in ("_prep_work", "_rec_lines", "_detect_or_pred"):
    if need not in methods:
        FAILS.append(f"{p.name}: متدِ {need} در کلاسِ RapidOcrMobile نیست")

if FAILS:
    print("FAIL:")
    for x in FAILS:
        print("  ✗", x)
    sys.exit(1)
print("PASS — چکِ رگرسیونِ v1.14.164: _ocr_impl سرِ جایش است؛ هیچ "
      "def(self,…) تودرتویی در ریپو نیست؛ لاگِ خطایِ OCR فعال است")
