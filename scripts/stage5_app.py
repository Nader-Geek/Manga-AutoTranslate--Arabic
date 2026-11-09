# -*- coding: utf-8 -*-
"""v1.14.246 — مرحله ۵ (manga_app.py): حذف classic + زنجیرهٔ glossary + helpers مرده"""
import re

P = '/home/z/manga-work/manga_app.py'
src = open(P, encoding='utf-8').read()
orig_len = len(src)
done = []


def rep(old, new, desc):
    global src
    n = src.count(old)
    assert n == 1, f"[{desc}] expected 1, found {n}"
    src = src.replace(old, new, 1)
    done.append(desc)


def span_rm(start, end, desc, keep_end=True):
    """حذف از start تا end (end خودش باقی میماند اگر keep_end)"""
    global src
    assert src.count(start) == 1, f"[{desc}] start not unique"
    i = src.find(start)
    j = src.find(end, i)
    assert j != -1, f"[{desc}] end not found"
    if keep_end:
        src = src[:i] + src[j:]
    else:
        src = src[:i] + src[j + len(end):]
    done.append(desc)


# ── ۱) _read_py_triple_string + strip_locked_instruction_tail (متنِ classic را از سورس میخواندند) ──
span_rm('def _read_py_triple_string(src: str, name: str) -> str:',
        'def load_default_system_instruction(tone_list=None) -> str:',
        'remove _read_py_triple_string + strip_locked_instruction_tail')

# ── ۲) load_default_system_instruction + cache + default_system_instruction ──
span_rm('def load_default_system_instruction(tone_list=None) -> str:',
        'def _norm_instr(text: str) -> str:',
        'remove default_system_instruction chain')

# ── ۳) _known_default_instruction_texts — فقط پرامپتهای مرجع ──
span_rm('def _known_default_instruction_texts() -> list:',
        'def normalize_api_base(url: str) -> str:',
        'remove old _known_default_instruction_texts')
rep('def normalize_api_base(url: str) -> str:',
    'def _known_default_instruction_texts() -> list:\n'
    '    """متنهایی که «پیشفرض» حساب میشوند و سفارشی نیستند (فقط مرجع — v1.14.246)."""\n'
    '    try:\n'
    '        from manga import PROMPT_PRESETS  # ایمپورتِ سنگین — فقط همین‌جا\n'
    '        return [v for v in PROMPT_PRESETS.values() if isinstance(v, str)]\n'
    '    except Exception:\n'
    '        return []\n'
    '\n'
    'def normalize_api_base(url: str) -> str:',
    'rewrite _known_default_instruction_texts')

# ── ۴) instruction_for_config مرده ──
span_rm('def instruction_for_config(text: str) -> str:',
        'PROMPT_MODE_DEFAULT = "auto"',
        'remove dead instruction_for_config')

# ── ۵) PROMPT_MODE_LABELS — حذفِ مدخلِ classic ──
m = re.search(r'\n    "classic": "[^"]*",', src)
assert m, 'classic label not found'
src = src[:m.start()] + src[m.end():]
done.append('PROMPT_MODE_LABELS drop classic')

# ── ۶) _PROMPT_MODE_LEGACY_LABELS — حذفِ نگاشتِ classic ──
m = re.search(r'\n    "[^"]*": "classic",', src)
assert m, 'legacy classic mapping not found'
src = src[:m.start()] + src[m.end():]
done.append('legacy labels drop classic')

# ── ۷) sanitize_prompt_mode ──
rep('    if s in ("auto", "professional", "lite", "classic"):',
    '    if s in ("auto", "professional", "lite"):',
    'sanitize_prompt_mode tuple')
rep('به یکی از auto/professional/lite/classic —',
    'به یکی از auto/professional/lite —',
    'sanitize_prompt_mode docstring')

# ── ۸) resolve_prompt_preview — فال‌بکِ classic → professional ──
rep('        resolved, txt = "classic", default_system_instruction()',
    '        resolved, txt = "professional", ""',
    'resolve_prompt_preview fallback')

# ── ۹) تکست‌باکسِ glossary در فرم ──
span_rm('            glossary_text = gr.Textbox(',
        '            # v1.14.145: چهار گزینه جمع شد',
        'remove glossary Textbox')

# ── ۱۰) امضای run_translation ──
rep('                            glossary_text_v, api_base_v,\n',
    '                            api_base_v,\n',
    'run_translation signature')

# ── ۱۱) بلوکِ نوشتنِ glossary و کامنتِ no-brief ──
span_rm('            glos_text = str(glossary_text_v or "").strip()',
        '            t0 = time.time()',
        'remove glossary cmd block + no-brief comment')

# ── ۱۲) _BACKUP_FIELDS ──
rep('            ("glossary_text", glossary_text),\n', '', '_BACKUP_FIELDS drop glossary')

# ── ۱۳) ورودیهای _click_kw ──
rep('                    glossary_text, api_base,\n',
    '                    api_base,\n',
    '_click_kw inputs drop glossary')

open(P, 'w', encoding='utf-8').write(src)
print(f"OK — {len(done)} ops, {orig_len} -> {len(src)} chars ({orig_len - len(src)} removed)")
for d in done:
    print("  ✓", d)
