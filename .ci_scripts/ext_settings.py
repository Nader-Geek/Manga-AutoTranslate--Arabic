#!/usr/bin/env python3
"""v1.14.134 — سازندهٔ manga_settings.xml برای گیتِ «مجموعهٔ گستردهٔ» امولاتور.

مصرف: python3 ext_settings.py <filename-on-device> <ocr_lang> > settings.xml
(ورکفلو: android-emulator.yml — بخشِ Run APK on extended test set)"""
import sys

fn = sys.argv[1] if len(sys.argv) > 1 else "ext_in.jpg"
lang = sys.argv[2] if len(sys.argv) > 2 else "en"

xml = (
    "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n"
    "<map>\n"
    "    <string name=\"inp_upload_path\">"
    "/data/user/0/com.amirwolf.mangatranslator/files/ext_" + fn +
    "</string>\n"
    "    <string name=\"fake_test\">true</string>\n"
    "    <string name=\"clean_only\">true</string>\n"
    "    <string name=\"web_debug\">true</string>\n"
    "    <string name=\"clean_method\">lama-manga</string>\n"
    "    <string name=\"out_fmt\">PDF</string>\n"
    "    <string name=\"readord\">rtl</string>\n"
    # v1.14.186 — ریشهٔ شکستِ گیتِ چندزبانه (183→185): اپِ نیتیو زبانِ
    # OCR را فقط از فیلدِ UI با id «manga_ocr_lang» میخواند
    # (MainActivity firstNonEmpty(o, "manga_ocr_lang", "ocr_lang") —
    # o همیشه manga_ocr_lang دارد)؛ کلیدِ «ocr_lang» هیچ‌وقت خوانده
    # نمیشد → دکمه رویِ پیشفرضِ en میماند → گاردِ CJKِ v1.14.154 کل
    # خطهایِ ژاپنی/چینی را حذف میکرد → گیت FAIL. هر دو کلید نوشته
    # میشود؛ سازگاریِ کامل.
    "    <string name=\"manga_ocr_lang\">" + lang + "</string>\n"
    "    <string name=\"ocr_lang\">" + lang + "</string>\n"
    "    <boolean name=\"battery_asked\" value=\"true\" />\n"
    "    <boolean name=\"viewer_hint_v3\" value=\"true\" />\n"
    "</map>\n"
)
sys.stdout.write(xml)
