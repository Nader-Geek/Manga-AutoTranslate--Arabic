#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ خودترمیمیِ لودر (v1.14.253) — چهار سناریو در سندباکسِ جدا:

A) کهنه:    بخشهایِ 1.14.251 + لودرِ 1.14.253 → تازهسازیِ پس‌زمینه → import بعدی = 253
B) غایب:    بدونِ manga_sections/ → دانلودِ blocking → همان لحظه اجرا
C) مرده:    بدونِ بخشها + میرورِ مرده → RuntimeError با پیامِ فارسی
D) مهر:     بلافاصله بعد از شکست → تلاشِ دوم توسطِ مهر رد میشود

میرور = file:// روی پوشهٔ ریپو (بدونِ شبکه). سناریوی C با کپیِ لودرِ
اصلاحشده (میرورِ پورتِ ۹ = connection refused فوری) اجرا میشود.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOADER = os.path.join(REPO, "manga.py")
SECTIONS = os.path.join(REPO, "manga_sections")
PY = sys.executable
MIRROR = "file://%s/" % REPO  # file:///…/manga-work/


def _patch_mirrors(loader_path, url):
    """کلِ تاپلِ میرورها را با یک میرورِ واحد جابهجا میکند."""
    ldr = open(loader_path, encoding="utf-8").read()
    ldr2 = re.sub(r"_UPDATE_MIRRORS = \(.*?\n\)",
                  '_UPDATE_MIRRORS = (r"%s",)' % url, ldr, flags=re.S)
    assert ldr2 != ldr, "mirror patch failed"
    open(loader_path, "w", encoding="utf-8").write(ldr2)

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("✅ PASS" if ok else "❌ FAIL") + f"  {name}" + (f" — {detail}" if detail else ""))


def make_tmp(tag):
    d = os.path.join(tempfile.mkdtemp(prefix="manga_heal_%s_" % tag), "app")
    os.makedirs(d)
    return d


def run_import(d, timeout=150):
    """import manga در پروسهٔ جدا؛ خروجی: (returncode, stdout+stderr)."""
    code = ("import sys; sys.path.insert(0, r'%s');\n"
            "import manga\n"
            "print('LOADED_APP_VER=' + str(manga.APP_VER))\n"
            "print('HAS_TR=' + str(hasattr(manga, 'MangaTranslator')))\n") % d
    p = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                       timeout=timeout, cwd=d)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sections_ver(d):
    try:
        src = open(os.path.join(d, "manga_sections", "00_base.py"),
                   encoding="utf-8").read(8192)
        m = re.search(r'APP_VER\s*=\s*"([^"]+)"', src)
        return m.group(1) if m else "?"
    except OSError:
        return None


# ── A) کهنه: 251 → تازهسازیِ پس‌زمینه → import دوم = 253 ──────────────
dA = make_tmp("stale")
shutil.copy(LOADER, os.path.join(dA, "manga.py"))
shutil.copytree(SECTIONS, os.path.join(dA, "manga_sections"),
                ignore=shutil.ignore_patterns("__pycache__"))
# شبیه‌سازیِ گوشی: 00_base کهنه + میرورِ file:// (لودر را وادار به تازهسازی)
p00 = os.path.join(dA, "manga_sections", "00_base.py")
src = open(p00, encoding="utf-8").read().replace('APP_VER = "1.14.253"',
                                                 'APP_VER = "1.14.251"')
open(p00, "w", encoding="utf-8").write(src)
# میرورِ file:// — فقط برای همین تست
ldr = open(os.path.join(dA, "manga.py"), encoding="utf-8").read()
ldr = ldr.replace('_UPDATE_MIRRORS = (', '_UPDATE_MIRRORS = (r"%s",' % MIRROR)
open(os.path.join(dA, "manga.py"), "w", encoding="utf-8").write(ldr)

rc, out = run_import(dA)
first_ver = sections_ver(dA)
check("A1: اجرای اول با نسخهٔ کهنه بالا میآید",
      rc == 0 and "LOADED_APP_VER=1.14.251" in out, f"rc={rc} ver={first_ver}")
# رشتهٔ پس‌زمینه: چند ثانیه صبر — file:// سریع است
t0 = time.time()
while time.time() - t0 < 30:
    if sections_ver(dA) == "1.14.253":
        break
    time.sleep(0.5)
check("A2: تازهسازیِ پس‌زمینه 00_base را به 253 برد",
      sections_ver(dA) == "1.14.253", f"ver={sections_ver(dA)}")
# MANIFEST هم باید نوشته شده باشد (که مسیرِ refresh زنده بماند)
check("A3: MANIFEST هم تازه شد",
      os.path.isfile(os.path.join(dA, "manga_sections", "MANIFEST")))
rc, out = run_import(dA)
check("A4: اجرای دوم = موتورِ 253",
      rc == 0 and "LOADED_APP_VER=1.14.253" in out and "HAS_TR=True" in out)

# ── B) غایب: دانلودِ blocking → همان لحظه اجرا ────────────────────────
dB = make_tmp("missing")
shutil.copy(LOADER, os.path.join(dB, "manga.py"))
ldr = open(os.path.join(dB, "manga.py"), encoding="utf-8").read()
ldr = ldr.replace('_UPDATE_MIRRORS = (', '_UPDATE_MIRRORS = (r"%s",' % MIRROR)
open(os.path.join(dB, "manga.py"), "w", encoding="utf-8").write(ldr)
rc, out = run_import(dB)
check("B1: بدونِ بخشها → خودش دانلود کرد و بالا آمد",
      rc == 0 and "LOADED_APP_VER=1.14.253" in out and "HAS_TR=True" in out,
      f"rc={rc}")
check("B2: پیامِ خودترمیمی چاپ شد", "دانلودِ خودترمیم" in out)
check("B3: بخشها + MANIFEST روی دیسک آمدند",
      sections_ver(dB) == "1.14.253"
      and os.path.isfile(os.path.join(dB, "manga_sections", "MANIFEST")))

# ── C) مرده: بدونِ بخشها + میرورِ مرده → RuntimeError ──────────────────
dC = make_tmp("dead")
shutil.copy(LOADER, os.path.join(dC, "manga.py"))
_patch_mirrors(os.path.join(dC, "manga.py"), "http://127.0.0.1:9/")
rc, out = run_import(dC, timeout=200)
check("C1: میرورِ مرده → RuntimeError (نه سکوتِ مرگبار)",
      rc != 0 and "manga_sections/ پیدا نشد" in out, f"rc={rc}")
check("C2: پیامِ راهنمای فارسی چاپ شد", "بهتنهایی کافی نیست" in out)

# ── D) مهر: تلاشِ دومِ بلافاصله رد میشود (بدونِ رفت‌وبرگشتِ شبکه) ───────
rc, out2 = run_import(dC, timeout=60)
check("D1: تلاشِ دوم توسطِ مهر رد شد (پیامِ دانلود نیامد)",
      rc != 0 and "دانلودِ خودترمیم" not in out2
      and "manga_sections/ پیدا نشد" in out2)
check("D2: پوشهٔ خالیِ بازی‌خورده ساخته نشد (بدونِ MANIFEST و بدونِ py)",
      not any(n.endswith(".py")
              for n in os.listdir(os.path.join(dC, "manga_sections")))
      if os.path.isdir(os.path.join(dC, "manga_sections")) else True)

print()
n_ok = sum(1 for _, ok, _ in results if ok)
print(f"—— {n_ok}/{len(results)} چکِ خودترمیمیِ لودر پاس شد ——")
sys.exit(0 if n_ok == len(results) else 1)
