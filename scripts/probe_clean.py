# پروبِ متمرکزِ پاکسازی — یک عکس، یک روش، با دامپِ کامل
import os, sys, time, pickle
import cv2
import numpy as np

ROOT = '/home/z/my-project/Manga-AutoTranslate'
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import manga  # noqa: E402

name, meth = sys.argv[1], sys.argv[2]
tag = os.path.splitext(os.path.basename(name))[0]
cache = f'/home/z/my-project/clean_out/extract_{tag}.pkl'
with open(cache, 'rb') as fh:
    regs = pickle.load(fh)
cf = [r for r in regs
      if r.kind == 'dialogue'
      and not getattr(r, 'ocr_empty', False)
      and ((r.source_text or '').strip()
           or (r.translated_text or '').strip())]
img = cv2.imread(name if os.path.isabs(name) else os.path.join('ci_imgs', name))
tr = manga.MangaTranslator(
    api_key='probe', provider='gemini', ocr_langs=['en'],
    font_path='fonts/Vazirmatn-Regular.ttf',
    clean_method=meth, gpu=False, force_lama=True,
    clean_only=True, debug=False, story_brief=False, max_workers=1)
t0 = time.time()
out = tr.clean_image(img.copy(), list(cf))
print(f'[probe] {tag} {meth} t={time.time()-t0:.1f}s regions={len(cf)}')
cv2.imwrite(f'/tmp/probe_{tag}__{meth}.jpg', out,
            [cv2.IMWRITE_JPEG_QUALITY, 92])
