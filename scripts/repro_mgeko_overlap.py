#!/usr/bin/env python3
"""v1.14.321 — بازتولیدِ باگِ فصلِ هم‌پوشانِ mgeko (چکِ سبز/قرمز).

سناریو (خواستهٔ کاربر):
  ورودی ۱: ch102,ch103 → استخراج/ترجمه کامل میشود.
  ورودی ۲: ch103,ch104 → موتور نباید بهخاطر فصلِ مشترکِ 103 یا کشِ مشترک
            خراب شود؛ ch103 باید بدونِ دانلود/ترجمه از «انبارِ فصلها»
            برگردد، فقط ch104 پردازش شود، و PDF نهایی دقیقاً ۸ صفحه
            با ترتیبِ درست (ch103 سپس ch104) باشد.

موتور با سرورِ محلیِ شبیهِ mgeko اجرا میشود (بدون اینترنت) با
--fake-translate (بدون کلید API) و پاکسازیِ opencv.

اجرا (فازی تا در timeout جا شود):
  python3 scripts/repro_mgeko_overlap.py --phase=A
  python3 scripts/repro_mgeko_overlap.py --phase=B
  python3 scripts/repro_mgeko_overlap.py --phase=C
  python3 scripts/repro_mgeko_overlap.py            # همه با هم

خروجی: exit 0 = همهٔ چکهای آن فاز سبز؛ exit 1 = رگرسیون.
"""
import http.server
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(HERE, "manga.py")
WORK = "/tmp/repro_mgeko"
STORE = os.path.join(WORK, "chapter_store")
# مثل اندروید: هر سه اجرا «همان» مسیرِ خروجی را میگیرند (کشِ مشترک)
OUT_A = os.path.join(WORK, "manga.pdf")
OUT_B = os.path.join(WORK, "manga.pdf")
OUT_C = os.path.join(WORK, "manga.pdf")
LOG_A = os.path.join(WORK, "runA.log")
LOG_B = os.path.join(WORK, "runB.log")
LOG_C = os.path.join(WORK, "runC.log")

PAGES_PER_CH = 4
CHAPTERS = (102, 103, 104)
FONT = os.path.join(HERE, "fonts", "Vazirmatn-Bold.ttf")

_REQUESTS = {"html": [], "img": []}
_LOCK = threading.Lock()
RESULTS = []


def _make_page_png(ch: int, pg: int) -> bytes:
    """صفحهٔ مانگای ساختگی: حباب بیضی + متنِ انگلیسی + نشانِ ترتیب."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 640, 900
    im = Image.new("RGB", (W, H), (252, 252, 250))
    d = ImageDraw.Draw(im)
    d.ellipse([80, 180, 560, 480], outline=(20, 20, 20), width=4,
              fill=(255, 255, 255))
    try:
        f_big = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        f_small = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        f_big = f_small = ImageFont.load_default()
    d.text((150, 260), f"CHAPTER {ch}", fill=(10, 10, 10), font=f_big)
    d.text((150, 320), f"PAGE {pg} TEST", fill=(10, 10, 10), font=f_big)
    d.text((150, 380), "THE VILLAGE IS QUIET", fill=(10, 10, 10), font=f_small)
    d.polygon([(200, 470), (180, 540), (260, 480)], fill=(255, 255, 255),
              outline=(20, 20, 20))
    d.rounded_rectangle([120, 600, 520, 780], radius=60,
                        outline=(20, 20, 20), width=4,
                        fill=(255, 255, 255))
    d.text((170, 660), f"LOOK OUT {pg}", fill=(10, 10, 10), font=f_big)
    val = (ch * 1000 + pg)
    for bit in range(16):
        x = 40 + bit * 34
        y = 850 if (val >> bit) & 1 else 862
        d.rectangle([x, y, x + 24, y + 10], fill=(30, 30, 30))
    buf = io.BytesIO()
    try:
        im.save(buf, format="WEBP", quality=92)
    except Exception:
        buf = io.BytesIO()
        im.save(buf, format="PNG")
    return buf.getvalue()


class MockHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        m = re.match(r"^/data/testvillage/chapter-(\d+)/(\d+)\.webp$",
                     self.path)
        if m:
            ch, pg = int(m.group(1)), int(m.group(2))
            if ch in CHAPTERS and 1 <= pg <= PAGES_PER_CH:
                self._send(200, b"", "image/webp")
                return
        self._send(404, b"", "text/plain")

    def do_GET(self):
        m = re.match(r"^/reader/en/testvillage-chapter-(\d+)-eng-li/?$",
                     self.path)
        if m:
            ch = int(m.group(1))
            if ch in CHAPTERS:
                with _LOCK:
                    _REQUESTS["html"].append(ch)
                imgs = "\n".join(
                    f'<img src="/data/testvillage/chapter-{ch}/{i}.webp">'
                    for i in range(1, PAGES_PER_CH + 1))
                html = (f"<html><body><h1>Test Village Ch.{ch}</h1>"
                        f"{imgs}</body></html>").encode()
                self._send(200, html, "text/html")
                return
        m = re.match(r"^/data/testvillage/chapter-(\d+)/(\d+)\.webp$",
                     self.path)
        if m:
            ch, pg = int(m.group(1)), int(m.group(2))
            if ch in CHAPTERS and 1 <= pg <= PAGES_PER_CH:
                with _LOCK:
                    _REQUESTS["img"].append((ch, pg))
                png = _make_page_png(ch, pg)
                self._send(200, png, "image/webp")
                return
        self._send(404, b"nope", "text/plain")


def start_server():
    # پورتِ ثابت — کلیدِ انبارِ فصل به URL (شامل پورت) وابسته است
    for port in (8765, 8766, 8767, 8768):
        try:
            srv = http.server.ThreadingHTTPServer(
                ("127.0.0.1", port), MockHandler)
            break
        except OSError:
            continue
    else:
        raise RuntimeError("پورت آزاد برای سرورِ شبیه‌ساز پیدا نشد")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def run_engine(inp: str, out_pdf: str, log_path: str) -> int:
    env = dict(os.environ)
    env["MANGA_CHAPTER_STORE"] = STORE
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [
        sys.executable, ENGINE,
        "-i", inp,
        "-o", out_pdf,
        "--font", FONT,
        "--fake-translate",
        "--clean-method", "opencv",
        "--cpu",
        "--img-format", "jpg",
        "--workers", "1",
    ]
    with open(log_path, "w") as lf:
        p = subprocess.run(cmd, cwd=HERE, env=env, stdout=lf,
                           stderr=subprocess.STDOUT, timeout=520)
    return p.returncode


def read_log(p: str) -> str:
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def pdf_pages(pdf_path: str):
    import fitz
    import numpy as np
    doc = fitz.open(pdf_path)
    pages = []
    for pg in doc:
        pix = pg.get_pixmap(dpi=100)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n)[:, :, :3]
        pages.append(arr.copy())
    doc.close()
    return pages


def sim(a, b) -> float:
    import cv2
    import numpy as np

    def _g(arr):
        g = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) \
            if arr.ndim == 3 and arr.shape[2] == 3 else arr
        return cv2.resize(g, (96, 128)).astype(np.float32)

    ga, gb = _g(a), _g(b)
    if ga.shape != gb.shape:
        return 999.0
    return float(np.mean(np.abs(ga - gb)))


def load_img_rgb(path: str):
    import cv2
    arr = cv2.imread(path, cv2.IMREAD_COLOR)
    return cv2.cvtColor(arr, cv2.COLOR_BGR2RGB) if arr is not None else None


def store_chapters():
    out = {}
    if not os.path.isdir(STORE):
        return out
    for name in os.listdir(STORE):
        mp = os.path.join(STORE, name, "meta.json")
        try:
            with open(mp, encoding="utf-8") as f:
                meta = json.load(f)
            url = meta.get("url") or ""
            m = re.search(r"chapter-(\d+)", url)
            ch = m.group(1) if m else "?"
            out[ch] = [os.path.join(STORE, name, p["f"])
                       for p in (meta.get("pages") or [])]
        except Exception:
            continue
    return out


def check(name: str, ok: bool, detail: str = ""):
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""),
          flush=True)


def _fail_fast(log: str):
    print("\n--- آخرین خطوط لاگ ---")
    print("\n".join(log.strip().splitlines()[-40:]))
    sys.exit(1)


def run_phase_a(in_a: str):
    print("\n[Run A] ch102,ch103 …", flush=True)
    rc = run_engine(in_a, OUT_A, LOG_A)
    log_a = read_log(LOG_A)
    check("A: موتور بدون خطا تمام شد", rc == 0, f"rc={rc}")
    if rc != 0:
        _fail_fast(log_a)

    n_pdf_a = len(pdf_pages(OUT_A)) if os.path.isfile(OUT_A) else 0
    check(f"A: PDF دقیقاً {2 * PAGES_PER_CH} صفحه دارد",
          n_pdf_a == 2 * PAGES_PER_CH, f"got {n_pdf_a}")

    st = store_chapters()
    check("A: هر دو فصل در انبار ذخیره شدند",
          set(st.keys()) == {"102", "103"}, f"store={sorted(st.keys())}")
    check("A: هر فصل انبار کامل است",
          all(len(v) == PAGES_PER_CH for v in st.values()),
          "sizes=%s" % {k: len(v) for k, v in st.items()})


def run_phase_b(in_b: str):
    with _LOCK:
        _REQUESTS["html"].clear()
        _REQUESTS["img"].clear()
    print("\n[Run B] ch103,ch104 (فصلِ هم‌پوشان) …", flush=True)
    rc = run_engine(in_b, OUT_B, LOG_B)
    log_b = read_log(LOG_B)
    check("B: موتور بدون خطا تمام شد", rc == 0, f"rc={rc}")
    if rc != 0:
        _fail_fast(log_b)

    check("B: ch103 از انبار برگشت (بدون دانلود/ترجمه)",
          ("از انبارِ فصلها" in log_b),
          "" if "از انبارِ فصلها" in log_b else "پیام انبار در لاگ نیست")
    with _LOCK:
        html_reqs = list(_REQUESTS["html"])
        img_reqs = list(_REQUESTS["img"])
    n_html_103 = html_reqs.count(103)
    n_img_103 = sum(1 for ch, _ in img_reqs if ch == 103)
    n_img_104 = sum(1 for ch, _ in img_reqs if ch == 104)
    check("B: هیچ درخواست دانلودی برای ch103 نرفت",
          n_html_103 == 0 and n_img_103 == 0,
          f"html103={n_html_103} img103={n_img_103}")
    check(f"B: ch104 کامل دانلود شد ({PAGES_PER_CH} تصویر)",
          n_img_104 == PAGES_PER_CH, f"img104={n_img_104}")

    pages_b = pdf_pages(OUT_B) if os.path.isfile(OUT_B) else []
    check(f"B: PDF دقیقاً {2 * PAGES_PER_CH} صفحه دارد",
          len(pages_b) == 2 * PAGES_PER_CH, f"got {len(pages_b)}")

    st_b = store_chapters()
    if "103" in st_b and len(pages_b) >= 2 * PAGES_PER_CH:
        ok_order = True
        worst = 0.0
        for i in range(PAGES_PER_CH):
            exp = load_img_rgb(st_b["103"][i])
            d = sim(pages_b[i], exp)
            worst = max(worst, d)
            if d > 14.0:
                ok_order = False
        check("B: ترتیب درست — صفحاتِ اول = ch103 (از انبار، همان رندرِ A)",
              ok_order, f"بیشترین اختلاف پیکسلی={worst:.1f}")
        ok_104 = True
        worst2 = 0.0
        for i in range(PAGES_PER_CH):
            if "104" not in st_b:
                ok_104 = False
                break
            exp = load_img_rgb(st_b["104"][i])
            d = sim(pages_b[PAGES_PER_CH + i], exp)
            worst2 = max(worst2, d)
            if d > 14.0:
                ok_104 = False
        check("B: ترتیب درست — صفحاتِ دوم = ch104 (رندرِ تازه)",
              ok_104, f"بیشترین اختلاف پیکسلی={worst2:.1f}")
    else:
        check("B: انبارِ ch103 برای چکِ ترتیب آماده بود",
              False, f"store={sorted(st_b.keys())}")

    check("B: فصل ch104 هم در انبار ذخیره شد",
          set(st_b.keys()) == {"102", "103", "104"},
          f"store={sorted(st_b.keys())}")


def run_phase_c(in_b: str):
    with _LOCK:
        _REQUESTS["html"].clear()
        _REQUESTS["img"].clear()
    print("\n[Run C] تکرارِ همان ورودی B (همه از انبار) …", flush=True)
    rc = run_engine(in_b, OUT_C, LOG_C)
    log_c = read_log(LOG_C)
    check("C: موتور بدون خطا تمام شد", rc == 0, f"rc={rc}")
    if rc != 0:
        _fail_fast(log_c)
    n_store_hits_c = len(re.findall(r"از انبارِ فصلها", log_c))
    check("C: هر دو فصل از انبار آمدند (بدونِ دانلود)",
          n_store_hits_c >= 2, f"hits={n_store_hits_c}")
    pages_c = pdf_pages(OUT_C) if os.path.isfile(OUT_C) else []
    check(f"C: PDF همان {2 * PAGES_PER_CH} صفحه را دارد",
          len(pages_c) == 2 * PAGES_PER_CH, f"got={len(pages_c)}")
    with _LOCK:
        img_reqs_c = len(_REQUESTS["img"])
    check("C: هیچ تصویری از شبکه نیامد", img_reqs_c == 0,
          f"img reqs={img_reqs_c}")


def main():
    phase = "all"
    if len(sys.argv) > 1 and sys.argv[1].startswith("--phase="):
        phase = sys.argv[1].split("=", 1)[1]
    if phase == "A":
        shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(STORE, exist_ok=True)

    srv, port = start_server()
    tmpl = "http://127.0.0.1:%d/reader/en/testvillage-chapter-%%d-eng-li/" % port
    in_a = (tmpl % 102) + "," + (tmpl % 103)
    in_b = (tmpl % 103) + "," + (tmpl % 104)
    with open(os.path.join(WORK, "inputs.json"), "w") as f:
        json.dump({"in_a": in_a, "in_b": in_b}, f)

    if phase in ("all", "A"):
        run_phase_a(in_a)
    if phase in ("all", "B"):
        run_phase_b(in_b)
    if phase in ("all", "C"):
        run_phase_c(in_b)

    n_ok = sum(1 for _, okk, _ in RESULTS if okk)
    print("\n%s\n[نتیجه] %d/%d چک سبز" % ("=" * 60, n_ok, len(RESULTS)))
    for name, okk, det in RESULTS:
        if not okk:
            print("  ✗ FAILED: %s %s" % (name, det))
    srv.shutdown()
    sys.exit(0 if n_ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
