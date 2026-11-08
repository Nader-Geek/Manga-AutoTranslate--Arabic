# -*- coding: utf-8 -*-
"""v1.14.235 — تستِ منطقِ فیکسِ «فایلِ محلیِ عکس میدم ارور میده».

سناریوی کاربر (لاگِ 234 روی ویندوز):
  ۱) آپلودِ ۲ عکس → manga_app.py در <out>/<sid12>/input_batch کپی میکند
     → src = «مسیر۱,مسیر۲»
  ۲) پاک‌سازیِ استارتِ همان تابع همهٔ زیرپوشه‌ها را rmtree میکرد
     → input_batch هم پاک میشد
  ۳) موتور: os.path.isfile → False → مسیر به requests سپرده میشد
     → «No connection adapters were found for 'C:\\…'»

این تست همان دو فیکس را شبیه‌سازی میکند:
  فیکس A (manga_app.py): استثنای input_batch در پاک‌سازی
  فیکس B (manga.py): گاردِ مسیرِ محلی قبل از requests.get
"""
import os
import re
import shutil
import sys
import tempfile

FAILED = []


def check(name, cond, extra=""):
    tag = "✅" if cond else "❌"
    print(f"  {tag} {name}" + (f" — {extra}" if extra else ""))
    if not cond:
        FAILED.append(name)


# ── فیکس A: پاک‌سازی با استثنای input_batch ─────────────────────────
print("── تست A: پاک‌سازیِ استارت نباید input_batch را پاک کند ──")
tmp = tempfile.mkdtemp(prefix="manga235_")
try:
    # شبیه‌سازیِ دقیقِ توالی manga_app.py
    user_out_dir = os.path.join(tmp, "workspace", "output", "5f295da5e47f")
    batch_dir = os.path.join(user_out_dir, "input_batch")
    os.makedirs(batch_dir, exist_ok=True)
    # فایلهای آپلودی (مثل file_001.jpg / file_002.webp کاربر)
    f1 = os.path.join(batch_dir, "file_001.jpg")
    f2 = os.path.join(batch_dir, "file_002.webp")
    open(f1, "wb").write(b"JPEGDATA1")
    open(f2, "wb").write(b"WEBPDATA2")
    # خروجیهای اجرای قبلی (باید پاک شوند — v1.14.210)
    old_out = os.path.join(user_out_dir, "chapter1.pdf")
    old_cache = os.path.join(user_out_dir, "cache")
    os.makedirs(old_cache, exist_ok=True)
    open(old_out, "wb").write(b"OLD")
    open(os.path.join(old_cache, "page1.json"), "wb").write(b"{}")
    src = ",".join(os.path.join(batch_dir, n) for n in sorted(os.listdir(batch_dir)))

    up_files = [f1, f2]  # → شرطِ پاک‌سازی فعال است (مثلِ اجرای واقعی)
    if up_files:
        # ── همان حلقهٔ فیکس‌شدهٔ manga_app.py (حرف‌به‌حرف) ──
        for _n in os.listdir(user_out_dir):
            if _n == "input_batch":
                continue
            _p = os.path.join(user_out_dir, _n)
            if os.path.isdir(_p):
                shutil.rmtree(_p, ignore_errors=True)
            else:
                try:
                    os.remove(_p)
                except Exception:
                    pass

    check("input_batch زنده ماند", os.path.isdir(batch_dir))
    check("file_001.jpg سالم", os.path.isfile(f1) and os.path.getsize(f1) == 9)
    check("file_002.webp سالم", os.path.isfile(f2) and os.path.getsize(f2) == 9)
    check("خروجیِ کهنه پاک شد (v1.14.210)", not os.path.exists(old_out))
    check("کشِ resume کهنه پاک شد", not os.path.exists(old_cache))

    # ── گیتِ اولِ manga.py: فایلهای محلی چندگانه → بدون دانلود ──
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".avif",
                  ".heic", ".heif"}

    def _local_img(s):
        s = (s or "").strip()
        if s.lower().startswith("file://"):
            s = s[7:]
        if (s and os.path.isfile(s)
                and os.path.splitext(s)[1].lower() in IMAGE_EXTS):
            return s
        return None

    parts = [p for p in re.split(r"[,\n\r\t]+", src) if p.strip()]
    loc = [_local_img(p) for p in parts]
    check("گیتِ «فایل محلی — بدون دانلود» فعال شد",
          bool(parts) and all(loc) and len(loc) == 2)

    # ── اگر فایل غایب باشد: گاردِ فیکس B (قبل از requests) ──
    for _p in [f1, f2]:
        os.remove(_p)
    loc2 = [_local_img(p) for p in parts]
    check("فایل غایب → گیت رد میشود (به URL-برنچ میرود)",
          not all(loc2))

    # گاردِ فیکس B: رِجِکسِ مسیرِ محلی (حرف‌به‌حرفِ manga.py)
    def is_local_path(u):
        return (re.match(r"^[A-Za-z]:[\\/]", u)
                or u.startswith("\\\\")
                or (u.startswith("/")
                    and not u.lower().startswith("//")))

    samples = {
        r"C:\Users\AmirWolf\Desktop\Manga-AutoTranslate-main\workspace\output\5f295da5e47f\input_batch\file_001.jpg": True,
        r"c:\x\y.png": True,
        r"D:/pics/2.webp": True,
        r"\\NAS\share\a.jpg": True,
        "/home/u/a.jpg": True,
        r"C:\missing\ghost.jpg": True,
        "https://site.com/page.jpg": False,
        "http://site.com/x.png?w=100": False,
        "//site.com/img/1.jpg": False,
        "https://raw.githubusercontent.com/a/b/main/1.jpg": False,
    }
    for u, want in samples.items():
        check(("مسیر → " if want else "URL  → ") + u[:58],
              bool(is_local_path(u)) == want)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILED:
    print(f"❌ {len(FAILED)} تست رد شد: {FAILED}")
    sys.exit(1)
print("✅ همهٔ تستها پاس شدند.")
