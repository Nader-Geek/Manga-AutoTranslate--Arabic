# -*- coding: utf-8 -*-
"""Apply merged v272 blocks to the repo (reader.html + manga_app.py) + version bumps."""
import ast, sys

R = '/home/z/manga-repo/'
B = R + '_v272_blocks/'
NEW_CSS = open(B + 'css.txt', encoding='utf-8').read()
NEW_SVG = open(B + 'svg.txt', encoding='utf-8').read()
NEW_OFF = open(B + 'off.txt', encoding='utf-8').read()
JS_RAW = open(B + 'js.txt', encoding='utf-8').read()

# — JS embedding transform: IIFE → tail-of-function (الگوی v268/v269) —
HEAD = '  // ——— هم‌خوانِ نکو-گِرل v272 — موتورِ ۲۴ حالته + قایم‌شدن پشتِ دیوار + خاموش‌کردنِ صفحه ———\n  (function () {\n'
if not JS_RAW.startswith(HEAD):
    sys.exit('!! js head mismatch')
TAIL = '\n  })();'
if not JS_RAW.endswith(TAIL):
    sys.exit('!! js tail mismatch')
body = JS_RAW[len(HEAD):-len(TAIL)]
body = body.replace('  if (!MCAT) return;', '  if (MCAT) {', 1)
if 'if (MCAT) {' not in body:
    sys.exit('!! MCAT guard transform failed')
body = body.replace('var MCAT_USE_S = false;', 'var MCAT_USE_S = true;', 1)
NEW_JS = ('  // ——— هم‌خوانِ نکو-گِرل v272 (دخترِ گربه‌گوشِ استیکری — سرِ گردِ توپُش) ———\n'
          '  // موتورِ ۲۴ حالته + قایم‌شدن پشتِ دیوارِ لبهٔ صفحه + خاموش‌کردنِ صفحه بعد از\n'
          '  // ۱۰ اذیتِ پیوسته + نقاطِ رهاکردن (بکش و ول کن) + چشمهای دنبال‌کنندهٔ موس.\n'
          + body + '\n    mcatUpdate();\n    mcatTick();\n  }')
for bad in ['"""', 'mcatGoCorner', 'corner-bl']:
    if bad in NEW_JS:
        sys.exit('!! bad token in NEW_JS: ' + bad)

ok = []
def sub(text, start, end, new, name, incl_end=True):
    try:
        i = text.index(start)
        j = text.index(end, i)
    except ValueError:
        sys.exit('!! marker not found for: ' + name)
    if incl_end:
        j += len(end)
    ok.append(name)
    return text[:i] + new + text[j:]

CSS_S = '/* —— هم‌خوانِ نکو-گِرل: دخترِ گربه‌ایِ انیمه‌ای (گوش + دُم، خودش دختر!) —— */'
CSS_E = '@keyframes offBlink{0%,86%,100%{transform:scaleY(1)}90%,94%{transform:scaleY(.06)}}'
SVG_S = '<div class="mcat st-read" id="mcat" title="هم‌خوانِ گربه‌ای — کشیدن = جابه‌جایی، ضربه = نوازش (زیادش نکن!)">'
SVG_E = '<div class="mcat-say"></div>\n</div>'
OFF_S = '<div id="mcatOff" aria-hidden="true">'
OFF_E = '<div class="off-t3">برای روشن‌کردن، صفحه را لمس کن</div>\n</div>'
JS_AND_S = '  // ——— هم‌خوانِ نکو-گِرل (دخترِ گربه‌ایِ انیمه‌ای — گوش + دُمِ گربه،'
JS_LIVE_S = '  // ——— هم‌خوانِ نکو-گِرل (وبِ زنده) — دخترِ گربه‌ایِ انیمه‌ای + ۱۳ حالت: خواندن / هیجانِ اسکرول /'
JS_SA_S = '  // ——— هم‌خوانِ نکو-گِرل (نمایشگرِ مستقل) — دخترِ گربه‌ایِ انیمه‌ای +'
JS_E = '    mcatUpdate();\n    mcatTick();\n  }'
SA_CSS_S = '            "/* —— هم‌خوانِ نکو-گِرل: دخترِ گربه‌ایِ انیمه‌ای (گوش + دُم، خودش دختر!) —— */"'
SA_CSS_E = '            "@keyframes offBlink{0%,86%,100%{transform:scaleY(1)}90%,94%{transform:scaleY(.06)}}"'
MHTML_S = '# ——— هم‌خوانِ نکو-گِرل (نمایشگرِ مستقل): SVG دخترِ گربه‌ایِ انیمه‌ای ———'
MHTML_E = "            '</div>\\n'\n        )"

# ═══ 1) reader.html (اندروید — ES6 مجاز، ما ES5 می‌گذاریم) ═══
p = R + 'android/app/src/main/assets/reader.html'
src = open(p, encoding='utf-8').read()
src = sub(src, CSS_S, CSS_E, NEW_CSS, 'reader CSS')
src = sub(src, SVG_S, SVG_E, NEW_SVG, 'reader SVG')
src = sub(src, OFF_S, OFF_E, NEW_OFF, 'reader mcatOff')
src = sub(src, JS_AND_S, JS_E, NEW_JS, 'reader JS')
open(p, 'w', encoding='utf-8').write(src)

# ═══ 2) manga_app.py ═══
p = R + 'manga_app.py'
src = open(p, encoding='utf-8').read()
# — وبِ زنده (ES5): CSS/SVG/mcatOff/JS —
src = sub(src, CSS_S, CSS_E, NEW_CSS, 'live CSS')
src = sub(src, SVG_S, SVG_E, NEW_SVG, 'live SVG')
src = sub(src, OFF_S, OFF_E, NEW_OFF, 'live mcatOff')
src = sub(src, JS_LIVE_S, JS_E, NEW_JS, 'live JS')
# — مستقل: CSS (python-string) —
SA_CSS = '\n'.join('            "' + ln + '"' for ln in NEW_CSS.split('\n'))
src = sub(src, SA_CSS_S, SA_CSS_E, SA_CSS, 'standalone CSS')
# — مستقل: JS —
src = sub(src, JS_SA_S, JS_E, NEW_JS, 'standalone JS')
# — مستقل: _MCAT_HTML (SVG + mcatOff به‌صورت python-string) —
def pylit(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")
MCAT_PY = ('# ——— هم‌خوانِ نکو-گِرل v272 (نمایشگرِ مستقل): دخترِ گربه‌گوشِ استیکری ———\n'
           '        _MCAT_HTML = (\n'
           + ''.join("            '" + pylit(ln) + "\\n'\n"
                     for ln in (NEW_SVG + '\n' + NEW_OFF).split('\n'))
           + '        )')
src = sub(src, MHTML_S, MHTML_E, MCAT_PY, '_MCAT_HTML')
open(p, 'w', encoding='utf-8').write(src)
ast.parse(open(p, encoding='utf-8').read())
ok.append('ast.parse manga_app.py')

# ═══ 3) نسخه‌ها ═══
for f, subs in {
    R + 'manga_sections/00_base.py': [('APP_VER = "1.14.269"', 'APP_VER = "1.14.272"')],
    R + 'manga.py': [('APP_VER = "1.14.269"', 'APP_VER = "1.14.272"')],
    R + 'VERSION': [('versionCode=273', 'versionCode=274'),
                    ('versionName=1.14.269', 'versionName=1.14.272')],
    R + 'android/app/build.gradle.kts': [('versionCode = 273', 'versionCode = 274'),
                                         ('versionName = "1.14.269"', 'versionName = "1.14.272"')],
}.items():
    t = open(f, encoding='utf-8').read()
    for a, b in subs:
        if a not in t:
            sys.exit('!! version marker missing in ' + f + ': ' + a)
        t = t.replace(a, b)
    open(f, 'w', encoding='utf-8').write(t)
ok.append('versions')
print('ALL OK:', ok)
