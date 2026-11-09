#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_manga.py — ساختِ تکفایلِ manga.py از پوشهٔ manga_sections/

از v1.14.250 منبعِ اصلیِ کدِ موتور، فایلهایِ manga_sections/ هستند
(هر موضوع یک فایل: نصب، سختافزار، LaMa، تشخیص، OCR، API، ترجمه،
پاکسازی، رندر، استخراج، خروجی، ...). این اسکریپت همهٔ آنها را بهترتیبِ
شمارهٔ فایل بههم میچسباند و «manga.py»یِ تکی میسازد.

چرا تکفایل؟ چون همهٔ مسیرهایِ توزیع (آپدیترِ خودکارِ دسکتاپ، لانچرِ
اندروید، APK و دانلودِ مستقیم از GitHub) فقط «یک فایلِ» manga.py
میگیرند — تکفایل ماندنِ خروجی یعنی هیچ نصبِ قدیمیای نمیشکند.

قواعد:
  • فایلهایِ بخش با پیشوندِ عددی مرتب میشوند (00، 10، ...، 300) —
    ترتیبِ چسباندن = ترتیبِ عددِ ابتدایِ نام.
  • خطهای بینِ «# BUILD-STRIP-START» و «# BUILD-STRIP-END» (سربرگهایِ
    راهنما و کلاسِ پوششیِ قطعههایِ کلاس) در بیلد حذف میشوند.
  • ویرایش فقط در manga_sections/ — manga.py ساخته میشود، دست نزنید!

استفاده:
  python scripts/build_manga.py           # ساختِ manga.py
  python scripts/build_manga.py --check   # فقط چکِ همخوانی (برای CI)
  python scripts/build_manga.py --list    # فهرستِ بخشها
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEC_DIR = os.path.join(ROOT, "manga_sections")
OUT_PATH = os.path.join(ROOT, "manga.py")

STRIP_START = "# BUILD-STRIP-START"
STRIP_END = "# BUILD-STRIP-END"


def _section_sort_key(name: str):
    i = 0
    while i < len(name) and name[i].isdigit():
        i += 1
    return (int(name[:i]) if i else 10 ** 9, name)


def section_files():
    if not os.path.isdir(SEC_DIR):
        return []
    names = [n for n in os.listdir(SEC_DIR)
             if n.endswith(".py") and n[:1].isdigit()]
    return sorted(names, key=_section_sort_key)


def _read_section(path: str):
    """محتوایِ یک بخش را میخواند و بلاکهایِ STRIP را حذف میکند."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    out, stripping = [], False
    saw_marker = False
    for ln in lines:
        if ln.strip() == STRIP_START:
            stripping, saw_marker = True, True
            continue
        if stripping:
            if ln.strip() == STRIP_END:
                stripping = False
            continue
        out.append(ln)
    if stripping:
        raise ValueError("بلاکِ STRIP بسته نشد: %s" % path)
    if out and not out[-1].endswith("\n"):
        pass  # خطهای بدونِ \\n در join نهایی مدیریت میشود
    return out, saw_marker


def build_source(stats=None):
    parts = []
    for name in section_files():
        lines, _ = _read_section(os.path.join(SEC_DIR, name))
        if stats is not None:
            stats.append((name, len(lines)))
        if lines:
            parts.append("\n".join(lines) + "\n")
    return "".join(parts)


def main(argv):
    if "--list" in argv:
        stats = []
        build_source(stats)
        if not stats:
            print("پوشهٔ manga_sections/ خالی است یا وجود ندارد.")
            return 1
        total = 0
        for name, n in stats:
            print(f"  {name:38s} {n:6d} خط")
            total += n
        print(f"  {'— مجموع':38s} {total:6d} خط")
        return 0

    stats = []
    src = build_source(stats)
    if not src:
        print("❌ هیچ بخشی برایِ بیلد پیدا نشد (manga_sections/ ؟)")
        return 1

    if "--check" in argv:
        try:
            with open(OUT_PATH, "r", encoding="utf-8", newline="") as f:
                cur = f.read()
        except OSError:
            print("❌ manga.py وجود ندارد — اول یک بار بدونِ --check بیلد کنید.")
            return 1
        if cur == src:
            print("✔ manga.py با بخشها همخوان است (%d خط، %d بایت)."
                  % (src.count("\n"), len(src.encode('utf-8'))))
            return 0
        print("❌ manga.py با manga_sections/ همخوان نیست — دوباره بیلد کنید:")
        print("   python scripts/build_manga.py")
        return 1

    # کامپایلِ سریعِ سینتکس قبل از نوشتن — manga.py خراب تحویل ندهیم
    try:
        compile(src, "manga.py", "exec")
    except SyntaxError as e:
        print("❌ سینتکسِ بیلدشده خراب است — نوشتن لغو شد: خط %s: %s"
              % (e.lineno, e.msg))
        return 1

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    print("✔ manga.py ساخته شد — %d بخش، %d خط، %d بایت."
          % (len(stats), src.count("\n"), len(src.encode('utf-8'))))
    for name, n in stats:
        print(f"    {name:38s} {n:6d} خط")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
