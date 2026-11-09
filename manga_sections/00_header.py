# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 هدِ فایل — docstring، importها، APP_VER و ثابتهای زمانِ شروع
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ⚠️ این فایل بهصورتِ خودکار ساخته شده — «scripts/build_manga.py»
# (از v1.14.250 منبعِ اصلیِ کد، فایلهایِ پوشهٔ manga_sections/ است؛
# این فایل را مستقیم ویرایش نکنید — برایِ ساختِ دوباره: python scripts/build_manga.py)
from __future__ import annotations
import time as _time_t0  # v1.14.68 — سنجشِ زمانِ importها (باید اول باشد)
_T0_IMPORT = _time_t0.time()
APP_VER = "1.14.250"

# v1.14.246 — پرامپتِ classic کلاً حذف شد (دستورِ سازنده) — تنها سبکها: auto / professional / lite

# ── v1.14.242 — پرامپتهای مرجع — استخراجِ بایت‌به‌بایت از APKِ اپِ مرجع ──
# (LibAssemblyStore → XALZ/LZ4 → اسمبلی → دیکدِ C#؛ سه کپچرِ واقعیِ ارسالیِ
# سازنده [تک‌صفحه lite، تک‌صفحه pro، شش‌صفحه pro] با همین ثابتها بایت‌به‌بایت
# بازسازی و تطبیق داده شدند — حتی `\n` لفظی + CRLF عیناً حفظ شده است.)
# سبکِ درخواست (حالتِ نوشتاریِ مرجع = «عکسِ فیک»):
#   system = SYSTEM BEHAVIOR PROTOCOL (۲..۶) [+ بلوکِ ژاپنی] [+ بندِ ۷: اسکیما]
#   user   = TASK: Translate… + [بلوکِ ژاپنی] + TRANSLATION RULES: {pro|lite}
#            + INPUT PAGES AND DIALOGUES (JSON): [{filename, dialogues}]
# هیچ عکسی ارسال نمی‌شود — filename فقط شناسهٔ صفحه است (01.png / slice_0001.webp).
# مرجع همهٔ متنها را در «یک» درخواست می‌فرستد و هیچ بریف/خلاصهٔ داستانی ندارد.
# قوانینِ «حرفه‌ای» (پیشفرضِ مرجع — Prompts[0]: «پرامپت ترجمه حرفه‌ای (مدل های Flash, Pro)»)
