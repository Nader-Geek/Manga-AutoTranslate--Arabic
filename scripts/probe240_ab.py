# ایزوله‌کردن مرحلهٔ مقصر: پچ‌های پایین-چپ/راستِ نواحی (دیوارهٔ حباب)
import os, sys, time
os.chdir("/home/z/my-project/Manga-AutoTranslate")
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")
import numpy as np, cv2

import manga

SRC = "/tmp/test_shanshan.jpg"

# پچ‌های مشکوک (از diff قبلی)
SUSPECTS = [
    ("bottom-left  R2", 101, 1899, 48, 89),
    ("bottom-right R2", 769, 1904, 48, 84),
    ("bottom       R1", 730, 1553, 53, 101),
    ("R1/2 boundary  ", 786, 1624, 103, 30),
]

def diff_patches(img, cleaned):
    diff = cv2.absdiff(img, cleaned)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 12, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    hit = []
    for (name, x, y, w, h) in SUSPECTS:
        sub = mask[y:y+h, x:x+w]
        hit.append(int(cv2.countNonZero(sub)))
    tot = cv2.countNonZero(mask)
    return hit, tot

img = cv2.imread(SRC)
H, W = img.shape[:2]

variants = [
    ("baseline (همه روشن)", {}),
    ("DOT_SWEEP=0", {"MANGA_DOT_SWEEP": "0"}),
]
for name, env in variants:
    for k, v in env.items():
        os.environ[k] = v
    for k in ("MANGA_DOT_SWEEP",):
        if k not in env:
            os.environ.pop(k, None)
    mt = manga.MangaTranslator(api_key="dummy", ocr_langs=["en"], debug=False,
                               gpu=False, clean_only=True,
                               font_path="fonts/Vazirmatn-Bold.ttf")
    regions, _ = mt.extract_regions_phase(img)
    cleaned = mt._clean_image_page(img, regions)
    hits, tot = diff_patches(img, cleaned)
    print(f"\n=== {name} ===  total_diff={tot}px")
    for (nm, x, y, w, h), hh in zip(SUSPECTS, hits):
        print(f"  {nm} @({x},{y},{w},{h}): {hh}px changed")

# پالی‌های OCR نواحی → کجا هستند نسبت به پچ‌ها
mt = manga.MangaTranslator(api_key="dummy", ocr_langs=["en"], debug=False,
                           gpu=False, clean_only=True,
                           font_path="fonts/Vazirmatn-Bold.ttf")
regions, _ = mt.extract_regions_phase(img)
print("\nنواحی و پالی‌ها:")
for i, r in enumerate(regions):
    rx, ry, rw, rh = [int(v) for v in r.rect[:4]]
    print(f"#{i} rect=({rx},{ry},{rw},{rh})")
    for j, p in enumerate(r.ocr_polys or []):
        pa = np.asarray(p, dtype=np.float32).reshape(-1, 2)
        print(f"   poly{j}: x=[{pa[:,0].min():.0f}..{pa[:,0].max():.0f}] y=[{pa[:,1].min():.0f}..{pa[:,1].max():.0f}]")
