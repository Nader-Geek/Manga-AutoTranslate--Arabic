#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.170 — گیتِ «استخراجِ چندزبانهٔ ML Kit» برایِ امولاتور.

درخواستِ سازنده: «حذف کن بره paddle-lite ناقص استخراج میزنه ml kit بزار …
همه زبان هارو خوب بتونه استخراج کنه انگلیسی ژاپنی کره چینی … اگ نمیتونی
رو خودت اندروید اجرا کنی رو GitHub action تست کن».

از لاگِ موتورِ همان صفحاتِ ci_imgs (up0822_en / up0904_en / lang_ja_bw /
lang_ja_color / lang_ko / lang_zh / up0929_zh) ناحیههایِ استخراج را
میکند و الزام میکند متنِ واقعیِ زبانِ هر صفحه خوانده شده باشد:
  ja → حداقل یک ناحیه با کانا (هیراگانا/کاتاکانا) یا ≥۲ هان
  ko → حداقل یک ناحیه با هانگول
  zh → حداقل یک ناحیه با ≥۲ هان (بدونِ کانا)
  en → حداقل یک ناحیه با ≥۳ حرفِ لاتین

ناحیهها با همان قاعدهٔ check_extract.py خوانده میشوند (#NN … rect= سپس
«متن: …»). خروجی: exit 0 = عبور؛ exit 1 = شکست.

usage: check_mlkit.py LOG LANG   (LANG = ja|ko|zh|en — پیشوند کافی است)
"""
import re
import sys


def _regions(log: str):
    regs, cur = [], None
    for line in log.splitlines():
        if re.search(r"#\d+\s+\S+.*\|\s*rect\s*=", line):
            cur = []
            regs.append(cur)
            continue
        m = re.match(r"\s*متن:\s*(.*)$", line)
        if m and cur is not None:
            cur.append(m.group(1))
    return [" ".join(r).replace("⏎", " ") for r in regs]


def _counts(t: str):
    kana = hangul = han = latin = 0
    i, n = 0, len(t)
    while i < n:
        cp = ord(t[i])
        if 0xD800 <= cp <= 0xDFFF:
            i += 1
            continue
        if (0x3040 <= cp <= 0x30FF) or (0x31F0 <= cp <= 0x31FF) \
                or (0xFF66 <= cp <= 0xFF9D):
            kana += 1
        elif (0xAC00 <= cp <= 0xD7A3) or (0x1100 <= cp <= 0x11FF) \
                or (0x3130 <= cp <= 0x318F):
            hangul += 1
        elif (0x2E80 <= cp <= 0x2EFF) or (0x3400 <= cp <= 0x4DBF) \
                or (0x4E00 <= cp <= 0x9FFF) or (0xF900 <= cp <= 0xFAFF):
            han += 1
        elif (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A):
            latin += 1
        i += 1
    return kana, hangul, han, latin


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: check_mlkit.py LOG LANG")
        return 1
    lang = sys.argv[2].strip().lower().split()[0]
    try:
        with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as f:
            log = f.read()
    except Exception as e:
        print(f"[mlkit-gate] cannot read log: {e}")
        return 1
    regs = _regions(log)
    nonempty = [t for t in regs if t.strip()]
    if not nonempty:
        print("[mlkit-gate] FAIL — no region text found in log "
              "(detector regions empty or OCR gave nothing)")
        print("--- log tail ---")
        print(log[-1200:])
        return 1
    ok = False
    desc = ""
    for t in nonempty:
        kana, hangul, han, latin = _counts(t)
        if lang.startswith("ja") and (kana >= 1 or han >= 2):
            ok, desc = True, f"kana={kana} han={han}"
            break
        if lang.startswith("ko") and hangul >= 1:
            ok, desc = True, f"hangul={hangul}"
            break
        if lang.startswith("zh") and han >= 2 and kana == 0:
            ok, desc = True, f"han={han}"
            break
        if lang.startswith("en") and latin >= 3:
            ok, desc = True, f"latin={latin}"
            break
    n_regions = re.findall(r"متن\s*استخراج\s*شد:\s*(\d+)\s*ناحیه", log)
    n = max([int(x) for x in n_regions], default=0)
    crashed = bool(re.search(r"Traceback|خطای مهلک|FATAL", log))
    print(f"[mlkit-gate] {lang}: regions={n} | nonempty-texts={len(nonempty)} "
          f"| script-proof: {desc if ok else '—'} "
          f"| crash: {crashed} | {'PASS' if (ok and not crashed) else 'FAIL'}")
    if not ok:
        print("--- first 3 region texts ---")
        for t in nonempty[:3]:
            print("   «" + t[:90] + "»")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
