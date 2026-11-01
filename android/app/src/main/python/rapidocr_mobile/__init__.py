# -*- coding: utf-8 -*-
"""rapidocr_mobile — موتورِ PP-OCRv6 سبک برایِ اندروید (v1.14.123).

دیکدِ K3 v4.1.1 (درخواستِ کاربر: «K3 چطور سریع و کامل استخراج میزنه؟»)
نشان داد K3 رویِ گوشی همان پایپلاینِ ONNXِ پی‌سی را اجرا میکند:
  ComicDetectorService (باکسِ حباب) → RunRapidOcrPipelineOnCrop /
  RunPaddleOcrV5RecWithSession → _ppOcrDict (ppocrv6_dict.txt)
  → SlicerGroupNearbyBlocks / MergeOcrBlocks → LaMa (LinearLama).

این ماژول همان پایپلاینِ RapidOCRِ پکیجِ PC را «بدونِ وابستگیِ
extra» بازسازی میکند تا داخلِ APK (Chaquopy) اجرا شود:
  • det: PP-OCRv6_det_small.onnx (DBNet) — پارامترهایِ عینِ
    config.yamlِ rapidocr (limit=736/min، thresh=0.3، box_thresh=0.5،
    unclip=1.6، dilation=2×2، score_mode=fast)
  • rec: PP-OCRv6_rec_small.onnx (CTC) — 3×48×W، بچِ ۶، دیکشنریِ
    «داخلِ خودِ مدل» (ppocrv6_chars.txt = metadataِ `character`
    استخراجشده از فایلِ onnxِ همان مدل)
  • unclip بدونِ pyclipper/shapely (پدِ مستطیلِ minAreaRect —
    ریاضیاتاً معادلِ خروجیِ PyclipperOffset برایِ rect)
  • سشن = شیمِ onnxruntimeِ باندلشده (پلِ Java ORT-android)

خروجیِ `ocr()` همان قالبِ RapidOCRBackend است:
  [ [box(np.float32 4×2), (text, score)], ... ]

v1.14.152 — مجموعهٔ K3: رویِ گوشیِ واقعی det/rec از فایلهایِ رسمیِ
PaddlePaddle است (PP-OCRv6_medium_det_onnx / PP-OCRv6_medium_rec_onnx /
PP-OCRv5_korean_rec + جفتِ ch_PP-OCRv4 برایِ چینی) — دقیقاً همان ۵ فایلِ
اپِ K3. charset از فایلهایِ باندلشده خوانده میشود (ppocrv6_chars /
korean_chars / ppocr_keys_v1). شبیهسازِ x86_64 (CI) همان مدلهایِ small
قبلی را میگیرد تا گیتها دستنخورده بمانند.
v1.14.155-speed — سشنِ OCR گوشی حالا XNNPACK/NNAPI دارد
(پیشفرض XNNPACK با کانفیگِ رسمی؛ MANGA_MOBILE_OCR_EP=auto
بنچمارکِ NNAPI/GPU هم میکند) + درمانِ EACCES در لحظهٔ
بازکردنِ مدل + دورِ دومِ آستانهٔ بازِ det بدونِ اجرایِ دوباره.
v1.14.156 — درمانِ کرشِ سیگ‌فالتِ 1.14.155: پروبِ EP در پروسهٔ
اصلی بود و سیگ‌فالتِ نیتیوِ XNNPACK (رویِ بعضی مدلها/گوشیها) اپ را
میکشت — در پایتون قابلِ گرفتن نیست. حالا EP فقط با تأییدِ پروبِ
پروسهٔ جدا (:epprobe → EpProbeService.kt: بنچِ det 64²/512² + rec
48×320 + چکِ صحتِ خروجی مقابلِ CPU) فعال میشود؛ برنده = سالمِ
سریعتر؛ کَش: <models>/.ep_probe.json. هیچ EP بدونِ تأیید در پروسهٔ
اصلی ساخته نمیشود → کرشِ EP دیگر اپ را تهدید نمیکند.
"""
import math
import os

import cv2
import numpy as np

import onnxruntime  # رویِ اندروید = شیمِ پلِ Java ORT؛ رویِ PC = پکیجِ واقعی

_HERE = os.path.dirname(os.path.abspath(__file__))
_CHARS_TXT = os.path.join(_HERE, "ppocrv6_chars.txt")


def _load_charset(path: str = _CHARS_TXT):
    """['blank'] + سطرهایِ dict + [' '] — دقیقاً قراردادِ PP-OCR CTC."""
    with open(path, "r", encoding="utf-8") as f:
        chars = [ln.rstrip("\n\r") for ln in f]
    chars = [c for c in chars if c != ""]
    return ["blank"] + chars + [" "]


def _android_env() -> bool:
    """محیطِ اندروید (Chaquopy): ANDROID_ROOT/ANDROID_DATA ست میشوند."""
    try:
        if "ANDROID_ROOT" in os.environ and "ANDROID_DATA" in os.environ:
            return True
    except Exception:
        pass
    try:
        return os.path.exists("/system/build.prop")
    except Exception:
        return False


def _x86_machine() -> bool:
    try:
        import platform as _pf
        return _pf.machine().lower() in ("x86_64", "amd64")
    except Exception:
        return False


def _avail_eps():
    try:
        return set(onnxruntime.get_available_providers())
    except Exception:
        return set()


def _big_core_count() -> int:
    """هستههایِ سریع (big) از cpufreq — برایِ threadpoolِ XNNPACK.
    Snapdragon 870: 1×3.2 + 3×2.42 + 4×1.8GHz → آستانهٔ ۶۰٪ → ۴."""
    import glob as _glob
    _freqs = []
    try:
        for _p in _glob.glob(
                "/sys/devices/system/cpu/cpu[0-9]*/cpufreq/cpuinfo_max_freq"):
            try:
                with open(_p) as _fh:
                    _freqs.append(int(_fh.read().strip() or 0))
            except Exception:
                pass
    except Exception:
        pass
    if len(_freqs) >= 4:
        _mx = max(_freqs)
        if _mx > 0:
            return max(1, sum(1 for _v in _freqs if _v >= _mx * 0.6))
    try:
        return max(1, os.cpu_count() or 4)
    except Exception:
        return 4


def _xnn_threads() -> int:
    try:
        _v = int(os.environ.get("MANGA_XNN_THREADS", "0") or 0)
        if _v > 0:
            return max(1, min(8, _v))
    except Exception:
        pass
    try:
        return max(2, min(6, _big_core_count()))
    except Exception:
        return 4


def _is_eacces(e) -> bool:
    """«system error number 13» / Permission denied — EACCESِ مدل."""
    try:
        _m = str(e).lower()
    except Exception:
        return False
    return ("error number 13" in _m or "errno 13" in _m
            or "permission denied" in _m or "eacces" in _m)


def _heal_model_file(path: str) -> None:
    """ترمیمِ مجوزِ خواندنِ فایلِ مدل (بعد از بهروزرسانیِ اپ/بازیابی)."""
    try:
        os.chmod(path, 0o644)
    except Exception:
        pass
    try:
        os.chmod(os.path.dirname(path) or ".", 0o755)
    except Exception:
        pass
    try:
        from java import jclass as _jc
        _f = _jc("java.io.File")(path)
        _f.setReadable(True, False)
    except Exception:
        pass


def _probe_input(path: str, small: bool = True) -> np.ndarray:
    """ورودیِ نمونه برایِ پروب/بنچمارک بر اساسِ نوعِ مدل (det/rec)."""
    _p = str(path).lower()
    if "_det" in _p:
        return np.zeros((1, 3, 64, 64) if small else (1, 3, 512, 512),
                        dtype=np.float32)
    return np.zeros((1, 3, 48, 320), dtype=np.float32)


_APP_CTX = None


def _app_ctx():
    """کانتکستِ اپ برایِ startService (چاکوپی؛ فال‌بکِ ActivityThread)."""
    global _APP_CTX
    if _APP_CTX is not None:
        return _APP_CTX
    try:
        from java import jclass
        try:
            _c = jclass(
                "com.chaquo.python.android.AndroidPlatform").getApplication()
        except Exception:
            _c = None
        if _c is None:
            try:
                _c = jclass("android.app.ActivityThread").currentApplication()
            except Exception:
                _c = None
        if _c is not None:
            _APP_CTX = _c
    except Exception:
        _APP_CTX = None
    return _APP_CTX


def _android_build_model() -> str:
    try:
        from java import jclass
        return str(jclass("android.os.Build").MODEL or "")
    except Exception:
        return ""


# v1.14.156 — تغییرِ کانفیگِ پروب/گیت → این رشته عوض شود تا پروبِ دوباره بگیرد
_EP_PROBE_VER = "v156.1"
_EP_PLAN_CACHE = {"key": None, "plan": (None, {})}
_EP_NOTE_156 = False

# v1.14.174 — تستِ NNAPI بدونِ env (رویِ APK متغیرِ محیطی دستِ کاربر نیست —
# گلایهٔ سازنده: «میگم nnapi بزار تست بزنم Xnnpack میزاری جاش؟»):
#   • فایلِ «nnapi.txt» کنارِ فایلهایِ مدل (0 بایت) = اجازهٔ تستِ NNAPI
#     (تورنمنتِ NNAPI+XNNPACK با گیتِ پروبِ پروسهٔ جدا).
#   • نشانِ «.ep_nnapi_last» = «اجرایِ NNAPI شروع شد ولی به یک کراپِ
#     کاملِ سالم نرسید» (کرشِ نیتیوِ اینفرنسِ واقعی که پروب نمیبیند)
#     → اجرایِ بعدِ CPU — حلقهٔ کرش نمیسازد. اولین کراپِ سالم (پوشِ
#     ocr) نشان را پاک میکند؛ NNAPIِ سالم همیشه میماند.
# v1.14.175 — دستورِ سازنده («هرچیزی ترکیبی nnapi xnnpack و… فقط سریع
# استخراج بزنه»): تورنمنتِ ترکیبیِ NNAPI+XNNPACK «پیشفرض» شد؛ نشانِ
# کرش نسخهآگاه شد (آپدیتِ اپ = فرصتِ تازه)، فالبکِ کرش = XNNPACK نه
# CPU، کوتاهبرِ پروب = اولین سالم کافی، «no_nnapi.txt» = قفلِ خاموش.
_LAUNCH_TOKEN = "%d:%.6f" % (os.getpid(), __import__("time").time())
_NNAPI_ACTIVE = False
_NNAPI_GUARD = None
_NNAPI_HINT = False


def _nnapi_switch_path(mdir: str) -> str:
    return os.path.join(mdir, "nnapi.txt")


def _nnapi_guard_path(mdir: str) -> str:
    return os.path.join(mdir, ".ep_nnapi_last")


def _nnapi_guard_write(gpath: str) -> None:
    """نوشتنِ نشان با شناسهٔ همین اجرا + نسخهٔ اپ (MANGA_APP_VER) —
    پروسهٔ همین اجرا خودش را میشناسد (موتورِ دومِ همان اجرا فالبکِ
    اشتباه نمیخورد)؛ آپدیتِ اپ = فرصتِ تازه برایِ NNAPI."""
    global _NNAPI_GUARD
    try:
        import json as _json
        with open(gpath, "w", encoding="utf-8") as _f:
            _json.dump({"launch": _LAUNCH_TOKEN,
                        "ver": os.environ.get("MANGA_APP_VER", "")}, _f)
        _NNAPI_GUARD = gpath
    except Exception:
        _NNAPI_GUARD = None


def _nnapi_guard_stale(gpath: str) -> bool:
    """نشانِ «اجرایِ قبلیِ NNAPI که به یک کراپِ کامل نرسید»؟
    • نشانِ همین اجرا (شناسه/موتورِ دوم) = تازه → نه
    • نشانِ اجرایِ قبلی با همان نسخهٔ اپ = کرشِ احتمالی → بله
    • نشانِ نسخهٔ دیگر (آپدیتِ اپ) یا محتوایِ متنیِ قدیمیِ 1.14.174
      = فرصتِ تازه برایِ NNAPI → نه"""
    try:
        with open(gpath, "r", encoding="utf-8") as _f:
            _txt = (_f.read() or "").strip()
    except Exception:
        return False
    if not _txt:
        return False
    try:
        import json as _json
        _d = _json.loads(_txt)
        _launch = str(_d.get("launch") or "")
        _ver = str(_d.get("ver") or "")
    except Exception:
        # محتوایِ متنیِ سادهٔ 1.14.174 = نشانِ نسخهٔ دیگر → فرصتِ تازه
        return False
    if _launch == _LAUNCH_TOKEN:
        return False
    return _ver == os.environ.get("MANGA_APP_VER", "")


def _nnapi_guard_clear() -> None:
    """اولین کراپِ کاملِ سالم با NNAPI → نشانِ کرش پاک (NNAPI میماند)."""
    global _NNAPI_ACTIVE, _NNAPI_GUARD
    if not _NNAPI_ACTIVE:
        return
    _NNAPI_ACTIVE = False
    if _NNAPI_GUARD:
        try:
            os.remove(_NNAPI_GUARD)
        except Exception:
            pass
        _NNAPI_GUARD = None


def _ep_flag_path(mdir: str) -> str:
    return os.path.join(mdir, ".ep_probe.json")


def _probe_key(paths) -> str:
    st = [getattr(onnxruntime, "__version__", "?"), _EP_PROBE_VER,
          _android_build_model()]
    for _p in paths:
        try:
            st.append("%s:%d:%d" % (os.path.basename(_p),
                                    os.path.getsize(_p),
                                    int(os.path.getmtime(_p)) // 60))
        except Exception:
            # فایل هنوز نیست (دانلود نشده) — basename کافی است تا کلید
            # نسبت به مدلِ انتخابی حساس بماند
            st.append(str(os.path.basename(_p)) + ":?")
    return "|".join(st)


def _ep_probe_read(mdir: str, key: str):
    try:
        import json
        with open(_ep_flag_path(mdir), "r", encoding="utf-8") as _f:
            _d = json.load(_f)
        if str(_d.get("key") or "") != key:
            return {}
        return dict(_d.get("eps") or {})
    except Exception:
        return {}


def _ep_probe_write(mdir: str, key: str, eps: dict) -> None:
    try:
        import json
        _p = _ep_flag_path(mdir)
        _tmp = _p + ".tmp"
        with open(_tmp, "w", encoding="utf-8") as _f:
            json.dump({"key": key, "eps": eps}, _f)
        os.replace(_tmp, _p)
    except Exception:
        pass


def _parse_probe_txt(txt):
    """«verdict ok <ms>» → ok؛ «verdict fail …» → fail؛
    غایب = کرشِ نیتیو (سیگ‌فالت) یا تایم‌اوت → EP مردود."""
    if not txt:
        return {"ok": False, "why": "probe-crash-or-timeout"}
    for _ln in str(txt).splitlines():
        _ln = _ln.strip()
        if _ln.startswith("verdict ok"):
            try:
                _ms = float(_ln.split()[2])
            except Exception:
                _ms = 1e9
            return {"ok": True, "ms": _ms}
        if _ln.startswith("verdict fail"):
            return {"ok": False, "why": _ln[12:120].strip()}
    return {"ok": False, "why": "no-verdict"}


def _ep_probe_proc_alive() -> bool:
    """پروسهٔ :epprobe هنوز زنده است؟ (getRunningAppProcesses فقط
    پروسههایِ خودِ اپ را میدهد؛ خطا → True تا تایم‌اوت منتظر بماند)."""
    try:
        _ctx = _app_ctx()
        if _ctx is None:
            return True
        _am = _ctx.getSystemService("activity")
        _procs = _am.getRunningAppProcesses() or []
        for _p in _procs:
            try:
                if str(_p.processName).endswith(":epprobe"):
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return True


def _start_ep_probe_service(det_path, rec_path, ep_short, out_path, threads):
    try:
        _ctx = _app_ctx()
        if _ctx is None:
            return False
        from java import jclass
        _Intent = jclass("android.content.Intent")
        _Srv = jclass("com.amirwolf.mangatranslator.EpProbeService")
        _it = _Intent(_ctx, _Srv)
        _it.putExtra("det", str(det_path))
        _it.putExtra("rec", str(rec_path))
        _it.putExtra("ep", str(ep_short))
        _it.putExtra("out", str(out_path))
        _it.putExtra("threads", str(threads))
        _ctx.startService(_it)
        return True
    except Exception:
        return False


def _ep_probe_timeout() -> float:
    # v1.14.174 — 90→180: بارِ اولِ بعد از آپدیت پروبِ 90 ثانیهایِ 1.14.173
    # تایم‌اوت خورد (لاگِ گوشی: «Xnnpack=timeout») — سقفِ پیشفرض دوبرابر.
    try:
        return float(os.environ.get("MANGA_EP_PROBE_TIMEOUT", "180") or 180)
    except Exception:
        return 180.0


def _ep_gate_ensure(mdir, det_path, rec_path, wanted, threads):
    """پروبِ پروسهٔ جدا برایِ EPهایِ هنوزتأییدنشده؛ خروجی: name→info.
    v1.14.175 — کوتاهبرِ ترتیب: به ترتیبِ wanted پروب میگیرد و با
    «اولین سالم» میایستد (وقتی NNAPI سالم است XNNPACK دیگر پروبِ
    دوباره نمیگیرد — استارتِ سریعتر؛ ترتیبِ wanted = اولویتِ برنده)."""
    global _EP_NOTE_156
    import time as _time
    _res = _ep_probe_read(mdir, _probe_key([det_path, rec_path]))
    for _name in wanted:
        if _name in _res:
            # v1.14.175 — اولین سالمِ کَشِده = کوتاهبر (ترتیبِ wanted)
            if (_res[_name] or {}).get("ok"):
                break
            continue
        _short = "nnapi" if "Nnapi" in _name else "xnnpack"
        _out = os.path.join(mdir, ".ep_probe_%s.txt" % _short)
        try:
            os.remove(_out)
        except Exception:
            pass
        if not _start_ep_probe_service(det_path, rec_path, _short,
                                       _out, threads):
            _res[_name] = {"ok": False, "why": "service-start-failed"}
            continue
        if not _EP_NOTE_156:
            print("[⚡] آزمونِ "
                  + _short + " در پروسهٔ "
                  "جدا (:epprobe) — بارِ "
                  "اول پس از آپدیت؛ "
                  "بارهایِ بعد "
                  "از کَش میآید")
            _EP_NOTE_156 = True
        _t0 = _time.time()
        _tmo = _ep_probe_timeout()
        _info = None
        while _time.time() - _t0 < _tmo:
            _txt = None
            if os.path.isfile(_out):
                try:
                    with open(_out, "r", encoding="utf-8") as _f:
                        _txt = _f.read()
                except Exception:
                    _txt = None
                if _txt and "verdict" in _txt:
                    _info = _parse_probe_txt(_txt)
                    break
            if not _ep_probe_proc_alive():
                # پروسه رفت — ۲ ثانیه فرصتِ آخر برایِ نوشتنِ فایل
                _time.sleep(2.0)
                if os.path.isfile(_out):
                    try:
                        with open(_out, "r", encoding="utf-8") as _f:
                            _txt = _f.read()
                    except Exception:
                        _txt = None
                    if _txt and "verdict" in _txt:
                        _info = _parse_probe_txt(_txt)
                if _info is None:
                    _info = {"ok": False, "why": "probe-crash"}
                break
            _time.sleep(0.4)
        if _info is None:
            _info = {"ok": False, "why": "timeout"}
        _res[_name] = _info
        # v1.14.175 — اولین سالمِ تازه = کوتاهبر (بقیه پروب نمیگیرند)
        if _info.get("ok"):
            break
    _ep_probe_write(mdir, _probe_key([det_path, rec_path]), _res)
    return _res


def _ep_plan(det_path: str, rec_path: str):
    """v1.14.156 — EPِ سشنِ OCRِ گوشی فقط با تأییدِ پروبِ پروسهٔ جدا.

    ریشهٔ کرشِ 1.14.155: پروبِ EP در پروسهٔ اصلی اجرا میشد؛ سیگ‌فالتِ
    نیتیوِ XNNPACK (رویِ بعضی مدلها/گوشیها — onnxruntime#23826 «حساس
    به لایهٔ/چیدمانِ مدل») در پایتون قابلِ گرفتن نیست (try/except فقط
    ORT_FAIL را میگیرد) → اپ موقعِ ساختِ سشنِ اولین OCR میمرد.
    حالا: هیچ سشنِ EP بدونِ «verdict ok» از پروبِ :epprobe ساخته
    نمیشود؛ برنده = سالمِ سریعتر (ms از پروب). کَش:
    <models>/.ep_probe.json (کلید = نسخهٔ ORT + حجم/زمانِ مدلها +
    مدلِ گوشی) → بارِ اول پس از هر آپدیت، بارهایِ بعد فوری.

    MANGA_MOBILE_OCR_EP: cpu | xnnpack | nnapi | auto (پیشفرض) —
    v1.14.173: auto = فقط XNNPACK (کرشِ نیتیوِ NNAPI در اینفرنسِ واقعی
    — پروبِ OK ولی سیگفالت در پروسهٔ اصلی).
    v1.14.174: تستِ NNAPI با فایلِ «nnapi.txt» کنارِ مدلها (env رویِ
    APK دستِ کاربر نیست).
    v1.14.175 — دستورِ سازنده («هرچیزی ترکیبی nnapi xnnpack و… فقط
    سریع استخراج بزنه»): auto/پیشفرض = تورنمنتِ ترکیبیِ NNAPI+XNNPACK
    (NNAPI مقدم — اولین سالمِ گیتِ پروب کافی است). نشانِ کرشِ
    .ep_nnapi_last: شروعِ اجرایِ NNAPI نوشته، اولین کراپِ سالم پاک
    میشود؛ نشانِ مانده از اجرایِ «قبلیِ» همان نسخه → NNAPI از تورنمنتِ
    آن اجرا حذف (فالبکِ XNNPACK — CPUِ خالی نمیماند)؛ آپدیتِ اپ یا
    محتوایِ قدیمیِ 1.14.174 = فرصتِ تازه. فایلِ «no_nnapi.txt» = قفلِ
    فقط-XNNPACK (خاموشکردنِ NNAPI از داخلِ اپ). MANGA_EP_NO_PROBE=1
    فقط برایِ توسعه. خروجی: (ep_name|None, opts) — None = CPU خالص."""
    global _EP_PLAN_CACHE, _NNAPI_HINT, _NNAPI_ACTIVE
    try:
        _e = str(os.environ.get("MANGA_MOBILE_OCR_EP", "") or "") \
            .strip().lower()
    except Exception:
        _e = ""
    if _e == "cpu":
        return None, {}
    if not _android_env() or _x86_machine():
        # PC / امولاتورِ x86_64: رفتارِ قبل (providers=None) — CI دستنخورده
        return None, {}
    if str(os.environ.get("MANGA_EP_NO_PROBE", "") or "").strip() == "1":
        if "XnnpackExecutionProvider" in _avail_eps():
            return "XnnpackExecutionProvider", {}
        return None, {}
    _mdir = os.path.dirname(det_path) or "."
    _switch = os.path.isfile(_nnapi_switch_path(_mdir))
    if _e == "nnapi":
        # v1.14.173 — تستِ صریحِ NNAPI (دستورِ سازنده: «nnapi میخوام
        # تست کنم نه xnnpack»). پروبِ پروسهٔ جدا هنوز گیت است ولی کرشِ
        # نیتیوِ اینفرنسِ واقعی (لاگِ گوشیِ 1.14.172: پروبِ NNAPI با
        # ms=3969 تأیید شد و باز کرش کرد) در پایتون قابلِ گرفتن نیست —
        # ریسکِ تست با سازنده؛ ORT_FAILِ قابلِ گرفتن → فالبکِ CPU در
        # _Sess._open سرِ جایش است.
        # v1.14.177 — انتخابِ صریحِ «فقط NNAPI» (پنلِ اپ یا env) =
        # خواستهٔ روشنِ «تستِ دوباره» (دکمهٔ تستِ خودِ سازنده): نشانِ
        # کرشِ کهنه پاک میشود تا NNAPI واقعاً آزموده شود. گاردِ ضدِ
        # حلقهٔ کرش فقط برایِ auto/تورنمنت سرِ جایش است.
        try:
            _gp0 = _nnapi_guard_path(_mdir)
            if os.path.isfile(_gp0):
                os.remove(_gp0)
                print("[*] تستِ صریحِ NNAPI → نشانِ کرشِ کهنه پاک شد — "
                      "NNAPI دوباره آزموده میشود", flush=True)
        except Exception:
            pass
        try:
            print("[⚡] تستِ NNAPI (MANGA_MOBILE_OCR_EP=nnapi) — "
                  "اگر کرش کند اجرایِ بعدِ خودکار بدونِ NNAPI میشود",
                  flush=True)
        except Exception:
            pass
        _wanted = ["NnapiExecutionProvider"]
    elif os.path.isfile(os.path.join(_mdir, "no_nnapi.txt")):
        # v1.14.175 — قفلِ فقط-XNNPACK از داخلِ اپ (فایلِ 0بایتیِ
        # «no_nnapi.txt» کنارِ مدلها) — برایِ وقتی که NNAPI مدام کرش
        # میکند و سازنده نمیخواهد دیگر امتحان شود.
        if not _NNAPI_HINT:
            print("[*] no_nnapi.txt → فقط XNNPACK (NNAPI خاموش)",
                  flush=True)
            _NNAPI_HINT = True
        _wanted = ["XnnpackExecutionProvider"]
    elif _switch:
        # v1.14.174 — فایلِ «nnapi.txt» (در 1.14.175 تورنمنتِ ترکیبی
        # پیشفرض شد؛ فایل همان رفتار + پیامِ مخصوصِ خودش را دارد).
        if not _NNAPI_HINT:
            print("[⚡] تستِ NNAPI (فایلِ nnapi.txt) — تورنمنتِ پروبِ "
                  "پروسهٔ جدا؛ بعد از یک کرش، اجرایِ بعد بدونِ NNAPI "
                  "میشود", flush=True)
            _NNAPI_HINT = True
        _wanted = ["NnapiExecutionProvider", "XnnpackExecutionProvider"]
    elif _e in ("", "auto", "xnnpack,nnapi", "nnapi,xnnpack"):
        # v1.14.175 — دستورِ سازنده («هرچیزی ترکیبی nnapi xnnpack و…
        # فقط سریع استخراج بزنه»): تورنمنتِ ترکیبیِ NNAPI+XNNPACK
        # پیشفرض شد (در 1.14.173/174 فقط-XNNPACK بود). NNAPI مقدم —
        # اولین سالمِ گیتِ پروب کافی است؛ بعد از یک کرشِ واقعی، نشانِ
        # .ep_nnapi_last NNAPI را از اجرایِ بعد حذف میکند (آپدیتِ اپ =
        # فرصتِ تازه). قفلِ فقط-XNNPACK: فایلِ no_nnapi.txt یا
        # MANGA_MOBILE_OCR_EP=xnnpack.
        if not _NNAPI_HINT:
            print("[⚡] تورنمنتِ ترکیبیِ NNAPI+XNNPACK — برنده = "
                  "سالمِ سریعتر (پروبِ پروسهٔ جدا؛ بعد از یک کرش، "
                  "اجرایِ بعد بدونِ NNAPI میشود)", flush=True)
            _NNAPI_HINT = True
        _wanted = ["NnapiExecutionProvider", "XnnpackExecutionProvider"]
    else:
        _wanted = ["XnnpackExecutionProvider"]
    _wanted = [w for w in _wanted if w in _avail_eps()]
    if not _wanted:
        return None, {}
    # v1.14.176 — کلیدِ کَش = کلیدِ پروب + ترکیبِ wanted: وقتی سازنده از
    # پنلِ «آزمایشگاهِ سرعت» شتابدهنده را عوض میکند (auto→nnapi→xnnpack→
    # cpu یا no_nnapi.txt) پلنِ قبلیِ کَشده نباید برگردد — با wantedِ
    # تازه دوباره تصمیمگیری میشود (کَشِ پروبِ رویِ دیسک سرِ جایش
    # میماند → هیچ پروبِ تکراریِ گران نمیگیرد).
    _key = _probe_key([det_path, rec_path]) + "#" + ",".join(_wanted)
    if _EP_PLAN_CACHE.get("key") == _key:
        return _EP_PLAN_CACHE["plan"]
    # v1.14.175 — نشانِ کرشِ اجرایِ «قبلی» (همان نسخه) → NNAPI از
    # تورنمنت حذف میشود؛ حتی پروبِ دوباره نمیگیرد (استارتِ سریع)،
    # فالبک = XNNPACK نه CPUِ خالی.
    if "NnapiExecutionProvider" in _wanted \
            and _nnapi_guard_stale(_nnapi_guard_path(_mdir)):
        print("[!] NNAPI: اجرایِ قبل با NNAPI به یک کراپِ کامل نرسید "
              "(کرشِ احتمالی) → این اجرا بدونِ NNAPI — تستِ دوباره: "
              "«تستِ سرعت» را از پنلِ اپ اجرا کن (پنجرهٔ NNAPI خودش "
              "نشان را پاک میکند؛ یا .ep_nnapi_last را حذف کن)", flush=True)
        _wanted = [w for w in _wanted
                   if w != "NnapiExecutionProvider"]
        if not _wanted:
            _EP_PLAN_CACHE = {"key": _key, "plan": (None, {})}
            return (None, {})
    _res = _ep_gate_ensure(_mdir, det_path, rec_path, _wanted,
                           _xnn_threads())
    _winner, _wt = None, None
    for _name in _wanted:
        _inf = _res.get(_name) or {}
        if _inf.get("ok"):
            try:
                _ms = float(_inf.get("ms") or 1e9)
            except Exception:
                _ms = 1e9
            if _wt is None or _ms < _wt:
                _winner, _wt = _name, _ms
    if _winner is None:
        _why = "; ".join(
            "%s=%s" % (n.replace("ExecutionProvider", ""),
                       str((_res.get(n) or {}).get("why", "?"))[:48])
            for n in _wanted)
        print("[⚡] هیچ شتابدهندهٔ "
              "سالمی تأیید نشد → CPU ("
              + _why + ")")
        _plan = (None, {})
    else:
        if _winner == "XnnpackExecutionProvider":
            _plan = (_winner, {"intra_op_num_threads": str(_xnn_threads())})
        else:
            _plan = (_winner, {})
        print("[⚡] EP=" + _winner.replace("ExecutionProvider", "")
              + " تأیید شد "
              "(پروبِ پروسهٔ جدا؛ "
              "ms=" + ("%.0f" % _wt) + ")")
        if _winner == "NnapiExecutionProvider":
            # v1.14.174/175 — نشانِ «شروعِ اجرایِ NNAPI»: تا اولین
            # کراپِ کاملِ سالم زنده میماند؛ کرشِ نیتیوِ مسیرِ واقعی
            # (که پروبِ پروسهٔ جدا نمیبیند) → فایل میماند → اجرایِ
            # بعدی بدونِ NNAPI (XNNPACK/CPU).
            _nnapi_guard_write(_nnapi_guard_path(_mdir))
            _NNAPI_ACTIVE = True
    _EP_PLAN_CACHE = {"key": _key, "plan": _plan}
    return _plan

class _Sess:
    def __init__(self, path: str, intra: int, ep: str = None,
                 ep_opts: dict = None):
        self._intra = max(1, int(intra))
        so = onnxruntime.SessionOptions()
        so.inter_op_num_threads = 1
        if ep == "XnnpackExecutionProvider":
            # کانفیگِ رسمیِ XNNPACK: threadpoolِ ORT تکنخی؛ XNNPACK خودش
            # threadpoolِ هستههایِ سریع را میسازد.
            so.intra_op_num_threads = 1
        elif ep == "NnapiExecutionProvider":
            # نیازمندیهایِ مستندِ NNAPI EP (شکلِ داینامیک):
            # memory pattern خاموش + arena خاموش — نبودشان منبعِ
            # کرش/خرابیِ خروجی است.
            so.intra_op_num_threads = 1
            try:
                so.enable_mem_pattern = False
            except Exception:
                pass
            try:
                so.enable_cpu_mem_arena = False
            except Exception:
                pass
        else:
            so.intra_op_num_threads = self._intra
        if ep == "XnnpackExecutionProvider":
            try:
                so.add_session_config_entry(
                    "session.intra_op.allow_spinning", "0")
            except Exception:
                pass
        _prov = None
        if ep:
            _prov = [ep, "CPUExecutionProvider"]
            try:
                so.append_execution_provider(ep, dict(ep_opts or {}) or None)
            except Exception:
                try:
                    so.append_execution_provider(ep)
                except Exception:
                    pass
        self.sess = self._open(path, so, _prov)
        self.in_name = self.sess.get_inputs()[0].name
        self.out_name = self.sess.get_outputs()[0].name

    def _open(self, path, so, prov):
        try:
            _sess = onnxruntime.InferenceSession(
                path, sess_options=so, providers=prov)
        except Exception as e:
            if not _is_eacces(e):
                raise
            # v1.14.155 — درمانِ EACCES در لحظهٔ بازکردن («system error
            # number 13»): chmod + تستِ خواندن؛ هنوز قفل؟ → دانلودِ دوباره
            print("[!] فایلِ مدلِ OCR خواندنی نیست (errno 13) → ترمیمِ مجوز…")
            _heal_model_file(path)
            if not _selfread_ok(path):
                try:
                    os.remove(path)
                    print("[!] مدلِ ناخوانا حذف شد → دانلودِ دوباره لازم است")
                except Exception:
                    pass
            _sess = onnxruntime.InferenceSession(
                path, sess_options=so, providers=prov)
        if prov:
            # v1.14.66 محفوظ — پروبِ واقعیِ run: اگر EP با شکلِ داینامیک
            # بشکند (ORT_FAIL) → سشنِ CPUِ خالص؛ هیچ فالبکِ بیصدایی به
            # موتورِ دیگر در کار نیست.
            try:
                _in = _sess.get_inputs()[0].name
                _out = _sess.get_outputs()[0].name
                _sess.run([_out], {_in: _probe_input(path)})
            except Exception:
                try:
                    _so2 = onnxruntime.SessionOptions()
                    _so2.inter_op_num_threads = 1
                    _so2.intra_op_num_threads = self._intra
                    _sess = onnxruntime.InferenceSession(
                        path, sess_options=_so2, providers=None)
                    print("[!] EP در پروب شکست → سشنِ CPUِ خالص")
                except Exception:
                    raise
        return _sess

    def __call__(self, x: np.ndarray) -> np.ndarray:
        outs = self.sess.run(None, {self.in_name: x})
        return outs[0]


def _selfread_ok(path: str) -> bool:
    try:
        with open(path, "rb") as _f:
            _f.read(64)
        return True
    except Exception:
        return False


class RapidOcrMobile:
    """PP-OCRv6 det+rec — عینِ پیشفرضهایِ rapidocr config.yaml.

    v1.14.125 — crop_mode: حالتِ «برش» (کاسکادِ K3). det در حالتِ صفحه
    (limit=736، نوعِ min) برشهایِ کوچک را تا ضلعِ کوچکِ ۷۳۶ «بزرگ»
    میکند — برایِ برشِ حباب یعنی det رویِ ۴-۶× پیکسلِ بیشتر از لازم
    (عینِ ریشهٔ کندیِ 1.14.124). در crop_mode: هیچِ بزرگنماییِ نمیشود
    (متنِ برش بزرگ است) و فقط اگر ضلعِ بزرگ از det_cap گذشت، کوچک
    میشود — دقیقاً منطقِ RunRapidOcrPipelineOnCrop در K3 (برشِ کوچک =
    det/recِ سریع، مثلِ lama-nofft: سشنِ ONNX رویِ ورودیِ کوچک)."""

    def __init__(self, det_path: str, rec_path: str,
                 charset_path: str = _CHARS_TXT, intra_threads: int = 4,
                 limit_side_len: int = 736, thresh: float = 0.3,
                 box_thresh: float = 0.5, unclip_ratio: float = 1.6,
                 max_candidates: int = 1000, text_score: float = 0.5,
                 rec_img_shape=(3, 48, 320), rec_batch_num: int = 6,
                 det_cap: int = 960):
        # v1.14.156 — پلنِ EP یک بار برایِ هر دو مدل (پروبِ پروسهٔ جدا)
        _ep, _ep_opts = _ep_plan(det_path, rec_path)
        self.det = _Sess(det_path, intra_threads, ep=_ep,
                         ep_opts=_ep_opts)
        self.rec = _Sess(rec_path, intra_threads, ep=_ep,
                         ep_opts=_ep_opts)
        self.character = _load_charset(charset_path)
        self.limit_side_len = int(limit_side_len)
        self.det_cap = int(det_cap)
        self.thresh = float(thresh)
        self.box_thresh = float(box_thresh)
        self.unclip_ratio = float(unclip_ratio)
        self.max_candidates = int(max_candidates)
        self.text_score = float(text_score)
        self.rec_img_shape = tuple(rec_img_shape)
        self.rec_batch_num = int(rec_batch_num)
        self.min_size = 3
        self.dilation_kernel = np.array([[1, 1], [1, 1]], dtype=np.uint8)

    # ─────────────────────────── det ───────────────────────────

    def _det_preprocess(self, img: np.ndarray,
                        crop_mode: bool = False, det_cap=None):
        h, w = img.shape[:2]
        if crop_mode:
            # v1.14.125 — برش: بدونِ بزرگنمایی؛ فقط کوچککردنِ تا سقف
            try:
                _cap = int(det_cap) if det_cap else self.det_cap
            except Exception:
                _cap = 960
            _m = max(h, w)
            ratio = min(1.0, float(_cap) / _m) if _m > _cap else 1.0
        elif min(h, w) < self.limit_side_len:
            ratio = (float(self.limit_side_len) / h) if h < w else \
                (float(self.limit_side_len) / w)
        else:
            ratio = 1.0
        resize_h = int(round((int(h * ratio)) / 32) * 32)
        resize_w = int(round((int(w * ratio)) / 32) * 32)
        if resize_w <= 0 or resize_h <= 0:
            return None
        if (resize_h, resize_w) != (h, w):
            img = cv2.resize(img, (resize_w, resize_h))
        out = (img.astype("float32") * (1.0 / 255.0) - 0.5) / 0.5
        out = out.transpose((2, 0, 1))
        return np.expand_dims(out, axis=0).astype(np.float32)

    def _get_mini_boxes(self, contour: np.ndarray):
        bounding_box = cv2.minAreaRect(contour)
        points = sorted(list(cv2.boxPoints(bounding_box)), key=lambda x: x[0])

        index_1, index_2, index_3, index_4 = 0, 1, 2, 3
        if points[1][1] > points[0][1]:
            index_1, index_4 = 0, 1
        else:
            index_1, index_4 = 1, 0
        if points[3][1] > points[2][1]:
            index_2, index_3 = 2, 3
        else:
            index_2, index_3 = 3, 2

        box = np.array([points[index_1], points[index_2],
                        points[index_3], points[index_4]])
        return box, min(bounding_box[1])

    @staticmethod
    def _box_score_fast(bitmap: np.ndarray, _box: np.ndarray) -> float:
        h, w = bitmap.shape[:2]
        box = _box.copy()
        xmin = int(np.clip(np.floor(box[:, 0].min()), 0, w - 1))
        xmax = int(np.clip(np.ceil(box[:, 0].max()), 0, w - 1))
        ymin = int(np.clip(np.floor(box[:, 1].min()), 0, h - 1))
        ymax = int(np.clip(np.ceil(box[:, 1].max()), 0, h - 1))
        mask = np.zeros((ymax - ymin + 1, xmax - xmin + 1), dtype=np.uint8)
        box[:, 0] = box[:, 0] - xmin
        box[:, 1] = box[:, 1] - ymin
        cv2.fillPoly(mask, box.reshape(1, -1, 2).astype(np.int32), 1)
        return float(cv2.mean(bitmap[ymin:ymax + 1, xmin:xmax + 1], mask)[0])

    def _unclip(self, box: np.ndarray,
                unclip_ratio: float = None) -> np.ndarray:
        """معادلِ PyclipperOffset(JT_ROUND, distance=area*ratio/length).

        ورودی: ۴ گوشهٔ rect (ترتیبِ حلقه: TL,TR,BR,BL — خروجیِ
        _get_mini_boxes). هر گوشه به اندازهٔ dist در جهتِ دو ضلعِ مجاور
        بیرون میرود — برایِ rect دقیقاً معادلِ offsetِ کلایپر است
        (گوشههایِ گردِ JT_ROUND بعداً minAreaRect میشوند = همان rect)."""
        pts = np.asarray(box, dtype=np.float32).reshape(-1, 2)
        _ur = self.unclip_ratio if unclip_ratio is None else float(unclip_ratio)
        # rect واقعی از طولِ ضلعها (حلقهٔ TL,TR,BR,BL)
        w1 = float(np.linalg.norm(pts[1] - pts[0]))
        h1 = float(np.linalg.norm(pts[3] - pts[0]))
        area = max(1.0, w1 * h1)
        perim = max(1.0, 2.0 * (w1 + h1))
        dist = area * _ur / perim
        out = np.empty_like(pts)
        n = len(pts)
        for i in range(n):
            prev = pts[(i - 1) % n]
            nxt = pts[(i + 1) % n]
            d1 = pts[i] - prev
            d2 = pts[i] - nxt
            n1 = np.linalg.norm(d1)
            n2 = np.linalg.norm(d2)
            if n1 < 1e-6 or n2 < 1e-6:
                out[i] = pts[i]
                continue
            out[i] = pts[i] + dist * (d1 / n1 + d2 / n2)
        return out.reshape((-1, 1, 2))

    def _order_points_clockwise(self, pts: np.ndarray) -> np.ndarray:
        """عینِ rapidocr: sort بر اساسِ x، سپسِ جفتِ بالا/پایین."""
        points = sorted(list(pts), key=lambda x: x[0])
        if points[1][1] > points[0][1]:
            p1, p4 = points[0], points[1]
        else:
            p1, p4 = points[1], points[0]
        if points[3][1] > points[2][1]:
            p2, p3 = points[2], points[3]
        else:
            p2, p3 = points[3], points[2]
        return np.array([p1, p2, p3, p4], dtype=np.float32)

    def _det_postprocess(self, pred: np.ndarray, src_h: int, src_w: int,
                         thresh: float = None, box_thresh: float = None,
                         unclip_ratio: float = None):
        _t = self.thresh if thresh is None else float(thresh)
        _bt = self.box_thresh if box_thresh is None else float(box_thresh)
        _ur = self.unclip_ratio if unclip_ratio is None else float(unclip_ratio)
        pred = pred[:, 0, :, :]  # [1,H,W]
        mask = (pred[0] > _t).astype(np.uint8)  # [H,W]
        mask = cv2.dilate(mask, self.dilation_kernel)
        bitmap = mask
        height, width = bitmap.shape

        outs = cv2.findContours(
            (bitmap * 255).astype(np.uint8),
            cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = outs[1] if len(outs) == 3 else outs[0]

        num = min(len(contours), self.max_candidates)
        boxes, scores = [], []
        for idx in range(num):
            contour = contours[idx]
            points, sside = self._get_mini_boxes(contour)
            if sside < self.min_size:
                continue
            score = self._box_score_fast(pred[0], points.reshape(-1, 2))
            if _bt > score:
                continue
            box = self._unclip(points, _ur)
            box, sside = self._get_mini_boxes(box)
            if sside < self.min_size + 2:
                continue
            box[:, 0] = np.clip(np.round(box[:, 0] / width * src_w), 0, src_w)
            box[:, 1] = np.clip(np.round(box[:, 1] / height * src_h), 0, src_h)
            boxes.append(box.astype(np.float32))
            scores.append(float(score))
        return boxes, scores

    def _boxes_from_pred(self, pred: np.ndarray, src_h: int, src_w: int,
                         thresh: float = None, box_thresh: float = None,
                         unclip_ratio: float = None):
        """v1.14.155 — فیلتر + مرتبسازیِ باکسها رویِ predِ موجود.

        بدونِ اجرایِ دوبارهٔ مدل؛ دورِ دومِ آستانهٔ بازِ `ocr()` رویِ
        همین متد سوار است (متنِ کمکنتراست/حبابهایِ کموبه که در
        thresh=0.3/box=0.5 حذف میشدند — شکایتِ «حتی عکسِ دومتنی هم
        استخراج نمیشود»)."""
        boxes, scores = self._det_postprocess(
            pred, src_h, src_w, thresh=thresh, box_thresh=box_thresh,
            unclip_ratio=unclip_ratio)

        # filter_det_res: مرتبسازیِ ساعتگرد + حذفِ ضلعِ ≤3
        final = []
        for box, score in zip(boxes, scores):
            box = self._order_points_clockwise(box)
            box[:, 0] = np.clip(box[:, 0], 0, src_w - 1)
            box[:, 1] = np.clip(box[:, 1], 0, src_h - 1)
            wdt = int(np.linalg.norm(box[0] - box[1]))
            hgt = int(np.linalg.norm(box[0] - box[3]))
            if wdt <= 3 or hgt <= 3:
                continue
            final.append((box, score))

        # sorted_boxes: ردیفِ y (آستانهٔ 10) → x داخلِ ردیف
        if len(final) > 1:
            ys = np.array([b[0][0][1] for b in final])
            order = np.argsort(ys, kind="stable")
            final = [final[i] for i in order]
            ys = ys[order]
            line_ids = np.concatenate(
                [[0], np.cumsum((np.diff(ys) >= 10).astype(np.int32))])
            xs = np.array([final[i][0][0][0] for i in range(len(final))])
            order2 = np.lexsort((xs, line_ids))
            final = [final[i] for i in order2]
        return final

    def _detect(self, img: np.ndarray, crop_mode: bool = False,
                det_cap=None):
        src_h, src_w = img.shape[:2]
        pre = self._det_preprocess(img, crop_mode=crop_mode, det_cap=det_cap)
        if pre is None:
            return [], None
        pred = self.det(pre)
        return self._boxes_from_pred(pred, src_h, src_w), pred


    def _resize_norm(self, img: np.ndarray, img_w: int) -> np.ndarray:
        img_c, img_h, _ = self.rec_img_shape
        h, w = img.shape[:2]
        ratio = w / float(h)
        resized_w = img_w if math.ceil(img_h * ratio) > img_w \
            else int(math.ceil(img_h * ratio))
        resized = cv2.resize(img, (resized_w, img_h))
        resized = resized.astype("float32").transpose((2, 0, 1)) / 255.0
        resized -= 0.5
        resized /= 0.5
        pad = np.zeros((img_c, img_h, img_w), dtype=np.float32)
        pad[:, :, 0:resized_w] = resized
        return pad

    def _recognize(self, img_list):
        """خروجی: [(text, score), ...] به تعدادِ ورودی (CTC greedy)."""
        n = len(img_list)
        res = [("", 0.0)] * n
        width_list = [im.shape[1] / float(im.shape[0]) for im in img_list]
        indices = np.argsort(np.array(width_list))
        _, img_h, img_w = self.rec_img_shape
        for beg in range(0, n, self.rec_batch_num):
            end = min(n, beg + self.rec_batch_num)
            max_wh_ratio = img_w / float(img_h)
            for ino in range(beg, end):
                h, w = img_list[indices[ino]].shape[:2]
                max_wh_ratio = max(max_wh_ratio, w * 1.0 / h)
            batch_w = int(img_h * max_wh_ratio)
            batch = np.concatenate([
                self._resize_norm(img_list[indices[ino]], batch_w)[np.newaxis]
                for ino in range(beg, end)]).astype(np.float32)
            preds = self.rec(batch)
            preds_idx = preds.argmax(axis=2)
            preds_prob = preds.max(axis=2)
            for rno in range(preds_idx.shape[0]):
                tokens = preds_idx[rno]
                probs = preds_prob[rno]
                sel = np.ones(len(tokens), dtype=bool)
                sel[1:] = tokens[1:] != tokens[:-1]
                sel &= tokens != 0  # blank
                chars = [self.character[t] for t in tokens[sel]]
                text = "".join(chars)
                conf = float(np.mean(probs[sel])) if sel.any() else 0.0
                res[indices[beg + rno]] = (text, round(conf, 5))
        return res

    # ─────────────────────────── API ───────────────────────────

    @staticmethod
    def _get_rotate_crop(img: np.ndarray, points: np.ndarray) -> np.ndarray:
        """عینِ get_rotate_crop_image (پرسپکتیو + چرخشِ خطِ عمودی)."""
        pts = np.asarray(points, dtype=np.float32)
        w = int(np.linalg.norm(pts[0] - pts[1]))
        h = int(np.linalg.norm(pts[0] - pts[3]))
        if w < 1 or h < 1:
            return img
        std = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        m = cv2.getPerspectiveTransform(pts, std)
        crop = cv2.warpPerspective(
            img, m, (w, h),
            borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_CUBIC)
        if crop.shape[0] * 1.0 / max(1, crop.shape[1]) >= 1.5:
            crop = np.rot90(crop)
        return crop

    def _within_bounds(self, img: np.ndarray):
        """عینِ preprocess_img: max_side≤2000، min_side≥30 → (img, rh, rw)
        که ضربِ مختصات در (rh, rw) به تصویرِ اصلی برمیگردد. رزایزها
        به مضربِ ۳۲ گرد میشوند (عینِ reduce/increase_max_side)."""
        h, w = img.shape[:2]
        if max(h, w) > 2000:
            ratio = 2000.0 / max(h, w)
            resize_h = int(round((int(h * ratio)) / 32) * 32)
            resize_w = int(round((int(w * ratio)) / 32) * 32)
            if resize_w <= 0 or resize_h <= 0:
                raise ValueError("resize نامعتبر")
            img = cv2.resize(img, (resize_w, resize_h))
        if min(img.shape[:2]) < 30:
            h2, w2 = img.shape[:2]
            ratio2 = 30.0 / min(h2, w2)
            resize_h = int(round((int(h2 * ratio2)) / 32) * 32)
            resize_w = int(round((int(w2 * ratio2)) / 32) * 32)
            if resize_w <= 0 or resize_h <= 0:
                raise ValueError("resize نامعتبر")
            img = cv2.resize(img, (resize_w, resize_h))
        rh = h / float(img.shape[0])
        rw = w / float(img.shape[1])
        return img, rh, rw

    def _prep_work(self, image_bgr: np.ndarray):
        """v1.14.165 — آمادهسازیِ مشترکِ _ocr_impl/نردبان: bounds-resize + pad.
        خروجی: (work, rh, rw, pad_top)."""
        work, rh, rw = self._within_bounds(image_bgr)
        pad_top = 0
        h, w = work.shape[:2]
        if (w / float(max(1, h)) > 8.0) or h <= 30:
            new_h = max(int(w / 8.0), 30) * 2
            pad_top = int(abs(new_h - h) / 2)
            work = cv2.copyMakeBorder(
                work, pad_top, pad_top, 0, 0,
                cv2.BORDER_CONSTANT, value=(0, 0, 0))
        return work, rh, rw, pad_top

    def _rec_lines(self, dets, work, rh, rw, pad_top,
                   ori_h: int, ori_w: int):
        """v1.14.165 — crop + rec + فیلتر + map (نیمهٔ دومِ _ocr_impl)
        تا نردبانِ K3 بتواند در تلاشِ دوم فقط rec را صدا بزند.
        خروجی: [ [box, (text, score)], ... ] یا None."""
        if not dets:
            return None
        crops = [self._get_rotate_crop(work, b) for b, _s in dets]
        recs = self._recognize(crops)
        lines = []
        for (box, _ds), (text, rscore) in zip(dets, recs):
            if not text.strip() or rscore < self.text_score:
                continue
            bx = np.asarray(box, dtype=np.float32).copy()
            bx[:, 1] -= pad_top
            bx[:, 0] *= rw
            bx[:, 1] *= rh
            bx[:, 0] = np.clip(bx[:, 0], 0, ori_w)
            bx[:, 1] = np.clip(bx[:, 1], 0, ori_h)
            lines.append([bx, (text, float(rscore))])
        return [lines] if lines else None

    def _detect_or_pred(self, work, crop_mode: bool = False, det_cap=None):
        """det + دورِ دومِ آستانهٔ باز (v1.14.155) رویِ همان pred."""
        dets, pred = self._detect(work, crop_mode=crop_mode, det_cap=det_cap)
        if not dets and pred is not None:
            dets = self._boxes_from_pred(
                pred, work.shape[0], work.shape[1],
                thresh=max(0.15, self.thresh - 0.15),
                box_thresh=max(0.30, self.box_thresh - 0.20),
                unclip_ratio=self.unclip_ratio + 0.4)
        return dets

    def _ocr_impl(self, image_bgr: np.ndarray, crop_mode: bool = False,
            det_cap=None):
        """خروجی: [ [box, (text, score)], ... ] یا None (خالی).

        خطِ کاملِ rapidocr: bounds-resize → vertical-padding → det →
        crop → rec → فیلترِ text_score → mapِ باکسها به تصویرِ اصلی.
        v1.14.125 — crop_mode=True: detِ بدونِ بزرگنمایی با سقفِ det_cap
        (برشِ کاسکاد؛ ورودیِ کوچک = سریع، مثلِ K3).
        v1.14.165 — بازنویسی رویِ _prep_work/_detect_or_pred/_rec_lines
        (رفتار بیت‌به‌بیت)."""
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        ori_h, ori_w = image_bgr.shape[:2]
        work, rh, rw, pad_top = self._prep_work(image_bgr)
        dets = self._detect_or_pred(work, crop_mode=crop_mode,
                                    det_cap=det_cap)
        if not dets:
            return None
        return self._rec_lines(dets, work, rh, rw, pad_top, ori_h, ori_w)

    def ocr(self, image_bgr: np.ndarray, crop_mode: bool = False,
            det_cap=None):
        """v1.14.174 — پوشِ نقطهٔ ورود: یک کراپِ کامل که بدونِ کرش تا
        نتیجه برسد → نشانِ «کرشِ احتمالیِ NNAPI» (.ep_nnapi_last) پاک
        میشود؛ NNAPIِ سالم همیشه میماند. خودِ نردبان = _ocr_k3
        (عینِ ocrِ قبلی — بیت‌به‌بیت)."""
        _r = self._ocr_k3(image_bgr, crop_mode=crop_mode, det_cap=det_cap)
        _nnapi_guard_clear()
        return _r

    def _ocr_k3(self, image_bgr: np.ndarray, crop_mode: bool = False,
                det_cap=None):
        """v1.14.157 — نردبانِ K3 رویِ هر کراپ: برشِ کوچک اول با نسخهٔ
        ارتقایافته (×۲+unsharp تا سقفِ det_cap)؛ اطمینانِ <0.80 یا خالی
        → یک تلاشِ ارتقایافتهٔ دیگر؛ برنده = خطِ بیشتر/اطمینانِ بالاتر.
        PC/امولاتورِ x86_64 (CI) = مستقیمِ _ocr_impl (بیت‌به‌بیت)."""
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        if (not crop_mode) or (not _k3_on()):
            return self._ocr_impl(image_bgr, crop_mode=crop_mode,
                                  det_cap=det_cap)
        _h, _w = image_bgr.shape[:2]
        _ori_h, _ori_w = image_bgr.shape[:2]
        _s1 = _enh_scale_for(_w, _h, det_cap)
        _dets1 = None
        _prep1 = None
        if _s1 > 1.0:
            _r1 = _rescale_res(self._ocr_impl(
                _enhance_crop(image_bgr, _s1), True, det_cap), 1.0 / _s1)
        else:
            # v1.14.165 — قطعاتِ پاسِ اول نگه داشته میشوند تا تلاشِ دوم
            # فقط rec باشد (detِ گرانِ دوباره حذف — همان باکسها، rec روی
            # کراپِ واضحتر = اطمینانِ بالاتر؛ دقیقاً هدفِ «افزایشِ کیفیتِ
            # کراپ» در دستورِ K3).
            _work1, _rh1, _rw1, _pt1 = self._prep_work(image_bgr)
            _prep1 = (_rh1, _rw1, _pt1)
            _dets1 = self._detect_or_pred(_work1, crop_mode=True,
                                          det_cap=det_cap)
            _r1 = self._rec_lines(_dets1, _work1, _rh1, _rw1, _pt1,
                                  _ori_h, _ori_w) if _dets1 else None
        if not _low_quality(_r1):
            return _r1
        if _s1 > 1.0:
            return _r1  # اول هم ارتقایافته بود - تکرار بیفایده
        # تلاشِ ارتقایافته — عینِ پلهٔ بعدیِ نردبانِ K3 (زیرِ ۸۰٪ → بعدی)
        _s2 = _enh_scale_for(_w, _h, det_cap)
        if _s2 <= 1.0:
            _cap = det_cap if det_cap else 960
            _s2 = 2.0 if max(_w, _h) * 2.0 <= _cap else \
                _cap / float(max(_w, _h))
            if _s2 <= 1.05:
                return _r1  # برشِ درشتِ کماطمینان — ارتقا در سقف جا نمیشود
        _big = _enhance_crop(image_bgr, _s2)
        if _dets1:
            # v1.14.165 — فقط rec: باکسهایِ detِ پاسِ اول از مختصاتِ کارِ
            # پاسِ اول به مختصاتِ کارِ کراپِ ارتقایافته میرود.
            _rh1, _rw1, _pt1 = _prep1
            _work2, _rh2, _rw2, _pt2 = self._prep_work(_big)
            _h2, _w2 = _work2.shape[:2]
            _d2 = []
            for _b, _sc in _dets1:
                try:
                    _bb = np.asarray(_b, dtype=np.float32).copy()
                    _bb[:, 0] = (_bb[:, 0] * _rw1) / max(1e-6, _rw2)
                    _bb[:, 1] = ((_bb[:, 1] - _pt1) * _rh1) \
                        / max(1e-6, _rh2) + _pt2
                    _bb[:, 0] = np.clip(_bb[:, 0], 0, _w2 - 1)
                    _bb[:, 1] = np.clip(_bb[:, 1], 0, _h2 - 1)
                    _d2.append((_bb, _sc))
                except Exception:
                    continue
            _r2 = None
            if _d2:
                _r2 = _rescale_res(
                    self._rec_lines(_d2, _work2, _rh2, _rw2, _pt2,
                                    _big.shape[0], _big.shape[1]),
                    1.0 / _s2)
            if _r2 is None:
                # rec فقط چیزی نداد (باکسهایِ پاسِ اول بینتیجه بودند)
                # → فالبکِ کاملِ det+rec رویِ ارتقایافته (رفتارِ قبل).
                _r2 = _rescale_res(self._ocr_impl(_big, True, det_cap),
                                   1.0 / _s2)
        else:
            # پاسِ اول اصلاً باکس نداشت → detِ کامل رویِ ارتقایافته.
            _r2 = _rescale_res(self._ocr_impl(_big, True, det_cap),
                               1.0 / _s2)
        if not _K3_NOTE_157["retry"]:
            print("[⚡] کاسکادِ K3: "
                  "کراپِ کماطمینان "
                  "→ تلاشِ ارتقایافته "
                  "(×" + ("%.1f" % _s2) + ")")
            _K3_NOTE_157["retry"] = True
        return _better_res(_r1, _r2)

# ────────── v1.14.157 — دستورِ سازندهٔ K3 (روایتی از خودِ آنها) ──────────
# «اول با RT-DETR در سطح بلوک متنها رو تشخیص میدم. اونا رو کراپ میکنم…
# بعد از افزایشِ کیفیتِ کراپ… اگر درصدِ اطمینان زیر ۸۰ بود [موتورِ
# بعدی]… نکته این است که فقط باید در سطحِ کراپ کار کنی نه رویِ تمام
# صفحه — رویِ گوشی خیلی خیلی مهمه.»
# سهمِ ما: بلوک = برشِ امنِ ML Kit ✓ (کاسکادِ 1.14.124)؛ استخراجِ نهایی
# همچنان فقط PP-OCRv6 (قانونِ «ML Kit هرگز استخراج نمیکند»). چیزِ
# نبود: ① افزایشِ کیفیتِ کراپ ② نردبانِ اطمینانِ هر کراپ. اینجا اضافه
# میشود؛ فقط رویِ گوشیِ واقعی (CI/امولاتور بیت‌به‌بیتِ قبل).

_K3_NOTE_157 = {"retry": False}


def _k3_on() -> bool:
    """دستورِ K3 فقط رویِ گوشیِ واقعی؛ PC/امولاتورِ x86_64 = قبل."""
    try:
        if str(os.environ.get("MANGA_CROP_K3", "1") or "1").strip() == "0":
            return False
        return bool(_android_env()) and not _x86_machine()
    except Exception:
        return False


def _enh_scale_for(w: int, h: int, det_cap) -> float:
    """① «افزایش کیفیت کراپ»: برشِ کوچک ×۲ تا سقفِ det_cap — متنِ ریز
    که det/recِ 1:1 جا میاندازد. برشِ درشت = 1.0 (سرعت)."""
    try:
        _mn = float(os.environ.get("MANGA_CROP_ENH_MIN", "256") or 256)
    except Exception:
        _mn = 256.0
    if min(int(w), int(h)) >= _mn:
        return 1.0
    try:
        _s = float(os.environ.get("MANGA_CROP_ENH_SCALE", "2") or 2)
    except Exception:
        _s = 2.0
    _s = max(1.0, min(3.0, _s))
    try:
        _cap = int(det_cap) if det_cap else 960
    except Exception:
        _cap = 960
    if max(int(w), int(h)) * _s > _cap:
        _s = _cap / float(max(int(w), int(h)))
    return _s if _s > 1.05 else 1.0


def _enhance_crop(img: np.ndarray, sc: float) -> np.ndarray:
    """×۲ LANCZOS + unsharp (1.5/-0.5) — معادلِ سبکِ «افزایش کیفیت
    کراپ»ِ K3 (آنها Waifu2x داشتند؛ اینجا بدونِ مدلِ اضافه)."""
    _h, _w = img.shape[:2]
    big = cv2.resize(img, (max(1, int(round(_w * sc))),
                           max(1, int(round(_h * sc)))),
                     interpolation=cv2.INTER_LANCZOS4)
    try:
        _bl = cv2.GaussianBlur(big, (0, 0), 1.0)
        big = cv2.addWeighted(big, 1.5, _bl, -0.5, 0)
    except Exception:
        pass
    return big


def _lines_quality(res):
    """(n, mean_score) — سنجهٔ نردبانِ اطمینانِ K3."""
    if not res or not res[0]:
        return 0, 0.0
    _ls = res[0]
    try:
        return len(_ls), sum(float(p[1]) for _b, p in _ls) / max(1, len(_ls))
    except Exception:
        return len(_ls), 0.0


def _low_quality(res) -> bool:
    """«اگه درصدِ اطمینان زیر ۸۰ بود [موتورِ بعدی]» — خالی هم مردود."""
    try:
        _rs = float(os.environ.get("MANGA_CROP_RETRY_SCORE", "0.80") or 0.80)
    except Exception:
        _rs = 0.80
    _n, _sc = _lines_quality(res)
    return (_n == 0) or (_sc < _rs)


def _rescale_res(res, k: float):
    """باکسها از مختصاتِ برشِ ارتقایافته به کراپِ اصلی."""
    if (not res) or (not res[0]) or k >= 0.999999:
        return res
    _out = []
    for _b, _p in res[0]:
        try:
            _bb = np.asarray(_b, dtype=np.float32).copy() * float(k)
        except Exception:
            continue
        _out.append([_bb, _p])
    return [_out] if _out else None


def _better_res(a, b):
    """برنده = خطِ بیشتر؛ مساوی → اطمینانِ بالاتر (b = تلاشِ ارتقایافته)."""
    _an = len(a[0]) if a and a[0] else 0
    _bn = len(b[0]) if b and b[0] else 0
    if _bn != _an:
        return b if _bn > _an else a
    return b if _lines_quality(b)[1] >= _lines_quality(a)[1] else a

