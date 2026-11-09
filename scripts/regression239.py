# رگرسیون v1.14.239 — استخراج روی همهٔ ci_imgs + دو نوارِ فصلِ Green-Skin
# خروجی: JSON از (rect, kind, text) هر ناحیه برای مقایسهٔ قبل/بعد
import os, sys, json, time, traceback
os.chdir("/home/z/my-project/Manga-AutoTranslate")
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")
import numpy as np, cv2
import manga

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gs22/reg_new.json"

files = sorted(
    os.path.join("ci_imgs", f) for f in os.listdir("ci_imgs")
    if f.lower().endswith((".jpg", ".png", ".webp")))

# دو نوارِ فصلِ Green-Skin (صفحات ۶..۱۰ و ۱۱..۱۵)
try:
    for nm, rng in (("gs22_strip002", range(6, 11)), ("gs22_strip003", range(11, 16))):
        ims = [cv2.imread(f"/tmp/gs22/p{i:03d}.jpg") for i in rng]
        if all(im is not None for im in ims):
            cv2.imwrite(f"/tmp/gs22/{nm}.jpg", np.vstack(ims))
            files.append(f"/tmp/gs22/{nm}.jpg")
except Exception as e:
    print("gs strips:", e)

mt = manga.MangaTranslator(api_key="dummy", ocr_langs=["en"],
                           gpu=False, clean_only=True, debug=False,
                           font_path="fonts/Vazirmatn-Bold.ttf")
print("engine:", mt._ocr_backend_name)

out = {}
for f in files:
    t0 = time.time()
    try:
        im = cv2.imread(f)
        if im is None:
            out[f] = {"error": "read"}
            continue
        regions, _dbg = mt.extract_regions_phase(im)
        out[f] = {
            "n": len(regions),
            "t": round(time.time() - t0, 1),
            "regions": [
                {"r": [int(v) for v in rr.rect[:4]], "k": rr.kind,
                 "e": bool(getattr(rr, "ocr_empty", False)),
                 "t": (rr.source_text or "")[:120]}
                for rr in regions],
        }
        print(f"{os.path.basename(f):38s} n={len(regions):3d} t={time.time()-t0:6.1f}s")
    except Exception as e:
        out[f] = {"error": f"{type(e).__name__}: {e}"}
        print(f"{os.path.basename(f):38s} ERROR {e}")
        traceback.print_exc()

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("saved:", OUT)
