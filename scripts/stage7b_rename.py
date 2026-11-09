# -*- coding: utf-8 -*-
"""v1.14.249 — مرحلهٔ ۷b: تغییرِ نام مرجع → نامِ خنثی (mt/مرجع) در «همهٔ» فایلهایِ ریپو
دستورِ سازنده: «و کلمه مرجع عوض کن هرجا کد باشه سازندش نفهمه ازش گرفتم»"""
import re, subprocess, sys

ROOT = '/home/z/manga-work'

FILES = """manga.py
manga_app.py
PROGRESS.md
memory.md
android/README.md
android/app/src/main/python/bridge.py
android/app/src/main/python/extract_ui.py
android/app/src/main/python/onnxruntime/__init__.py
android/app/src/main/java/com/amirwolf/mangatranslator/MainActivity.kt""".split()
# + همهٔ اسکریپتها
out = subprocess.run(['rg', '-li', 'مرجع', 'scripts/', '--glob', '!*.pyc'],
                     capture_output=True, text=True, cwd=ROOT)
FILES += [f for f in out.stdout.strip().split('\n') if f]

# ── ۱) ترکیبهای خاص (طولانیترین اول) ──
COMPOUNDS = [
    ('اپِ مرجع', 'اپِ مرجع'),
    ('اپِ مرجع', 'اپِ مرجع'),
    ('APKِ اپِ مرجع', 'APKِ اپِ مرجع'),
    ('اپِ مرجع', 'اپِ مرجع'),
    ('اپِ مرجع', 'اپِ مرجع'),
    ('اپِ مرجع', 'اپِ مرجع'),
    ('اپِ مرجع', 'اپِ مرجع'),
    ('اپِ مرجع', 'اپِ مرجع'),
    ('MT polygon clean', 'MT polygon clean'),
    ('AutoRetry مرجع', 'AutoRetry مرجع'),
    ('رقیب', 'رقیب'),
    ('medium', 'medium'),
    # سه بلوکِ خاصِ تنظیمِ top_p/تنظیمِ دما
    ('        # v1.14.243 — مرجع: تنظیمِ top_p (Preferences «تنظیمِ top_p» پیشفرض 0.9؛\n'
     '        # Math.Clamp(0..1)) — حالا مثلِ خودِ مرجع از تنظیمات میآید نه هاردکد',
     '        # v1.14.243 — تنظیمِ top_p (ذخیره در تنظیمات؛ پیشفرض 0.9؛ کلمپ 0..1)\n'
     '        # — حالا مثلِ خودِ مرجع از تنظیمات میآید نه هاردکد'),
    ('        # v1.14.243 — temperature/topP از تنظیماتِ کاربر (مرجع: تنظیمِ دما/\n'
     '        # تنظیمِ top_p). استثنایِ gemini-3.6-flash (۰.۴/۰.۷) عینِ مرجع فقط وقتی',
     '        # v1.14.243 — temperature/topP از تنظیماتِ کاربر (مرجع: دما و\n'
     '        # top_pِ ذخیرهشده). استثنایِ gemini-3.6-flash (۰.۴/۰.۷) عینِ مرجع فقط وقتی'),
    ('            # (تنظیمِ دما / تنظیمِ top_p: پیشفرضِ هر دو = ۰.۷/۰.۹؛ دکمههایِ\n'
     '            # مرجع: temp ±۰.۱ با کلمپِ ۰..۱.۵، topP ±۰.۰۵ با کلمپِ ۰.۱..۱).',
     '            # (دما / top_pِ قابلِ تنظیم: پیشفرضِ هر دو = ۰.۷/۰.۹؛ دکمههایِ\n'
     '            # کم/زیاد: temp ±۰.۱ با کلمپِ ۰..۱.۵، topP ±۰.۰۵ با کلمپِ ۰.۱..۱).'),
]

# ── ۲) نامهای داخلیِ اپِ مرجع (ردپای قابلِ جستجو) ──
INTERNAL = [
    ('سازندهٔ درخواستِ متنیِ OpenAI در مرجع', 'سازندهٔ درخواستِ متنیِ OpenAI در مرجع'),
    ('سازندهٔ درخواستِ متنیِ بومیِ Gemini در مرجع', 'سازندهٔ درخواستِ متنیِ بومیِ Gemini در مرجع'),
    ('مسیرِ استریمِ ترجمه در مرجع', 'مسیرِ استریمِ ترجمه در مرجع'),
    ('راستیآزما/جابهجاییِ برش با تشخیصِ متن در مرجع', 'راستیآزما/جابهجاییِ برش با تشخیصِ متن در مرجع'),
    ('سرویسِ برشِ مرجع', 'سرویسِ برشِ مرجع'),
    ('پارسرِ جوابِ صفحه‌محورِ مرجع', 'پارسرِ جوابِ صفحه‌محورِ مرجع'),
    ('ویرایشگرِ قوانینِ مرجع', 'ویرایشگرِ قوانینِ مرجع'),
    ('نرمال‌سازِ مقایسهٔ متنِ مرجع', 'نرمال‌سازِ مقایسهٔ متنِ مرجع'),
    ('حلقهٔ استریمِ صفحه‌محور', 'حلقهٔ استریمِ صفحه‌محور'),
    ('صفحهٔ اصلیِ مرجع', 'صفحهٔ اصلیِ مرجع'),
    ('صفحهٔ تنظیماتِ مرجع', 'صفحهٔ تنظیماتِ مرجع'),
    ('تنظیمِ دما', 'تنظیمِ دما'),
    ('تنظیمِ top_p', 'تنظیمِ top_p'),
]

# ── ۳) شناسهها (کلمهٔ کامل؛ طولانیترین اول) ──
IDENTS = {
    'MtLadderOCR': 'MtLadderOCR',
    'MT_JP_SYSTEM_RULE': 'MT_JP_SYSTEM_RULE',
    'MT_JP_USER_DIRECTIVE': 'MT_JP_USER_DIRECTIVE',
    'MT_RESPONSE_SCHEMA_TEXT': 'MT_RESPONSE_SCHEMA_TEXT',
    'MT_SYSTEM_PROTOCOL_ITEMS': 'MT_SYSTEM_PROTOCOL_ITEMS',
    'MANGA_DEBUG_MT': 'MANGA_DEBUG_MT',
    'MANGA_MT_MODE': 'MANGA_MT_MODE',
    'MANGA_DUMP_MASK_3': 'MANGA_DUMP_MASK_3',
    '_MT_MODES': '_MT_MODES',
    '_MT_MODE_FA': '_MT_MODE_FA',
    '_MT_PAGE_BLOCK_RE': '_MT_PAGE_BLOCK_RE',
    '_MT_PURGE_EXTRA': '_MT_PURGE_EXTRA',
    '_MT_STATS': '_MT_STATS',
    '_apply_mt_pages': '_apply_mt_pages',
    '_mt_boost_crop': '_mt_boost_crop',
    '_mt_how': '_mt_how',
    '_mt_map_boxes': '_mt_map_boxes',
    '_mt_max': '_mt_max',
    '_mt_norm': '_mt_norm',
    '_mt_pages_payload': '_mt_pages_payload',
    '_mt_pages': '_mt_pages',
    '_mt_polygon_clean': '_mt_polygon_clean',
    '_mt_ring_samples': '_mt_ring_samples',
    '_mt_speed_report': '_mt_speed_report',
    '_mt_stats_note': '_mt_stats_note',
    '_mt_step': '_mt_step',
    '_mt_wait': '_mt_wait',
    '_n_mt': '_n_mt',
    'mt_system_instruction': 'mt_system_instruction',
    'mt_user_prompt': 'mt_user_prompt',
    '_ker31': '_ker31',
    '_ker3': '_ker3',
}

total = {}
for rel in FILES:
    path = f'{ROOT}/{rel}'
    src = open(path, encoding='utf-8').read()
    orig = src
    for old, new in COMPOUNDS:
        src = src.replace(old, new)
    for old, new in INTERNAL:
        src = src.replace(old, new)
    for old in sorted(IDENTS, key=len, reverse=True):
        src = re.sub(r'\b' + re.escape(old) + r'\b', IDENTS[old], src)
    src = re.sub(r'\bK3\b', 'مرجع', src)
    src = re.sub(r'\bk3\b', 'مرجع', src)
    if src != orig:
        open(path, 'w', encoding='utf-8').write(src)
        total[rel] = sum(1 for a, b in zip(orig.split('\n'), src.split('\n')) if a != b)

print(f"{len(total)} فایل تغییر کرد:")
for f, n in sorted(total.items(), key=lambda kv: -kv[1]):
    print(f"  {f}: {n} خط")
