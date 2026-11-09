# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 حالتِ موتور — پرچمِ توقف (REQUEST_STOP)، JobCancelled و پرچمهای _HAS_*
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
REQUEST_STOP = False


class JobCancelled(Exception):
    """وقتی کاربر دکمهٔ لغو را می‌زند پرتاب می‌شود."""


def request_stop() -> None:
    global REQUEST_STOP
    REQUEST_STOP = True


def clear_stop() -> None:
    global REQUEST_STOP
    REQUEST_STOP = False


def stop_requested() -> bool:
    return bool(globals().get("REQUEST_STOP"))


def _raise_if_stop() -> None:
    """لغو فوری — در همهٔ حلقه‌های ریز (OCR/پاکسازی/ترجمه/رندر) چک می‌شود
    تا «لغو» بدون معطلی درجا عملی شود (درخواست کاربر)."""
    if stop_requested():
        raise JobCancelled("لغو توسط کاربر")


os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_onednn", "0")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    print("خطا: arabic-reshaper / python-bidi بعد از نصب خودکار هنوز نیستند.", file=sys.stderr)
    raise

_HAS_GEMINI = False
try:
    from google import genai
    from google.genai import types as genai_types
    from google.genai import errors as genai_errors
    _HAS_GEMINI = True
except ImportError:
    genai = None
    genai_types = None
    genai_errors = None

_HAS_OPENAI = False
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    OpenAI = None


_HAS_PADDLE = False
try:
    from paddleocr import PaddleOCR
    _HAS_PADDLE = True
except ImportError:
    PaddleOCR = None

_HAS_RAPIDOCR = False
try:
    from rapidocr_onnxruntime import RapidOCR
    _HAS_RAPIDOCR = True
except ImportError:
    RapidOCR = None


try:
    import onnxruntime as ort
    try:
        if hasattr(ort, "preload_dlls"):
            ort.preload_dlls()
    except Exception:
        pass
except ImportError:
    ort = None
    print("[!] onnxruntime در دسترس نیست — پاک‌سازی فقط با OpenCV.", file=sys.stderr)

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    hf_hub_download = None




