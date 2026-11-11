# -*- coding: utf-8 -*-
"""Build merged v272 mascot blocks (my v272 art/engine + v269 wall-hide/blackout/PC-sizing).
Reads /tmp/v272_MASCOT_{CSS,HTML,JS}.txt (extracted from page.tsx) and writes
/home/z/manga-repo/_v272_blocks/{css,svg,js,off}.txt
"""
import os

CSS = open('/tmp/v272_MASCOT_CSS.txt', encoding='utf-8').read()
HTML = open('/tmp/v272_MASCOT_HTML.txt', encoding='utf-8').read()
JS = open('/tmp/v272_MASCOT_JS.txt', encoding='utf-8').read()

def sub(text, old, new, name, count=1):
    if text.count(old) != count:
        raise SystemExit('!! marker mismatch (%s): found %d x' % (name, text.count(old)))
    return text.replace(old, new)

# ═══════════════ CSS ═══════════════
CSS = sub(CSS,
    '/* —— هم‌خوانِ نکو-گِرل v272: دخترِ گربه‌گوشِ استیکری — سرِ گردِ توپُش + بدنِ خُرد — ۲۴ حالت —— */',
    '/* —— هم‌خوانِ نکو-گِرل v272: دخترِ گربه‌گوشِ استیکری — سرِ گردِ توپُش + بدنِ خُرد — ۲۴ حالت + قایم‌شدن پشتِ دیوار + خاموش‌کردنِ صفحه —— */',
    'css header')
# PC: 94px پایین-راست (از v269 — دستورِ سازنده)؛ موبایل دست‌نخورده (۸۸px بالا-راست)
CSS = sub(CSS,
    '.mcat{position:fixed;z-index:57;right:10px;top:58px;width:88px;',
    '.mcat{position:fixed;z-index:57;right:10px;top:58px;width:88px;',
    'mcat base')  # no-op sanity
CSS = sub(CSS,
    '.mcat svg{display:block;width:100%;height:auto;pointer-events:none}',
    """.mcat svg{display:block;width:100%;height:auto;pointer-events:none}
@media (min-width:768px){.mcat{width:94px;right:18px;top:auto;bottom:112px;filter:drop-shadow(0 6px 14px rgba(0,0,0,.55))}}
.mcat.hide-l svg{transform:scaleX(-1)}
.mcat.hide-l .mcat-bub,.mcat.hide-l .mcat-say{right:auto;left:0}
.mcat.hide-l .mcat-say:after{right:auto;left:14px}""",
    'pc media + hide-l')
# حذف قواعد گوشه‌های قدیمی (corner-*) — جایگزین: دیوار
_css_lines = CSS.split('\n')
_css_kept = [ln for ln in _css_lines if '.mcat.corner-' not in ln]
if len(_css_lines) - len(_css_kept) != 11:
    raise SystemExit('!! expected 11 corner-* CSS lines, got %d' % (len(_css_lines) - len(_css_kept)))
CSS = '\n'.join(_css_kept)
CSS = CSS.rstrip('\n') + """
/* — v272 (از v269): قایم‌شدن پشتِ دیوارِ لبهٔ صفحه — دیوارِ کرم داخلِ SVG نیمهٔ پشتی را می‌پوشاند — */
.cg-wall{display:none}
.mcat.st-hide .cg-wall{display:block}
/* — v272 (از v269): اذیتِ پیوسته (۱۰ بار) = خاموش‌کردنِ صفحه‌ی نمایش — */
#mcatOff{position:fixed;inset:0;z-index:95;background:#000;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;opacity:0;pointer-events:none;transition:opacity .5s ease;direction:rtl}
#mcatOff.show{opacity:1;pointer-events:auto;cursor:pointer}
#mcatOff .off-eyes{width:min(220px,46vw);height:auto;animation:offBlink 4.6s ease-in-out infinite}
#mcatOff .off-t1{color:#ffd964;font-weight:700;font-size:1.06rem}
#mcatOff .off-t2{color:#cfd2da;font-size:.92rem}
#mcatOff .off-t3{color:#6d6a63;font-size:.74rem;margin-top:16px}
@keyframes offBlink{0%,86%,100%{transform:scaleY(1)}90%,94%{transform:scaleY(.06)}}
"""

# ═══════════════ SVG ═══════════════
WALL = """<g class="cg-wall">
<rect x="71" y="-2" width="49" height="144" fill="#b7aa92"/>
<rect x="71" y="-2" width="49" height="7" rx="3.5" fill="#998b70"/>
<rect x="71" y="-2" width="2.4" height="144" fill="#d0c2a6"/>
<rect x="73.4" y="-2" width="1.4" height="144" fill="rgba(0,0,0,.22)"/>
<path d="M66 96 Q80 90 86 103 Q75 110 66 96 Z" fill="#bcd9f2" stroke="#9fc4ea" stroke-width="2"/>
<circle cx="82.5" cy="103" r="3.4" fill="#9fc4ea"/>
<g><path d="M65 55 q6.5 -6 14 -1.5 q1.5 6 -4.5 7.5 q-8 1.5 -9.5 -6 Z" fill="#f4a9b8"/><circle cx="78" cy="64" r="6.5" fill="#ffe9dc" stroke="#e8b9a4" stroke-width="1.3"/><path d="M74.9 69 l-.5 2.8 M78 69.4 l.2 2.8" stroke="#e8b9a4" stroke-width="1.6" stroke-linecap="round"/></g>
<g><path d="M66 71 q6.5 -6 14 -1.5 q1.5 6 -4.5 7.5 q-8 1.5 -9.5 -6 Z" fill="#f4a9b8"/><circle cx="79" cy="80" r="6.5" fill="#ffe9dc" stroke="#e8b9a4" stroke-width="1.3"/><path d="M75.9 85 l-.5 2.8 M79 85.4 l.2 2.8" stroke="#e8b9a4" stroke-width="1.6" stroke-linecap="round"/></g>
</g>
"""
SVG = sub(HTML, '</svg>', WALL + '</svg>', 'wall into svg')

OFF = """<div id="mcatOff" aria-hidden="true">
<svg class="off-eyes" viewBox="0 0 150 58" aria-hidden="true"><defs><radialGradient id="mcOffG"><stop offset="0" stop-color="#ffd964" stop-opacity=".55"/><stop offset=".55" stop-color="#ffd964" stop-opacity=".2"/><stop offset="1" stop-color="#ffd964" stop-opacity="0"/></radialGradient></defs><path d="M28 24 L33 8 L44 19 Z" fill="#ffd964" opacity=".38"/><path d="M122 24 L117 8 L106 19 Z" fill="#ffd964" opacity=".38"/><g><ellipse cx="40" cy="36" rx="34" ry="19" fill="url(#mcOffG)"/><path d="M16 36 Q40 18 64 36 Q40 52 16 36 Z" fill="#ffd964"/><circle cx="32" cy="33" r="3.2" fill="#fff" opacity=".95"/><circle cx="48" cy="39" r="2.1" fill="#fff" opacity=".75"/></g><g><ellipse cx="110" cy="36" rx="34" ry="19" fill="url(#mcOffG)"/><path d="M86 36 Q110 18 134 36 Q110 52 86 36 Z" fill="#ffd964"/><circle cx="102" cy="33" r="3.2" fill="#fff" opacity=".95"/><circle cx="118" cy="39" r="2.1" fill="#fff" opacity=".75"/></g></svg>
<div class="off-t1">دخترِ گربه‌ای خسته شد!</div>
<div class="off-t2">صفحه رو خاموش کرد… دیگه اذیت نکن!</div>
<div class="off-t3">برای روشن‌کردن، صفحه را لمس کن</div>
</div>"""

# ═══════════════ JS ═══════════════
JS = sub(JS,
    '  // ——— هم‌خوانِ نکو-گِرل v271 — موتورِ ۲۴ حالته ———',
    '  // ——— هم‌خوانِ نکو-گِرل v272 — موتورِ ۲۴ حالته + قایم‌شدن پشتِ دیوار + خاموش‌کردنِ صفحه ———',
    'js header')
JS = sub(JS,
    '  var mcatTaps = [], mcatAngerN = 0, mcatAngerLast = 0;',
    '  var mcatTaps = [], mcatAngerN = 0, mcatAngerLast = 0;\n  var mcatTeaseN = 0;',
    'tease var')
JS = sub(JS,
    "  var MCAT_HIDE_SAY = ['هیشکی اینجا منو پیدا نمیکنه!', 'من اینجا نبودم ها، اصلاً نبودم!', 'یه گوشهٔ خلوت لازمم بود!'];",
    "  var MCAT_HIDE_SAY = ['پشتِ دیوال قایم شدم، گیرم نمیاری!', 'هیشکی اینجا منو پیدا نمیکنه!', 'از پشتِ دیوال دارم نگاه می‌کنم!'];",
    'hide say')
JS = sub(JS,
    "  var MCAT_FOUND = ['اِ پیدام کردی؟! زرنگی!', 'وا! از کجا فهمیدی اینجام؟!', 'باشه باشه، باختم!'];",
    """  var MCAT_FOUND = ['اِ پیدام کردی؟! زرنگی!', 'وا! از کجا فهمیدی اینجام؟!', 'باشه باشه، باختم!'];
  var MCAT_OFF = ['بس بود! صفحه رو خاموش می‌کنم!', 'دیگه بسه! دکمهٔ خاموش کجاست…'];""",
    'off say')
# mcatPlace: bottom:auto (PC media از bottom استفاده می‌کند — تداخل با top)
JS = sub(JS,
    """    MCAT.style.left = (x - MCAT.offsetWidth / 2) + 'px';
    MCAT.style.top = (y - MCAT.offsetHeight / 2) + 'px';
    MCAT.style.right = 'auto';
  }""",
    """    MCAT.style.left = (x - MCAT.offsetWidth / 2) + 'px';
    MCAT.style.top = (y - MCAT.offsetHeight / 2) + 'px';
    MCAT.style.right = 'auto';
    MCAT.style.bottom = 'auto';
  }""",
    'place bottom')
# mcatRestore: hide-l هم پاک شود
JS = sub(JS,
    "    MCAT.classList.remove('away', 'peek-r', 'corner-bl', 'corner-br', 'corner-tl', 'corner-tr');\n    if (mcatSaved)",
    "    MCAT.classList.remove('away', 'peek-r', 'hide-l');\n    if (mcatSaved)",
    'restore hide-l')
# قلبِ ادغام: mcatGoCorner → mcatGoHide (دیوار، از v269)
OLD_CORNER = """  /* — قایم‌شدنِ رندوم در یکی از ۴ گوشه — */
  function mcatGoCorner() {
    if (mcatState === 'st-hide') return;
    var r = MCAT.getBoundingClientRect();
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    var corners = ['bl', 'br', 'tl', 'tr'];
    var c = corners[Math.floor(Math.random() * corners.length)];
    MCAT.classList.remove('corner-bl', 'corner-br', 'corner-tl', 'corner-tr');
    MCAT.classList.add('corner-' + c);
    mcatGlide(function () {
      var vw = window.innerWidth, vh = window.innerHeight;
      MCAT.style.right = 'auto';
      if (c === 'bl') { MCAT.style.left = '-48px'; MCAT.style.top = (vh - 66) + 'px'; }
      else if (c === 'br') { MCAT.style.left = (vw - 40) + 'px'; MCAT.style.top = (vh - 66) + 'px'; }
      else if (c === 'tl') { MCAT.style.left = '-54px'; MCAT.style.top = '-12px'; }
      else { MCAT.style.left = (vw - 34) + 'px'; MCAT.style.top = '-12px'; }
    });
    mcatSet('st-hide');
    mcatHideTill = Date.now() + 12000 + Math.random() * 6000;
    mcatSayNow(faR(MCAT_HIDE_SAY), 2800);
  }"""
NEW_HIDE = """  /* ——— قایم‌شدن پشتِ دیوار (از v269 — دستورِ سازنده): به لبهٔ نزدیکِ صفحه
     می‌رود، دیوارِ کرم داخلِ SVG نیمهٔ پشتیش را می‌پوشاند و از پشتِ دیوار
     نگاه می‌کند (دستها روی لبهٔ دیوار + نوکِ دُم بیرون!) ——— */
  function mcatGoHide() {
    if (mcatState === 'st-hide') return;
    var r = MCAT.getBoundingClientRect();
    var hw = MCAT.offsetWidth || 88, hh = MCAT.offsetHeight || 103;
    mcatSaved = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    var onRight = (r.left + r.width / 2) >= window.innerWidth / 2;
    MCAT.classList.toggle('hide-l', !onRight);
    var hy = Math.min(Math.max(r.top + r.height / 2, window.innerHeight * 0.36),
      window.innerHeight - hh / 2 - 30);
    /* چسبیده به لبه — دیوار با لبهٔ صفحه یکی می‌شود (بدون درز) */
    mcatGlide(function () {
      MCAT.style.left = (onRight ? window.innerWidth - hw + 1 : -1) + 'px';
      MCAT.style.top = (hy - hh / 2) + 'px';
      MCAT.style.right = 'auto';
      MCAT.style.bottom = 'auto';
    });
    mcatSet('st-hide');
    mcatHideTill = Date.now() + 12000 + Math.random() * 6000;
    mcatSayNow(faR(MCAT_HIDE_SAY), 2800);
  }"""
JS = sub(JS, OLD_CORNER, NEW_HIDE, 'GoCorner→GoHide')
# ماشینِ خاموشی (از v269) — بعد از mcatStartPeek
JS = sub(JS,
    "    mcatSayNow('…هنوز قهرم ها!', 2400);\n  }",
    """    mcatSayNow('…هنوز قهرم ها!', 2400);
  }
  /* ——— اذیتِ پیوسته (۱۰ بار) = خاموش‌کردنِ صفحه‌ی نمایش! (از v269) ———
     کلِ صفحه سیاه می‌شود، فقط دو چشمِ درخشانِ او در تاریکی می‌ماند؛
     با لمس (یا بعد از ~۵ ثانیه) دوباره روشن می‌شود. ——— */
  var mcatOffEl = document.getElementById('mcatOff');
  var mcatOffTimer = null;
  function mcatWake() {
    if (!mcatOffEl || !mcatOffEl.classList.contains('show')) return;
    mcatOffEl.classList.remove('show');
    if (mcatOffTimer) { clearTimeout(mcatOffTimer); mcatOffTimer = null; }
    mcatRestore('دیدی چیکار می‌کنم؟! دیگه اذیت نکن~');
  }
  function mcatBlackout() {
    mcatTeaseN = 0;
    mcatTaps = [];
    mcatAnnoyT = mcatAngryT = mcatPatT = mcatActT = mcatShyT = 0;
    mcatSayNow(faR(MCAT_OFF), 1900);
    mcatSet('st-annoy');
    mcatTick();
    setTimeout(function () {
      if (!mcatOffEl) return;
      mcatOffEl.classList.add('show');
      if (mcatOffTimer) clearTimeout(mcatOffTimer);
      mcatOffTimer = setTimeout(mcatWake, 5200);
    }, 1600);
  }""",
    'blackout machinery')
# شمارشِ اذیت در mcatUp
JS = sub(JS,
    "    if (fast >= 5) {",
    """    /* شمارشِ اذیت (از v269): ضربه در میانهٔ چج/اعصابی + خودِ اپیزودها؛
       ده بار = خاموش‌کردنِ صفحه‌نمایش! */
    if (mcatAnnoyT > now || mcatAngryT > now) mcatTeaseN++;
    if (fast >= 5 || mcatTaps.length >= 5) mcatTeaseN++;
    if (mcatTeaseN >= 10) { mcatBlackout(); return; }
    if (fast >= 5) {""",
    'tease count')
JS = sub(JS,
    "      setTimeout(function () { mcatGoCorner(); }, 1950);",
    "      setTimeout(function () { mcatGoHide(); }, 1950);",
    'annoy→hide')
JS = sub(JS,
    "        mcatGoCorner();",
    "        mcatGoHide();",
    'tick random hide')
# شنوندهٔ بیداری + hide-l در zone-land
JS = sub(JS,
    "  MCAT.addEventListener('pointercancel', function () { mcatDrag = null; if (ZONES) { ZONES.classList.remove('show'); mcatZoneCur = ''; } });",
    """  MCAT.addEventListener('pointercancel', function () { mcatDrag = null; if (ZONES) { ZONES.classList.remove('show'); mcatZoneCur = ''; } });
  /* لمسِ صفحهٔ خاموش = روشن‌کردنِ دوباره */
  if (mcatOffEl) mcatOffEl.addEventListener('pointerdown', function () { mcatWake(); });""",
    'wake listener')
JS = sub(JS,
    "    MCAT.classList.remove('away', 'corner-bl', 'corner-br', 'corner-tl', 'corner-tr');\n    if (z === 'top') {",
    "    MCAT.classList.remove('away', 'hide-l');\n    if (z === 'top') {",
    'zone land hide-l')
# قلابِ تست: دیوار + خاموشی
JS = sub(JS,
    "    if (st === 'st-hide') { mcatGoCorner(); mcatHideTill = Date.now() + 60000; return; }",
    "    if (st === 'st-hide') { mcatGoHide(); mcatHideTill = Date.now() + 60000; return; }\n    if (st === 'st-blackout') { mcatBlackout(); return; }",
    'force hooks')

# sanity
for marker, name in [
    ('mcatGoCorner', 'old corner gone'),
    ('function mcatGoHide', 'GoHide present'),
    ('function mcatBlackout', 'blackout present'),
    ('function mcatWake', 'wake present'),
    ('mcatTeaseN >= 10', 'tease threshold'),
    ('hide-l', 'hide-l css class'),
    ('corner-bl', 'corner leftovers'),
]:
    if (marker in JS) != (name in ('GoHide present', 'blackout present', 'wake present', 'tease threshold', 'hide-l css class')):
        raise SystemExit('!! sanity failed: ' + name)
if 'mcatGoCorner' in JS or 'corner-bl' in JS:
    raise SystemExit('!! corner leftovers in JS')
if 'MCAT_USE_S = false' not in JS or '__mcatKill' not in JS:
    raise SystemExit('!! boot markers missing')
if JS.count('mcatGoHide') < 4:
    raise SystemExit('!! mcatGoHide refs < 4')

os.makedirs('/home/z/manga-repo/_v272_blocks', exist_ok=True)
open('/home/z/manga-repo/_v272_blocks/css.txt', 'w', encoding='utf-8').write(CSS)
open('/home/z/manga-repo/_v272_blocks/svg.txt', 'w', encoding='utf-8').write(SVG)
open('/home/z/manga-repo/_v272_blocks/js.txt', 'w', encoding='utf-8').write(JS)
open('/home/z/manga-repo/_v272_blocks/off.txt', 'w', encoding='utf-8').write(OFF)
print('BUILD OK — css:%d svg:%d js:%d off:%d' % (len(CSS), len(SVG), len(JS), len(OFF)))
