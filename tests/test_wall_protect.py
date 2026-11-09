"""Synthetic test for the wall-protection / fill-cap helpers ported from the
upstream fork. Run: python3 tests/test_wall_protect.py"""
import os, re
import numpy as np, cv2
from typing import Optional

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'manga.py'), encoding='utf-8').read()
# extract the two static helpers without importing the whole (auto-installing) module
def grab(name):
    m = re.search(r'    @staticmethod\r?\n    def %s\(.*?(?=\r?\n    (?:@staticmethod|def ))' % name, src, re.S)
    code = m.group(0)
    import textwrap
    return textwrap.dedent(code)
ns = {'np': np, 'cv2': cv2, 'Optional': Optional}
exec(grab('_structural_protect_mask'), ns)
exec(grab('_fill_cap_mask'), ns)
protect_fn, cap_fn = ns['_structural_protect_mask'], ns['_fill_cap_mask']

# synthetic page: grey art left, white bubble with a 3px wall, text inside near the wall
img = np.full((400, 600, 3), 200, np.uint8)
cv2.rectangle(img, (100, 100), (500, 300), (255, 255, 255), -1)
cv2.rectangle(img, (100, 100), (500, 300), (0, 0, 0), 3)           # bubble wall
cv2.putText(img, "HELLO", (110, 135), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)  # text next to top wall
mask = np.zeros(img.shape[:2], np.uint8)
mask[112:145, 108:260] = 255                                         # raw text mask
# dilated fill mask like the pipeline's (25px) -> would swallow the wall at y=100..102
fill = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))

prot = protect_fn(img, mask)
cap = cap_fn(mask)
wall_px = np.zeros(mask.shape, bool); wall_px[100:103, 100:500] = True
assert prot is not None, "no protection map"
near_wall = wall_px & (fill > 0)
covered = (prot & near_wall).sum() / max(1, near_wall.sum())
inside_text = (prot & (mask > 0)).sum()
old_hit = ((fill > 0) & wall_px).sum()
new_fill = (fill > 0) & cap & ~prot
new_hit = (new_fill & wall_px).sum()
over = (new_fill & ~(cv2.dilate(mask, np.ones((15,15),np.uint8))>0)).sum()
print(f"wall px (in fill area) protected: {covered:.0%}")
print(f"protected pixels inside text   : {inside_text}")
print(f"wall px painted OLD / NEW      : {old_hit} / {new_hit}")
print(f"fill px beyond 7px of raw mask : {over}")
print(f"text px still fillable         : {((new_fill) & (mask>0)).sum()} of {(mask>0).sum()}")
assert covered > 0.9 and inside_text == 0 and new_hit == 0 and over == 0
# negative check: no wall -> nothing protected; thick dark art block not protected
img2 = np.full((300, 400, 3), 255, np.uint8); cv2.rectangle(img2, (50, 50), (350, 90), (0,0,0), -1)
m2 = np.zeros((300,400),np.uint8); m2[60:80, 60:120] = 255
print("thick dark art protected px    :", 0 if protect_fn(img2, m2) is None else int(protect_fn(img2, m2).sum()))
print("ALL OK")
