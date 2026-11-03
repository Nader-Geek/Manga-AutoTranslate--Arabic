# -*- coding: utf-8 -*-
"""v1.14.203 — تستِ عملیِ سه فیکسِ دستورِ سازنده:

۱) سرعتِ دانلودِ از لینک (~۸۹ثانیه → موازی): سرورِ HTTPِ محلی با
   تاخیرِ ۰.۵s برایِ هر تصویر — حداکثرِ اتصالِ همزمان ≥ ۳ (دانلودِ
   پشتسرهم همیشه ۱ است) + ترتیبِ ذخیره = ترتیبِ HTML + ردِ ۴۰۴ مثلِ قبل.
۲) برشِ امنِ نزدیکِ متن: با detectorِ ساختگیِ پیکسلی — برشِ جدید به
   متن نزدیکتر از حاشیهٔ قدیمی می‌نشیند و هرگز داخلِ باکسِ متن/حباب
   نیست.
۳) برشِ امنِ فقطِ باندِ ۷۰۰۰–۸۰۰۰ (دفعهٔ اولِ سریعتر): تعدادِ
   فراخوانیِ detector برایِ اولین برش به‌وضوح کمتر از اسکنِ کلِ نوار.
"""
import os
import sys
import time
import threading
import tempfile
import shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MANGA_SKIP_HEAVY_INIT", "1")

import manga  # noqa: E402

MangaTranslator = manga.MangaTranslator

_GATES = []


def gate(name: str, ok: bool) -> None:
    _GATES.append((name, bool(ok)))
    print(f"  {'✓' if ok else '✗'} {name}")


# ── ۱) گیتهایِ نسخه ──────────────────────────────────────────────────
def check_versions():
    print("[۱] نسخه")
    gate("APP_VER = 1.14.203", manga.APP_VER == "1.14.203")
    ver = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "VERSION"), encoding="utf-8").read()
    gate("VERSION versionCode=208", "versionCode=208" in ver)
    gate("VERSION versionName=1.14.203", "versionName=1.14.203" in ver)
    gradle = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "android/app/build.gradle.kts"),
        encoding="utf-8").read()
    gate("gradle versionCode = 208", "versionCode = 208" in gradle)
    gate("gradle versionName = 1.14.203", 'versionName = "1.14.203"' in gradle)


# ── ۲) گیتهایِ ایستایِ کد ────────────────────────────────────────────
def check_static():
    print("[۲] کد")
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "manga.py"), encoding="utf-8").read()
    gate("دانلود: سشنِ مشترک + HTTPAdapter",
         "_sess = requests.Session()" in src
         and "HTTPAdapter(" in src)
    gate("دانلود: استخرِ موازیِ ThreadPoolExecutor",
         "with ThreadPoolExecutor(max_workers=_dl_workers) as _dex:" in src)
    gate("دانلود: MANGA_DL_WORKERS", "MANGA_DL_WORKERS" in src)
    gate("دانلود: نوشتنِ ترتیبی در نخِ اصلی (zip)",
         "for img_url, _content in zip(img_urls, _dl_contents):" in src)
    gate("برش: اسکنِ فقطِ باند (_scan_band)",
         "def _scan_band(_band_top: int, _band_bot: int) -> None:" in src)
    gate("برش: اسکنِ باند قبلِ برشِ اصلی",
         "_scan_band(_band_lo, min(_band_hi, max_cut))" in src)
    gate("برش: اسکنِ باند برایِ فالبک", "_scan_band(_fb_lo, _fb_hi)" in src)
    gate("برش: حاشیهٔ نزدیکِ متن (edge=0.02)",
         "edge_margin = max(14, int(round(iw * 0.02)))" in src)
    gate("برش: paddingِ نزدیکِ متن (0.02)",
         "padding = max(14, int(round(target_w * 0.02)))" in src)
    gate("برش: باندِ قدیمیِ تمامنوار حذف شد",
         "_max_cut_probe" not in src and "scan_from = scan_limit" not in src)


# ── ۳) تستِ عملیِ دانلودِ موازی ──────────────────────────────────────
def check_download_parallel():
    print("[۳] دانلودِ موازی (سرورِ محلی)")
    tmp = tempfile.mkdtemp(prefix="m203dl_")
    try:
        pngs = {}
        names = ["pa", "pb", "pc", "pd", "pe", "pf", "pg", "ph",
                 "pi", "pj", "pk", "pl"]
        for n in names:
            img = np.full((320, 240, 3), 250, dtype=np.uint8)
            cv2.putText(img, n, (30, 160), cv2.FONT_HERSHEY_SIMPLEX,
                        1.2, (0, 0, 0), 3)
            ok, buf = cv2.imencode(".png", img)
            pngs[n + ".png"] = buf.tobytes()

        active = [0]
        conc = [0]
        lock = threading.Lock()

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, body: bytes, ctype: str, code: int = 200):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                with lock:
                    active[0] += 1
                    conc[0] = max(conc[0], active[0])
                try:
                    if self.path in ("/", "/index.html"):
                        html = "<html><body>" + "".join(
                            f'<img src="/{n}.png">' for n in names
                        ) + '<img src="/px.png"></body></html>'
                        self._send(html.encode(), "text/html")
                        return
                    if self.path == "/px.png":
                        self._send(b"nope", "text/plain", 404)
                        return
                    data = pngs.get(os.path.basename(self.path))
                    if data is None:
                        self._send(b"", "text/plain", 404)
                        return
                    time.sleep(0.5)  # شبیهسازیِ CDNِ کند
                    self._send(data, "image/png")
                finally:
                    with lock:
                        active[0] -= 1

        srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        base = f"http://127.0.0.1:{srv.server_address[1]}/"
        dest = os.path.join(tmp, "dl")
        t0 = time.time()
        saved = MangaTranslator._download_images_from_url(
            base, dest)
        dt = time.time() - t0
        srv.shutdown()
        got = [os.path.basename(p) for p in (saved or [])]
        expect = [n + ".png" for n in names]
        gate(f"۱۲ تصویر ذخیره شد (۴۰۴ رد شد) — {len(got)}",
             got == expect)
        gate("ترتیبِ ذخیره = ترتیبِ HTML", got == expect)
        gate(f"اتصالِ همزمان ≥ ۳ (موازی واقعی) — {conc[0]}",
             conc[0] >= 3)
        gate(f"زمانِ {dt:.1f}s < حدِ پشتسرهمِ 6.0s",
             dt < 6.0 and conc[0] >= 3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── detectorِ ساختگیِ پیکسلی (بهجایِ مدلِ واقعی — قطعی) ──────────────
class PixelDet:
    """جایگزینِ detector-v4-s در تست: میلههایِ تیره را باکس میزند."""

    def __init__(self):
        self.calls = 0
        self.lock = threading.Lock()

    def detect(self, image_bgr, fast=False):
        with self.lock:
            self.calls += 1
        g = (cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
             if image_bgr.ndim == 3 else image_bgr)
        dark = [y for y in range(g.shape[0]) if int(g[y].min()) < 128]
        bars = []
        for y in dark:
            if bars and y <= bars[-1][1] + 2:
                bars[-1][1] = y
            else:
                bars.append([y, y])
        w = int(image_bgr.shape[1])
        return [{"rect": (10, int(b[0]), w - 10, int(b[1]) + 1),
                 "class_name": "text_bubble", "confidence": 0.9}
                for b in bars if b[1] - b[0] >= 8]


def _make_page(path: str, bar_ys, w=800, h=2000):
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    for (y1, y2) in bar_ys:
        img[y1:y2, 250:550] = 20  # «متن»
    cv2.imwrite(path, img)


def _new_mt(det):
    mt = MangaTranslator.__new__(MangaTranslator)
    mt.det = det
    mt.stitch_max_height = 8000
    mt.stitch_keep_first = False
    mt.max_output_width = 0
    mt.img_format = "png"
    mt.img_quality = 90
    mt.repair_page_seams = False
    return mt


# ── ۴) تستِ عملیِ برشِ امن با ۷ صفحهٔ ۲۰۰۰px ─────────────────────────
def check_safe_cut():
    print("[۴] برشِ امن — فقطِ باند + نزدیکِ متن")
    tmp = tempfile.mkdtemp(prefix="m203cut_")
    try:
        # میلههایِ «متن»: درِ باند [7000,8000] یک میلهٔ 7380–7520 است
        page_bars = [
            [(400, 460)], [(2300, 2360)], [(4300, 4360)],
            [(300, 360), (1380, 1520)],   # صفحهٔ ۴ → مطلقِ 6300 و 7380–7520
            [(300, 360)],                 # صفحهٔ ۵ → مطلقِ 8300
            [(300, 360)],                 # صفحهٔ ۶ → مطلقِ 10300
            [(300, 360)],                 # صفحهٔ ۷ → مطلقِ 12300
        ]
        files = []
        for i, bars in enumerate(page_bars):
            f = os.path.join(tmp, f"p{i:02d}.png")
            _make_page(f, bars)
            files.append(f)

        det = PixelDet()
        mt = _new_mt(det)
        out_dir = os.path.join(tmp, "strips")
        os.makedirs(out_dir, exist_ok=True)
        strips = mt._stitch_pages_for_efficiency(files, out_dir)
        heights = [int(cv2.imread(s).shape[0]) for s in strips]
        n_calls = det.calls

        gate(f"۲ نوار ساخته شد ({len(strips)})", len(strips) == 2)
        h1 = heights[0] if heights else -1
        # کاندیدهایِ برش: 7334 (۴۶px بالایِ میلهٔ 7380) و 7918 (وسطِ شکافِ
        # 7552..8284) — نزدیکترین به هدفِ 7500 = 7334؛ رفتارِ قدیمی 7255 بود
        gate(f"برشِ نزدیکِ متن در باند (h1={h1} در [7280,7380))",
             7280 <= h1 < 7380)
        gate("برش از حاشیهٔ قدیمیِ (7255) به متن نزدیکتر شد", h1 > 7255)
        gate("متنِ 7380–7520 بریده نشد",
             not (7380 - 8 <= h1 <= 7520 + 8))
        gate(f"فراخوانیِ detector کم (فقطِ باند) = {n_calls} ≤ ۱۱",
             n_calls <= 11)

        # سناریویِ دوم: کلِ باند پُرِ متن → برشِ لبهٔ باند، نه وسطِ متن
        page_bars2 = [
            [(400, 460)], [(2300, 2360)], [(4300, 4360)],
            [(300, 360), (1050, 1950)],   # میلهٔ 7050–7950 = کلِ باند
            [(300, 360)], [(300, 360)], [(300, 360)],
        ]
        files2 = []
        for i, bars in enumerate(page_bars2):
            f = os.path.join(tmp, f"q{i:02d}.png")
            _make_page(f, bars)
            files2.append(f)
        det2 = PixelDet()
        mt2 = _new_mt(det2)
        out2 = os.path.join(tmp, "strips2")
        os.makedirs(out2, exist_ok=True)
        strips2 = mt2._stitch_pages_for_efficiency(files2, out_dir
                                                   if False else out2)
        h2 = int(cv2.imread(strips2[0]).shape[0]) if strips2 else -1
        gate(f"باندِ پُرِ متن → برش بیرونِ متن (h2={h2})",
             (h2 < 7050) or (h2 > 7950))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── ۵) یونیتِ _find_safe_cut_y_smart ─────────────────────────────────
def check_smart_cut():
    print("[۵] یونیتِ برشِ هوشمند")
    mt = _new_mt(PixelDet())
    strip = np.full((12000, 800, 3), 255, dtype=np.uint8)
    strip[5800:6200, 250:550] = 20
    cut = mt._find_safe_cut_y_smart(strip, 6000, 5500, 6500,
                                    search_radius=500)
    gate(f"برشِ نزدیکِ متن (cut={cut} در [5730,5800])",
         cut is not None and 5730 <= cut <= 5800)
    gate("متنِ 5800–6200 بریده نشد",
         cut is not None and not (5800 - 6 <= cut <= 6200 + 6))
    strip2 = np.full((12000, 800, 3), 255, dtype=np.uint8)
    strip2[5400:6600, 250:550] = 20  # کلِ پنجره متن
    cut2 = mt._find_safe_cut_y_smart(strip2, 6000, 5500, 6500,
                                     search_radius=500)
    gate("پنجرهٔ کاملاً متنی → None (برشِ کور ممنوع)", cut2 is None)


def main():
    print("── test_v114203_dl_cut ──")
    check_versions()
    check_static()
    check_download_parallel()
    check_safe_cut()
    check_smart_cut()
    bad = [n for n, ok in _GATES if not ok]
    print(f"── {len(_GATES) - len(bad)}/{len(_GATES)} گیتِ سبز ──")
    if bad:
        print("مردود:", *bad, sep="\n  ✗ ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
