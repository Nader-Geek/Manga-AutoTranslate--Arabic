#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.196 — سبکِ مرجع در manga.py:

  ۱. پارسرِ بخشندهٔ استریم (_salvage_stream_items): از جریانِ ناقصِ JSON
     فقط شیءهایِ «کاملِ» {id, translation} را بیرون میکشد؛ آیتمِ نیمهکاره
     دستنخورده میماند؛ escapeهایِ واقعی (\n، \"، \\) درست باز میشوند؛
     id تکراری دوباره اعمال نمیشود.
  ۲. درخواستِ کلِ فصل: با chapter_one_request=True، translate_regions
     کلِ بچ را در «یک» درخواست میفرستد (نه بستههایِ ۱۵تایی) — با یک
     فیکِ سبکِ translate_regions که فقط مسیرِ شبکه را میقاپد.
  ۳. سلامتِ نسخه: APP_VER = 1.14.196.
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

gate(manga.APP_VER == "1.14.196", f"APP_VER = {manga.APP_VER}")

print("── ۱. پارسرِ بخشندهٔ استریم ──")
applied = {}


def _on_item(rid, tr):
    applied[rid] = tr


# جریانِ ناقص: دو شیء کامل + یک شیء نیمهکاره + یک شیء کاملِ escapeدار
_partial = (
    '[{"id":3,"translation":"اول"\n'
    ',{"id":7,"translation":"دوم اینجاست"},\n'
    '{"id":9,"translation":"سومی که نصفه ماند، هنوز نقل قولش بسته نش'
)

manga.MangaTranslator._salvage_stream_items(_partial, _on_item)
gate(applied.get(3) == "اول", "شیءِ کاملِ ۱ استخراج شد")
gate(applied.get(7) == "دوم اینجاست", "شیءِ کاملِ ۲ استخراج شد")
gate(9 not in applied, "شیءِ نیمهکاره دستنخورده ماند (بدونِ ترجمهٔ ساختگی)")

applied2 = {}


def _on_item2(rid, tr):
    applied2[rid] = tr


_escaped = (
    '{"id":11,"translation":"خط اول\\nخط دوم \\"نقل\\" \\\\ پایان"},'
    '{"id":12,"translation":"بعدی"}'
)
manga.MangaTranslator._salvage_stream_items(_escaped, _on_item2)
gate(applied2.get(11) == 'خط اول\nخط دوم "نقل" \\ پایان',
     "escapeهایِ \\n و \\\" و \\\\ درست باز شدند")
gate(applied2.get(12) == "بعدی", "شیءِ کنارِ شیءِ escapeدار هم استخراج شد")

# id تکراری دوباره صدا زده میشود ولی مصرفکننده (on_item واقعی در
# _translate_regions_batch) با _applied جلوی دوبارهنویسی را میگیرد —
# همینجا هم شبیهسازی میکنیم:
applied3 = {}
_seen = set()


def _on_item3(rid, tr):
    if rid in _seen:
        return
    _seen.add(rid)
    applied3[rid] = tr


_dup = '{"id":5,"translation":"الف"},{"id":5,"translation":"ب"}'
manga.MangaTranslator._salvage_stream_items(_dup, _on_item3)
manga.MangaTranslator._salvage_stream_items(_dup, _on_item3)
gate(len(applied3) == 1 and applied3[5] == "الف",
     "id تکراری فقط یکبار اعمال میشود (رفتارِ _applied در مسیرِ اصلی)")

print("── ۲. درخواستِ کلِ فصل (بدونِ ۱۵تا۱۵تا) ──")
src = io.open("manga.py", encoding="utf-8").read()
gate("while len(dialogue_buffer) >= min_batch:" not in src,
     "هیچ حلقهٔ برشِ ۱۵تاییِ بافری در run() نیست")
gate("if getattr(self, \"chapter_one_request\", False):\n                return [list(items)]" in src,
     "_make_batches: کلِ بچ = یک درخواست")
gate("_clean_pages_bg([page_i])" in src,
     "پاکسازیٔ همزمانِ هر صفحه بعد از استخراجش")
gate("_wait_batch_clean_barrier" not in src,
     "سدِ توقفِ استخراج حذف شده")

print("── ۳. درخواستِ ساختگیِ کلِ فصل ──")
# یک ترنسلیتورِ حداقلی: فقط مسیرِ gemini را میقاپد تا ببینیم کلِ بچ
# در «یک» صدا رفت و پارسرِ نهایی همهٔ idها را نشاند.
import threading  # noqa: E402


class _Reg:
    def __init__(self, rid, text):
        self.id = rid
        self.source_text = text
        self.translated_text = ""
        self.bubble_style = ""
        self.kind = "dialogue"


class _Stub(manga.MangaTranslator):
    pass


try:
    tr = object.__new__(manga.MangaTranslator)
    tr.chapter_one_request = True
    tr.provider_type = "gemini"
    tr.provider = "gemini"
    tr.model_name = "stub"
    tr.max_retries = 1
    tr.request_delay = 0
    tr.translation_temperature = 0.4
    tr._api_lock = threading.Lock()
    tr._sbn_ok = True
    tr._brief_corpus = []
    tr._model_cascade = []
    tr._build_chapter_brief = lambda c: None
    tr._is_bad_translate_model = lambda m: False

    regs = [_Reg(i, f"متنِ {i}") for i in range(1, 26)]  # ۲۵ دیالوگ
    calls = {"n": 0, "sizes": []}

    def _fake_gemini(user_prompt, system_instruction, structured=True,
                     timeout=None, on_item=None):
        calls["n"] += 1
        # طولِ پرامپت باید همهٔ ۲۵ آیتم را داشته باشد
        calls["sizes"].append(user_prompt.count('"id":'))
        import json as _json
        return _json.dumps(
            [{"id": r.id, "translation": f"ترجمهٔ {r.id}"} for r in regs],
            ensure_ascii=False)

    tr._get_system_instruction = lambda: "sys"
    tr._pick_random_api_key = lambda reason="": None
    tr._fix_ocr_text = lambda t: t
    tr.uncensor_swears = lambda t: t
    manga.uncensor_swears = staticmethod(lambda t: t)
    tr._allowed_tones = lambda: []
    tr._glossary_prompt_block = lambda s: ""
    tr._brief_prompt_block = lambda: ""
    tr._ocr_lang_flags = lambda: (False, False, False)
    tr.resolve_prompt_mode = staticmethod(lambda *a, **k: "classic")
    tr._thread_client = lambda: None
    tr._thread_model = lambda: "stub"
    tr._pace_before_gemini_call = lambda: None
    tr._note_model_ok = lambda: None
    tr.save_glossary = lambda: None
    tr._force_translate_missing_1189 = lambda rs: 0
    tr._parse_translation_response = lambda text, rs: (
        [setattr(r, "translated_text", f"ترجمهٔ {r.id}")
         for r in rs if f'"id": {r.id}' in text or f'"id":{r.id}' in text])
    tr._translate_with_gemini = _fake_gemini

    tr.translate_regions(regs)
    gate(calls["n"] == 1, f"کلِ ۲۵ دیالوگ در {calls['n']} درخواست رفت (نه ۱۵تا۱۵تا)")
    gate(calls["sizes"] and calls["sizes"][0] >= 25,
         f"پرامپتِ همان یک درخواست همهٔ ۲۵ id را داشت ({calls['sizes'][0]})")
    done = sum(1 for r in regs if (r.translated_text or "").strip())
    gate(done == 25, f"همهٔ ۲۵ دیالوگ ترجمه نشستند ({done}/25)")
except Exception as _e:
    fail(f"مسیرِ ساختگیِ translate_regions: {_e}")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} چکِ مردود:")
    for _f in FAILS:
        print(f"    - {_f}")
    sys.exit(1)
print("[✓] همهٔ چکهایِ عملیِ v1.14.196 سبز.")
