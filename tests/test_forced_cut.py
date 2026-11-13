"""Chapters with no text-safe cut (full-bleed art) used to abort with
'الشريط بدون موضع قص آمن...'. With allow_forced_cut they are cut anyway. No models needed."""
import re, sys, tempfile, textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np, cv2
ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "manga.py").read_text(encoding="utf-8")

def grab(name):   # pull a method out of manga.py without importing it (the import auto-installs torch)
    mt = re.search(r'(?:    @staticmethod\r?\n)?    def %s\(.*?(?=\r?\n    (?:@staticmethod|def )|\r?\nclass |\Z)' % name, src, re.S)
    return textwrap.dedent(mt.group(0))

ns = {"np": np, "cv2": cv2, "os": __import__("os"), "List": List, "Optional": Optional, "Tuple": Tuple, "Dict": Dict}
body = "class T:\n" + textwrap.indent(grab("_find_safe_cut_y") + "\n" + grab("_stitch_pages_for_efficiency"), "    ")
exec(body, ns)
class _M:
    MangaTranslator = ns["T"]
m = _M
m.MangaTranslator._write_image = lambda self, image, path: cv2.imwrite(path, image)

class Det:                      # one tall "bubble" everywhere -> no protected-free area
    def detect(self, img): return [{"rect": (0, 0, img.shape[1], img.shape[0])}]

def make(force):
    t = m.MangaTranslator()
    t.stitch_max_height = 2000; t.stitch_short_threshold = 0; t.stitch_keep_first = False
    t.det = Det(); t.img_format = "png"; t.max_output_width = 0; t.allow_forced_cut = force
    t.repair_page_seams = True
    return t

d = Path(tempfile.mkdtemp()); rs = np.random.RandomState(0); files = []
for i in range(40):            # 40 x 1700px of noise = 68000px > 32000
    f = d / f"{i:03d}.png"; cv2.imwrite(str(f), rs.randint(0, 255, (1700, 300, 3), dtype=np.uint8)); files.append(str(f))

try:
    make(False)._stitch_pages_for_efficiency(files, str(d / "o1")); raise SystemExit("expected RuntimeError")
except RuntimeError as e:
    assert "موضع قص آمن" in str(e), e
out = make(True)._stitch_pages_for_efficiency(files, str(d / "o2"))
hs = [cv2.imread(f).shape[0] for f in out]
assert sum(hs) == 40 * 1700 and len(out) >= 4 and max(hs) < 40000, hs
print("test_forced_cut OK", len(out), "strips")
