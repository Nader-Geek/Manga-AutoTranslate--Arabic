# BUILD-STRIP-START
# نصب — وابستگیها، pip، تشخیص GPU + وضعیتِ توقف و پرچمهای کتابخانهها
# نصبِ خودکارِ وابستگیها (_ensure_all_dependencies و زنجیرهٔ pip) + REQUEST_STOP/JobCancelled و پرچمهای _HAS_GEMINI/_HAS_OPENAI/… .
# (این سربرگ فقط راهنمای همین فایل است؛ لودرِ manga.py و بیلد حذفش میکنند)
# BUILD-STRIP-END
def _pip_install(*packages: str) -> bool:
    if not packages:
        return True
    cmd = [sys.executable, "-m", "pip", "install", "-q", "--prefer-binary", *packages]
    print(f"[*] نصب: {' '.join(packages)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "")[-800:]
            print(f"    [!] ناموفق: {err}")
            return False
        return True
    except Exception as e:
        print(f"    [!] خطا: {e}")
        return False

def _pip_uninstall(*packages: str) -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", *packages],
            capture_output=True,
            timeout=180,
        )
    except Exception:
        pass

def _can_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:
        return False

def _nvidia_gpu_present() -> bool:
    try:
        import torch
        if torch.cuda.is_available():
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=8)
        if r.returncode == 0 and b"GPU" in (r.stdout or b""):
            return True
    except Exception:
        pass
    try:
        if os.path.exists("/dev/nvidia0") or os.path.exists("/dev/nvidiactl"):
            return True
    except Exception:
        return False
# ویندوزِ بدونِ nvidia-smi در PATH (نصبِ درایورِ استودیو یا
# PATHِ ناقصِ پایتون): همان پرسوجویِ wmic/powershellِ DirectML حالا
# NVIDIA را هم میبیند — گرایندهٔ «GPU صفر درصد» وقتی کارت هست ولی
# مسیرِ auto هیچوقت onnxruntime-gpu را نمیگرفت.
    try:
        if _platform.system().lower() == "windows":
            for _cmd in (
                ["wmic", "path", "win32_VideoController", "get", "name"],
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance win32_VideoController).Name"],
            ):
                try:
                    r = subprocess.run(_cmd, capture_output=True, text=True,
                                       timeout=12)
                    if r.returncode == 0 and "nvidia" in (r.stdout or "").lower():
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False

_DIRECTX_GPU_CACHE = None  # None = هنوز پروب نشده؛ True/False = کشِ نتیجه

def _directx_gpu_present() -> bool:
    """ — هر GPU-capable (AMD/Intel/گرافیکِ یکپارچه) رویِ ویندوز:
    برایِ DirectML. فقط ویندوز؛ لینوکس DirectML ندارد.
     — با
    RX 5700 XT — ریشه: wmic در ویندوزهایِ جدید (۲۴H۲+) حذف/خالی است و
    پاورشل هم گاهی جوابِ خالی میداد → تشخیصِ «GPU ویندوزی» False میشد و
    onnxruntime-directml هیچ‌وقت نصب نمیشد. حالا ۴ روشِ مستقل به‌ترتیب
    امتحان میشوند و اگر «هر کدام» نامِ یک کارتِ گرافیک بدهد کافی است:
    (۱) wmic، (۲) پاورشلِ Get-CimInstance، (۳) پاورشلِ Get-PnpDevice،
    (۴) رجیستریِ کلاسِ Display (بدونِ WMI — سریع‌ترین و مطمئن‌ترین).
    نتیجه در حافظهٔ ماژول کش میشود (پروبِ مکررِ کند حذف شد)."""
    global _DIRECTX_GPU_CACHE
    if _DIRECTX_GPU_CACHE is not None:
        return _DIRECTX_GPU_CACHE
    if _platform.system().lower() != "windows":
        _DIRECTX_GPU_CACHE = False
        return False

    def _names_to_bool(txt: str, have_header: bool) -> bool:
        low = (txt or "").lower()
        if not low.strip():
            return False
        hit = any(t in low for t in ("gpu", "radeon", "nvidia", "geforce",
                                     "intel", "arc", "graphics", "display"))
        if hit:
            return True
# خروجیِ فقط-سرستون (wmicِ ویندوزهایِ خراب) → None = نامشخص
        return bool(have_header and "videocontroller" in low)

# (۱) wmic — در ویندوزهایِ قدیمی سریع است
    try:
        r = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            res = _names_to_bool(r.stdout or "", have_header=True)
            if res:
                _DIRECTX_GPU_CACHE = True
                return True
    except Exception:
        pass
# (۲) پاورشل — Get-CimInstance
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance win32_VideoController).Name"],
            capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and (r.stdout or "").strip() \
                and _names_to_bool(r.stdout or "", have_header=False):
            _DIRECTX_GPU_CACHE = True
            return True
    except Exception:
        pass
# (۳) پاورشل — Get-PnpDevice (بدونِ وابستگی به WMI-ویدئو)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-PnpDevice -Class Display -Status OK).FriendlyName"],
            capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and (r.stdout or "").strip() \
                and _names_to_bool(r.stdout or "", have_header=False):
            _DIRECTX_GPU_CACHE = True
            return True
    except Exception:
        pass
# (۴) رجیستری — کلاسِ Display_ADAPTERS؛ بدونِ WMI/پاورشل همیشه هست
    try:
        r = subprocess.run(
            ["reg", "query",
             r"HKLM\SYSTEM\CurrentControlSet\Control\Class"
             r"\{4d36e968-e325-11ce-bfc1-08002be10318}", "/s", "/v", "DriverDesc"],
            capture_output=True, text=True, timeout=12)
        if r.returncode == 0 and _names_to_bool(r.stdout or "",
                                                have_header=False):
            _DIRECTX_GPU_CACHE = True
            return True
    except Exception:
        pass
    _DIRECTX_GPU_CACHE = False
    return False

def _ort_has_cuda() -> bool:
    try:
        import onnxruntime as _ort
        return "CUDAExecutionProvider" in _ort.get_available_providers()
    except Exception:
        return False

def _ort_has_dml() -> bool:
    """ — بیلدِ DirectML (پکیجِ onnxruntime-directml) نصب است؟
    برایِ کارت‌هایِ AMD/Intel رویِ ویندوز (CUDA که مالِ NVIDIA است؛ مسیرِ
    درستِ AMD رویِ ویندوز DirectML است)."""
    try:
        import onnxruntime as _ort
        return "DmlExecutionProvider" in _ort.get_available_providers()
    except Exception:
        return False

def _parallel_budget(kind: str = "ocr") -> int:
    """ — بودجهٔ موازیِ سیستم: چند ناحیهٔ متن همزمان کار کنند.

    .

    ورودی: cpu (os.cpu_count) + ramِ آزاد (/proc/meminfo؛ ویندوز:
    GlobalMemoryStatusEx) + gpu (CUDAِ onnxruntime). سقفِ عقلانی:
      • OCR — اندروید: cpu÷2 (سقف ۴؛ هر predictor پدل ۲ نخ؛ جمع ≈ همهٔ
        هسته‌ها)؛ PC/لینوکس: cpu−1 (سقف ۸) + ۱ اگر CUDA.
      • پاکسازی — cpu−1 (سقف ۸) رویِ همهٔ پلتفرم‌ها + ۱ اگر CUDA
        (پرکننده‌هایِ تخت/رنگیِ cv2 فقط CPUاند؛ LaMa خودش موازی است).
      • RAMِ آزادِ کم: ‎<1.2GB → ۲ کارگر، ‎<2.5GB → ۳ کارگر.
    override دستی: MANGA_REGION_WORKERS=N (هر دو)؛ MANGA_OCR_WORKERS
    (فقط OCR، مثلِ قبل) و MANGA_LAMA_WORKERS (فقط LaMa، مثلِ قبل)."""
    try:
        cpu = os.cpu_count() or 4
    except Exception:
        cpu = 4
# RAMِ آزاد
    ram_gb = 0.0
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    ram_gb = int(line.split()[1]) / (1024 * 1024)
                    break
    except Exception:
        pass
    if ram_gb <= 0.0 and os.name == "nt":
        try:
            import ctypes
            class _MSE(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong)]
            st = _MSE()
            st.dwLength = ctypes.sizeof(_MSE)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(
                    ctypes.byref(st)):
                ram_gb = st.ullAvailPhys / (1024 ** 3)
        except Exception:
            pass
    if ram_gb <= 0.0:
        try:
            import psutil as _ps
            ram_gb = float(_ps.virtual_memory().available) / (1024 ** 3)
        except Exception:
            pass
    try:
        _env = int(os.environ.get("MANGA_REGION_WORKERS", "0") or 0)
    except Exception:
        _env = 0
    if _env > 0:
        return max(1, min(8, _env))
    try:
# DirectML (AMD/Intel ویندوز) هم مثلِ CUDA یک نفرِ
# اضافهٔ موازی میگیرد
        _gpu = (not _IS_ANDROID) and (_ort_has_cuda() or _ort_has_dml())
    except Exception:
        _gpu = False
    if kind == "clean":
        base = max(2, min(8, cpu - 1))
        if _gpu:
            base += 1
    else:
        if _IS_ANDROID:
            base = max(2, min(4, cpu // 2))
        else:
            base = max(2, min(8, cpu - 1))
            if _gpu:
                base += 1
    if ram_gb > 0.0:
        if ram_gb < 1.2:
            base = min(base, 2)
        elif ram_gb < 2.5:
            base = min(base, 3)
    return max(1, base)

def _torch_available() -> bool:
    try:
        import torch
        return True
    except Exception:
        return False

def _ensure_rapidocr_pkg() -> bool:
    """موتور OCR سبک ONNX (rapidocr) را فقط اگر واقعاً لازم باشد نصب می‌کند.
    : دیگر در شروع برنامه نصب نمی‌شود — فقط وقتی موتور ONNX لود می‌شود."""
    if _can_import("rapidocr") or _can_import("rapidocr_onnxruntime"):
        return True
    if _IS_ANDROID:
        return False
    print("[*] نصب rapidocr (موتور OCR سبک ONNX) — فقط بار اول ...")
    if _pip_install("rapidocr"):
        return True
    if _can_import("rapidocr_onnxruntime"):
        return True
    return _pip_install("rapidocr-onnxruntime")

def _ensure_torch_cpu() -> bool:
    """torch را فقط برای روش پاکسازی lama-big نصب می‌کند (بار اول، ~۲۰۰MB).
    : نصب torch از شروع برنامه به همین نقطه منتقل شد."""
    if _torch_available():
        return True
    if _IS_ANDROID:
        return False
    print("[*] نصب torch CPU برای big-lama.pt — فقط بار اول (~۲۰۰MB) ...")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
             "torch", "--index-url", "https://download.pytorch.org/whl/cpu"],
            capture_output=True, text=True, timeout=1800)
        ok = (r.returncode == 0)
    except Exception as e:
        print(f"    [!] {e}")
        ok = False
    if not ok:
        print("    [!] torch CPU ناموفق → pip معمولی ...")
        ok = _pip_install("torch")
    if ok:
        print("[+] torch نصب شد → پاک‌سازی big-lama.pt فعال می‌شود.")
    else:
        print("[!] torch نصب نشد → پاک‌سازی با lama.onnx ادامه می‌دهد.")
    return ok
try:
    import java
    _IS_ANDROID = True
except Exception:
    _IS_ANDROID = False

def _ensure_all_dependencies() -> None:
    if _IS_ANDROID:
        print("[*] اندروید: وابستگی‌ها داخل APK موجود است — بررسی pip رد شد.")
        return
    print("[*] بررسی وابستگی‌ها ...")
    core = []
    if not _can_import("numpy"):
        core.append("numpy")
    cv2_ok = _can_import("cv2")
    if not cv2_ok and sys.platform.startswith("linux"):

        _pip_uninstall("opencv-python", "opencv-contrib-python")
    if not cv2_ok:
        core.append("opencv-python-headless>=4.8,<5")
    if not _can_import("PIL"):
        core.append("Pillow")
    if core:
        _pip_install(*core)

    if sys.platform.startswith("linux") and not _can_import("cv2"):

        print("[*] cv2 هنوز لود نمی‌شود → نصب libgl1 ...")
        for cmd in (
            ["sudo", "-n", "apt-get", "install", "-y", "libgl1", "libglib2.0-0"],
            ["apt-get", "install", "-y", "libgl1", "libglib2.0-0"],
        ):
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=300)
                if r.returncode == 0:
                    break
            except Exception:
                continue
        if not _can_import("cv2"):
            _pip_install("opencv-python-headless==4.10.0.84")

    text_pkgs = []
    if not _can_import("arabic_reshaper"):
        text_pkgs.append("arabic-reshaper")
    if not _can_import("bidi"):
        text_pkgs.append("python-bidi")
    if text_pkgs:
        _pip_install(*text_pkgs)

    misc = []
    if not _can_import("huggingface_hub"):
        misc.append("huggingface_hub")
    if not _can_import("requests"):
        misc.append("requests")
    if not _can_import("bs4"):
        misc.append("beautifulsoup4")
    if not _can_import("yaml"):
        misc.append("pyyaml")
    if not _can_import("tqdm"):
        misc.append("tqdm")
    if not (_can_import("pymupdf") or _can_import("fitz")):
        if not _IS_ANDROID:
            misc.append("pymupdf")
    if misc:
        _pip_install(*misc)

# rapidocr / paddleocr / torch دیگر در شروع نصب نمی‌شوند.
# paddleocr هیچ‌وقت خودکار نصب نمی‌شود (سنگین است؛ OCR سبک ONNX داریم)
# rapidocr فقط وقتی نصب می‌شود که موتور OCR ONNX واقعاً لود شود
# torch فقط وقتی نصب می‌شود که روش پاکسازی lama-big انتخاب شده باشد
    if not _IS_ANDROID:
        if not _can_import("google.genai") and not _can_import("google.generativeai"):
            _pip_install("google-genai")

        if not _can_import("openai"):
            _pip_install("openai")

    import platform as _platform

    want_gpu = _nvidia_gpu_present()
    has_ort = _can_import("onnxruntime")
    has_cuda = _ort_has_cuda() if has_ort else False

    _is_windows = _platform.system().lower() == "windows"
    _has_dml = False
    if has_ort:
        try:
            import onnxruntime as _ort
            _has_dml = "DmlExecutionProvider" in _ort.get_available_providers()
        except Exception:
            _has_dml = False
# GPU-capable رویِ ویندوز (حتی AMD/Intel) ولی بدونِ CUDA:
# خودکار onnxruntime-directml نصب شود (DirectML رویِ همهٔ DirectX12
# کار می‌کند) تا LaMa رویِ GPU برود؛ CPU به‌عنوانِ فال‌بک.
    _need_dml = (_is_windows and not want_gpu and not _has_dml
                 and _directx_gpu_present())

    def _torch_cuda_ver() -> str:
        try:
            import torch
            return str(getattr(torch.version, "cuda", None) or "")
        except Exception:
            return ""

    def _cuda_major() -> int:
        ver = _torch_cuda_ver()
        try:
            return int(ver.split(".")[0])
        except Exception:
            return 0

    def _clear_ort_modules() -> None:
        for name in list(sys.modules):
            if name == "onnxruntime" or name.startswith("onnxruntime."):
                del sys.modules[name]

    def _ort_prepare_cuda() -> bool:
        try:
            import torch
        except Exception:
            pass
        try:
            import onnxruntime as _ort
            if hasattr(_ort, "preload_dlls"):
                try:
                    _ort.preload_dlls()
                except Exception:
                    pass
            prov = list(_ort.get_available_providers())
            ok = "CUDAExecutionProvider" in prov
            print(f"    providers: {prov}")
            return ok
        except Exception as e:
            print(f"    [!] import ort: {e}")
            return False

    def _install_ort_cpu() -> None:
        if _can_import("onnxruntime"):
            print("[*] onnxruntime از قبل هست (CPU یا GPU).")
            return
        print("[*] نصب onnxruntime (CPU) ...")
        _pip_install("onnxruntime")

    def _install_ort_gpu() -> str:
        if _platform.system().lower() == "darwin":
            print("[*] macOS → فقط CPU")
            return "fail"

        major = _cuda_major()
        ver = _torch_cuda_ver() or "?"
        print(f"[*] GPU پیدا شد (CUDA={ver} | OS={_platform.system()}) → onnxruntime-gpu ...")
        _pip_uninstall("onnxruntime", "onnxruntime-gpu")

        ok_pip = False
        if major >= 13:
            print("[*] CUDA 13+ → ort-cuda-13-nightly")
            cmd = [
                sys.executable, "-m", "pip", "install", "-q", "--prefer-binary", "--pre",
                "--index-url",
                "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/ort-cuda-13-nightly/pypi/simple/",
                "onnxruntime-gpu",
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                ok_pip = r.returncode == 0
                if not ok_pip:
                    print("    [!] nightly ناموفق → PyPI onnxruntime-gpu")
                    ok_pip = _pip_install("onnxruntime-gpu")
            except Exception as e:
                print(f"    [!] {e}")
                ok_pip = _pip_install("onnxruntime-gpu")
        elif major == 12 or major == 0:
            print("[*] CUDA 12 → onnxruntime-gpu==1.26.0 (+ cuda/cudnn runtime)")
            ok_pip = _pip_install("onnxruntime-gpu==1.26.0")
            if not ok_pip:
                for pkg in ("onnxruntime-gpu==1.25.1", "onnxruntime-gpu==1.22.0"):
                    print(f"    fallback: {pkg}")
                    if _pip_install(pkg):
                        ok_pip = True
                        break
            if ok_pip:
                if not _pip_install("onnxruntime-gpu[cuda,cudnn]==1.26.0"):
                    _pip_install(
                        "nvidia-cublas-cu12",
                        "nvidia-cudnn-cu12",
                        "nvidia-cuda-runtime-cu12",
                        "nvidia-cufft-cu12",
                        "nvidia-curand-cu12",
                    )
        elif major == 11:
            print("[*] CUDA 11 → feed cuda-11")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
                 "coloredlogs", "flatbuffers", "numpy", "packaging", "protobuf", "sympy"],
                capture_output=True, timeout=300,
            )
            cmd = [
                sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
                "onnxruntime-gpu",
                "--index-url",
                "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/",
            ]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                ok_pip = r.returncode == 0
            except Exception:
                ok_pip = False
            if not ok_pip:
                ok_pip = _pip_install("onnxruntime-gpu==1.18.1")
        else:
            ok_pip = _pip_install("onnxruntime-gpu")

        if not ok_pip:
            return "fail"

        _clear_ort_modules()
        if _ort_prepare_cuda():
            print("[+] onnxruntime-gpu با CUDAExecutionProvider آماده است.")
            return "cuda"

        print(
            "[!] CUDA EP الان در providers نیست. "
            "بستهٔ GPU نگه داشته می‌شود؛ یک‌بار Restart session بزن یا ادامه با CPU provider."
        )
        return "cpu"

    if want_gpu:
        major = _cuda_major()
        need_repin = False
        if has_cuda and major == 12:
            try:
                import onnxruntime as _ort
                ov = getattr(_ort, "__version__", "") or ""
                parts = ov.split(".")
                if len(parts) >= 2 and int(parts[0]) == 1 and int(parts[1]) >= 27:
                    need_repin = True
                    print(f"[*] ORT {ov} برای CUDA13 است؛ سیستم CUDA12 → 1.26.0")
            except Exception:
                pass

        if has_cuda and not need_repin:
            print("[*] onnxruntime-gpu آماده (CUDA).")
            _ort_prepare_cuda()
        else:
            status = _install_ort_gpu()
            if status == "fail":
                _install_ort_cpu()
            elif status in ("cuda", "cpu"):
                if os.environ.get("_ORT_GPU_REEXEC") != "1":
                    print("[*] راه‌اندازی مجدد پروسه برای لود CUDA libs ...")
                    os.environ["_ORT_GPU_REEXEC"] = "1"
                    os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        if _need_dml:
# GPUِ ویندوزیِ غیرِ CUDA (AMD/Intel): DirectML
            print("[*] GPU (DirectML) رویِ ویندوز پیدا شد؛ نصبِ onnxruntime-directml ...")
            _pip_uninstall("onnxruntime", "onnxruntime-gpu")
            if _pip_install("onnxruntime-directml"):
                _clear_ort_modules()
                try:
                    import onnxruntime as _ort2
                    prov2 = list(_ort2.get_available_providers())
                    if "DmlExecutionProvider" in prov2:
                        if os.environ.get("_ORT_DML_REEXEC") != "1" and \
                                os.environ.get("_ORT_GPU_REEXEC") != "1":
                            print("[*] راه‌اندازیِ مجددِ پروسه برایِ بارگذاریِ DirectML DLLs ...")
                            os.environ["_ORT_DML_REEXEC"] = "1"
                            os.execv(sys.executable, [sys.executable] + sys.argv)
                    else:
                        print(f"    [!] DirectML در providers نیست ({prov2}) → CPU")
                except Exception as e:
                    print(f"    [!] import ort پسِ DML: {e} → CPU")
            else:
                print("    [!] نصبِ onnxruntime-directml ناموفق → onnxruntime (CPU)")
                _pip_install("onnxruntime")
        else:
            _install_ort_cpu()

    print("[+] بررسی وابستگی‌ها تمام شد.\n")

_ensure_all_dependencies()

import argparse
import copy
import json
import re
import shutil
import string
import time
import zipfile
import base64
import glob
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import threading
import random

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
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
