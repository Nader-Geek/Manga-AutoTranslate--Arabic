#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ v1.14.252 — دیباگِ آبیِ det + فیکسِ خواهرانِ پنجرهٔ سیستم (فیلترِ ۲۲۵).

بازتولیدِ باگِ فصلِ ۸۸ (لاگِ 8e7dd2bc — the-apocalypse-is-here-chapter-88):
حبابِ «THIS DEPARTMENT STORE IS DIVIDED INTO THE EAST WING AND THE WEST
WING.» → ۴ خطِ split؛ خطِ چهارم («THE WEST WING.») را فیلترِ ۲۲۵ با
شباهتِ فازیِ ۰٫۷۷ (آستانهٔ ۰٫۶۲) + ۱۰px همپوشانی، «هممتنِ» خطِ سوم میپنداشت
و حذف میکرد (کوچکتر میمُرد).

اجرا:
  python3 scripts/test_v114252_det_debug.py          # فقط ریاضیاتِ فیلتر
  python3 scripts/test_v114252_det_debug.py --bubble # + ساختِ تصویرِ حبابِ ۴خطی
                                                     #   → /tmp/manga252/test_bubble.png
                                                     #   سپس: python3 manga.py -i آن
                                                     #   --clean-only --cpu --debug …
انتظار:
  • فیلترِ ۲۲۵ رویِ خواهرانِ هم‌والد دیگر kill نمیزند (فیکسِ ۲۵۲)
  • پاسِ detِ خام (--debug): [🔍252] با جعبههایِ آبی رویِ همان عکسِ دیباگ
  • خطِ گم‌شده = جعبهٔ آبی بدونِ قرمز + لاگِ «det دید ولی rec/فیلتر نگرفت»
"""
import difflib
import sys

A = "the east wing and"   # خطِ سومِ حباب (میماند — بزرگتر)
B = "the west wing."      # خطِ چهارمِ حباب (قبلاً حذف میشد — کوچکتر)


def check_filter_math() -> int:
    """همان تصمیمی که _dedup_duplicate_text_regions میگرفت — قبل/بعدِ فیکس."""
    r = difflib.SequenceMatcher(None, A, B).ratio()
    # rectهای واقعیِ لاگ: #09=(154,10694,349,43) و خط۴≈(185,10726,284,46)
    a1 = (154, 10694, 154 + 349, 10694 + 43)
    b1 = (185, 10726, 185 + 284, 10726 + 46)
    ix = max(0.0, min(a1[2], b1[2]) - max(a1[0], b1[0]))
    iy = max(0.0, min(a1[3], b1[3]) - max(a1[1], b1[1]))
    inter = ix * iy
    aa = (a1[2] - a1[0]) * (a1[3] - a1[1])
    ab = (b1[2] - b1[0]) * (b1[3] - b1[1])
    ov = inter / min(aa, ab)
    kill_before = (r >= 0.62) and (ov >= 0.18)
    print(f"شباهتِ فازی = {r:.3f} (آستانهٔ ۰٫۶۲) | همپوشانی = {ov:.3f} "
          f"(آستانهٔ ۰٫۱۸)")
    print(f"قبل از فیکسِ ۲۵۲: kill={'بله ← باگ!' if kill_before else 'خیر'}")
    print("بعد از فیکسِ ۲۵۲: خواهرِ هم‌والدِ پنجرهٔ سیستم "
          "(sys_split + cover_rect یکسان) → مستثنا ← زنده میماند")
    return 0 if r >= 0.62 and ov >= 0.18 else 1


def make_bubble() -> int:
    """تصویرِ حبابِ ۴خطی برایِ تستِ دستیِ پایپلاین با --debug."""
    from PIL import Image, ImageDraw, ImageFont

    out_dir = "/tmp/manga252"
    import os
    os.makedirs(out_dir, exist_ok=True)
    img = Image.new("RGB", (900, 1300), (235, 235, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 880, 640], outline=(60, 60, 60), width=3)
    d.rectangle([20, 660, 880, 1280], outline=(60, 60, 60), width=3)
    try:
        f = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    except Exception:
        f = ImageFont.load_default()
    d.ellipse([80, 90, 620, 430], fill="white", outline="black", width=4)
    y = 135
    for ln in ("THIS DEPARTMENT", "STORE IS DIVIDED INTO",
               "THE EAST WING AND", "THE WEST WING."):
        d.text((160, y), ln, fill="black", font=f)
        y += 68
    d.polygon([(240, 420), (200, 560), (330, 428)],
              fill="white", outline="black")
    d.ellipse([180, 720, 760, 1090], fill="white", outline="black", width=4)
    y = 775
    for ln in ("THE PLACE YOU'RE IN", "RIGHT NOW IS", "THE WEST WING."):
        d.text((260, y), ln, fill="black", font=f)
        y += 68
    d.polygon([(560, 1080), (640, 1230), (690, 1075)],
              fill="white", outline="black")
    p = os.path.join(out_dir, "test_bubble.png")
    img.save(p)
    print(f"saved: {p}")
    print("سپس: python3 manga.py -i " + p + " --clean-only --cpu --debug "
          "--font fonts/Vazirmatn-Bold.ttf -o /tmp/manga252/out")
    return 0


if __name__ == "__main__":
    rc = check_filter_math()
    if "--bubble" in sys.argv:
        rc |= make_bubble()
    sys.exit(rc)
