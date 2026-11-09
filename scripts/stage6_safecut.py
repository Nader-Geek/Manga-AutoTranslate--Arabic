# -*- coding: utf-8 -*-
"""v1.14.246 — مرحله ۶: سرعتِ برشِ امن به سبکِ مرجع (ManhwaSlicer.راستیآزما/جابهجاییِ برش با تشخیصِ متن در مرجع)
(۱) spans_ready: باندِ برش از قبل با کشِ دوطرفه/اسکنِ زنده پوشش داده شده → حذفِ تشخیصِ دومِ
    تمام‌عیار (قبلاً هر برش یک det.detectِ ~۱۵۰۰px با پاسِ چندمقیاسیِ کند میگرفت)؛
(۲) مسیرِ تشخیصِ زنده fast=True (تک‌مقیاس — عینِ _scan_window)؛
(۳) جستجوی مارپیچِ ±۱px دورِ هدف قبل از ردِ کلِ باند (عینِ مرجع)."""

P = '/home/z/manga-work/manga.py'
src = open(P, encoding='utf-8').read()
done = []


def rep(old, new, desc):
    global src
    n = src.count(old)
    assert n == 1, f"[{desc}] expected 1, found {n}"
    src = src.replace(old, new, 1)
    done.append(desc)


# ── ۱) امضا: پارامترِ spans_ready ──
rep(
    '        protected_ranges: Optional[List[Tuple[int, int]]] = None,\n'
    '    ) -> Optional[int]:\n'
    '        # v1.14.163',
    '        protected_ranges: Optional[List[Tuple[int, int]]] = None,\n'
    '        spans_ready: bool = False,\n'
    '    ) -> Optional[int]:\n'
    '        # v1.14.163',
    'signature spans_ready param')

# ── ۲) بلوکِ ساختِ spans: شاخهٔ spans_ready (بدون تشخیص) + fast=True مسیرِ زنده ──
rep(
    '            probe_half = max(250, int(round((y1 - y0) * 0.25)),\n'
    '                             clearance + edge_margin)\n'
    '            wy0 = max(0, y0 - probe_half)\n'
    '            wy1 = min(ih, y1 + probe_half)\n'
    '            if wy1 - wy0 < 100:\n'
    '                return None\n'
    '            band = strip[wy0:wy1]\n'
    '            boxes = self.det.detect(band)\n'
    '            spans: List[Tuple[int, int]] = []\n'
    '            for box in boxes:\n'
    '                _, by1, _, by2 = box["rect"]\n'
    '                top = max(0, wy0 + int(by1) - edge_margin)\n'
    '                bot = min(ih, wy0 + int(by2) + 1 + edge_margin)\n'
    '                if bot > top:\n'
    '                    spans.append((top, bot))\n'
    '            for top, bottom in (protected_ranges or []):\n'
    '                spans.append((max(0, int(top) - edge_margin),\n'
    '                              min(ih, int(bottom) + 1 + edge_margin)))\n'
    '            spans.sort()',
    '            # v1.14.246 — سرعتِ برش به سبکِ مرجع (ManhwaSlicer.\n'
    '            # راستیآزما/جابهجاییِ برش با تشخیصِ متن در مرجع): (۱) باندِ برش از\n'
    '            # قبل پوشش داده شده (کشِ دوطرفه یا اسکنِ زندهٔ _scan_band)\n'
    '            # → دیگر هیچ تشخیصِ دومی رویِ همان ناحیه اجرا نمیشود\n'
    '            # (قبلاً هر برش یک det.detectِ تمام‌عیارِ ~۱۵۰۰px با پاسِ\n'
    '            # چندمقیاسیِ کند اضافه میگرفت)؛ (۲) مسیرِ تشخیصِ زنده فقط\n'
    '            # پنجرهٔ کوچکِ دورِ هدف و fast=True (تک‌مقیاس — عینِ\n'
    '            # _scan_window)؛ (۳) خروجِ زودهنگامِ «هدف بی‌متن است» +\n'
    '            # جستجوی مارپیچِ ±۱px (پایینتر) — عینِ مرجع.\n'
    '            spans: List[Tuple[int, int]] = []\n'
    '            if spans_ready:\n'
    '                # spans از _scan_band از قبل حاشیهدار شدهاند (پدینگ =\n'
    '                # max(14, 2%·target_w) — همان مقیاسِ edge_margin چون عرضِ\n'
    '                # نوار = target_w)؛ دوباره پد نمیشوند.\n'
    '                for top, bottom in (protected_ranges or []):\n'
    '                    t, b = int(top), int(bottom)\n'
    '                    if b > t:\n'
    '                        spans.append((max(0, t), min(ih, b)))\n'
    '            else:\n'
    '                probe_half = max(250, int(round((y1 - y0) * 0.25)),\n'
    '                                 clearance + edge_margin)\n'
    '                wy0 = max(0, y0 - probe_half)\n'
    '                wy1 = min(ih, y1 + probe_half)\n'
    '                if wy1 - wy0 < 100:\n'
    '                    return None\n'
    '                band = strip[wy0:wy1]\n'
    '                boxes = self.det.detect(band, fast=True)\n'
    '                for box in boxes:\n'
    '                    _, by1, _, by2 = box["rect"]\n'
    '                    top = max(0, wy0 + int(by1) - edge_margin)\n'
    '                    bot = min(ih, wy0 + int(by2) + 1 + edge_margin)\n'
    '                    if bot > top:\n'
    '                        spans.append((top, bot))\n'
    '                for top, bottom in (protected_ranges or []):\n'
    '                    spans.append((max(0, int(top) - edge_margin),\n'
    '                                  min(ih, int(bottom) + 1 + edge_margin)))\n'
    '            spans.sort()',
    'spans_ready branch + fast=True live path')

# ── ۳) فیلترِ کاندیدها + جستجوی مارپیچِ مرجع قبل از None ──
rep(
    '            if not cands:\n'
    '                return None\n'
    '            return min(cands, key=lambda y: abs(y - target_y))',
    '            cands = [c for c in cands if not _hit_text(c)]\n'
    '            if cands:\n'
    '                return min(cands, key=lambda y: abs(y - target_y))\n'
    '            # v1.14.246 — جستجوی مارپیچِ ±۱px دورِ هدف (عینِ مرجع:\n'
    '            # VerifyAndAdjust — localCutY∓n): نزدیکترین ردیفِ بی‌متن به\n'
    '            # هدف، قبل از ردِ کلِ باند → فالبکِ اسکنِ مجددِ باندِ عقبتر\n'
    '            # کمتر لازم میشود.\n'
    '            _t = int(target_y)\n'
    '            for _d in range(1, max(y1 - _t, _t - y0) + 1):\n'
    '                _yy = _t - _d\n'
    '                if y0 <= _yy <= y1 and not _hit_text(_yy):\n'
    '                    return _yy\n'
    '                _yy = _t + _d\n'
    '                if y0 <= _yy <= y1 and not _hit_text(_yy):\n'
    '                    return _yy\n'
    '            return None',
    'candidate filter + مرجع spiral search')

# ── ۴) دو فراخوانِ _cut_and_emit → spans_ready=True ──
rep(
    '                    cut_y = self._find_safe_cut_y_smart(\n'
    '                        strip, _band_mid, _band_lo, min(_band_hi, max_cut),\n'
    '                        search_radius=max(250, (_band_hi - _band_lo) // 2),\n'
    '                        protected_ranges=protected,\n'
    '                    )',
    '                    cut_y = self._find_safe_cut_y_smart(\n'
    '                        strip, _band_mid, _band_lo, min(_band_hi, max_cut),\n'
    '                        search_radius=max(250, (_band_hi - _band_lo) // 2),\n'
    '                        protected_ranges=protected,\n'
    '                        # v1.14.246 — باند بالا همین الان با _scan_band\n'
    '                        # اسکن شد؛ تشخیصِ دوم لازم نیست (سبکِ مرجع)\n'
    '                        spans_ready=True,\n'
    '                    )',
    'cut_and_emit band call spans_ready')

rep(
    '                        cut_y = self._find_safe_cut_y_smart(\n'
    '                            strip, _fb_hi, _fb_lo, _fb_hi,\n'
    '                            search_radius=max(200, _fb_hi - _fb_lo),\n'
    '                            protected_ranges=protected,\n'
    '                        )',
    '                        cut_y = self._find_safe_cut_y_smart(\n'
    '                            strip, _fb_hi, _fb_lo, _fb_hi,\n'
    '                            search_radius=max(200, _fb_hi - _fb_lo),\n'
    '                            protected_ranges=protected,\n'
    '                            spans_ready=True,  # v1.14.246 — همین الان با _scan_band اسکن شد\n'
    '                        )',
    'cut_and_emit fallback call spans_ready')

open(P, 'w', encoding='utf-8').write(src)
print(f"OK — {len(done)} ops")
for d in done:
    print("  ✓", d)
