# بنچمارکِ عینیِ پاکسازی — v1.14.204
# برایِ هر عکسِ ci_imgs: استخراجِ واقعی (detector+OCR) یکبار (کشِ pickle) →
# پاکسازی با هر روش (lama-manga onnx / opencv) → متریکِ هر ناحیه:
#   untouched  = پیکسلِ ماسکِ متن که دست نخورده (متنِ قبلی جا مانده)
#   resid_dark = جوهرِ تیرهٔ متن که هنوز در خروجی تیره است (متن پیداست)
#   black_new  = تیرهٔ تازه داخلِ ماسک (لگهٔ سیاهِ پرکننده)
#   white_new  = سفیدِ تازه داخلِ ماسک رویِ متنِ تیره (لگهٔ سفید)
#   black_out / white_out = لگهٔ تازه بیرونِ ماسک (حباب/هنر خراب)
#   chg_out    = هر تغییرِ بیرونِ ماسک (آسیبِ اطراف)
# خروجی: جدول + JSON + عکس‌هایِ پاک‌شده + کراپِ بدترین ناحیه‌ها
import os, sys, time, json, pickle
import cv2
import numpy as np

ROOT = '/home/z/my-project/Manga-AutoTranslate'
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import manga  # noqa: E402

OUT = '/home/z/my-project/clean_out'
os.makedirs(OUT, exist_ok=True)

IMAGES = ['img2.webp', 'img3.webp', 'img4.jpg', 'img5.webp', 'img6.jpg',
          'img7.jpg', 'lang_ja_bw.jpg', 'lang_ja_color.jpg', 'lang_ko.jpg',
          'lang_zh.jpg', 'up0822_en.jpg', 'up0904_en.jpg', 'up0929_zh.jpg',
          'IMG_20261018_140944_899.jpg',
          '/home/z/my-project/upload/1793755746410.jpg',
          '/home/z/my-project/upload/1793755663517.jpg']


def _img_path(name):
    if os.path.isabs(name):
        return name
    p = os.path.join('ci_imgs', name)
    if os.path.isfile(p):
        return p
    return os.path.join('/home/z/my-project/upload', name)


def make_tr(method):
    return manga.MangaTranslator(
        api_key='bench', provider='gemini', ocr_langs=['en'],
        font_path='fonts/Vazirmatn-Regular.ttf',
        clean_method=method, gpu=False, force_lama=True,
        clean_only=True, debug=False, story_brief=False,
        max_workers=1)


def extract_regions(tr, img):
    return tr._extract_regions_from_bubbles(img)


def clean_filter(regions):
    regs = [r for r in regions
            if r.kind == 'dialogue'
            and not getattr(r, 'ocr_empty', False)
            and ((r.source_text or '').strip()
                 or (r.translated_text or '').strip())]
    return regs


def _stroke_like(binm, max_area=3000, max_dim=150):
    """کامپوننتهایِ ضربه/تکه مانندِ متن (نه خطِ بلندِ پنل، نه سایهٔ بزرگ)"""
    try:
        n, lab, st, _ = cv2.connectedComponentsWithStats(
            binm.astype(np.uint8), 8)
    except Exception:
        return binm
    out = np.zeros_like(binm)
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        w = int(st[i, cv2.CC_STAT_WIDTH])
        h = int(st[i, cv2.CC_STAT_HEIGHT])
        if a < 30 or a > max_area or max(w, h) > max_dim:
            continue
        if max(w, h) >= 130 and min(w, h) * 9 <= max(w, h) and a * 5 <= w * h:
            continue  # خطِ کشیدهٔ پنل/کادر
        out |= (lab == i)
    return out


def region_metrics(go, gc, mc, pad_mode='in'):
    goi = go.astype(np.int16)
    gci = gc.astype(np.int16)
    diff = np.abs(goi - gci)
    n_mask = int(mc.sum())
    mrd = cv2.dilate(mc.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    keep = (~mrd).astype(np.float32)
    k31 = np.ones((41, 41), np.float32)
    num = cv2.filter2D(goi.astype(np.float32) * keep, -1, k31)
    den = cv2.filter2D(keep, -1, k31)
    bgest = np.where(den > 40, num / np.maximum(den, 1), 255.0)
    bgi = bgest.astype(np.int16)
    bgv = go[~mrd]
    bg = int(np.median(bgv)) if bgv.size else 255
    glyph = mc & (np.abs(goi - bgi) > 60)
    n_glyph = int(glyph.sum())
    out = ~mrd
    # پسزمینهٔ محلیِ خودِ «خروجی» — برایِ تشخیصِ ضربهٔ باقیمانده
    keep_c = (~cv2.dilate(glyph.astype(np.uint8),
                          np.ones((11, 11), np.uint8))).astype(np.float32)
    numc = cv2.filter2D(gci.astype(np.float32) * keep_c, -1, k31)
    denc = cv2.filter2D(keep_c, -1, k31)
    bgc = np.where(denc > 40, numc / np.maximum(denc, 1), 255.0).astype(np.int16)
    dark_c = gci < np.minimum(bgc - 60, 110)
    lite_c = gci > np.maximum(bgc + 60, 200)
    chg = diff > 28          # فقط رنگِ «تازه» — دیوارِ حبابِ دستنخورده نه
    # ضربهٔ باقیمانده = تیره/روشنِ ضربه مانند رویِ خروجی
    dsoft = _stroke_like(dark_c & (mc | mrd) & chg)
    lsoft = _stroke_like(lite_c & (mc | mrd) & chg)
    dsoft_o = _stroke_like(dark_c & out & chg)
    lsoft_o = _stroke_like(lite_c & out & chg)
    d = {
        'n_mask': n_mask, 'bg': bg, 'n_glyph': n_glyph,
        # متنِ قبلی: گلیفِ دستنخورده + ضربهٔ باقیماندهٔ کنتراستدار
        'resid_same': int((glyph & (diff <= 30)).sum()),
        'resid': int((glyph & (dsoft | lsoft)).sum()),
        'black_new': int((mc & dsoft).sum()),
        'white_bad': int(((mc | mrd) & lsoft).sum()),
        'black_out': int((out & dsoft_o).sum()),
        'white_out': int((out & lsoft_o).sum()),
        'chg_out': int((out & (diff > 28)).sum()),
    }
    d['resid_pct'] = round(100.0 * d['resid'] / max(1, n_glyph), 1)
    return d


def worst_crops(img_o, img_c, mask, regs, tag, topk=3):
    H, W = mask.shape[:2]
    scored = []
    for i, r in enumerate(regs):
        rx, ry, rw, rh = [int(v) for v in r.rect]
        x0, y0, x1, y1 = rx, ry, rx + rw, ry + rh
        pad = 26
        X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
        X1, Y1 = min(W, x1 + pad), min(H, y1 + pad)
        if X1 - X0 < 4 or Y1 - Y0 < 4:
            continue
        mc = mask[Y0:Y1, X0:X1] > 0
        go = cv2.cvtColor(img_o[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
        gc = cv2.cvtColor(img_c[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
        m = region_metrics(go, gc, mc)
        bad = (m['resid'] + m['black_new'] + m['white_bad']
               + m['black_out'] + m['white_out'])
        scored.append((bad, i, m, (X0, Y0, X1, Y1)))
    scored.sort(reverse=True, key=lambda t: t[0])
    crops = []
    for bad, i, m, box in scored[:topk]:
        if bad <= 0:
            break
        X0, Y0, X1, Y1 = box
        pair = np.hstack([img_o[Y0:Y1, X0:X1], img_c[Y0:Y1, X0:X1]])
        p = os.path.join(OUT, f'crop_{tag}_r{i}.jpg')
        cv2.imwrite(p, pair, [cv2.IMWRITE_JPEG_QUALITY, 88])
        m['rect'] = [int(v) for v in regs[i].rect]
        crops.append((p, m))
    return crops


def main():
    methods = ['lama-manga', 'opencv']
    if len(sys.argv) > 1:
        methods = sys.argv[1].split(',')
    only = sys.argv[2].split(',') if len(sys.argv) > 2 else IMAGES

    tr_ex = make_tr(methods[0])
    report = {}
    for name in only:
        path = _img_path(name)
        img = cv2.imread(path)
        if img is None:
            print(f'[SKIP] {name} خوانده نشد')
            continue
        tag = os.path.splitext(os.path.basename(name))[0]
        cache = os.path.join(OUT, f'extract_{tag}.pkl')
        t0 = time.time()
        if os.path.isfile(cache):
            with open(cache, 'rb') as fh:
                regs = pickle.load(fh)
            t_ex = -1.0
            print(f'[extract] {name}: از کش ({len(regs)} ناحیهٔ خام)')
        else:
            regs = extract_regions(tr_ex, img)
            t_ex = time.time() - t0
            with open(cache, 'wb') as fh:
                pickle.dump(regs, fh)
            print(f"[extract] {name}: {len(regs)} ناحیهٔ خام در {t_ex:.1f}s", flush=True)
        cf = clean_filter(regions=regs)
        print(f"[filter] {name}: {len(cf)} ناحیهٔ پاکشدنی از {len(regs)}", flush=True)
        if not cf:
            report[name] = {'regions_raw': len(regs), 'clean': {}}
            continue
        mask = tr_ex._build_text_mask(img, cf)
        rep_img = {'regions_raw': len(regs), 'regions_clean': len(cf),
                   'mask_px': int((mask > 0).sum()), 'clean': {}}
        for meth in methods:
            tr = make_tr(meth)
            t0 = time.time()
            try:
                cleaned = tr.clean_image(img.copy(), list(cf))
                dt = time.time() - t0
            except Exception as e:
                import traceback
                traceback.print_exc()
                rep_img['clean'][meth] = {'error': str(e)[:200]}
                continue
            op = os.path.join(OUT, f'{tag}__{meth}.jpg')
            cv2.imwrite(op, cleaned, [cv2.IMWRITE_JPEG_QUALITY, 90])
            per = []
            H, W = mask.shape
            for i, r in enumerate(cf):
                rx, ry, rw, rh = [int(v) for v in r.rect]
                x0, y0, x1, y1 = rx, ry, rx + rw, ry + rh
                pad = 26
                X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
                X1, Y1 = min(W, x1 + pad), min(H, y1 + pad)
                if X1 - X0 < 4 or Y1 - Y0 < 4:
                    continue
                mc = mask[Y0:Y1, X0:X1] > 0
                go = cv2.cvtColor(img[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
                gc = cv2.cvtColor(cleaned[Y0:Y1, X0:X1], cv2.COLOR_BGR2GRAY)
                m = region_metrics(go, gc, mc)
                m['i'] = i
                m['rect'] = [rx, ry, rw, rh]
                m['text'] = (r.source_text or '')[:40]
                per.append(m)
            full_diff = int((np.abs(
                cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.int16)
                - cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY).astype(np.int16))
                > 28).sum())
            rep_img['clean'][meth] = {
                'time_s': round(dt, 1), 'full_diff_px': full_diff,
                'regions': per,
            }
            crops = worst_crops(img, cleaned, mask, cf,
                                f'{tag}__{meth}', topk=4)
            rep_img['clean'][meth]['worst'] = [
                {'crop': p, **m} for p, m in crops]
        report[name] = rep_img
        with open(os.path.join(OUT, 'report.json'), 'w') as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)

    print('\n==== خلاصه ====')
    for name, ri in report.items():
        for meth, rc in (ri.get('clean') or {}).items():
            if 'error' in rc:
                print(f'{name} [{meth}] خطا: {rc["error"][:80]}')
                continue
            bad = [m for m in rc['regions']
                   if (m['resid'] > 150 or m['resid_pct'] > 18
                       or m['black_new'] > 60 or m['white_bad'] > 400
                       or m['black_out'] > 400 or m['white_out'] > 400
                       or m['chg_out'] > 400)]
            print(f'{name} [{meth}] t={rc["time_s"]}s '
                  f'full_diff={rc["full_diff_px"]} '
                  f'بد={len(bad)}/{len(rc["regions"])}')
            for m in bad:
                print(f"   r{m['i']} {m['rect']} «{m['text']}» "
                      f"res={m['resid']}({m['resid_pct']}%/"
                      f"{m['n_glyph']}) same={m['resid_same']} "
                      f"bN={m['black_new']} wB={m['white_bad']} "
                      f"bO={m['black_out']} wO={m['white_out']} "
                      f"co={m['chg_out']}")


if __name__ == '__main__':
    main()
