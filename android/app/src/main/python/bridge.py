# -*- coding: utf-8 -*-

import contextlib
import json
import logging
import os
import re
import shutil
import threading
import time
import traceback

try:
    import manga
except Exception:
    manga = None
from extract_ui import extract

import manga_app


def _manga():
    global manga
    if manga is None:
        import importlib
        manga = importlib.import_module("manga")
    return manga

STATE = {"job": None, "lock": threading.Lock()}
_MF_CACHE = {"mf": None}


def _pil_webp_ok():
    try:
        from PIL import features
        return bool(features.check("webp"))
    except Exception:
        return False


def _webp_to_png_android(src):
    try:
        from android.graphics import BitmapFactory, Bitmap
        from java.io import FileOutputStream
        bm = BitmapFactory.decodeFile(src)
        if bm is None:
            return None
        dst = os.path.splitext(src)[0] + ".png"
        out = FileOutputStream(dst)
        ok = bm.compress(Bitmap.CompressFormat.PNG, 100, out)
        out.flush()
        out.close()
        bm.recycle()
        return dst if ok else None
    except Exception:
        return None


def _is_webp_file(path):
    try:
        with open(path, "rb") as f:
            head = f.read(12)
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    except Exception:
        return False


def install_webp_guards():
    if _pil_webp_ok():
        return
    try:
        from PIL import Image

        if not getattr(Image.Image.save, "_manga_webp_guard", False):
            _orig_save = Image.Image.save

            def _safe_save(self, fp, format=None, **params):
                try:
                    return _orig_save(self, fp, format=format, **params)
                except KeyError as e:
                    if str(e).strip("'\"").upper() != "WEBP":
                        raise
                    path = str(fp)
                    base, ext = os.path.splitext(path)
                    new_path = (base + ".jpg") if ext.lower() == ".webp" else path
                    print("[!] کدک WEBP در Pillow نیست → ذخیره به‌صورت JPG: %s" % new_path)
                    try:
                        q = int(params.get("quality", 90))
                    except Exception:
                        q = 90
                    q = max(40, min(q, 100))
                    return _orig_save(self, new_path, format="JPEG", quality=q, optimize=True)

            _safe_save._manga_webp_guard = True
            Image.Image.save = _safe_save

        if not getattr(Image.open, "_manga_webp_guard", False):
            _orig_open = Image.open

            def _safe_open(fp, *a, **kw):
                try:
                    return _orig_open(fp, *a, **kw)
                except Exception:
                    try:
                        path = str(getattr(fp, "name", fp))
                    except Exception:
                        path = ""
                    if path and os.path.isfile(path) and _is_webp_file(path):
                        png = _webp_to_png_android(path)
                        if png:
                            print("[!] ورودی WEBP با کدک اندروید به PNG تبدیل شد: %s" % png)
                            return _orig_open(png, *a, **kw)
                    raise

            _safe_open._manga_webp_guard = True
            Image.open = _safe_open
    except Exception:
        pass


def _resolve_img_format(p):
    fmt = str(p.get("img_format") or p.get("format") or "").strip().lstrip(".").lower()
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in ("webp", "jpg", "png"):
        fmt = "webp" if _pil_webp_ok() else "jpg"
    elif fmt == "webp" and not _pil_webp_ok():
        fmt = "jpg"
    return fmt


install_webp_guards()

_IMG_MAGICS = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
    (b"PK\x03\x04", ".zip"),
    (b"PK\x05\x06", ".zip"),
    (b"%PDF", ".pdf"),
)
_ACCEPTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".zip", ".pdf"}


def _fix_input_ext(path):

    try:
        if not path or "://" in path or not os.path.isfile(path):
            return path
        ext = os.path.splitext(path)[1].lower()
        if ext in _ACCEPTED_EXTS:
            if ext != ".webp" or _pil_webp_ok():
                return path
            png = _webp_to_png_android(path)
            return png if png else path
        with open(path, "rb") as f:
            head = f.read(16)
        fixed = ""
        for magic, e in _IMG_MAGICS:
            if head.startswith(magic):
                fixed = e
                break
        if not fixed and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            fixed = ".webp"
            if not _pil_webp_ok():
                png = _webp_to_png_android(path)
                if png:
                    return png
        if not fixed:
            try:
                from PIL import Image
                with Image.open(path) as im:
                    fmt = (im.format or "").lower()
                if fmt == "jpeg":
                    fmt = "jpg"
                if fmt in ("png", "jpg", "webp", "bmp", "gif"):
                    fixed = "." + fmt
            except Exception:
                return path
        if not fixed:
            return path
        base = os.path.basename(path).replace(":", "_")
        new_path = os.path.join(os.path.dirname(path), base + fixed)
        if os.path.abspath(new_path) == os.path.abspath(path):
            return path
        import shutil as _sh
        _sh.copyfile(path, new_path)
        return new_path
    except Exception:
        return path


def _bundles():
    try:
        b = list(manga_app.FONT_BUNDLES)
        if b:
            return b
    except Exception:
        pass
    return []


def _font_dir():
    try:
        return manga_app.FONT_DIR
    except Exception:
        return os.path.join(os.getcwd(), "fonts")


def _tone_ready(fname):
    p = os.path.join(_font_dir(), fname)
    try:
        return os.path.isfile(p) and os.path.getsize(p) > 20_000
    except Exception:
        return False


def _slot_fields(mf):

    slots = [b[0] for b in _bundles()]
    if not slots:
        return {}
    mapping = {}
    for sec in mf.get("sections", []):
        for f in sec.get("fields", []):
            fid = f.get("id") or ""
            for slot in slots:
                if fid.endswith("_" + slot):
                    m = mapping.setdefault(slot, {})
                    if f.get("type") == "file":
                        m["file"] = fid
                    elif f.get("type") == "bool":
                        m["en"] = fid
    return mapping


def _defaults(mf):
    # v1.14.146 — متنِ پرامپتِ خودکار (برایِ پیش‌فرضِ کادرِ پرامپتِ گوشی)
    # v1.14.147 — نقشهٔ value_if: با تغییرِ دروپ‌داونِ سبک، متنِ کادرِ پرامپت
    # زنده عوض میشود (فیکسِ «سبک را میگذارم lite ولی پرامپت عوض نمیشود»).
    _auto_prompt = ""
    _preset_map = {}
    try:
        _mg = _manga()
        _cfgp = str(manga_app.load_config().get("provider") or "gemini")
        _cfgm = str(manga_app.load_config().get("model") or "")
        _auto_prompt = str(_mg.prompt_preset_text("auto", _cfgp, _cfgm) or "")
        _preset_map = {
            "auto": _auto_prompt,
            "professional": str(_mg.PROMPT_PRESETS.get("professional") or ""),
            "lite": str(_mg.PROMPT_PRESETS.get("lite") or ""),
            "classic": str(_mg.PROMPT_PRESETS.get("classic") or ""),
        }
    except Exception:
        try:
            _mg = _manga()
            _auto_prompt = str(_mg.PROMPT_PRESETS["professional"] or "")
            _preset_map = {"auto": _auto_prompt}
        except Exception:
            _auto_prompt = ""
            _preset_map = {}
    for sec in mf.get("sections", []):
        for f in sec.get("fields", []):
            if not isinstance(f, dict):
                continue
            if f.get("id") == "instruction_text":
                # v1.14.146: دیگر متنِ کلاسیک پیشفرض نمینشیند — خالی = خودکار
                # (پُرکردنِ قبلی باعثِ «رویِ گوشی پرامپت auto نمیشود» بود)
                f["default"] = ""
            elif f.get("id") == "prompt_mode":
                cur = f.get("default")
                cur = cur.get("default") if isinstance(cur, dict) else cur
                if not (isinstance(cur, str) and cur.strip()
                        in ("auto", "professional", "lite", "classic")):
                    f["default"] = "auto"
            elif f.get("id") in ("prompt_preview_body", "prompt_body"):
                cur = f.get("default")
                cur = cur.get("default") if isinstance(cur, dict) else cur
                if not (isinstance(cur, str) and cur.strip()) and _auto_prompt:
                    f["default"] = _auto_prompt
                if _preset_map:
                    # v1.14.147 — MainActivity با تغییرِ prompt_mode متن را
                    # بر اساسِ این نقشه زنده عوض میکند
                    f["value_if"] = {"field": "prompt_mode", "values": _preset_map}
            elif f.get("id") == "readord":
                cur = f.get("default")
                if isinstance(cur, dict):
                    cur.setdefault("default", "rtl")
                elif cur not in ("rtl", "ltr"):
                    f["default"] = "rtl"
            elif f.get("id") == "clean_method":
                if f.get("default") not in ("lama-manga", "lama-big", "opencv"):
                    f["default"] = "lama-manga"


def _bundled_source(name):

    import importlib
    mod = importlib.import_module(name)
    loader = getattr(mod, "__loader__", None)
    if loader is None:
        raise RuntimeError("no loader for " + name)
    return loader.get_source(name)


def _android() -> bool:
    try:
        import java  # noqa: F401 — فقط روی Chaquopy موجود است
        return True
    except Exception:
        return False


def _drop_choice(choices, token):
    """حذف یک گزینه از لیست انتخاب — مقدار می‌شود c[0] نه برچسب c[1]."""
    bad = str(token or "").strip().lower()
    if not bad:
        return choices
    kept = []
    for c in choices or []:
        if isinstance(c, (list, tuple)) and len(c) > 1:
            val, lab = str(c[0]), str(c[1])
        else:
            val, lab = str(c), str(c)
        if bad in val.lower() or bad in lab.lower():
            continue
        kept.append(c)
    return kept


def manifest():

    files_dir = os.environ.get("MANGA_FILES_DIR") or os.getcwd()
    upd = os.path.join(files_dir, "updates", "manga_app.py")
    mf = None
    err = None
    for get_src in (
        lambda: (open(upd, encoding="utf-8").read(), "file")
        if os.path.isfile(upd) else (_ for _ in ()).throw(IOError(upd)),
        lambda: (_bundled_source("manga_app"), "loader"),
    ):
        try:
            src, _how = get_src()
            mf = extract(src, is_source=True)
            break
        except Exception as e:
            err = e
    if mf is None:
        try:
            mf = extract(manga_app.__file__)
        except Exception as e2:
            return json.dumps({"error": str(err or e2)}, ensure_ascii=False)
    try:
        provs = [str(x) for x in manga_app.PROVIDERS]
    except Exception:
        provs = ["gemini", "openai", "chatgpt", "deepseek", "groq"]
    for sec in mf.get("sections", []):
        for f in sec.get("fields", []):
            if f.get("choices_from") == "PROVIDERS" or f.get("id") == "provider":
                # v1.14.220 — «auto» اولِ منو (همان ترتیبِ وب: auto|gemini|
                # مدلهایِ کاربر|custom — مدلهایِ کاربر را MainActivity از
                # حافظهٔ دستگاه به گزینهها اضافه میکند)
                _pc = ["auto"] + [str(x) for x in provs
                                  if str(x).lower() not in ("auto",)]
                f["choices"] = [[p, p] for p in _pc]
                f.pop("choices_from", None)
            if f.get("id") in ("manga_api_base", "api_base"):
                f["visible_if"] = {"field": "provider", "equals": "custom"}
                f["label"] = "دامنهٔ API سفارشی (فقط برای custom — مثال: https://api.example.com/v1)"
            # --- گوشی: گزینهٔ PSD از قالب خروجی حذف می‌شود (درخواست کاربر) ---
            if f.get("id") in ("out_fmt", "manga_out_fmt", "fmt") and _android():
                f["choices"] = _drop_choice(f.get("choices") or [], "psd")
            # --- گوشی: lama-big قابل اجرا نیست → فقط دو حالت دیگر می‌آید ---
            if f.get("id") == "clean_method" and _android():
                f["choices"] = _drop_choice(f.get("choices") or [], "lama-big")
                if f.get("default") == "lama-big":
                    f["default"] = "lama-manga"
        # --- ترتیبِ خواستهٔ کاربر: ارائه‌دهنده → لینک(custom) → کلید → مدل ---
        # (دکمهٔ «تست کلید» در MainActivity بعد از «مدل» رندر می‌شود)
        _forder = {"provider": 0, "manga_provider": 0,
                   "manga_api_base": 1, "api_base": 1,
                   "manga_api_keys": 2, "api_keys": 2,
                   "manga_model": 3, "model": 3}
        _fs = sec.get("fields") or []
        if any(f.get("id") in _forder for f in _fs):
            sec["fields"] = sorted(_fs,
                                   key=lambda f: _forder.get(f.get("id"), 10))
    try:
        _defaults(mf)
    except Exception:
        traceback.print_exc()
    _MF_CACHE["mf"] = mf
    return json.dumps(mf, ensure_ascii=False)


def _cfg(key, dflt=None):
    try:
        return manga_app.load_config().get(key, dflt)
    except Exception:
        return dflt


def _resolve_main_font(job):
    custom = job["params"].get("font_upload_file") or job["params"].get("font_file")
    if custom and os.path.isfile(custom):
        _log(job, "فونت اصلی (آپلودی): %s" % os.path.basename(custom))
        return custom
    fp = ""
    try:
        fp = manga_app.find_font() or ""
    except Exception:
        pass
    if fp:
        return fp
    _log(job, "فونت روی دستگاه نیست — دانلود…")
    try:
        manga_app.download_fonts(log=lambda m: _log(job, str(m)))
    except Exception as e:
        _log(job, "[!] دانلود فونت ناموفق: %s" % e)
    try:
        fp = manga_app.find_font() or ""
    except Exception:
        fp = ""
    return fp


def _resolve_tones(job, mf):

    slot_map = _slot_fields(mf)
    p = job["params"]
    font_by_style, active = {}, []
    for slot, fname, _desc, _u in _bundles():
        ids = slot_map.get(slot, {})
        en_fid = ids.get("en")
        on = True if en_fid is None else bool(p.get(en_fid, True))
        file_fid = ids.get("file")
        custom = p.get(file_fid + "_file") if file_fid else None
        path = custom if (custom and os.path.isfile(custom)) \
            else os.path.join(_font_dir(), fname)
        lbl = slot
        if not on:
            _log(job, "لحن خاموش: %s" % lbl)
            continue
        if path and os.path.isfile(path) and os.path.getsize(path) > 20_000:
            font_by_style[slot] = path
            active.append(slot)
        else:
            _log(job, "[!] فونت لحن «%s» پیدا نشد — با فونت اصلی رندر می‌شود" % lbl)
    return font_by_style, active


def _clean_method_of(p):
    cm = str(p.get("clean_method") or "").strip().lower()
    if cm in ("lama-manga", "lama-big", "opencv"):
        if cm == "lama-big" and _android():
            return "lama-manga"
        return cm
    if "use_lama" in p:
        return "lama-manga" if bool(p.get("use_lama")) else "opencv"
    if bool(p.get("force_cpu")):
        return "opencv"
    return "lama-manga"


def _out_stem_from_src(src: str) -> str:
    s = str(src or "").strip()
    if not s:
        return ""
    try:
        if s.lower().startswith(("http://", "https://")):
            from urllib.parse import urlparse, unquote
            name = os.path.basename(unquote(urlparse(s).path))
        else:
            name = os.path.basename(s.replace("\\", "/"))
        stem = os.path.splitext(name)[0].strip()
    except Exception:
        stem = ""
    stem = re.sub(r'[\\/:*?"<>|]+', "_", stem).strip(" ._")
    return stem[:80]


def _prompt_params(p):
    """(prompt_mode, instruction) از پارامترهایِ جابِ گوشی — v1.14.146.
    prompt_mode: گزینهٔ دروپ‌داونِ سبکِ پرامپت در گوشی.
    instruction: متنِ کادرِ پرامپتِ گوشی — اگر برابرِ پیشفرضهایِ شناختهشده
    باشد سفارشی حساب نمیشود (خودِ MangaTranslator هم نرمالایز میکند)."""
    _pm = str(p.get("prompt_mode") or "").strip().lower()
    if _pm not in ("auto", "professional", "lite", "classic"):
        _pm = "auto"
    _body = ""
    for _k in ("prompt_body", "prompt_preview_body", "instruction", "instruction_text"):
        _v = str(p.get(_k) or "").strip()
        if _v and not _body:
            _body = _v
    try:
        _mg = _manga()
        if _body and _mg.is_known_default_instruction(_body):
            _body = ""
    except Exception:
        pass
    return _pm, (_body or None)



def _resolve_auto_or_named(p, keys, log):
    """v1.14.220 — resolveِ «auto» و «مدلِ نامیِ کاربر» قبل از ساختِ
    MangaTranslator (مثلِ وب؛ manga.py دستنخورده میماند).
    ورودی: p (پارامترهایِ job — شاملِ custom_models از MainActivity)،
    keys (لیستِ کلیدها)، log (تابعِ لاگِ زنده).
    خروجی: keysِ (احتمالاً) بهروزشده؛ p هم درجا بهروز میشود (provider/
    api_base/keys/model همیشه providerِ واقعیِ gemini/custom میشوند)."""
    try:
        _cm = p.get("custom_models")
        if isinstance(_cm, str):
            _cm = json.loads(_cm) if _cm.strip().startswith("[") else []
        _cm = [m for m in (_cm or [])
               if isinstance(m, dict) and str(m.get("name") or "").strip()]
        _prov0 = str(p.get("provider") or "").strip()
        _keys0 = str(p.get("keys") or "")
        _mdl0 = str(p.get("model") or "")
        if _prov0 and _prov0 not in ("auto", "gemini", "custom"):
            # مدلِ نامیِ کاربر — اگر در لیست نبود/لیست خالی بود → gemini
            # (providerِ «ناموجود» هرگز به موتور نمیرود)
            _named = getattr(manga_app, "resolve_ai_named", None)
            _r = _named(_cm, _prov0, _keys0, _mdl0) if (_named and _cm) else None
            if _r:
                _np, _nb, _nk, _nm = _r
                p["provider"] = _np
                if _nb:
                    p["api_base"] = _nb
                if _nk:
                    p["keys"] = _nk
                if _nm:
                    p["model"] = _nm
                keys = [k.strip() for k in str(p.get("keys") or "").split(",") if k.strip()]
                log("🤖 مدلِ «%s» → provider=%s%s"
                    % (_prov0, _np, (" — %s" % _nb) if _nb else ""))
            else:
                log("[!] مدلِ «%s» در لیستِ مدلها نبود → gemini" % _prov0)
                p["provider"] = "gemini"
        elif _prov0 == "auto":
            _auto = getattr(manga_app, "resolve_ai_auto", None)
            if _auto:
                _r = _auto(_cm, _keys0, _mdl0,
                           probe=getattr(_manga(), "test_api_keys", None))
                _np, _nb, _nk, _nm, _lines = _r
                for _ln in (_lines or []):
                    log(_ln)
                if _np:
                    p["provider"] = _np
                    if _nb:
                        p["api_base"] = _nb
                    if _nk:
                        p["keys"] = _nk
                    if _nm:
                        p["model"] = _nm
                    keys = [k.strip() for k in str(p.get("keys") or "").split(",") if k.strip()]
                else:
                    log("[!] auto مدلِ در دسترسی پیدا نکرد → gemini")
                    p["provider"] = "gemini"
            else:
                log("[!] resolveِ auto در دسترس نیست → gemini")
                p["provider"] = "gemini"
    except Exception as _re:
        log("[!] resolveِ AI ناموفق: %s" % str(_re)[:120])
        if str(p.get("provider") or "") == "auto":
            p["provider"] = "gemini"
    return keys


def start_job(params_json, files_dir):
    with STATE["lock"]:
        if STATE["job"] and not STATE["job"].get("done"):
            return json.dumps({"error": "یک کار در حال اجراست"}, ensure_ascii=False)
        p = json.loads(params_json)
        work = os.path.join(files_dir, "work")
        os.makedirs(work, exist_ok=True)
        out = os.path.join(work, "out")
        fmt = str(p.get("fmt", "PDF")).upper()
        # --- گوشی: PSD پشتیبانی نمی‌شود (حذف شد) → PDF ---
        if fmt == "PSD" and _android():
            fmt = "PDF"
            p["fmt"] = "PDF"
        ext = "pdf" if fmt == "PDF" else fmt.lower()
        _stem = _out_stem_from_src(p.get("src") or p.get("url") or "")
        out_file = os.path.join(out, (_stem or "manga") + "." + ext)
        job = {
            "done": False, "log": "آماده‌سازی…", "error": None,
            "out_file": None, "images": [], "debug_images": [],
            "params": p, "out": out, "out_file_path": out_file,
            "cancel_requested": False, "cancelled": False,
            "files_dir": files_dir,
        }
        STATE["job"] = job
    try:
        _manga().clear_stop()
    except Exception:
        pass
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return json.dumps({"ok": True}, ensure_ascii=False)


# v1.14.153 — ترتیبِ نشانهها مهم است (اولین تطبیق برنده میشود).
# («آماده شد» حذف شد — خطِ «صفحهٔ N آماده شد» را میدزدید و اعلان
# را رویِ «رندر و ذخیره» قفل میکرد؛ شمارهٔ صفحه از regexِ پایین
# میآید. «لود نشد» = خطایِ بارگذاریِ موتور (v1.14.183 — فالبکی
# نیست؛ کاربر در اعلان خطا را میبیند).
_PROG_PHASES_1151 = (
    ("بارگذاری موتور", "بارگذاری مدلها"),
    ("لود نشد", "خطا"),
    # v1.14.154 — نشانگرهایِ شروعِ فازِ هر صفحه (پرینتهایِ جدیدِ manga.py)
    # + حالتهایِ پایانی. ترتیب مهم است (اولین تطبیق برنده): خطهایِ
    # «[OCR] … خطا: …» اول گاردِ استخراج را میگیرند نه «خطا» را.
    ("استخراج متن", "استخراج متن"),
    ("متن استخراج شد", "استخراج متن"),
    ("(PaddleOCR)", "استخراج متن"),
    ("OCR]", "استخراج متن"),
    ("ترجمه:", "ترجمه"),
    ("فاز ۳", "ترجمه"),
    ("ترجمه با", "ترجمه"),
    ("پاکسازی متن", "پاکسازی"),
    ("روش پاکسازی", "پاکسازی"),
    ("پاکسازی:", "پاکسازی"),
    ("[✓] تمام شد", "تمام شد"),
    ("لغو شد", "لغو شد"),
    ("خطا:", "خطا"),
    ("آماده شد", "رندر و ذخیره"),
    ("OCR:", "استخراج متن"),
    ("پدلِ رسمیِ اندروید", "استخراج متن"),
    ("پدلِ اندروید", "استخراج متن"),
)


def _update_prog_1151(job, msg):
    """v1.14.151 — فازِ فعلی و شمارهٔ صفحه برای اعلانِ پیشزمینه."""
    try:
        m = re.search(r"(\d{1,4})\s+آماده شد", msg)
        ph = None
        for _k, _v in _PROG_PHASES_1151:
            if _k in msg:
                ph = _v
                break
        if m or ph:
            with STATE["lock"]:
                if m:
                    job["prog_page"] = int(m.group(1))
                if ph:
                    job["prog_phase"] = ph
    except Exception:
        pass


def _heal_models_dirs(job):
    """v1.14.154 — پیشدرمانِ EACCES (system error 13): رویِ بعضیِ گوشیها
    فایلهایِ مدل بعد از بهروزرسانیِ اپ مجوزِ خواندن ندارند → ONNX
    Runtime میشکند و استخراجِ همان کراپ خالی میماند. اینجا قبل از
    بارگذاریِ موتور، مجوزِ همهٔ فایلهایِ پوشههایِ مدل اصلاح میشود
    (chmodِ 0o644). فقط اندروید؛ خروجی/کارِ قبلی دستنخورده."""
    if not _android():
        return
    fd = str((job or {}).get("files_dir") or "").strip()
    if not fd or not os.path.isdir(fd):
        return
    _skip = {"work", "cache", "updates", "tmp"}
    _targets = ("rapidocr_models", "models")
    _n = 0
    try:
        for _root, _dirs, _files in os.walk(fd):
            _dirs[:] = [d for d in _dirs if d not in _skip]
            if os.path.basename(_root) not in _targets:
                continue
            for _fn in _files:
                _fp = os.path.join(_root, _fn)
                try:
                    _st = os.stat(_fp)
                    if (_st.st_mode & 0o444) != 0o444:
                        os.chmod(_fp, 0o644)
                        _n += 1
                except Exception:
                    pass
    except Exception:
        pass
    if _n:
        _log(job, "[*] مجوزِ خواندنِ %d فایلِ مدل اصلاح شد (درمانِ EACCES)" % _n)


def _log(job, msg):
    _update_prog_1151(job, str(msg))
    with STATE["lock"]:
        txt = str(job.get("log") or "")
        job["log"] = (txt + "\n" + str(msg))[-12000:]
    _FULLLOG.write(str(msg) + "\n")  # v1.14.16: لاگ کامل


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class _FullLog:
    """v1.14.16: لاگ کاملِ بدون برش → <files_dir>/manga.log
    لاگِ باکسِ UI هر خط را تا ۳۰۰ نویسه و کل را تا ۱۲هزار نویسه برش می‌زند؛
    این فایل همه‌چیز را خام نگه می‌دارد تا کاربر بتواند متن کامل را بفرستد."""

    def __init__(self):
        self._lock = threading.Lock()
        self._fh = None
        self.path = None

    def open(self, files_dir):
        with self._lock:
            self._close()
            self.path = None
            try:
                d = str(files_dir or "").strip()
                if not d:
                    return
                os.makedirs(d, exist_ok=True)
                p = os.path.join(d, "manga.log")
                old_p = os.path.join(d, "manga_old.log")
                # لاگ اجرای قبلی → manga_old.log (دو فایل، همان‌طور که کاربر خواست)
                if os.path.isfile(p):
                    try:
                        if os.path.getsize(p) <= 8 * 1024 * 1024:
                            try:
                                os.remove(old_p)
                            except Exception:
                                pass
                            os.replace(p, old_p)
                        else:
                            os.remove(p)
                    except Exception:
                        pass
                with open(p, "w", encoding="utf-8") as f:
                    f.write(_fulllog_header())
                self._fh = open(p, "a", encoding="utf-8")
                self.path = p
            except Exception:
                self._fh = None
                self.path = None

    def write(self, s):
        if not s:
            return
        with self._lock:
            if not self._fh:
                return
            try:
                self._fh.write(str(s).replace("\r", "\n"))
                self._fh.flush()
            except Exception:
                try:
                    self._fh.close()
                except Exception:
                    pass
                self._fh = None

    def _close(self):
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None

    def close(self):
        with self._lock:
            self._close()


_FULLLOG = _FullLog()


def _fulllog_header():
    try:
        _ver = getattr(manga, "APP_VER", "?") if manga is not None else "?"
    except Exception:
        _ver = "?"
    _cpu = "?"
    try:
        _cpu = str(os.cpu_count() or "?")
    except Exception:
        pass
    _arch = ""
    try:
        _arch = os.uname().machine
    except Exception:
        pass
    return ("=== Manga Translator v%s | %s | cpu=%s %s ===\n"
            % (_ver, time.strftime("%Y-%m-%d %H:%M:%S"), _cpu, _arch))


def _fulllog_params(job):
    try:
        p = job.get("params") or {}
        keys = ("provider", "model", "api_base", "fmt", "debug", "fake",
                "two_pass", "tones", "font", "ocr", "langs", "readord",
                "clean_method", "story_brief")
        kvs = []
        for k in keys:
            v = p.get(k)
            if v not in (None, "", [], {}):
                s = str(v)
                if len(s) > 60:
                    s = s[:57] + "..."
                kvs.append("%s=%s" % (k, s))
        return "params: " + (", ".join(kvs) if kvs else "-")
    except Exception:
        return "params: ?"


class _TeeStream:


    def __init__(self, job):
        self._job = job
        self._lock = threading.Lock()
        self._parts = []
        self._len = 0
        self._tail = []

    def write(self, s):
        if not s:
            return 0
        with self._lock:
            self._tail.append(s)
            if len(self._tail) > 800:
                del self._tail[:-400]
            self._parts.append(s)
            self._len += len(s)
            big = self._len >= 256
        if big or "\n" in s or "\r" in s:
            self.flush()
        return len(s)

    def flush(self):
        with self._lock:
            chunk = "".join(self._parts)
            self._parts = []
            self._len = 0
        if not chunk:
            return
        _FULLLOG.write(chunk)  # v1.14.16: خام و بدون برش به فایل
        pieces = chunk.replace("\r", "\n").split("\n")
        for ln in pieces[:-1]:
            self._emit(ln)
        if pieces[-1]:
            with self._lock:
                self._parts.append(pieces[-1])
                self._len = len(pieces[-1])

    def _emit(self, ln):
        ln = _ANSI.sub("", ln).rstrip()
        if not ln:
            return
        if len(ln) > 300:
            ln = "…" + ln[-300:]
        # v1.14.153 — ریشهٔ «اعلان گیرِ درحال بارگیری، عوض نمیشه»:
        # ماشینِ فاز فقط خطهایِ _log را میدید؛ ولی تقریباً همهٔ پیامهایِ
        # پایپلاین (صفحهٔ N آماده شد / OCR: / فاز ۳) با print() از
        # _TeeStream میآیند → فاز هیچوقت عوض نمیشد. حالا هر خطِ
        # stdout هم فاز/شمارهٔ صفحه را بهروز میکند.
        _update_prog_1151(self._job, ln)
        with STATE["lock"]:
            txt = str(self._job.get("log") or "")
            lines = txt.split("\n") if txt else []
            prev = lines[-1] if lines else ""
            if "%|" in ln and "%|" in prev:
                lines[-1] = ln
            else:
                lines.append(ln)
            self._job["log"] = ("\n".join(lines))[-12000:]

    def getvalue(self):
        self.flush()
        with self._lock:
            return "".join(self._tail)


def _heartbeat(job):

    t0 = time.time()
    last = -1
    while True:
        time.sleep(30)
        with STATE["lock"]:
            if job.get("done"):
                return
            cur = len(str(job.get("log") or ""))
        if cur == last:
            _log(job, "در حال کار… %d ثانیه — صفحه‌های سنگین/دانلود مدل طول می‌کشد" % int(time.time() - t0))
        last = cur


def _attach_log_handlers(tee):

    class _H(logging.Handler):
        def emit(self, record):
            try:
                tee.write(self.format(record) + "\n")
            except Exception:
                pass

    h = _H(level=logging.INFO)
    h.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    targets = [logging.getLogger()]
    rapid = logging.getLogger("RapidOCR")
    if rapid not in targets:
        targets.append(rapid)
    attached = []
    for lg in targets:
        try:

            if lg.getEffectiveLevel() > logging.INFO:
                lg.setLevel(logging.INFO)
            lg.addHandler(h)
            attached.append(lg)
        except Exception:
            pass
    return (h, attached)


def _detach_log_handlers(attached):
    try:
        h, lgs = attached
        for lg in lgs:
            lg.removeHandler(h)
    except Exception:
        pass


def _run(job):
    p = job["params"]
    job["_t0"] = time.time()
    _FULLLOG.open(job.get("files_dir"))  # v1.14.16: لاگ کامل
    _FULLLOG.write(_fulllog_params(job) + "\n")
    try:
        os.makedirs(job["out"], exist_ok=True)
        for old in os.listdir(job["out"]):
            try:
                _p = os.path.join(job["out"], old)
                if os.path.isdir(_p):
                    shutil.rmtree(_p, ignore_errors=True)
                else:
                    os.remove(_p)
            except Exception:
                pass
        job["live"] = os.path.join(job["out"], "live")
        shutil.rmtree(job["live"], ignore_errors=True)
        os.environ["MANGA_LIVE_DIR"] = job["live"]
        job["live_dbg"] = os.path.join(job["out"], "live_debug")
        shutil.rmtree(job["live_dbg"], ignore_errors=True)
        os.environ["MANGA_LIVE_DEBUG_DIR"] = job["live_dbg"]
        langs = [x for x in str(p.get("ocr_lang") or "en").split() if x.strip()]
        # v1.14.163 — سبکِ «استخراج و پاکسازی»ٔ گوشی حذف شد؛ موتورِ استخراج
        # فقط یکی است (همان سبکِ PC): detector-v4-s مکانِ متن را پیدا
        # میکند و OCR فقط رویِ همان کراپها اجرا میشود.
        # v1.14.170→184 — موتورِ OCRِ گوشی = SDKِ رسمیِ PaddleOCR
        # اندروید (ppocr-sdkِ وندورشده با PP-OCRv6_smallِ باندل).
        # v1.14.184 — «هرروشی تو گوشی واسه استخراج شده حذف کن فقط از
        # همین لینک بالا استفاده کنه» → هر انتخابِ کهنه
        # (mlkit/rapidocr/onnx/paddle/…) نادیده گرفته میشود.
        try:
            _oe = str(p.get("ocr_engine") or "").strip().lower()
            if _oe:
                _log(job, "[!] انتخابِ موتورِ «%s» دیگر پشتیبانی نمیشود "
                          "(v1.14.184) — SDKِ رسمیِ PaddleOCR اندروید "
                          "(PP-OCRv6_smallِ باندل) بهکار میرود" % _oe)
        except Exception:
            pass
        _src0 = str(p.get("src") or "")
        # --- چند فایل انتخاب‌شده (اندروید: با کاما جدا شده) → پوشهٔ دسته‌ای ---
        if ("," in _src0 and "://" not in _src0
                and not _src0.lower().startswith(("http://", "https://"))):
            _parts = [s.strip() for s in _src0.split(",") if s.strip()]
            if len(_parts) > 1 and all(os.path.isfile(s) for s in _parts):
                try:
                    _batch_dir = os.path.join(
                        os.path.dirname(os.path.abspath(_parts[0])), "batch_input")
                    os.makedirs(_batch_dir, exist_ok=True)
                    for _bi, _bp in enumerate(_parts, 1):
                        _extb = os.path.splitext(_bp)[1].lower() or ".bin"
                        _dstb = os.path.join(_batch_dir, "file_%03d%s" % (_bi, _extb))
                        with open(_bp, "rb") as _fa, open(_dstb, "wb") as _fb:
                            shutil.copyfileobj(_fa, _fb, 1024 * 512)
                    _src0 = _batch_dir
                    _log(job, "%d فایل ورودی در پوشهٔ دسته‌ای آماده شد" % len(_parts))
                except Exception as _be:
                    _log(job, "[!] ساخت پوشهٔ دسته‌ای ناموفق (%s) — فقط اولین فایل" % _be)
                    _src0 = _parts[0]
        _src1 = _fix_input_ext(_src0)
        if _src1 != _src0:
            p["src"] = _src1
            _log(job, "پسوند ورودی اصلاح شد → %s" % os.path.basename(_src1))
        # v1.14.181 — دکمهٔ «تستِ سرعت» (v1.14.178) کامل حذف شد؛ روشِ
        # استخراج = فقط SDKِ رسمیِ PaddleOCR — speed_lab_env پایینتر
        # اعمالش میکند.
        keys = [k.strip() for k in str(p.get("keys") or "").split(",") if k.strip()]
        # ── v1.14.220 — resolveِ «auto» و «مدلِ نامیِ کاربر» (مثلِ وب) ──
        # لیستِ مدلهایِ سفارشی از MainActivity (custom_models) میآید؛
        # سنجشِ دسترسی = همان probeِ موتور (manga.test_api_keys)؛
        # manga.py هیچ تغییری نمیکند — خروجیِ resolve همیشه providerِ
        # واقعیِ gemini/custom است.
        keys = _resolve_auto_or_named(p, keys, lambda m: _log(job, str(m)))
        if not keys and not (bool(p.get("fake")) or bool(p.get("clean_only"))):
            _log(job, "[!] حداقل یک کلید API لازم است — کلید بده یا "
                      "«حالت تست» / «حالت پاکسازی» را در تنظیمات پیشرفته فعال کن.")
            with STATE["lock"]:
                job["done"] = True
                job["error"] = True
            return
        glossary_path = None
        if p.get("glossary"):
            glossary_path = os.path.join(job["out"], "glossary.txt")
            with open(glossary_path, "w", encoding="utf-8") as f:
                f.write(str(p["glossary"]))

        fp = _resolve_main_font(job)
        if not fp:
            _log(job, "[!] فونت اصلی پیدا نشد — اینترنت را چک کن یا فونت .ttf آپلود کن.")
            with STATE["lock"]:
                job["done"] = True
                job["error"] = True
            return

        def _f(key, dflt):
            try:
                return float(p.get(key) or dflt)
            except Exception:
                return dflt

        def _i(key, dflt):
            try:
                return int(float(p.get(key) or dflt))
            except Exception:
                return dflt

        tee = _TeeStream(job)
        hb = threading.Thread(target=_heartbeat, args=(job,), daemon=True)
        hb.start()
        handlers = _attach_log_handlers(tee)
        # v1.14.176 — «آزمایشگاهِ سرعتِ استخراج»: تنظیمهایِ پنلِ اپ →
        # envهایِ OCRِ گوشی (پیشفرض = رفتارِ قبل) + ریستِ سنجههایِ سرعت
        try:
            _sl = getattr(_manga(), "speed_lab_env", None)
            if _sl:
                _sl_line = _sl(p)
                if _sl_line:
                    _log(job, _sl_line)
        except Exception:
            pass

        def _def_workers():
            try:
                return max(2, min(4, os.cpu_count() or 2))
            except Exception:
                return 2

        try:
            with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
                _heal_models_dirs(job)  # v1.14.154 — پیشدرمانِ EACCES
                _log(job, "در حال بارگذاری موتور و مدل‌ها…"
                          " (بار اول مدل‌ها دانلود می‌شوند)")
                mf = _MF_CACHE["mf"]
                if mf is None:
                    try:
                        mf = json.loads(manifest())
                    except Exception:
                        mf = {}
                font_by_style, active = _resolve_tones(job, mf)
                _pmode, _instr = _prompt_params(p)
                tr = _manga().MangaTranslator(
                    api_key=keys or ["placeholder"],
                    provider=str(p.get("provider") or "gemini"),
                    model_name=(str(p.get("model")) or None) if p.get("model") else None,
                    api_base=(str(p.get("api_base") or "").strip()
                              or _cfg("api_base") or None) or None,
                    ocr_langs=langs,
                    font_path=fp,
                    reading_order=str(p.get("readord") or "rtl"),
                    gpu=False if (p.get("force_cpu") and not p.get("clean_method")) else None,
                    clean_method=_clean_method_of(p),
                    two_pass_ocr=bool(p.get("two_pass", True)),
                    debug=bool(p.get("debug")),
                    glossary_path=glossary_path,
                    story_brief=bool(p.get("story_brief", True)),
                    fake_translate=bool(p.get("fake")),
                    clean_only=bool(p.get("clean_only")),
                    max_workers=_i("workers", _def_workers()),
                    bubbles_per_request=_i("bubbles", 6),
                    api_timeout=_f("timeout", 40.0),
                    max_retries=_i("maxre", 8),
                    request_delay=_f("reqdelay", 0.0),
                    translation_temperature=_f("temp", 0.85),
                    img_quality=_i("quality", 92),
                    img_format=_resolve_img_format(p),
                    style_fonts=bool(active),
                    active_tones=active or None,
                    instruction_text=_instr,
                    prompt_mode=_pmode,
                )

                if (getattr(manga, "_on_android", lambda: False)()
                        and getattr(tr, "det", None) is not None):
                    tr.stitch_max_height = 4000
                    # v1.14.106 — اندروید صراحتاً برش می‌خواهد (رمِ کم)؛
                    # حالتِ صفحاتِ مستقل روی گوشی رد می‌شود (رفتارِ قبلی)
                    tr.stitch_explicit = True
                tr.batch_workers = _i("batchw", 3)

                _cm_log = str(getattr(tr, "clean_method", "") or "")
                if _cm_log == "opencv":
                    _log(job, "پاک‌سازی: opencv")
                elif _cm_log == "lama-big":
                    _log(job, "پاک‌سازی: big-lama — بار اول مدل ~۲۰۰MB دانلود می‌شود")
                else:
                    _log(job, "پاک‌سازی: lama.onnx")
                if font_by_style:
                    tr.font_by_style = font_by_style
                    tr.style_fonts = True
                tr.run(str(p.get("src")), job["out_file_path"], resume=False)
        finally:
            _detach_log_handlers(handlers)
            # v1.14.215 — خطا/لغو وسطِ کار: صفحه‌هایِ در انتظارِ گیتِ ترتیبِ
            # نمایشِ زنده به‌ترتیب آزاد شوند تا نمایش ناقص نماند.
            try:
                _manga()._live_seq_flush()
            except Exception:
                pass
            os.environ.pop("MANGA_LIVE_DIR", None)
            # v1.14.176 — گزارشِ سرعتِ «این اجرا» (آزمایشگاهِ سرعت): میانگینِ
            # کراپ + سهمِ پلهها → سازنده بینِ حالتهایِ پنل مقایسه میکند
            try:
                _rep = getattr(_manga(), "_k3_speed_report", None)
                if _rep:
                    _rep_line = _rep()
                    if _rep_line:
                        _log(job, _rep_line)
            except Exception:
                pass

        _ORIG_DIRS = ("src", "normalized", "stitched")
        imgs, dbg = [], []
        cache = job["out_file_path"] + ".cache"
        for root, _d, files in os.walk(cache):
            dname = os.path.basename(os.path.normpath(root)).lower()
            if any("/" + o + "/" in root.lower().replace(os.sep, "/") + "/"
                   for o in _ORIG_DIRS):
                continue
            is_dbg = dname.startswith("debug")
            is_out = dname == "out" or dname.startswith("out_")
            if not is_out and not is_dbg:
                continue
            for f in sorted(files):
                if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    continue
                lp = os.path.join(root, f)
                if is_dbg or "debug" in f.lower():
                    dbg.append(lp)
                else:
                    imgs.append(lp)
        import re as _re

        def _natkey(s):
            return [int(t) if t.isdigit() else t for t in _re.split(r"(\d+)", s)]

        imgs.sort(key=_natkey)
        dbg.sort(key=_natkey)
        if not imgs:

            for root, dirs_, files in os.walk(job["out"]):
                rel = root.lower().replace(os.sep, "/")
                segs = [s for s in rel.split("/") if s]
                dname = os.path.basename(os.path.normpath(root)).lower()
                in_cache = any(s.endswith(".cache") for s in segs)
                if in_cache and not (
                        dname == "out" or dname.startswith("out_")
                        or dname.startswith("debug")):
                    dirs_[:] = []
                    continue
                if any("/" + o + "/" in rel + "/" for o in _ORIG_DIRS):
                    dirs_[:] = []
                    continue
                for f in sorted(files):
                    lp = os.path.join(root, f)
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        (dbg if "debug" in f.lower() else imgs).append(lp)
        if not imgs:
            imgs = _live_pages(job)
        dl = job["out_file_path"] if os.path.isfile(job["out_file_path"]) else None
        # 🔍 v1.14.13: دیباگ = «یک خروجی یکپارچه» مثل خروجی اصلی — نه تصاویر
        # جدا جدا. اگر موتور خودش *_debug.pdf ساخته (خروجی PDF/HTML/ZIP) همون
        # استفاده می‌شود؛ وگرنه از تصاویر دیباگ یک PDF واحد ساخته می‌شود.
        dbg_out = None
        try:
            _root, _ext = os.path.splitext(job["out_file_path"])
            _cand = _root + "_debug" + _ext
            if os.path.isfile(_cand):
                dbg_out = _cand
            elif dbg:
                _cand2 = _root + "_debug.pdf"
                try:
                    _tr = tr  # noqa: F821 — موتور اگر ساخته شده باشد در اسکوپ است
                    _tr._save_as_pdf(dbg, _cand2)
                except Exception:
                    pass
                if os.path.isfile(_cand2):
                    dbg_out = _cand2
        except Exception:
            dbg_out = None
        with STATE["lock"]:
            job["images"] = imgs
            job["debug_images"] = dbg
            job["out_file"] = dl
            job["debug_out_file"] = dbg_out
            job["done"] = True
        _log(job, "[✓] تمام شد — %d صفحه، خروجی: %s" % (len(imgs), dl or "-"))
        if dbg_out:
            _log(job, "خروجی دیباگ: %s" % os.path.basename(dbg_out))
        elif bool(p.get("debug")) and dbg:
            _log(job, "%d تصویر دیباگ ساخته شد — فایل یکپارچه‌ای ساخته نشد." % len(dbg))
        if bool(p.get("debug")) and not dbg:
            _log(job, "دیباگ روشن بود ولی تصویر دیباگی ساخته نشد — "
                      "تصویر دیباگ فقط برای صفحه‌هایی که متن/حباب دارند تولید می‌شود.")
    except _manga().JobCancelled:
        _log(job, "[!] ترجمه لغو شد")
        with STATE["lock"]:
            job["done"] = True
            job["cancelled"] = True
            job["error"] = False
    except BaseException:
        try:
            _txt = tee.getvalue()
            if _txt.strip():
                _log(job, "…" + _txt[-4000:])
        except Exception:
            pass
        _log(job, "خطا:\n" + traceback.format_exc()[-2500:])
        with STATE["lock"]:
            job["done"] = True
            job["error"] = True
    finally:
        # v1.14.16: جمع‌بندی و بستن لاگ کامل در همهٔ مسیرها (موفق/لغو/خطا)
        _FULLLOG.write(
            "=== END — done=%s cancelled=%s error=%s — %.1fs ===\n"
            % (bool(job.get("done")), bool(job.get("cancelled")),
               bool(job.get("error")), time.time() - job.get("_t0", time.time())))
        _FULLLOG.close()


def _live_pages(job, dbg: bool = False):
    """صفحه‌های تمام‌شدهٔ لحظه‌ای از پوشهٔ live — برای نمایش زنده بدون رفرش.
    dbg=True → پوشهٔ live_debug (صفحه‌های دیباگ زنده)."""
    d = job.get("live_dbg" if dbg else "live")
    if not d or not os.path.isdir(d):
        return []
    try:
        import re as _re
        files = [os.path.join(d, f) for f in os.listdir(d)
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        files.sort(key=lambda s: [int(t) if t.isdigit() else t
                                  for t in _re.split(r"(\d+)", s)])
        return files
    except Exception:
        return []


def _live_total(job, dbg: bool = False) -> int:
    """تعداد کل صفحه‌ها از total.txt (موتور همان اول تعداد کل را می‌نویسد)
    — تا نمایشگر زنده از اول اسلات لودینگ برای همه بگذارد (v1.14.29)."""
    d = job.get("live_dbg" if dbg else "live")
    if not d:
        return 0
    try:
        with open(os.path.join(d, "total.txt"), encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0


def poll():
    with STATE["lock"]:
        job = STATE["job"]
        if not job:
            return json.dumps({"idle": True}, ensure_ascii=False)
        # v1.14.154 — «کدوم قسمته، کدوم عکسه، چند درصده»: صفحهٔ جاری
        # (در حال کار = آمادهشده + ۱) و درصد، اینجا حساب میشود تا
        # اعلان فقط نمایش بدهد.
        _pt = _live_total(job)
        _pp = int(job.get("prog_page") or 0)
        if _pt > 0:
            _pn = _pp if job.get("done") else min(_pp + 1, _pt)
            _ppct = int(_pn * 100 / _pt)
        else:
            _pn, _ppct = _pp, 0
        return json.dumps({
            "idle": False,
            "done": bool(job.get("done")),
            "error": bool(job.get("error")),
            "cancelled": bool(job.get("cancelled")),
            "cancel_requested": bool(job.get("cancel_requested")),
            "log": job.get("log", ""),
            "images": job.get("images", []),
            "debug_images": job.get("debug_images", []),
            "out_file": job.get("out_file"),
            "debug_out_file": job.get("debug_out_file"),
            "debug_on": bool((job.get("params") or {}).get("debug")),
            "live_images": _live_pages(job),
            "live_debug_images": _live_pages(job, dbg=True),
            "live_total": _live_total(job),
            "live_total_dbg": _live_total(job, dbg=True),
            "prog_page": int(job.get("prog_page") or 0),
            "prog_phase": str(job.get("prog_phase") or ""),
            "prog_now": _pn,
            "prog_total": _pt,
            "prog_pct": _ppct,
        }, ensure_ascii=False)


def cancel():
    """لغو واقعی کار در حال اجرا — پرچم توقف موتور را می‌گذارد؛ حلقهٔ
    اصلی manga.py بین صفحه‌ها آن را می‌بیند و JobCancelled می‌دهد."""
    with STATE["lock"]:
        job = STATE["job"]
    if not job or job.get("done"):
        return json.dumps({"ok": True, "idle": True}, ensure_ascii=False)
    job["cancel_requested"] = True
    _log(job, "درخواست لغو ثبت شد — در اولین فرصت توقف می‌شود…")
    try:
        _manga().request_stop()
    except Exception:
        pass
    return json.dumps({"ok": True}, ensure_ascii=False)


def test_keys(params_json):
    """تست کلیدهای API / لینک سفارشی برای دکمهٔ «تست کلید» اندروید.
    params_json: {"keys": "...", "provider": "...", "api_base": "...",
                  "model": "..."}"""
    try:
        p = json.loads(params_json or "{}")
    except Exception:
        p = {}
    keys = str(p.get("keys") or "")
    provider = str(p.get("provider") or "gemini")
    api_base = str(p.get("api_base") or "")
    model = str(p.get("model") or "")
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from manga import test_api_keys, format_key_test_text
        res = test_api_keys(keys, provider, api_base, model=model)
        return json.dumps(
            {"ok": True, "text": format_key_test_text(res)},
            ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
