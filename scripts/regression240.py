# رگرسیون پاکسازی v1.14.240 — مقایسهٔ خروجیِ clean همهٔ ci_imgs
# خروجی: PNG پاک‌شدهٔ هر عکس + JSON از هش و آمارِ UIB
import os, sys, json, time, hashlib, traceback
os.chdir("/home/z/my-project/Manga-AutoTranslate")
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")
import numpy as np, cv2
import manga

TAG = sys.argv[1] if len(sys.argv) > 1 else "new"
OUTDIR = f"/tmp/reg240/{TAG}"
os.makedirs(OUTDIR, exist_ok=True)

files = sorted(
    os.path.join("ci_imgs", f) for f in os.listdir("ci_imgs")
    if f.lower().endswith((".jpg", ".png", ".webp")))
# صفحهٔ جدیدِ SHAN SHAN هم اضافه
if os.path.exists("/tmp/test_shanshan.jpg"):
    files.insert(0, "/tmp/test_shanshan.jpg")

mt = manga.MangaTranslator(api_key="dummy", ocr_langs=["en"],
                           gpu=False, clean_only=True, debug=False,
                           font_path="fonts/Vazirmatn-Bold.ttf")
print("engine:", mt._ocr_backend_name, flush=True)

out = {}
for f in files:
    base = os.path.basename(f)
    t0 = time.time()
    try:
        im = cv2.imread(f)
        if im is None:
            out[base] = {"error": "read"}
            continue
        regions, _dbg = mt.extract_regions_phase(im)
        cleaned = mt._clean_image_page(im, regions)
        cv2.imwrite(os.path.join(OUTDIR, base + ".png"), cleaned)
        # آمار UIB از مسیر داخلی: چند پیکسل نجاتِ جوهر
        hsh = hashlib.sha256(
            cv2.imencode(".png", cleaned)[1].tobytes()).hexdigest()[:16]
        out[base] = {
            "n": len(regions), "t": round(time.time() - t0, 1),
            "sha": hsh,
            "regions": [
                {"r": [int(v) for v in rr.rect[:4]], "k": rr.kind,
                 "t": (rr.source_text or "")[:80]}
                for rr in regions],
        }
        print(f"{base:38s} n={len(regions):3d} t={time.time()-t0:6.1f}s "
              f"sha={hsh}", flush=True)
    except Exception as e:
        out[base] = {"error": f"{type(e).__name__}: {e}"}
        print(f"{base:38s} ERROR {e}", flush=True)
        traceback.print_exc()

with open(os.path.join(OUTDIR, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("saved:", os.path.join(OUTDIR, "summary.json"))
