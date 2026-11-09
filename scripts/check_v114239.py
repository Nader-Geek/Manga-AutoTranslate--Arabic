# check_v114239.py — چکهای منطقی نسخهٔ v1.14.239
# (۱) ارورِ گرادیوِ «needed: 15, returned: 14»  (۲) گاردِ برشِ حبابِ چسبیده
# (۳) دراپِ باکسِ تکراریِ حبابِ متن‌دار  (۴) نوارِ پیشرفتِ K3 (موتور + پارسر)
import os, re, sys, subprocess

os.chdir("/home/z/my-project/Manga-AutoTranslate")
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")

APP = "manga_app.py"
ENG = "manga.py"
app_src = open(APP, encoding="utf-8").read()
eng_src = open(ENG, encoding="utf-8").read()

PASS, FAIL = [], []


def chk(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL") + f" | {name}"
          + (f" — {detail}" if detail and not cond else ""))


# ── ۱) فیکسِ ۱۵-خروجیِ گرادیو ─────────────────────────────────────────
m = re.search(r"_poll_outputs = \[(.*?)\]", app_src, re.S)
n_out = len(re.findall(r"\w+", m.group(1))) if m else -1
chk("_poll_outputs پانزده مؤلفه دارد (با prog_html)", n_out == 15, f"got {n_out}")

seg = app_src[app_src.index("def _hydrate_after_js"):app_src.index("def _hydrate_after_js") + 700]
chk("_hydrate_after_js خالی → (gr.update(),) * 15",
    "(gr.update(),) * 15" in seg and "* 14" not in seg)
seg = app_src[app_src.index("def _sid_box_sync"):app_src.index("def _sid_box_sync") + 500]
chk("_sid_box_sync خالی → (gr.update(),) * 15",
    "(gr.update(),) * 15" in seg and "* 14" not in seg)
# هیچ «* 14»ی رویِ هندلرهای _poll_outputs-دار نمانده
bad14 = [ln.strip()[:70] for ln in app_src.splitlines()
         if "(gr.update(),) * 14" in ln]
chk("هیچ returnِ ۱۴تاییِ دیگر در manga_app نیست (فقط *27 مشروعِ restore و *15/*13های هم‌اندازه)",
    not bad14, str(bad14))

# ── ۲) گاردِ برشِ حبابِ چسبیده ────────────────────────────────────────
chk("_split_cuts_text_239 تعریف شده", "def _split_cuts_text_239" in eng_src)
chk("گارد در نقطهٔ فراخوانیِ split سیم‌کشی شده",
    "self._split_cuts_text_239(image, b[\"rect\"], parts)" in eng_src)
chk("هیچ فراخوانیِ use_rec=False در موتور نیست (مسمومیتِ update_paramsِ rapidocr 3)",
    "use_rec=False" not in eng_src.replace(
        "(use_rec=False → همهٔ پاسهایِ بعدیِ همهٔ کارگرها", "") and
    "use_rec=False" not in app_src)


class _FakeOCR:
    """OCRِ ساختگی برایِ تستِ هندسهٔ گارد — boxها در مختصاتِ کراپ."""

    def __init__(self, lines=None, exc=None):
        self.lines = lines or []
        self.exc = exc

    def ocr(self, crop, crop_mode=False):
        if self.exc:
            raise self.exc
        return [[[np_box(b), ("txt", 0.9)] for b in self.lines]]


def np_box(b):
    import numpy as np
    x0, y0, x1, y1 = b
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)


import numpy as np
import manga

mt = manga.MangaTranslator.__new__(manga.MangaTranslator)  # بدونِ __init__ (بدونِ مدل)


def guard(fake_ocr, full, parts):
    mt.ocr = fake_ocr
    return mt._split_cuts_text_239(np.zeros((7500, 800, 3), np.uint8), full, parts)


# الف) کپشنِ یک‌خطیِ HELLO — خط از درزِ 494..522 میگذرد → برش باید لغو شود
# (مختصاتِ خطها crop-local: مبداِ کراپ = full ± pad ۶)
hello_parts = [[142, 4606, 522, 4744], [494, 4606, 723, 4744]]
ok = guard(_FakeOCR([(110, 14, 685, 119)]), (41, 4607, 723, 4745), hello_parts)
chk("HELLO: خطِ سراسری → برش لغو میشود", ok is True)

# ب) دو حبابِ واقعیِ چسبیده — هر خط داخلِ پارتِ خودش → برش مجاز
ok = guard(_FakeOCR([(115, 19, 435, 119), (510, 19, 680, 119)]),
           (41, 4607, 723, 4745), hello_parts)
chk("دو حبابِ واقعی: خطهای جدا → برش مجاز", ok is False)

# ج) نشتِ کوچکِ unclip (۸px از درز عبور) → تحمل → برش مجاز
ok = guard(_FakeOCR([(115, 19, 495, 119)]), (41, 4607, 723, 4745), hello_parts)
chk("نشتِ ~۸px از لبهٔ unclip → تحمل (برش مجاز)", ok is False)

# د) رویهم (درزِ افقی) — خط از وسط میگذرد → لغو
parts_stack = [[100, 100, 700, 400], [100, 430, 700, 750]]
ok = guard(_FakeOCR([(61, 61, 561, 601)]), (95, 95, 705, 755), parts_stack)
chk("رویهم: خط از درزِ افقی میگذرد → برش لغو", ok is True)

# هـ) OCR خراب/ناموجود → رفتارِ قبل (برش مجاز — فال‌بک امن)
ok = guard(_FakeOCR(exc=RuntimeError("nope")), (41, 4607, 723, 4745), hello_parts)
chk("OCR ناموجود → فال‌بک امن (برش مجاز)", ok is False)

# و) خطِ حبابِ همسایه (کامل بیرونِ باکس) نادیده گرفته میشود
ok = guard(_FakeOCR([(61, 160, 561, 235)]), (95, 95, 705, 755), parts_stack)
chk("خطِ همسایه با مرکزِ بیرونِ باکس → نادیده", ok is False)

# ── ۳) دراپِ باکسِ تکراری ────────────────────────────────────────────
chk("دراپِ باکسِ تکراریِ حبابِ متن‌دار در حلقهٔ نواحی هست",
    "باکسِ تکراریِ" in eng_src and "_iom239 >= 0.28" in eng_src)

# هندسهٔ موردِ واقعی (Green-Skin 22): IoM = 0.415 → دراپ میشود
def iom(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    aa = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
    ab = max(1e-6, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / min(aa, ab)


empty = (142, 5443, 740, 5680)
text = (200, 5602, 646, 5789)
chk("هندسهٔ AHHH: IoM=0.415 ≥ 0.28 → دراپ", iom(empty, text) >= 0.28,
    f"IoM={iom(empty, text):.3f}")
# دو حبابِ مجاورِ واقعی نباید دراپ شوند (هم‌پوشانیِ کم)
chk("دو حبابِ مجاورِ واقعی: IoM < 0.28 → میمانند",
    iom((100, 100, 400, 300), (395, 150, 700, 350)) < 0.28)

# ── ۴) نوارِ پیشرفتِ K3 ──────────────────────────────────────────────
chk("موتور: تیکِ استخراج (n/N صفحه)", "استخراج متن: {_n239}/{len(pending)} صفحه" in eng_src)
chk("موتور: تیکِ پاکسازی (n/N صفحه)", "پاکسازی متن: {_cn239}/{_ctot239} صفحه" in eng_src)
chk("موتور: تیکِ ترجمه (n/N ناحیه)", "ترجمه: {_n239}/{_t239} ناحیه" in eng_src)
chk("موتور: _ext_prog_tick در کارگرِ استخراج", eng_src.count("_ext_prog_tick()") >= 2)
chk("موتور: نشانِ پایانِ استخراج در clean-only",
    "(حالتِ فقط-پاکسازی)" in eng_src)
chk("موتور: «صفحهٔ N آماده شد» در اولین نوشتنِ اسلات (K3)",
    "_first_write239" in eng_src and "or _first_write239" in eng_src)
chk("پارسرِ وب: سه شمارندهٔ n/N",
    all(k in app_src for k in ("استخراج متن[:：]", "پاکسازی متن[:：]", "ترجمه[:：]")))
chk("پارسرِ وب: بازنشستگیِ شمارندهٔ استخراج بعد از اتمام",
    "صفحه کامل شد" in app_src)

# پارسر — سناریوهای کلیدی (همان تستهای کامل در test_progparse239.py)
ns = {"re": re}
start = app_src.index("_WEB_PROG_PHASES = (")
end = app_src.index("C_BG = ")
exec(app_src[start:end], ns)
p = ns["_web_prog_parse"]
ph, cur, tot, unit = p("[*] استخراج متن: 5/27 صفحه\n[🔍] جارو\n")
chk("پارسر: استخراج 5/27", (ph, cur, tot, unit) == ("استخراج متن", 5, 27, "صفحه"))
ph, cur, tot, unit = p("[*] استخراج متن: 27/27 صفحه\n[✓] استخراجِ همهٔ 27 صفحه کامل شد — ...\n[*] ترجمه: 40/210 ناحیه\n")
chk("پارسر: ترجمه بعد از اتمامِ استخراج", (ph, cur, tot) == ("ترجمه", 40, 210))
ph, cur, tot, unit = p("[*] ترجمه: 40/210 ناحیه\n[*] صفحهٔ 7 آماده شد\n")
chk("پارسر: رندرِ نهایی (آماده شد)", (ph, cur, unit) == ("رندر و ذخیره", 8, "صفحهٔ"))
ph, cur, tot, unit = p("[+] متن استخراج شد: 6 ناحیه\n[*] صفحهٔ 3 آماده شد\n")
chk("پارسر: پس‌سازگاریِ لاگِ قدیمی", (ph, cur) == ("رندر و ذخیره", 4))

# ── ۵) کامپایل ───────────────────────────────────────────────────────
r = subprocess.run([sys.executable, "-m", "py_compile", ENG, APP],
                   capture_output=True, text=True)
chk("py_compile هر دو فایل", r.returncode == 0, r.stderr[-200:])

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} پاس")
if FAIL:
    print("ناموفق:", FAIL)
sys.exit(1 if FAIL else 0)
