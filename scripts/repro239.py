# بازتولید مشکلات ۲ و ۳ — strip_001 فصل Green Skin 22 (mgeko)
# خروجی: نواحی استخراجشده + باکسهای خام detector + نتیجهٔ split حباب HELLO
import os, sys, time, json
os.chdir("/home/z/my-project/Manga-AutoTranslate")
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")
import numpy as np, cv2

import manga

imgs = [cv2.imread(f"/tmp/gs22/p{i:03d}.jpg") for i in range(1, 6)]
assert all(im is not None for im in imgs), "page load failed"
strip = np.vstack(imgs)
print("strip:", strip.shape)
cv2.imwrite("/tmp/gs22/strip001.jpg", strip)

t0 = time.time()
mt = manga.MangaTranslator(api_key="dummy", ocr_langs=["en"], debug=True,
                           gpu=False, clean_only=True,
                           font_path="fonts/Vazirmatn-Bold.ttf")
print(f"init={time.time()-t0:.1f}s | ocr={mt._ocr_backend_name} | det={type(mt.det).__name__}")

t0 = time.time()
regions, dbg = mt.extract_regions_phase(strip)
print(f"extract={time.time()-t0:.1f}s | regions={len(regions)}")

out = []
for i, r in enumerate(regions):
    out.append({
        "i": i, "rect": tuple(int(v) for v in r.rect[:4]),
        "kind": r.kind, "text": (r.source_text or "")[:90],
        "angle": float(getattr(r, "angle", 0.0) or 0.0),
        "npolys": len(getattr(r, "ocr_polys", None) or []),
    })
for o in out:
    print(f"#{o['i']:02d} {o['kind']:<10} rect={o['rect']} a={o['angle']:+.1f} polys={o['npolys']}")
    if o["text"]:
        print(f"     متن: {o['text']}")

with open("/tmp/gs22/repro_regions.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ── تستِ مستقیمِ split روی باکسِ HELLO ──
box = (39, 4606, 723, 4744)
parts = manga.MangaTranslator._split_adjacent_balloons(strip, list(box))
print("SPLIT of", box, "->", parts)

# ── باکسهای خامِ detector روی ناحیهٔ پایینِ صفحه (AHHH) ──
raw = mt.det.detect(strip)
print("raw det boxes:", len(raw))
for b in raw:
    x, y, w, h = [int(v) for v in b["rect"][:4]]
    if y + h > 5200 and y < 6400:
        print(f"  RAW rect=({x},{y},{w},{h}) cls={b.get('class_name')} conf={float(b.get('confidence',0)):.2f}")
