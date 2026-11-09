#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.199 — دقیقاً طبقِ دستورِ سازنده:

  «چرا هر عکسی استخراج میشه میره مترجم — حداقل ۳۰ تا ۳۰ تا جمع کنه
   ترجمه کنه… جای اصلیشون بزاره بخونم»
  «اول کامل استخراج کنه دو طرفه + پاکسازی یک طرفه»
  «استخراج تموم شد پاکسازی دو طرفه»

  ۱. هیچ متنی حینِ استخراج به مترجم نمیرود: فقط «یک» فلاش بعد از
     اتمامِ کاملِ استخراج وجود دارد (force=True بعد از joinِ دو کارگر).
  ۲. فلاشِ پایانی بافر را به بستههایِ ۳۰تاییِ «متوازن» میشکند و
     «پشتسرهم» (trans_pool تک‌نمونه — نه موازی) میفرستد؛ با تمامِ
     هر بسته، ترجمههایِ همان بسته رویِ صفحاتِ خودشان مینشینند.
  ۳. در حالتِ درخواستِ واحد، translate_regions هم بستهها را
     پشتسرهم میبرد (workers=1 — «موازی» ممنوع).
  ۴. تقسیمِ متوازن: هیچ بستهای زیرِ ۳۰ نیست وقتی کل ≥ ۳۰ است
     (۱۳۰ → ۳۳/۳۳/۳۲/۳۲؛ نه ۳۰/۳۰/۳۰/۳۰/۱۰).
  ۵. رگرسیون: اسلاتِ صریحِ ۱۹۸ + دوطرفه/دوفازی/مرجعِ ۱۹۷.
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

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


print("── بارگذاریِ manga.py ──")
import manga  # noqa: E402

gate(manga.APP_VER == "1.14.199", f"APP_VER = {manga.APP_VER}")
src = io.open("manga.py", encoding="utf-8").read()

print("── ۱. هیچ ترجمهای حینِ استخراج ──")
gate(src.count("_flush_translate_buffer(") == 2,
     "فقط «یک» فراخوانیِ فلاش در کلِ فایل (تعریف + صدا)")
gate("_flush_translate_buffer(force=True)" in src,
     "فلاش force=True — بعد از joinِ هر دو کارگرِ استخراج")
_i_flash = src.index("_flush_translate_buffer(force=True)")
_i_join = src.index("_t_bwd.join()")
_i_extdone = src.index('extraction_done["v"] = True')
gate(_i_join < _i_extdone < _i_flash,
     "ترتیب: پایانِ هر دو کارگرِ استخراج → پرچمِ فاز ۲ → فلاشِ ترجمه")
_qd = src[src.index("def _queue_dialogues"):
          src.index("if getattr(self, \"clean_only\", False):")]
gate("_flush_translate_buffer" not in _qd,
     "_queue_dialogues هیچ فلاشی نمیکند — صفِ دیالوگ فقط انبار میکند")
gate("_translate_chunk_bg(" not in _qd,
     "صفِ دیالوگ مستقیماً هم چیزی به مترجم نمیدهد")

print("── ۲. فلاشِ پایانی: ۳۰تا۳۰تایِ پشتسرهم ──")
_fl = src[src.index("def _flush_translate_buffer"):
          src.index("def _queue_dialogues")]
gate("_split_one_request_batches(\n                dialogue_buffer" in _fl.replace("            ", "                ") or
     "_split_one_request_batches(" in _fl,
     "فلاش بافر را با _split_one_request_batches میشکند")
gate("for _g in _groups:\n                _translate_chunk_bg(_g)" in _fl,
     "هر بسته جداگانه به صفِ ترجمه میرود — trans_pool تک‌نمونه = پشتسرهم")
gate("۳۰تا۳۰تا" in _fl, "لاگِ فلاش صریح میگوید ۳۰تا۳۰تا")
gate("def _one_request_caps()" in src and
     'os.environ.get("MANGA_ONE_REQ_MAX", "30") or 30' in src,
     "سقفِ پیشفرض = ۳۰ (MANGA_ONE_REQ_MAX قابلِ تغییر)")

print("── ۳. درخواستِ واحد = هرگز موازی ──")
_tr = src[src.index("def translate_regions"):
          src.index("def _translate_regions_batch")]
gate("if getattr(self, \"chapter_one_request\", False):\n                workers = 1" in _tr,
     "در حالتِ درخواستِ واحد workers=1 — بستهها پشتسرهم")

print("── ۴. تقسیمِ متوازنِ ۳۰تایی (تستِ کارکردی) ──")


def _reg(i, txt="سلام"):
    return manga.TextRegion(id=i, boxes=[], source_text=txt)


g = manga._split_one_request_batches([_reg(i) for i in range(5)])
gate(len(g) == 1 and len(g[0]) == 5, "۵ دیالوگ → دقیقاً یک درخواست")
g = manga._split_one_request_batches([_reg(i) for i in range(30)])
gate(len(g) == 1 and len(g[0]) == 30, "۳۰ دیالوگ → دقیقاً یک درخواست (سقف)")
g = manga._split_one_request_batches([_reg(i) for i in range(31)])
gate([len(x) for x in g] == [31],
     f"۳۱ دیالوگ → { [len(x) for x in g] } (یک بستهٔ ۳۱تایی — نه بستهٔ ۱تاییِ لنگ)")
g = manga._split_one_request_batches([_reg(i) for i in range(130)])
gate([len(x) for x in g] == [33, 33, 32, 32],
     f"۱۳۰ دیالوگ → { [len(x) for x in g] } (متوازن — نه ۳۰/۳۰/۳۰/۳۰/۱۰)")
gate(all(len(x) >= 30 for x in g), "هیچ بستهای زیرِ ۳۰ نیست")
g = manga._split_one_request_batches([_reg(i) for i in range(61)])
gate([len(x) for x in g] == [31, 30], f"۶۱ دیالوگ → { [len(x) for x in g] }")
g = manga._split_one_request_batches([_reg(i) for i in range(200)])
gate(len(g) == 6 and all(30 <= len(x) <= 35 for x in g),
     f"۲۰۰ دیالوگ → {len(g)} بستهٔ { [len(x) for x in g] }")
_ids = [r.id for grp in g for r in grp]
gate(_ids == list(range(200)), "ترتیبِ روایی دستنخورده")
g = manga._split_one_request_batches([_reg(i, "x" * 900) for i in range(40)])
gate(all(sum(len(r.source_text) for r in x) <= 10000 for x in g),
     f"سقفِ نویسه محترم است → { [len(x) for x in g] }")
gate(manga._split_one_request_batches([], 30, 10000) == [], "بافرِ خالی → هیچ")

print("── ۵. رگرسیونِ ۱۹۸ (اسلاتِ صریح) ──")
n_slot = src.count("slot=page_i + 1")
gate(n_slot >= 5, f"اسلاتِ صریحِ صفحه در همهٔ مسیرها ({n_slot} مورد)")
gate("def _live_page_dump(out_file: str, key: Optional[str] = None,\n                    slot: Optional[int] = None)" in src,
     "_live_page_dump slot دارد")

print("── ۶. رگرسیونِ ۱۹۷ (دوطرفه + دوفازی + مرجع) ──")
gate("def _claim_ext(role" in src, "استخراج دوطرفه سرِ جایش")
gate('extraction_done["v"] = True' in src, "پرچمِ پایانِ استخراج")
gate('thread_name_prefix="clean2"' in src, "کارگرِ دومِ پاکسازی (پایین→بالا)")
gate("MANGA_TIMEOUT_RETRIES" in src, "AutoRetry همهمدلِ مرجع")
gate("60.0 + 1.5 * len(work_regions)" in src, "سقفِ زمانیِ متناسبِ حجم")
gate("_salvage_stream_items" in src, "پارسرِ افزایشیِ استریم")
gate("فهرستِ بلند است: اینها حبابهایِ دیالوگِ مانگا هستند" in src,
     "دستورِ ضدِ کتابیِ پرامپت سرِ جایش")

print("── ۷. نسخه ──")
_ver = io.open("VERSION", encoding="utf-8").read()
gate("versionName=1.14.199" in _ver, "VERSION = 1.14.199")
gate("versionCode=204" in _ver, "versionCode = 204")
_g = io.open("android/app/build.gradle.kts", encoding="utf-8").read()
gate("versionCode = 204" in _g and 'versionName = "1.14.199"' in _g,
     "build.gradle.kts همگام")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ مردود:")
    for m in FAILS:
        print(f"  - {m}")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.199 سبز")
