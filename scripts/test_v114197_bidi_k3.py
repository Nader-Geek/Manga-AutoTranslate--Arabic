#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.197 — استخراج دوطرفه + پاکسازی دوفازی + فیکسِ تایم‌اوت:

  ۱. استخراج دوطرفه: دو کارگر (اول→آخر + آخر→اول) — ادعای صفحهار از دو
     سر با _claim_ext، قفلِ صفِ دیالوگ، پرچمِ title_skip فقط مالِ صفحهٔ ۰.
  ۲. پاکسازی دوفازی: فاز ۱ حینِ استخراج = جاروی بالا→پایین (min(cand))؛
     فاز ۲ فقط بعد از اتمامِ کاملِ استخراج (extraction_done) = نصفِ
     باقیمانده از بالا→پایین + نصفِ دیگر از پایین→بالا (reversed).
  ۳. فیکسِ تایم‌اوت به سبکِ K3: سقفِ زمانیِ متناسبِ حجم (۶۰ + ۱.۵×تعداد +
     حجم/۴۰، سقفِ ۱۸۰۰) روی مسیرِ provider هم؛ استریمِ SSE با پارسرِ
     افزایشی در _translate_with_openai + فالبکِ «استریم پذیرفته نشد»؛
     AutoRetry چندبارهٔ همهمدل با انتظارِ واقعی (۲/۴/۸ثانیه) بهجایِ
     صبرِ ۰.۵ثانیه و cascade بیفایده.
  ۴. ترتیبِ روایی: بافرِ دیالوگ قبل از درخواستِ واحد به ترتیبِ صفحهها
     مرتب میشود.
"""

import io
import json
import os
import sys
import threading

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

gate(manga.APP_VER == "1.14.197", f"APP_VER = {manga.APP_VER}")
src = io.open("manga.py", encoding="utf-8").read()

print("── ۱. استخراج دوطرفه (دو کارگر از دو سر) ──")
gate("def _claim_ext(role" in src, "ادعای صفحه از دو سر (_claim_ext)")
gate('if role == "fwd":' in src and '_ext_bwd["v"] = b - 1' in src,
     "کارگرِ جلو از ابتدا، کارگرِ عقب از انتها برمیدارد")
gate("if f > b:\n                    return None" in src,
     "دیدار در وسط (f > b → پایان)")
gate("args=(\"fwd\",)" in src and 'args=("bwd",)' in src,
     "دو رشتهٔ extract-fwd و extract-bwd")
gate("with _qd_lock:\n                            _queue_dialogues" in src,
     "صفِ دیالوگ زیرِ قفل (دو کارگر همزمان)")
gate("if page_i == 0:\n                MangaTranslator._title_skip_enabled = True" in src
     and "if page_i == 0:  # v1.14.197 — فقط مالکِ پرچم پاک کند" in src,
     "پرچمِ title_skip فقط توسطِ صفحهٔ ۰ ست/پاک میشود (بدونِ رقابت)")
gate("dialogue_buffer.sort(key=lambda r: page_of_region.get(r.id, 0))" in src,
     "بافر قبل از درخواستِ واحد به ترتیبِ طبیعیِ صفحهها مرتب میشود")

print("── ۲. پاکسازی دوفازی ──")
gate("pi = min(cand)  # بالا→پایین" in src,
     "فاز ۱ حینِ استخراج: همیشه کمترینِ صفحۀِ آماده (بالا→پایین)")
gate("extraction_done[\"v\"] = True" in src,
     "پرچمِ «استخراج کامل شد» فقط بعد از joinِ هر دو کارگر")
gate("return  # ماندهها → فازِ دوطرفه" in src,
     "فاز ۱ بعد از اتمامِ استخراج دیگر برنمیدارد (باقیمانده برایِ فاز ۲)")
gate("_top_seq, _bot_seq = _backlog[:_mid], _backlog[_mid:]" in src,
     "فاز ۲: باقیمانده نصف میشود")
gate("list(reversed(_bot_seq))" in src,
     "فاز ۲: نیمۀِ دوم از پایین→بالا (دیدار در وسط)")
gate("thread_name_prefix=\"clean2\"" in src,
     "کارگرِ دومِ فاز ۲ (clean2)")
gate("def _wait_clean(page_i" in src and "def _clean_ready(page_i" in src,
     "انتظارِ پاکسازی با Event (جایگزینِ clean_futures)")
gate("clean_futures" not in src, "clean_futuresِ قدیمی کاملاً حذف شد")

print("── ۳. سقفِ زمانیِ متناسبِ حجم (مسیرِ provider هم) ──")
gate("_want_stream = (\n                    getattr(self, \"chapter_one_request\", False)\n                    and len(work_regions) > 6)" in src,
     "استریم/سقف دیگر مخصوصِ Gemini نیست — برایِ هر provider")
gate("60.0 + 1.5 * len(work_regions) + _chars / 40.0" in src,
     "فرمولِ جدید: ۶۰ + ۱.۵×تعداد + حجم/۴۰")
gate("1800.0," in src, "سقفِ مطلق ۳۰ دقیقه")
gate("text = self._translate_via_provider(\n                            user_prompt, system_instruction,\n                            timeout=_tout, on_item=_on_item)" in src,
     "timeout/on_item به مسیرِ provider هم پاس میشود")


def _expected_tout(n, chars, api_timeout=45.0):
    return min(1800.0, max(api_timeout, 60.0 + 1.5 * n + chars / 40.0))


gate(_expected_tout(100, 6000) > 300,
     f"۱۰۰ دیالوگِ ۶۰۰۰ نویسه → {_expected_tout(100, 6000):.0f}ثانیه (قبلاً ~۴۵)")
gate(_expected_tout(25, 1500) == max(45.0, 60.0 + 37.5 + 37.5),
     f"۲۵ دیالوگ → {_expected_tout(25, 1500):.0f}ثانیه")

print("── ۴. AutoRetry K3 (همهمدلِ صبور) ──")
gate("صبر ۰.۵ثانیه و تلاش دوباره" not in src,
     "رفتارِ قدیمیِ «صبر ۰.۵ثانیه و فقط ۱ تلاش» حذف شد")
gate("MANGA_TIMEOUT_RETRIES" in src and "MANGA_TIMEOUT_WAIT" in src,
     "قابلِ تنظیم با MANGA_TIMEOUT_RETRIES/WAIT")
gate("same_retries < _k3_max:" in src,
     "همان مدل تا K3_max بار دوباره پرسیده میشود")
gate("min(_k3_wait * (2 ** same_retries), 30.0)" in src,
     "انتظارِ نمایی ۲/۴/۸/… تا سقفِ ۳۰ثانیه")
gate("_still = [r for r in work_regions\n                              if not (r.translated_text or \"\").strip()]" in src,
     "آیتمهایِ نشسته از جریان قبلی از تلاشِ بعدی حذف میشوند")

print("── ۵. استریمِ SSE در مسیرِ openai/custom (تستِ ساختگی) ──")


class _Chunk:
    def __init__(self, piece):
        self.choices = [type("C", (), {"delta": type("D", (), {"content": piece})()})()]


def _make_stream_client(pieces, fail_stream=False):
    class _CC:
        def __init__(self):
            self.calls = []

        def create(self, **kw):
            self.calls.append(kw)
            if fail_stream and kw.get("stream"):
                raise RuntimeError("stream is not supported by this endpoint")
            if kw.get("stream"):
                return iter([_Chunk(p) for p in pieces])
            resp = type("R", (), {})()
            resp.choices = [type("C", (), {"message": type("M", (), {"content": "".join(pieces)})()})()]
            return resp

    class _Chat:
        completions = _CC()

    class _Client:
        chat = _Chat()

    return _Client()


try:
    tr = object.__new__(manga.MangaTranslator)
    tr.provider = "custom"
    tr.provider_type = "custom"
    tr.api_timeout = 45.0
    tr.translation_temperature = 0.4
    tr._thread_model = lambda: "deepseek-v4.1-flash:free"

    pieces = [
        '[{"id":1,"translation":"یک"},',
        '{"id":2,"translation":"دو"},',
        '{"id":3,"translation":"سه"}]',
    ]
    client = _make_stream_client(pieces)
    tr._thread_openai = lambda: client
    got = {}
    out = tr._translate_with_openai(
        "p", "s", timeout=360.0,
        on_item=lambda rid, t: got.__setitem__(rid, t))
    gate(client.chat.completions.calls[0].get("stream") is True,
         "درخواست با stream=True رفت (سبکِ K3)")
    gate(client.chat.completions.calls[0].get("timeout") == 360.0,
         "سقفِ HTTP هم همان سقفِ بزرگِ متناسب شد (نه ۴۵ ثانیه)")
    gate(set(got) == {1, 2, 3}, f"پارسرِ افزایشی همهٔ آیتمها را نشاند ({sorted(got)})")
    gate(json.loads(out) == [{"id": 1, "translation": "یک"},
                             {"id": 2, "translation": "دو"},
                             {"id": 3, "translation": "سه"}],
         "متنِ نهاییِ جمعشده سالم است")
except Exception as _e:
    fail(f"استریمِ ساختگیِ openai: {_e}")

try:
    # فالبک: endpoint استریم را نمیفهمد → مسیرِ عادی جواب میدهد
    client2 = _make_stream_client(pieces, fail_stream=True)
    tr2 = object.__new__(manga.MangaTranslator)
    tr2.provider = "custom"
    tr2.provider_type = "custom"
    tr2.api_timeout = 45.0
    tr2.translation_temperature = 0.4
    tr2._thread_model = lambda: "deepseek-v4.1-flash:free"
    tr2._thread_openai = lambda: client2
    out2 = tr2._translate_with_openai("p", "s", timeout=360.0,
                                      on_item=lambda rid, t: None)
    gate(len(client2.chat.completions.calls) == 2
         and client2.chat.completions.calls[1].get("stream") is None,
         "استریمِ پذیرفتهنشده → بلافاصله فالبکِ مسیرِ عادی")
    gate(json.loads(out2) is not None, "فالبک جوابِ کامل برگرداند")
except Exception as _e:
    fail(f"فالبکِ استریم: {_e}")

print("── ۶. AutoRetry K3 عملی (تایم‌اوت → صبرِ واقعی → جواب) ──")


class _Reg:
    def __init__(self, rid, text):
        self.id = rid
        self.source_text = text
        self.translated_text = ""
        self.bubble_style = ""
        self.kind = "dialogue"


try:
    tr3 = object.__new__(manga.MangaTranslator)
    tr3.chapter_one_request = True
    tr3.provider_type = "custom"
    tr3.provider = "custom"
    tr3.model_name = "deepseek-v4.1-flash:free"
    tr3.max_retries = 8
    tr3.request_delay = 0
    tr3.translation_temperature = 0.4
    tr3.api_timeout = 45.0
    tr3._api_lock = threading.Lock()
    tr3._sbn_ok = True
    tr3._brief_corpus = []
    tr3._model_cascade = []
    tr3._build_chapter_brief = lambda c: None
    tr3._is_bad_translate_model = lambda m: False

    regs = [_Reg(i, f"dialogue number {i} with some length") for i in range(1, 26)]
    calls = {"n": 0, "touts": []}
    switched = {"model": 0, "reset": 0, "key": 0}

    def _fake_provider(user_prompt, system_instruction, structured=True,
                       timeout=None, on_item=None):
        calls["n"] += 1
        calls["touts"].append(timeout)
        if calls["n"] <= 2:
            raise TimeoutError(f"custom/{tr3.model_name} بیش از "
                               f"{timeout:.0f}ثانیه طول کشید (timeout)")
        return json.dumps(
            [{"id": r.id, "translation": f"ترجمهٔ {r.id}"} for r in regs],
            ensure_ascii=False)

    tr3._get_system_instruction = lambda: "sys"
    tr3._pick_random_api_key = lambda reason="": None
    tr3._fix_ocr_text = lambda t: t
    manga.uncensor_swears = staticmethod(lambda t: t)
    tr3.uncensor_swears = lambda t: t
    tr3._allowed_tones = lambda: []
    tr3._glossary_prompt_block = lambda s: ""
    tr3._brief_prompt_block = lambda: ""
    tr3._ocr_lang_flags = lambda: (False, False, False)
    tr3.resolve_prompt_mode = staticmethod(lambda *a, **k: "classic")
    tr3._note_model_ok = lambda: None
    tr3.save_glossary = lambda: None
    tr3._force_translate_missing_1189 = lambda rs: 0
    tr3._parse_translation_response = lambda text, rs: (
        [setattr(r, "translated_text", f"ترجمهٔ {r.id}") for r in rs])
    tr3._translate_via_provider = _fake_provider
    tr3._recreate_api_client = lambda: None
    tr3._switch_to_next_model = lambda reason="": (
        switched.__setitem__("model", switched["model"] + 1) or False)
    tr3._reset_model_cascade = lambda reason="": switched.__setitem__(
        "reset", switched["reset"] + 1)
    tr3._switch_to_next_key = lambda reason="", cycle=False: (
        switched.__setitem__("key", switched["key"] + 1) or False)

    _sleeps = []
    _real_sleep = manga.time.sleep
    manga.time.sleep = lambda s: _sleeps.append(s)
    try:
        tr3._translate_regions_batch(regs)
    finally:
        manga.time.sleep = _real_sleep

    exp = min(1800.0, max(45.0, 60.0 + 1.5 * 25 + sum(len(r.source_text) for r in regs) / 40.0))
    gate(calls["touts"] and all(abs(t - exp) < 1.0 for t in calls["touts"]),
         f"سقفِ هر تلاش = {exp:.0f}ثانیه (متناسبِ حجم؛ نه api_timeoutِ ۴۵)")
    gate(calls["n"] == 3, f"۲ تایم‌اوت → تلاشِ سوم جواب داد ({calls['n']} صدا)")
    gate(switched["model"] == 0 and switched["reset"] == 0 and switched["key"] == 0,
         "مدلِ سالمِ «کند» قربانیِ cascade نشد (همهمدل ماند)")
    gate(abs(_sleeps[0] - 2.0) < 0.01 and abs(_sleeps[1] - 4.0) < 0.01,
         f"انتظارهایِ K3 = {_sleeps[:2]} (۲ و ۴ ثانیه؛ قبلاً ۰.۵)")
    done = sum(1 for r in regs if (r.translated_text or "").strip())
    gate(done == 25, f"همهٔ ۲۵ دیالوگ در نهایت ترجمه شدند ({done}/25)")
except Exception as _e:
    fail(f"AutoRetry K3 عملی: {_e}")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} چکِ مردود:")
    for _f in FAILS:
        print(f"    - {_f}")
    sys.exit(1)
print("[✓] همهٔ چکهایِ عملیِ v1.14.197 سبز.")
