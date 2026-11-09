# بازتولید مشکلِ v1.14.240 — صفحهٔ SHAN SHAN (10.jpg جدید):
# «جای بدونِ متن پاک شده — پایین-چپ — حباب خراب کرده»
# خروجی: نواحی + باکسهای خام detector + تصویر پاکشده + نقشهٔ تفاضل
import os, sys, time, json
os.chdir("/home/z/my-project/Manga-AutoTranslate")
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")
import numpy as np, cv2

import manga

SRC = "/tmp/test_shanshan.jpg"
img = cv2.imread(SRC)
assert img is not None, "load failed"
H, W = img.shape[:2]
print("page:", W, "x", H)

t0 = time.time()
mt = manga.MangaTranslator(api_key="dummy", ocr_langs=["en"], debug=True,
                           gpu=False, clean_only=True,
                           font_path="fonts/Vazirmatn-Bold.ttf")
print(f"init={time.time()-t0:.1f}s | ocr={mt._ocr_backend_name} | det={type(mt.det).__name__}")

t0 = time.time()
regions, dbg = mt.extract_regions_phase(img)
print(f"extract={time.time()-t0:.1f}s | regions={len(regions)}")

for i, r in enumerate(regions):
    rect = tuple(int(v) for v in r.rect[:4])
    txt = (r.source_text or "").replace("\n", " / ")[:100]
    print(f"#{i:02d} {r.kind:<10} rect={rect} polys={len(getattr(r,'ocr_polys',None) or [])} text={txt!r}")

# باکسهای خام detector
raw = mt.det.detect(img)
print("\nraw det boxes:", len(raw))
for b in raw:
    x, y, w, h = [int(v) for v in b["rect"][:4]]
    print(f"  RAW rect=({x},{y},{w},{h}) cls={b.get('class_name')} conf={float(b.get('confidence',0)):.2f}")

# فاز پاکسازی
cleaned = mt._clean_image_page(img, regions)
cv2.imwrite("/tmp/shanshan_cleaned.png", cleaned)

# نقشهٔ تفاضل: کجا پاک شده؟
diff = cv2.absdiff(img, cleaned)
gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
_, mask = cv2.threshold(gray, 12, 255, cv2.THRESH_BINARY)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
print("\ncleaned patches (diff>12):")
patches = []
for i in range(1, n):
    x, y, w, h, area = stats[i]
    if area < 400:
        continue
    patches.append((int(x), int(y), int(w), int(h), int(area)))
    print(f"  PATCH x={x} y={y} w={w} h={h} area={area}")

# کراپِ پایینِ صفحه برای بازبینی چشمی
cv2.imwrite("/tmp/shanshan_cleaned_bottom.png", cleaned[int(H*0.62):, :])
cv2.imwrite("/tmp/shanshan_orig_bottom.png", img[int(H*0.62):, :])
print("\nsaved: /tmp/shanshan_cleaned.png + bottom crops")
