# BUILD-STRIP-START
# مدلها و سختافزار — ORT/CUDA/DML، LaMa، تشخیصِ متن، دانلودِ مدلها
# ساختِ sessionهای ONNX (DML/CUDA/CPU + کشها)، مدلهای LaMa (ONNX/Torch)، ردیابِ متن RTDetrV2 و دانلودِ آینهایِ مدلهای OCR.
# (این سربرگ فقط راهنمای همین فایل است؛ لودرِ manga.py و بیلد حذفش میکنند)
# BUILD-STRIP-END
def _sys_avail_ram_gb():
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for ln in f:
                if ln.startswith("MemAvailable"):
                    return float(ln.split()[1]) / (1024.0 * 1024.0)
    except Exception:
        pass
    return None

def _android_x86_emulator() -> bool:
    """-speed (SRV-G) — «امولاتورِ» واقعی: محیطِ اندروید + CPU
    x86_64. همان قراردادِ SRV-F: ANDROID_ROOT/ANDROID_DATA یا import java
    رویِ x86_64 → True (نخ = ۱). رویِ گوشیِ واقعیِ arm64 و PC همیشه
    False."""
    try:
        import platform as _pfx
        if _pfx.machine().lower() not in ("x86_64", "amd64"):
            return False
    except Exception:
        return False
    try:
        return bool(_on_android() or _android_like_env())
    except Exception:
        return False

_GPU_VENDOR_CACHE = None

def _cpu_ep_xnnpack() -> bool:
    """-speed (SRV-G) — A/Bِ XNNPACK: فقط با env
    MANGA_CPU_EP=xnnpack (پیش‌فرض: خاموش). سشن‌هایِ CPU-EP به‌جای
    CPU-Only از ["XnnpackExecutionProvider","CPUExecutionProvider"]
    می‌روند با کانفیگِ رسمی: ORT intra=1 + XNNPACK intra=هسته‌هایِ
    فیزیکی + spinning خاموش. رویِ اندروید/امولاتور اعمال نمی‌شود تا
    مسیرِ گوشی دست‌نخورده بماند."""
    try:
        if (os.environ.get("MANGA_CPU_EP", "").strip().lower()
                != "xnnpack"):
            return False
    except Exception:
        return False
    try:
        if _on_android() or _android_like_env():
            return False
    except Exception:
        pass
    return True

def _physical_core_count() -> int:
    """-speed (SRV-G) — هسته‌هایِ فیزیکی (برایِ XNNPACK
    threadpool). fallback: os.cpu_count()."""
    try:
        _phys = set()
        _pid = _cid = None
        with open("/proc/cpuinfo", "r", encoding="ascii", errors="ignore") as _f:
            for _ln in _f:
                _ln = _ln.strip()
                if _ln.startswith("physical id"):
                    _pid = _ln.split(":", 1)[1].strip()
                elif _ln.startswith("core id"):
                    _cid = _ln.split(":", 1)[1].strip()
                elif _ln.startswith("processor") and _ln.endswith(":") is False:
                    pass
                if _ln == "" and _pid is not None and _cid is not None:
                    _phys.add((_pid, _cid))
                    _pid = _cid = None
        if _phys:
            return max(1, len(_phys))
    except Exception:
        pass
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:
        return 1

def _ort_session_options(threads: int = 4, low_mem: Optional[bool] = None,
                         prefer_gpu: Optional[bool] = None):
    so = ort.SessionOptions()
    so.log_severity_level = 3
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
# speed — فیکسِ باگِ تک‌نخیِ x86_64: محدودیتِ «نخ=۱» فقط برایِ
# اندروید بود (ORT-androidِ x86_64 در زمان‌بندِ thread-pool تقسیم‌برِصفر
# /SIGFPE می‌دهد) ولی چون فقط machine را چک می‌کرد، رویِ «همهٔ»
# میزبان‌هایِ x86_64 (PC/سرورِ لینوکس/ویندوز) هم اعمال می‌شد → LaMa/
# دیتکتور/OCR رویِ PC تک‌نخ می‌شدند و چند برابر کند بودند. حالا فقط
# وقتی فعال است که واقعاً اندروید باشیم (Chaquopy یا نشانه‌هایِ محیطِ
# اندروید مثل /system/build.prop یا ANDROID_ROOT) و معماری x86_64
# (یعنی امولاتور).
# (SRV-H4) — بازگشتِ دقیق به معنایِ e32bccf: مقدارِ «پاس‌شده»
# (پیش‌فرضِ ۴) رویِ همهٔ میزبان‌هایِ غیرِ امولاتور استفاده می‌شود
# «۰ = ORT auto»یِ SRV-G رویِ سرور کندتر بود (SRV-H2: +30..+67٪ CPU)
# و حذف شد. امولاتورِ x86_64 همان قراردادِ SRV-F (intra=1).
# MANGA_ORT_THREADS=N همچنان اوررایدِ صریح دارد (اولاً بعد از cap1).
    _cap1 = _android_x86_emulator()
    _xnn = _cpu_ep_xnnpack()
    try:
        _env_t = int(os.environ.get("MANGA_ORT_THREADS", "0") or 0)
    except Exception:
        _env_t = 0
    if _cap1:
        threads = 1
    elif _env_t > 0:
        threads = _env_t
    elif _xnn:
# کانفیگِ رسمیِ XNNPACK (فقط MANGA_CPU_EP=xnnpack): threadpoolِ ORT
# تک‌نخی؛ XNNPACK خودش threadpoolِ هسته‌هایِ فیزیکی را می‌سازد.
        threads = 1
    else:
# speed (SRV-L) — هیوریستیکِ میزبان به‌جایِ مقدارِ ثابتِ
# «پاس‌شده»: رویِ PC/سرورِ واقعیِ x86_64 با ≥۸ هسته، برندهٔ سوییپِ
# SRV-K (t8: CPU ۳۲.۲s / GPU ۱۸.۷s) پیش‌فرضِ fastest-mode می‌شود
# رویِ میزبانِ ضعیف/کم‌هسته همان مقدارِ پاس‌شده (۴) می‌ماند.
# MANGA_ORT_THREADS همچنان اوررایدِ مطلق است (فقط cap1 امولاتور
# از آن بالاتر است).
# انحرافِ مستندشده از اسپک (SRV-L): رشتهٔ «gvisor» در
# uname.release دیگر سقفِ ۴ را رویِ میزبانِ بزرگ اعمال نمی‌کند —
# سرورِ ۲۰ هسته‌ایِ Azure هم «4.19.0-gvisor» گزارش می‌کند (SRV-K
# آن را با AVX512 «بدونِ gVisor» تشخیص داده بود) و سوییپِ خودِ
# همان میزبان t8 را برنده داد؛ در داده‌هایِ میزبانِ قبلیِ gVisor
# هم CPU با ۸ نخ بهتر بود (SRV-H3: c8nb 34.8s در برابرِ c4nb
# 39.0s). گاردِ میزبانِ ضعیف، شرطِ «≥۸ هسته» است (میزبان‌هایِ
# gVisorِ کوچک/CI → همان ۴).
        try:
            import platform as _pfl
            _m_l = _pfl.machine().lower() in ("x86_64", "amd64")
            _gv_l = "gvisor" in (os.uname().release.lower()
                                 if hasattr(os, "uname") else "")
            if _m_l and (os.cpu_count() or 4) >= 8:
                threads = 8
            elif _gv_l:
                threads = 4  # میزبانِ gVisorِ کوچک → صریحاً ۴
# else: همان threadsِ پاس‌شده — بدونِ auto
        except Exception:
            pass
    try:
        _t = int(threads)
    except Exception:
        _t = 4
# speed (SRV-L) — گاردِ SIGABRTِ مسیرِ CUDA: با نخِ ۲۰ رویِ
# سشن‌هایِ CUDA/TRT، per-patchِ LaMa رویِ سرورِ تازه ORT را با
# SIGABRT (exit=134) می‌کشد (SRV-K g20). سقفِ سختِ ۱۶ فقط وقتی
# سشنِ GPU خواسته شده؛ مسیرِ CPU دست‌نخورده می‌ماند.
    try:
        if prefer_gpu and _t > 16:
            _t = 16
    except Exception:
        pass
    so.intra_op_num_threads = _t if _t > 0 else 0
    so.inter_op_num_threads = 1
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
# پچ‌های موازی LaMa + OCR هم‌زمان اجرا می‌شوند؛ spin-wait هسته‌ها را می‌سوزاند
# رویِ x86_64 این کانفیگ SIGFPE می‌دهد (حدس: شمارشِ spin=۰
# → تقسیم بر صفر در مسیرِ x86) — فقط رویِ arm خاموش می‌شود
    if not _on_x86():
        try:
            so.add_session_config_entry(
                "session.intra_op.allow_spinning", "0")
        except Exception:
            pass
# speed (SRV-G phase2) — tuningِ spin برایِ threadpoolِ CPU
# چندنخی (کمبوِ رسمیِ مستنداتِ threadingِ onnxruntime):
# spin_duration_us=1000 + spin_backoff_max=8
# (SRV-H4) — پیش‌فرضِ خاموش (رویِ میزبانِ gVisor کندتر بود
# SRV-H2)؛ فقط با MANGA_SPIN=1 و وقتی pool چندنخی است (۰ یا >۱)
# رویِ میزبانِ غیرِ اندروید و خارج از XNNPACK فعال می‌شود.
    try:
        _spin_h4 = str(os.environ.get("MANGA_SPIN", "")).strip() == "1"
    except Exception:
        _spin_h4 = False
    if _spin_h4 and (not _cap1) and (not _xnn) \
            and (not _android_like_env()) and (_t == 0 or _t > 1):
        try:
            so.add_session_config_entry(
                "session.intra_op.spin_duration_us", "1000")
            so.add_session_config_entry(
                "session.intra_op.spin_backoff_max", "8")
        except Exception:
            pass
    if _xnn:
# کانفیگِ رسمیِ XNNPACK: spinning خاموش (نخِ ORT فقط هماهنگ می‌کند)
        try:
            so.add_session_config_entry(
                "session.intra_op.allow_spinning", "0")
        except Exception:
            pass
    if low_mem is None:
        _av = _sys_avail_ram_gb()
# MANGA_LOW_MEM=1: اجبارِ حالتِ کم‌رم (آرنا/الگوی
# حافظه خاموش) — برایِ دستگاه‌هایِ ۴GB و نوارهایِ بلندِ وبتون که
# به مرزِ OOM می‌رسند
        low_mem = bool(_on_android()
                       or (_av is not None and _av < 3.0)
                       or os.environ.get("MANGA_LOW_MEM", "") == "1")
    so.enable_cpu_mem_arena = (not low_mem)
    so.enable_mem_pattern = (not low_mem)
    return so

def _trt_ep_usable() -> bool:
    """-speed — TensorrtExecutionProvider فقط وقتی «واقعاً» قابلِ
    استفاده است. حضورش در get_available_providers کافی نیست؛ بدونِ
    کتابخانهٔ nvinfer ساختِ سشن یا شکست می‌خورد یا برایِ ساختِ engine
    گیر می‌کند → ماژولِ tensorrt لازم است یا اجباری با MANGA_ALLOW_TRT=1
    (و انکار با MANGA_NO_TRT=1)."""
    try:
        if os.environ.get("MANGA_NO_TRT", "").strip() == "1":
            return False
    except Exception:
        pass
    try:
        import tensorrt  # noqa: F401
        return True
    except Exception:
        pass
    try:
        return os.environ.get("MANGA_ALLOW_TRT", "").strip() == "1"
    except Exception:
        return False

def _best_providers_for(kind: str = "generic", prefer_gpu: bool = True):
    """-speed — انتخابگرِ مرکزیِ EP از آنچه واقعاً نصب/موجود است.

    خروجی: لیستِ مرتبِ providers برایِ ort.InferenceSession — سریع‌ترین
    EPِ موجود اول و همیشه CPU آخرِ لیست. اولویتِ GPU: TensorRT (فقط
    usable) → CUDA → ROCm → MIGraphX → Dml (ویندوز) → QNN/NNAPI
    (اندروید) → CoreML (مک). در حالتِ --cpu فقط CPU (اگر OpenVINOِ واقعی
    نصب باشد جلوتر می‌آید؛ «Azure» ضمیمهٔ همهٔ بیلدهایِ معمولی ORT است و
    EPِ شتاب‌دهندهٔ لوکال نیست → هرگز جلو نمی‌آید). انتخابِ EP خروجیِ
    مدل‌ها را عوض نمی‌کند — فقط سرعتِ اجرا."""
    try:
        avail = list(ort.get_available_providers())
    except Exception:
        avail = []
    out = []
    if prefer_gpu:
        for _ep in ("TensorrtExecutionProvider", "CUDAExecutionProvider",
                    "ROCmExecutionProvider", "MIGraphXExecutionProvider",
                    "DmlExecutionProvider"):
            if _ep not in avail:
                continue
            if _ep == "TensorrtExecutionProvider" and not _trt_ep_usable():
                continue
            out.append(_ep)
        try:
            if _on_android() or _android_like_env():
                for _ep in ("QNNExecutionProvider", "NNAPIExecutionProvider"):
                    if _ep in avail:
                        out.append(_ep)
            elif sys.platform == "darwin" \
                    and "CoreMLExecutionProvider" in avail:
                out.append("CoreMLExecutionProvider")
        except Exception:
            pass
    else:
# cpu: x86_64 → فقط CPU (همان EPِ همیشگی، نتیجهٔ بیت‌به‌بیت یکسان)
# OpenVINO دیگر «به‌طورِ پیش‌فرض» ترجیح نمیشود:
# بنچمارکِ واقعی (scripts/bench_out/ov238_results.json) رویِ
# ورودیهایِ ضبطشده از ۱۰ عکسِ تست: onnxruntime-openvino (۱.۲۴.۱ —
# تنها نسخهٔ PyPI) در rec ۲۳٪ «کندتر» (۱۰۳s در برابرِ ۸۴s)، در
# LaMa ۱۶٪ کندتر و فقط در det ۲.۴× سریع‌تر است (سهمِ det از OCR
# ~۱۸٪) → سوییچِ بی‌صدا = ضررِ خالص. فقط با MANGA_ALLOW_OV=1.
        try:
            _allow_ov = str(os.environ.get(
                "MANGA_ALLOW_OV", "")).strip().lower() == "1"
        except Exception:
            _allow_ov = False
        if _allow_ov and "OpenVINOExecutionProvider" in avail:
            out.append("OpenVINOExecutionProvider")
# speed (SRV-G) — A/Bِ XNNPACK (فقط MANGA_CPU_EP=xnnpack):
# سشن‌هایِ CPU-EP از XNNPACK+CPU می‌روند با کانفیگِ رسمی
# (ORT intra=1 + XNNPACK intra=فیزیکی + spin خاموش) — پیش‌فرضِ خاموش.
        if _cpu_ep_xnnpack() and "XnnpackExecutionProvider" in avail:
            out.append("XnnpackExecutionProvider")
# امولاتورِ اندرویدِ x86_64: CPU-EPِ ORT-android می‌میرد (SIGFPE)
# → XNNPACK اجباری (همان رفتارِ )
    if _on_x86() and "XnnpackExecutionProvider" in avail:
        out.append("XnnpackExecutionProvider")
    out.append("CPUExecutionProvider")
    _seen, _res = set(), []
    for _p in out:
        if _p not in _seen:
            _seen.add(_p)
            _res.append(_p)
    return _res or ["CPUExecutionProvider"]

def _cudnn_algo_search() -> Optional[str]:
    """ (SRV-H4) — الگوریتمِ جست‌وجویِ cudnn برایِ convها.

    پیش‌فرضِ «HEURISTIC» برایِ «همهٔ» سشن‌هایِ CUDA — تنها بردِ اثبات‌
    شدهٔ speed2 رویِ GPU (SRV-H3: 01.jpg GPU بدونِ batch = 21.3s در
    برابرِ 23.3s بیس‌لاین). جست‌وجویِ EXHAUSTIVEِ پیش‌فرضِ ORT برایِ هر
    شکلِ تازه رویِ میزبانِ gVisor صدها میلی‌ثانیه می‌گیرد؛ HEURISTIC آن
    را حذف می‌کند. opt-out: MANGA_CUDNN_ALGO=exhaustive (یا off/none/0)
    → None → رفتارِ قدیمیِ EXHAUSTIVE دست‌نخورده."""
    try:
        _v_h4 = os.environ.get("MANGA_CUDNN_ALGO", "").strip().lower()
        if _v_h4 in ("exhaustive", "off", "none", "0"):
            return None
    except Exception:
        pass
    return "HEURISTIC"

def _build_provider_options(providers):
    """-speed (SRV-G phase2) — provider options برایِ سشن‌هایِ GPU:
    CUDA → {"cudnn_conv_use_max_workspace": "1"} (صریح؛ پیش‌فرضِ ORT هم 1
    است ولی این‌طور به آن اعتماد نمی‌کنیم). cudnn_conv_algo_search دست
    نمی‌خورد (EXHAUSTIVE می‌ماند) و CUDA graphs روشن نمی‌شود (شکل‌هایِ
    داینامیک). XNNPACK (فقط MANGA_CPU_EP=xnnpack) → intra_op_num_threads =
    هسته‌هایِ فیزیکی (کانفیگِ رسمی). خروجی None رویِ لیستِ بدونِ CUDA/XNNPACK
    → دقیقاً رفتارِ قبلی (سشنِ CPU خالص).
     (SRV-H4) — کلیدِ «cudnn_conv_algo_search»: "HEURISTIC"
    پیش‌فرض است (MANGA_CUDNN_ALGO=exhaustive حذفش می‌کند) — تکِ نقطهٔ
    مونتاژِ optionsِ CUDA برایِ همهٔ سشن‌ها از همین تابع می‌گذرد."""
    try:
        if not providers:
            return None
        _gpu_cuda = "CUDAExecutionProvider" in providers
        _xnn = _cpu_ep_xnnpack() and "XnnpackExecutionProvider" in providers
        if not (_gpu_cuda or _xnn):
            return None
        _opts = [{} for _ in providers]
        for _i, _p in enumerate(providers):
            if _p == "CUDAExecutionProvider":
                _opts[_i] = {"cudnn_conv_use_max_workspace": "1"}
# (SRV-H4) — HEURISTIC پیش‌فرض (حذفِ re-searchِ
# EXHAUSTIVE برایِ هر شکلِ تازه)؛ MANGA_CUDNN_ALGO=exhaustive
# → None → بدونِ این کلید (رفتارِ قدیمی).
                _algo_h4 = _cudnn_algo_search()
                if _algo_h4:
                    _opts[_i]["cudnn_conv_algo_search"] = _algo_h4
            elif _p == "XnnpackExecutionProvider":
                try:
                    _opts[_i] = {"intra_op_num_threads":
                                 str(max(1, int(_physical_core_count())))}
                except Exception:
                    _opts[_i] = {}
        return _opts
    except Exception:
        return None

# کشِ «مدلِ بهینه‌شده» برایِ LaMa ──────────────────────────
# لاگِ POCO F4 : [TIME] lama-wait=67.3s → کلِ زمان در
# OrtEnvironment.createSession رویِ مدلِ ۲۰۶MB می‌رود؛ بهینه‌سازِ گرافِ
# ORT تک‌نخی است و رویِ هسته‌هایِ ضعیف + رمِ آزادِ ~۳۵۵MB ده‌ها ثانیه
# طول می‌کشد (رویِ PC/امولاتور <۱s — برایِ همین دیده نمی‌شد).
# راه: بارِ اول، مدلِ بهینه‌شده رویِ دیسک ذخیره می‌شود
# (SessionOptions.optimized_model_filepath — در pip هست؛ در شیمِ اندروید
# به OrtSession.SessionOptions.setOptimizationModelFilePath جاوا
# می‌رود) و بارهایِ بعدی از همان فایل ساخته می‌شوند → مرحلهٔ
# بهینه‌سازی کامل حذف می‌شود. ذخیره با EPِ CPU انجام می‌شود (الگوی
# استاندارد؛ مدلِ بهینه‌شده، گرافِ عمومیِ بهینه است) و بارگذاری با
# هر EPِ درخواستی خودش دوباره EP را سوار می‌کند.
_LAMA_OPT_LOCK = threading.Lock()

def _lama_opt_cache_path(model_path: str, providers) -> str:
    _v = "x"
    try:
        _v = str(getattr(ort, "__version__", "x") or "x")
    except Exception:
        pass
    _ep = "cpu"
    try:
        for _p in (providers or ()):
            if str(_p).lower().startswith("xnnpack"):
                _ep = "xnnpack"
                break
    except Exception:
        pass
    _d, _f = os.path.split(str(model_path))
    _stem = _f[:-5] if _f.lower().endswith(".onnx") else _f
    return os.path.join(_d, f"{_stem}.opt69-{_v}-{_ep}.onnx")

def _lama_session_cached(model_path, so, providers, provider_options=None):
    """سشنِ LaMa با کشِ مدلِ بهینه‌شده + [TIME]ِ زمانِ ساخت.

    شکستِ هر مرحله = رفتارِ قبل (بدونِ کش) — هیچ مسیرِ تازه‌ای نباید
    بتواند ساختِ سشن را خراب کند.
    -speed (SRV-G): provider_options اختیاری است (CUDA EP:
    cudnn_conv_use_max_workspace=1). None = دقیقاً رفتارِ قبل."""
    _t = time.time()
    _opt = None
    try:
        if str(os.environ.get("MANGA_LAMA_OPT_CACHE", "1")).strip() == "1" \
                and isinstance(model_path, str):
            _opt = _lama_opt_cache_path(model_path, providers)
    except Exception:
        _opt = None
    if _opt and os.path.isfile(_opt) \
            and os.path.getsize(_opt) > 1_000_000:
        try:
# ساختِ سشنِ DML هم زیرِ قفلِ سراسری: هم‌زمانیِ
# ساختِ سشن با runِ سشنِ دیگر رویِ درایورهایِ AMD همان
# 887A0006 را میدهد (سشن CPU بدونِ قفل — بی‌تغییر)
            if "DmlExecutionProvider" in (providers or []):
                with _DML_RUN_LOCK:
                    _s = ort.InferenceSession(_opt, sess_options=so,
                                                providers=providers,
                                                provider_options=provider_options)
            else:
                _s = ort.InferenceSession(_opt, sess_options=so,
                                            providers=providers,
                                            provider_options=provider_options)
            try:
                print(f"[TIME] lama-create={time.time() - _t:.1f}s "
                      f"(از کشِ بهینه‌شده)", flush=True)
            except Exception:
                pass
            return _s
        except Exception:
            try:
                os.remove(_opt)
            except Exception:
                pass
# بارِ اول: مدلِ بهینه‌شده ذخیره می‌شود (اگر ORT پشتیبانی نکرد
# بی‌صدا مثلِ قبل). رویِ اندروید سطحِ بهینه‌سازی BASIC — بهینه‌سازِ
# ALLِ تک‌نخی بخشِ بزرگی از همان ۶۷s است و XNNPACKِ سنگین‌کارِ
# اصلی را خودش انجام می‌دهد (رویِ PC: ALL→BASIC فقط ‎+۴٪ زمانِ
# اجرا؛ ساخت ×۲.۵ سریع‌تر).
    _part = None
    try:
        _android = _on_android()
    except Exception:
        _android = False
    if _opt and _android:
        try:
            so.graph_optimization_level = \
                ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        except Exception:
            pass
    if _opt:
        _part = _opt + ".part"
        try:
            so.optimized_model_filepath = _part
        except Exception:
            _part = None
    try:
# ساختِ سشنِ DML زیرِ قفلِ سراسری (توضیح: بالا)
        if "DmlExecutionProvider" in (providers or []):
            with _DML_RUN_LOCK:
                _s = ort.InferenceSession(model_path, sess_options=so,
                                            providers=providers,
                                            provider_options=provider_options)
        else:
            _s = ort.InferenceSession(model_path, sess_options=so,
                                        providers=providers,
                                        provider_options=provider_options)
    finally:
        try:
            if _part and os.path.isfile(_part):
                with _LAMA_OPT_LOCK:
                    try:
                        os.replace(_part, _opt)
                        try:
                            print(f"[TIME] lama-create={time.time() - _t:.1f}s "
                                  f"(مدلِ بهینه‌شده ذخیره شد → کش)", flush=True)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            os.remove(_part)
                        except Exception:
                            pass
        except Exception:
            pass
    try:
        print(f"[TIME] lama-create={time.time() - _t:.1f}s", flush=True)
    except Exception:
        pass
    return _s

_ORT_CUDA_OK = None

# DirectML (AMD/Intel رویِ ویندوز): مستنداتِ رسمیِ ORT:
# «EPِ DirectML از اجرایِ موازی پشتیبانی نمیکند؛ در هر لحظه فقط یک
# نخ میتواند Run را رویِ سشن صدا بزند.» لاگِ 232 رویِ RX 5700 XT:
# ۴ کارگرِ موازیِ OCR همزمان رویِ سشنهایِ rapidocr → 887A0006
# «GPU will not respond to more commands» → همه چیز بی‌صدا به CPU
# برگشت و GPU هرگز استفاده نشد. قفلِ سراسریِ زیر «همهٔ» اینفرنسهایِ
# DML (دیتکتور/OCR/LaMa) را سریال میکند؛ CPU خالص و CUDA/TRT و
# اندروید دست‌نخورده میمانند.
# RLock (نه Lock): اگر همین نخ قفل را دارد و دوباره میخواهد (ساختِ
# سشنِ DML داخلِ runِ قفل‌شده)، بن‌بست نمیشود؛ نخهایِ دیگر همچنان
# سریال میشوند.
_DML_RUN_LOCK = threading.RLock()

def _dml_sess(sess) -> bool:
    """سرِ providersِ سشن DML است؟"""
    try:
        _p = list(sess.get_providers())
        return bool(_p) and _p[0] == "DmlExecutionProvider"
    except Exception:
        return False

def _dml_run(sess, feeds):
    """ — session.run رویِ سشنِ DML فقط زیرِ قفلِ سراسری
    (اجرایِ موازیِ DML ممنوع است — 887A0006 رویِ AMD). سشنهایِ CPU/CUDA
    بدونِ قفل و بدونِ سربار میروند."""
    if _dml_sess(sess):
        with _DML_RUN_LOCK:
            return sess.run(None, feeds)
    return sess.run(None, feeds)

def _dml_run_outs(sess, outs, feeds):
    """ — همان _dml_run ولی با لیستِ خروجیهایِ صریح (پروبهایِ
    داخلی مثلِ _ort_probe_ok)."""
    if _dml_sess(sess):
        with _DML_RUN_LOCK:
            return sess.run(outs, feeds)
    return sess.run(outs, feeds)

def _dml_probe_cache_get(model_path: str):
    """ — کشِ دیسکِ نتیجهٔ پروبِ DML (کنارِ فایلِ مدل
    .dmlprobe). پروبِ هر مدل چند ثانیه ساختِ سشن رویِ GPU است؛ بدونِ
    کش هر استارت تکرار میشد. MANGA_ORT_EP_REPROBE=1 → بی‌اعتنا به کش
    (همان قراردادِ پروبِ LaMa). کلید: حجمِ فایل + نسخهٔ ORT."""
    try:
        if os.environ.get("MANGA_ORT_EP_REPROBE", "").strip() == "1":
            return None
        _f = str(model_path) + ".dmlprobe"
        if not os.path.isfile(_f):
            return None
        import json as _json
        with open(_f, "r", encoding="utf-8") as _fh:
            _d = _json.load(_fh)
        if int(_d.get("size", -1)) != int(os.path.getsize(model_path)):
            return None
        if str(_d.get("ort", "")) != str(getattr(ort, "__version__", "")):
            return None
        return bool(_d.get("ok"))
    except Exception:
        return None

def _dml_probe_cache_set(model_path: str, ok: bool) -> None:
    try:
        import json as _json
        _f = str(model_path) + ".dmlprobe"
        with open(_f, "w", encoding="utf-8") as _fh:
            _json.dump({"ok": bool(ok),
                          "size": int(os.path.getsize(model_path)),
                          "ort": str(getattr(ort, "__version__", ""))},
                         _fh)
    except Exception:
        pass

def _dml_probe_model(model_path: str) -> bool:
    """ — پروبِ واقعیِ DML رویِ یک فایلِ مدل: ساختِ سشن +
    «یک اینفرنسِ واقعی» با فیدِ دامی از رویِ شکلِ ورودیها. «سشن ساخته
    شد» کافی نیست — لاگِ 232: سشنهایِ det/rec ساخته شدند ولی اولین
    Run با 887A0006 مرد. False = این مدل رویِ این GPU/DirectML کار
    نمیکند (مثلاً int8 کوانتیزه — 80070057). نتیجه در دیسک کش
    میشود (.dmlprobe) تا استارتِ بعدی پروبِ مجاز نخواهد."""
    _c = _dml_probe_cache_get(model_path)
    if _c is not None:
        return _c
    _ok = _dml_probe_model_live(model_path)
    _dml_probe_cache_set(model_path, _ok)
    return _ok

def _dml_probe_model_live(model_path: str) -> bool:
    try:
        if not model_path or not os.path.isfile(model_path):
            return False
        _so = _ort_session_options(2, prefer_gpu=True)
        try:
# مستنداتِ DML: الگویِ حافظه باید خاموش باشد
            _so.enable_mem_pattern = False
        except Exception:
            pass
# ساختِ سشن و run «هر دو» زیرِ قفل: در لحظهٔ پروب ممکن است
# پیش‌بارگذاریِ پس‌زمینهٔ LaMa همینجا سشنِ DML بسازد/اجرا کند
        with _DML_RUN_LOCK:
            _ps = ort.InferenceSession(
                model_path, sess_options=_so,
                providers=["DmlExecutionProvider", "CPUExecutionProvider"])
            if not _dml_sess(_ps):
                return False
            _feed = _ep_ab_feed(_ps, side=320)
            if not _feed:
                return False
# فیکسِ RT-DETR: ورودیِ int64ِ (B,2)ِ orig_target_sizes باید
# هم‌بُعدِ batchِ تصویر باشد — فیدِ خام (2,2) میسازد که با
# تصویرِ (1,...) mismatch میدهد و پروبِ سالم هم «مردود»
# میشود. batch همهٔ ورودیها را با بزرگ‌ترین batchِ 4بُعدی
# هم‌تراز میکنیم.
            _b = 1
            for _v in _feed.values():
                if getattr(_v, "ndim", 0) == 4:
                    _b = max(_b, int(_v.shape[0]))
            for _k, _v in list(_feed.items()):
                if getattr(_v, "ndim", 0) == 2 \
                        and _v.dtype in (np.int64, np.int32) \
                        and int(_v.shape[0]) != _b:
                    _feed[_k] = np.full(
                        (_b, int(_v.shape[1])), 320, dtype=_v.dtype)
            _outs = [o.name for o in _ps.get_outputs()][:1]
            _ps.run(_outs, _feed)
        try:
            del _ps
        except Exception:
            pass
        import gc as _gc
        _gc.collect()
        return True
    except Exception:
        return False

def _prepare_ort_cuda_dlls() -> None:
# ویندوز: DLLهایِ CUDA/cuDNN که pip در site-packages/nvidia
# میگذارد باید با add_dll_directory معرفی شوند تا سشنِ CUDA واقعاً
# بالا بیاید (ریشهٔ «GPU صفر درصد»: بیلدِ GPU نصب است ولی سشن
# بیصدا به CPU برمی‌گشت). لینوکس: LD_LIBRARY_PATH را خودِ pip-wheels
# هندل میکنند — این بلوک فقط ویندوز است.
    try:
        if os.name == "nt":
            import site as _site
            import glob as _glob
            for _sp in set(_site.getsitepackages() or []):
                for _nd in sorted(_glob.glob(
                        os.path.join(_sp, "nvidia", "*", "bin"))):
                    try:
                        os.add_dll_directory(_nd)
                    except Exception:
                        pass
                for _nd230b in sorted(_glob.glob(
                        os.path.join(_sp, "nvidia", "cuda_runtime", "bin"))):
                    try:
                        os.add_dll_directory(_nd230b)
                    except Exception:
                        pass
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            try:
                _ = torch.empty(1, device="cuda")
            except Exception:
                pass
    except Exception:
        pass
    try:
        if hasattr(ort, "preload_dlls"):
            try:
                ort.preload_dlls(cuda=True, cudnn=True, msvc=True, directory="")
            except TypeError:
                ort.preload_dlls()
            except Exception:
                try:
                    ort.preload_dlls()
                except Exception:
                    pass
    except Exception:
        pass

def _on_x86() -> bool:
    """ — فقط «امولاتورِ x86_64» (اندروید + x86): CPU-EPِ
    libonnxruntimeِ x86_64 در sess.run تقسیم‌برصفر (SIGFPE) می‌دهد؛
    XNNPACK سالم است. PCِ لینوکسی x86 هم هست ولی اندروید نیست → False
    (وگرنه نخِ PC به ۱ محدود و مسیرِ XNNPACK خراب می‌شد)."""
    try:
        if not _on_android():
            return False
        import platform as _pf
        return _pf.machine().lower() in ("x86_64", "amd64")
    except Exception:
        return False

def _is_auto_ep() -> bool:
    try:
        v = (os.environ.get("MANGA_ORT_EP", "auto") or "auto").strip().lower()
    except Exception:
        return True
    return v in ("", "auto")

def _resolve_lama_ep():
    try:
        v = (os.environ.get("MANGA_ORT_EP", "auto") or "auto").strip().lower()
    except Exception:
        v = "auto"
    if v in ("", "off", "none", "0", "cpu"):
        return None
    if v in ("nnapi", "NnapiExecutionProvider"):
        return "NnapiExecutionProvider"
    if v in ("webgpu", "WebGpuExecutionProvider"):
        return "WebGpuExecutionProvider"
    if v in ("xnnpack", "XnnpackExecutionProvider"):
        return "XnnpackExecutionProvider"
    if v in ("cuda", "CUDAExecutionProvider"):
        return "CUDAExecutionProvider"
    if v in ("dml", "directml", "DmlExecutionProvider"):
        return "DmlExecutionProvider"
    try:
        avail = list(ort.get_available_providers())
    except Exception:
        avail = []
    for cand in ("CUDAExecutionProvider", "DmlExecutionProvider",
                 "XnnpackExecutionProvider", "NnapiExecutionProvider",
                 "WebGpuExecutionProvider"):
        if cand in avail:
            return cand
    return None

def _lama_ep_cache_path(model_path: str) -> str:
    return str(model_path) + ".epab"

def _lama_ep_cached(model_path: str):
    try:
        if os.environ.get("MANGA_ORT_EP_REPROBE", "0") == "1":
            return None
        p = _lama_ep_cache_path(model_path)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                v = (f.read() or "").strip().lower()
            if v in ("cpu", "xnnpack", "nnapi", "webgpu", "cuda", "dml"):
                return v
    except Exception:
        pass
    return None

def _lama_ep_store(model_path: str, v: str):
    try:
        v = (v or "").strip().lower()
        if v in ("cpuexecutionprovider", ""):
            v = "cpu"
        if v == "directml":
            v = "dml"
        with open(_lama_ep_cache_path(model_path), "w", encoding="utf-8") as f:
            f.write(v)
    except Exception:
        pass

def _ep_ab_feed(sess, side: int = 256) -> dict:
    feed = {}
    for inp in sess.get_inputs():
        try:
            dt = getattr(inp, "type", "") or ""
        except Exception:
            dt = ""
        if "int64" in dt:
            np_dt = np.int64
        elif "int32" in dt:
            np_dt = np.int32
        elif "float16" in dt:
            np_dt = np.float16
        elif "double" in dt:
            np_dt = np.float64
        elif "bool" in dt:
            np_dt = np.bool_
        else:
            np_dt = np.float32
        shp = []
        try:
            for d in (inp.shape or []):
                shp.append(d if isinstance(d, int) and d > 0 else None)
        except Exception:
            shp = []
        nm = (getattr(inp, "name", "") or "").lower()
        is_mask = ("mask" in nm or "msk" in nm)
        if np_dt in (np.int64, np.int32) and len(shp) <= 2:
            dims = [d if d is not None else (2 if len(shp) >= 2 else 1)
                    for d in (shp or [1, 2])]
            arr = np.full(dims, side, dtype=np_dt)
            feed[inp.name] = arr
            continue
        if len(shp) == 4:
            b = shp[0] or 1
            c = shp[1] if shp[1] else (1 if is_mask else 3)
            h = shp[2] or side
            w = shp[3] or side
            arr = np.zeros((b, c, h, w), dtype=np_dt)
            if np_dt == np.float32 and is_mask:
                h2, w2 = arr.shape[2], arr.shape[3]
                arr[:, :, h2 // 4:h2 // 2, w2 // 4:w2 // 2] = 1.0
            feed[inp.name] = arr
            continue
        if len(shp) == 3:
            dims = [shp[0] or 1, shp[1] or side, shp[2] or side]
            feed[inp.name] = np.zeros(dims, dtype=np_dt)
            continue
        if len(shp) in (0, 1):
            feed[inp.name] = np.zeros([d or 1 for d in shp] or [1], dtype=np_dt)
            continue
        dims = [d if d is not None else 1 for d in shp] or [1]
        feed[inp.name] = np.zeros(dims, dtype=np_dt)
    return feed

_LAMA_STATIC_SIDE = None

def _lama_static_side() -> int:
    """ — شکلِ ثابتِ پچِ LaMa برایِ EPهایی که با شکلِ داینامیک
    می‌میرند (xnnpack رویِ اندروید: پروبِ ثابت پاس می‌شود ولی پچِ واقعیِ
    384×~200 ORT_FAIL می‌دهد — ریشهٔ مرگِ LaMa و فال‌بکِ OpenCV). وقتی
    فعال باشد، هر ورودیِ LaMa دقیقاً به (side×side) پد می‌شود → xnnpack
    فقط یک‌بار کامپایل می‌کند و واقعاً کار می‌کند (سریع‌تر از CPUِ خالی).
    env: MANGA_LAMA_STATIC_SIDE=0 (خاموش) | N (اندازه) | خالی = خودکار
    (اندروید + xnnpack موجود → 384، بقیه → 0)."""
    global _LAMA_STATIC_SIDE
    if _LAMA_STATIC_SIDE is not None:
        return int(_LAMA_STATIC_SIDE)
    v = -1
    try:
        _raw = (os.environ.get("MANGA_LAMA_STATIC_SIDE", "") or "").strip()
        if _raw != "":
            v = int(_raw)
    except Exception:
        v = -1
    side = 0
    if v > 0:
        side = (int(v) // 64) * 64
    elif v == 0:
        side = 0
    else:
        try:
            if _on_android() and ort is not None and (
                    "XnnpackExecutionProvider"
                    in list(ort.get_available_providers())):
                side = 384
        except Exception:
            side = 0
    _LAMA_STATIC_SIDE = int(side)
    return int(side)

def _lama_probe_side(ab: bool = False) -> int:
    """شکلِ فیدِ پروب/AB — وقتی باکتِ ثابت فعال است، پروب باید با همان
    شکلِ واقعیِ پچ‌ها باشد تا کامپایلِ xnnpack از همان ابتدا درست باشد."""
    s = _lama_static_side()
    if s > 0:
        return s
    return 256 if ab else 64

def _ep_ab_time(sess) -> float:
    try:
        feed = _ep_ab_feed(sess, side=_lama_probe_side(True))
        if not feed:
            return float("inf")
        outs = [o.name for o in sess.get_outputs()][:1]
        best = float("inf")
        for i in range(3):
            t0 = time.time()
            sess.run(outs, feed)
            dt = time.time() - t0
            if i > 0 and dt < best:
                best = dt
        return best
    except Exception:
        return float("inf")

def _lama_probeok_path(model_path: str) -> str:
    return str(model_path) + ".probeok"

def _lama_probeok_key(model_path: str, ep_name: str) -> str:
    _v = "x"
    try:
        _v = str(getattr(ort, "__version__", "x") or "x")
    except Exception:
        pass
    try:
        _side = int(_lama_static_side())
    except Exception:
        _side = 0
    try:
        _sz = int(os.path.getsize(model_path)) if model_path else 0
    except Exception:
        _sz = 0
    _ep = str(ep_name or "").lower().replace("executionprovider", "")
    return f"{_ep}|{_v}|{_side}|{_sz}"

def _lama_probeok_hit(model_path, ep_name) -> bool:
    try:
        if not model_path or not isinstance(model_path, str):
            return False
        if os.environ.get("MANGA_ORT_EP_REPROBE", "0") == "1":
            return False
        p = _lama_probeok_path(model_path)
        if not os.path.isfile(p):
            return False
        with open(p, "r", encoding="utf-8") as f:
            v = (f.read() or "").strip()
        return v == _lama_probeok_key(model_path, ep_name) + "|ok"
    except Exception:
        return False

def _lama_probeok_store(model_path, ep_name) -> None:
    try:
        if not model_path or not isinstance(model_path, str):
            return
        with open(_lama_probeok_path(model_path), "w", encoding="utf-8") as f:
            f.write(_lama_probeok_key(model_path, ep_name) + "|ok")
    except Exception:
        pass

def _ort_probe_ok(sess, threads: int, model_path=None,
                  ep_name: str = "") -> bool:
    _t = time.time()
# کشِ نتیجهٔ پروب: پروبِ سلامت/سریالی تا ۵ اینفرنسِ
# ۳۸۴² رویِ xnnpack انجام می‌دهد (رویِ گوشی ده‌ها ثانیه) و در هر
# استارت تکرار می‌شد؛ نتیجه برایِ (مدل، EP، نسخهٔ ORT، ساید، حجم)
# ماندگار می‌شود. MANGA_ORT_EP_REPROBE=1 → پروبِ دوباره.
    try:
        if _lama_probeok_hit(model_path, ep_name):
            try:
                print("    [*] پروبِ EP از کش — بدونِ اینفرنسِ دوباره",
                      flush=True)
            except Exception:
                pass
            return True
    except Exception:
        pass
    try:
        feed = _ep_ab_feed(sess, side=_lama_probe_side(False))
        if not feed:
            try:
                print("    [!] پروب: فیدِ خالی (شکلِ ورودیِ مدل؟)")
            except Exception:
                pass
            return False
        outs = [o.name for o in sess.get_outputs()][:1]
        try:
            _dml_run_outs(sess, outs, feed)
        except Exception as _pe:
            try:
                print(f"    [!] پروبِ run با نام خروجی: {str(_pe)[:110]}")
            except Exception:
                pass
            try:
                _dml_run(sess, feed)
            except Exception as _pe2:
                try:
                    print(f"    [!] پروبِ run هم با None: {str(_pe2)[:110]}")
                except Exception:
                    pass
                return False
        if threads <= 0:
            _lama_probeok_store(model_path, ep_name)
            return True
        t0 = time.time()
        try:
            _dml_run_outs(sess, outs, feed)
            _dml_run_outs(sess, outs, feed)
            t_ser = time.time() - t0
        except Exception:
            return False
        if t_ser <= 0.02:
            _lama_probeok_store(model_path, ep_name)
            return True
# اندروید: فقط اعتبارسنجی (۱ ران کافی است)
# مقایسهٔ سریال/موازی ۴ اینفرنسِ اضافه می‌خواهد و رویِ گوشیِ
# کم‌رم ده‌ها ثانیه به استارت اضافه می‌کند، درحالی‌که A/Bِ
# واقعی (.epab) جداگانه EP را با CPU مقایسه کرده است.
        try:
            _and = _on_android()
        except Exception:
            _and = False
        if _and:
            try:
                print(f"[TIME] lama-probe={time.time() - _t:.1f}s "
                      f"(اندروید: فقط اعتبارسنجی)", flush=True)
            except Exception:
                pass
            _lama_probeok_store(model_path, ep_name)
            return True
# امولاتورِ x86_64: رانِ موازیِ همزمان در libonnxruntimeِ
# x86_64 SIGFPE می‌دهد (تقسیمِ صحیحِ صفر در زمان‌بندِ thread-pool) —
# پروبِ موازی رویِ x86 بی‌معناست (CI فقط درستی می‌سنجد) → پرش.
        try:
            import platform as _pf
            if _pf.machine().lower() in ("x86_64", "amd64"):
                return True
        except Exception:
            pass
        from concurrent.futures import ThreadPoolExecutor as _TPE
        try:
            with _TPE(max_workers=2) as ex:
                t1 = time.time()
                f1 = ex.submit(sess.run, outs, feed)
                f2 = ex.submit(sess.run, outs, feed)
                f1.result(timeout=60)
                f2.result(timeout=60)
                t_con = time.time() - t1
        except Exception:
            return False
        if t_con > t_ser * 1.6:
            try:
                print(f"    [!] EP رانِ همزمان را سریال می‌کند "
                      f"({t_con:.2f}s در برابر ۲×{t_ser:.2f}s) → CPU موازی")
            except Exception:
                pass
            return False
        try:
            print(f"[TIME] lama-probe={time.time() - _t:.1f}s", flush=True)
        except Exception:
            pass
        _lama_probeok_store(model_path, ep_name)
        return True
    except Exception:
        return False

_AB_EPS = ["XnnpackExecutionProvider", "NnapiExecutionProvider",
           "WebGpuExecutionProvider", "CUDAExecutionProvider",
           "DmlExecutionProvider"]

def _ep_tournament(model_path: str, threads: int, include_gpu: bool = True):
    t_all0 = time.time()
    try:
        budget = float(os.environ.get("MANGA_AB_BUDGET", "45") or 45)
    except Exception:
        budget = 45.0
    try:
        avail = list(ort.get_available_providers())
    except Exception:
        avail = []
    rows = []
    for cand in _AB_EPS:
        short = cand.replace("ExecutionProvider", "").lower()
        if cand not in avail:
            continue
        if cand in ("CUDAExecutionProvider", "DmlExecutionProvider") \
                and not include_gpu:
            continue
        if (time.time() - t_all0) > budget:
            try:
                print(f"    [*] {short}: رد شد (اتمام بودجهٔ {budget:.0f}s پروب)")
            except Exception:
                pass
            continue
        s_c = None
        try:
# speed (SRV-L) — کاندیدِ CUDA تورنمنت هم گاردِ سقفِ
# نخِ GPU را می‌گیرد (SIGABRTِ SRV-K g20 در per-patchِ LaMa)
            so_c = _ort_session_options(
                threads,
                prefer_gpu=(cand == "CUDAExecutionProvider"))
            try:
                so_c.append_execution_provider(cand)
            except Exception:
                try:
                    so_c._eps = [(cand, {})]
                except Exception:
                    pass
            t0 = time.time()
# speed (SRV-H3) — کاندیدِ CUDA در تورنمنت هم همان
# optionsِ سشنِ نهایی را بگیرد (workspace + MANGA_CUDNN_ALGO)
# تا A/B با کانفیگِ نهایی قابلِ مقایسه باشد؛ برایِ بقیهٔ EPها
# None = دقیقاً رفتارِ قبل.
            _po_h3 = (_build_provider_options(
                [cand, "CPUExecutionProvider"])
                if cand == "CUDAExecutionProvider" else None)
            s_c = ort.InferenceSession(model_path, sess_options=so_c,
                                       providers=[cand, "CPUExecutionProvider"],
                                       provider_options=_po_h3)
            t_make = time.time() - t0
            if not _ort_probe_ok(s_c, threads if threads > 0 else 0,
                                 model_path, cand):
                try:
                    print(f"    [*] {short}: مردود (پروب سلامت/سریالی)")
                except Exception:
                    pass
                s_c = None
                continue
            t_c = _ep_ab_time(s_c)
            try:
                print(f"    [*] پروب {short}: {t_c:.2f}s (ساخت {t_make:.1f}s)")
            except Exception:
                pass
            rows.append((t_c, short, s_c))
        except Exception as e:
            try:
                print(f"    [*] {short}: ناموفق ({str(e)[:90]})")
            except Exception:
                pass
            s_c = None
            continue
    s_cpu, t_cpu = None, float("inf")
    if _on_x86():
# سشنِ CPU رویِ x86 ساخته می‌شود ولی run نمی‌شود
# (SIGFPE)؛ فقط برایِ فال‌بکِ نهایی
        try:
            s_cpu = ort.InferenceSession(model_path,
                                         sess_options=_ort_session_options(
                                             threads),
                                         providers=["CPUExecutionProvider"])
        except Exception:
            s_cpu = None
    else:
        try:
            s_cpu = ort.InferenceSession(
                model_path,
                sess_options=_ort_session_options(threads),
                providers=["CPUExecutionProvider"])
            t_cpu = _ep_ab_time(s_cpu)
            try:
                print(f"    [*] پروب CPU: {t_cpu:.2f}s")
            except Exception:
                pass
        except Exception:
            pass
    rows.sort(key=lambda r: r[0])
# امولاتورِ x86_64: مقایسه با CPU (سشنِ CPU) خودش کرش
# می‌کند → برندهٔ سخت‌افزاریِ پروب‌شده را بی‌مقایسه بپذیر
    if _on_x86():
        if rows:
            winner = rows[0]
            try:
                print(f"[*] پروب EP (x86 — بدونِ مقایسه با CPU): {winner[1]}")
            except Exception:
                pass
            _lama_ep_store(model_path, winner[1])
            return winner[2]
        _lama_ep_store(model_path, "cpu")
        return s_cpu
    winner = rows[0] if (rows and rows[0][0] < t_cpu) else None
    try:
        summary = " | ".join(f"{r[1]} {r[0]:.2f}s" for r in rows) or "—"
        print(f"[*] پروب EP ({os.path.basename(model_path)}): "
              f"{summary} | CPU {t_cpu:.2f}s → برنده: "
              f"{winner[1] if winner else 'CPU'}")
    except Exception:
        pass
    if winner is not None:
        _lama_ep_store(model_path, winner[1])
        try:
            print(f"[+] شتاب سخت‌افزاری ORT فعال شد: {winner[1]} "
                  f"(پروب A/B — سریع‌تر از CPU)")
        except Exception:
            pass
        return winner[2]
    _lama_ep_store(model_path, "cpu")
    return s_cpu

def _make_ort_session(model_path: str, prefer_gpu: bool = True, threads: int = 4,
                      ep: Optional[str] = None, ep_ab: bool = False):
    global _ORT_CUDA_OK
    if ort is None:
        raise RuntimeError("onnxruntime نصب نیست")
# امولاتورِ x86_64 (CI): CPU-EPِ ORT-android در createSession
# SIGFPE می‌دهد و تورنمنت هم پروب را رد می‌کند → سشنِ دومِ fallback
# کرشِ نیتیو می‌دهد. تجربهٔ ران ۲۴: ساختِ اولینِ سشنِ XNNPACK سالم بود
# پس: هیچ تورنمنت، هیچ پروب، هیچ سشنِ دوم — فقط یک سشنِ مستقیمِ
# XNNPACK+CPU (گره‌هایِ پشتیبانی‌نشده خودکار به CPU برمی‌گردند).
    try:
        import platform as _pf
        if _on_android() and _pf.machine().lower() in ("x86_64", "amd64"):
            so2 = _ort_session_options(1)
            try:
                so2.append_execution_provider("XnnpackExecutionProvider")
            except Exception:
                try:
                    so2._eps = [("XnnpackExecutionProvider", {})]
                except Exception:
                    pass
            sess2 = ort.InferenceSession(
                model_path, sess_options=so2,
                providers=["XnnpackExecutionProvider", "CPUExecutionProvider"])
            try:
                print("[*] x86_64: سشنِ مستقیمِ XNNPACK (بدونِ تورنمنت/پروب)")
            except Exception:
                pass
            return sess2
    except Exception as e:
        try:
            print(f"[!] x86_64 سشنِ مستقیمِ XNNPACK ناموفق: {str(e)[:110]}")
        except Exception:
            pass
# speed (SRV-L) — «want» قبل از ساختِ سشن محاسبه می‌شود تا
# گاردِ سقفِ نخِ GPU (SIGABRT ≥۲۰ رویِ CUDA/TRT) رویِ سشنِ اصلی هم
# اعمال شود؛ مسیرِ CPU بدونِ clamp می‌ماند.
    want = prefer_gpu and (_ORT_CUDA_OK is not False)
    so = _ort_session_options(threads, prefer_gpu=want)

    if want:
        _prepare_ort_cuda_dlls()

    _EP_SHORT2FULL = {"xnnpack": "XnnpackExecutionProvider",
                      "nnapi": "NnapiExecutionProvider",
                      "webgpu": "WebGpuExecutionProvider",
                      "cuda": "CUDAExecutionProvider",
                      "dml": "DmlExecutionProvider"}
    if ep and ep_ab:
        _cached = _lama_ep_cached(model_path)
        if _cached == "cpu":
            ep, ep_ab = None, False
        elif _cached in _EP_SHORT2FULL:
            ep, ep_ab = _EP_SHORT2FULL[_cached], False
    elif ep and not ep_ab:
        pass  # EPِ اجباری (MANGA_ORT_EP) — کشِ opt خودش بر اساسِ EP کلید می‌خورد

    if ep:
        try:
            avail = list(ort.get_available_providers())
        except Exception:
            avail = []
        _any_hw = ep in avail or any(c in avail for c in _AB_EPS)
        if _any_hw and ep_ab:
            s_win = _ep_tournament(model_path, threads, include_gpu=prefer_gpu)
            if s_win is not None:
                return s_win
            import gc as _gcp
            try:
                _gcp.collect()
            except Exception:
                pass
        elif ep in avail:
# speed (SRV-L) — مسیرِ EPِ اجباری: اگر CUDA اجباری
# است، گاردِ سقفِ نخِ GPU اعمال شود
            so_ep = _ort_session_options(
                threads, prefer_gpu=(ep == "CUDAExecutionProvider"))
            if ep == "DmlExecutionProvider":
# مستنداتِ DML: الگویِ حافظه خاموش
                try:
                    so_ep.enable_mem_pattern = False
                except Exception:
                    pass
            try:
                so_ep.append_execution_provider(ep)
            except Exception:
                try:
                    so_ep._eps = [(ep, {})]
                except Exception:
                    pass
            try:
# speed (SRV-H3) — مسیرِ EPِ اجباری هم optionsِ
# CUDAِ مرکزی را می‌گیرد (workspace + MANGA_CUDNN_ALGO) تا
# «همهٔ» سشن‌هایِ CUDA یک کانفیگ داشته باشند؛ برایِ epهای
# غیرِ CUDA خروجیِ _build_provider_options None است.
                s_ep = _lama_session_cached(
                    model_path, so_ep, [ep, "CPUExecutionProvider"],
                    provider_options=_build_provider_options(
                        [ep, "CPUExecutionProvider"]))
                if _ort_probe_ok(s_ep, threads if threads > 0 else 0,
                                 model_path, ep):
                    try:
                        print(f"[+] شتاب سخت‌افزاری ORT فعال شد: {ep} "
                              f"(MANGA_ORT_EP — اجباری)")
                    except Exception:
                        pass
                    return s_ep
                try:
                    s_ep = None
                except Exception:
                    pass
            except Exception as e:
                try:
                    print(f"    [!] ساخت سشن {ep} ناموفق ({str(e)[:120]}) → CPU")
                except Exception:
                    pass
            import gc as _gcp
            try:
                _gcp.collect()
            except Exception:
                pass
        else:
            try:
                print(f"    [!] {ep} در این ORT نیست (available={avail}) → CPU")
            except Exception:
                pass

# speed — EPها از انتخابگرِ مرکزیِ _best_providers_for
# می‌آیند (TensorRT/CUDA/ROCm/MIGraphX/Dml/… بر اساسِ آنچه واقعاً
# نصب است + XNNPACKِ امولاتور + CPU همیشه آخر) — به‌جای چکِ
# هاردکدِ CUDA که بقیهٔ EPهایِ GPU را از قلم می‌انداخت.
    providers = _best_providers_for("lama", prefer_gpu=want)
# مستنداتِ رسمیِ DirectML: «بهینه‌سازیِ الگویِ حافظه
# (enable_mem_pattern) برایِ سشنهایِ DML باید خاموش باشد» — پیشفرضِ
# PC روشن است و سشنِ DML را ناپایدار میکند.
    if "DmlExecutionProvider" in providers:
        try:
            so.enable_mem_pattern = False
        except Exception:
            pass
# speed (SRV-G phase2) — CUDA EP options
# (cudnn_conv_use_max_workspace=1) + XNNPACKِ A/B (intra=فیزیکی)
    _popts = _build_provider_options(providers)

    try:
# کشِ مدلِ بهینه‌شده (گوشی: createSession تا 67s طول
# می‌کشد؛ بارهایِ بعدی از فایلِ بهینه‌شده ساخته می‌شوند)
        sess = _lama_session_cached(model_path, so, providers,
                                    provider_options=_popts)
    except Exception as e:
        print(f"[!] InferenceSession GPU ناموفق ({e}) → CPU")
        if "DmlExecutionProvider" in (providers or []):
# شکستِ «همین مدل» رویِ DML نباید پرچمِ سراسری را
# مسموم کند (لاگِ 232: شکستِ دیتکتورِ int8 باعث شد LaMa هم
# بی‌دلیل CPU شود) — هر مدلی پشتیبانیِ اپراتورهایِ خودش را
# دارد. بازسازیِ CPU و خروجِ مستقیم.
            _so233c = _ort_session_options(threads, prefer_gpu=False)
            return ort.InferenceSession(
                model_path, sess_options=_so233c,
                providers=["CPUExecutionProvider"])
        _ORT_CUDA_OK = False
        sess = ort.InferenceSession(
            model_path, sess_options=so, providers=["CPUExecutionProvider"]
        )

    active = list(sess.get_providers())
# پروبِ واقعیِ اینفرنس رویِ سشنِ DML: «ساخته‌شدنِ سشن»
# کافی نیست (لاگِ 232: سشنهایِ det/rec ساخته شدند ولی اولین Run با
# 887A0006 مرد). یک اینفرنسِ دامیِ کوچک (نتیجه در دیسک-کش:
# .dmlprobe)؛ شکست → «همین مدل» رویِ CPU بازساخته میشود بدونِ
# مسموم‌کردنِ بقیهٔ مدلها. CUDA/TRT/CPU دست‌نخورده.
    if "DmlExecutionProvider" in active:
        try:
            if not _dml_probe_model(model_path):
                print("[!] اینفرنسِ آزمایشیِ DirectML رویِ این مدل ناموفق "
                      "→ همین مدل رویِ CPU")
                _so233c = _ort_session_options(threads, prefer_gpu=False)
                return ort.InferenceSession(
                    model_path, sess_options=_so233c,
                    providers=["CPUExecutionProvider"])
        except Exception:
            pass
# DML هم مثلِ CUDA «سشنِ GPUِ موفق» است (AMD/Intel رویِ
# ویندوز): قبلاً سشنِ سالمِ Dml باعثِ چاپِ «CUDA ساخته نشد» و
# قفلِ _ORT_CUDA_OK=False → همهٔ سشنهایِ بعدی CPU میشدند.
    if want and ("CUDAExecutionProvider" in active
                 or "DmlExecutionProvider" in active):
        _ORT_CUDA_OK = True
    elif want:
        _ORT_CUDA_OK = False
        if "DmlExecutionProvider" in (providers or []):
# پیامِ مخصوصِ DML (قبلاً راهنمایِ cuDNNِ CUDA
# چاپ میشد و کاربرِ AMD را گمراه میکرد)
            print(
                f"[!] session providers={active} (GPU ساخته نشد؛ DirectML "
                f"این مدل را قبول نکرد — مدلهایِ int8/کوانتیزه رویِ DML "
                f"پشتیبانی نمیشوند)."
            )
        else:
            print(
                f"[!] session providers={active} (GPU ساخته نشد؛ "
                f"اغلب کمبود cuDNN/cublas رویِ CUDA). "
                f"امتحان: pip install 'onnxruntime-gpu[cuda,cudnn]==1.26.0'"
            )
    return sess

def _cpu_thread_fallback(session, model_path: str, use_threads: int,
                         allow_bump: bool = True):

    try:
# x86_64: بازسازیِ سشنِ CPU = SIGFPE → دست‌نخورده برگرد
        import platform as _pf
        if _on_android() and _pf.machine().lower() in ("x86_64", "amd64"):
            return session, use_threads
        provs = list(session.get_providers())
        _cap = 4 if _on_android() else 8
        cpu_n = max(1, min(_cap, os.cpu_count() or 4))
# (SRV-H4) — شرطِ e32bccf بازگشت (گاردِ use_threads>0یِ
# SRV-G حذف شد؛ use_threads در تماس‌گیرنده‌ها همیشه ≥1 clamp شده)
        if (allow_bump and "CUDAExecutionProvider" not in provs
                and use_threads < cpu_n):
            print(f"    [*] اینپینت روی CPU است → threads: {use_threads} → {cpu_n}")
            return _make_ort_session(model_path, prefer_gpu=False, threads=cpu_n), cpu_n
    except Exception:
        pass
    return session, use_threads

class LamaONNX:

    REPO = "Carve/LaMa-ONNX"
    FILE = "lama_fp32.onnx"

    def __init__(self, model_path: Optional[str] = None, prefer_gpu: bool = True,
                 size: int = 512, threads: int = 4, cache_dir: Optional[str] = None):
        self.prefer_gpu = bool(prefer_gpu)
        self.size = 256 if not prefer_gpu else size
        if not model_path or not os.path.isfile(model_path):
            model_path = self._download_model(cache_dir=cache_dir)
        self.model_path = model_path

        if not prefer_gpu:
            try:
                use_threads = int(os.environ.get("MANGA_LAMA_THREADS", "0") or 0)
            except Exception:
                use_threads = 0
            if use_threads <= 0:
                use_threads = 2
            use_threads = max(1, min(use_threads, os.cpu_count() or 4))
        else:
            use_threads = max(1, int(threads))
        self.session = _make_ort_session(model_path, prefer_gpu=prefer_gpu,
                                         threads=use_threads,
                                         ep=_resolve_lama_ep(),
                                         ep_ab=_is_auto_ep())
        self.session, use_threads = _cpu_thread_fallback(
            self.session, model_path, use_threads, allow_bump=False)
        print(
            f"[+] LaMa ONNX آماده | providers={self.session.get_providers()} | "
            f"threads={use_threads} | max_size={self.size}"
        )
        names = [i.name for i in self.session.get_inputs()]
        self._in_image = names[0]
        self._in_mask = names[1] if len(names) > 1 else "mask"
        for n in names:
            low = n.lower()
            if "mask" in low:
                self._in_mask = n
            elif "image" in low or "img" in low:
                self._in_image = n

        self._fixed_size = False
        try:
            for inp in self.session.get_inputs():
                dims = list(inp.shape)[-2:]
                fixed = [d for d in dims if isinstance(d, int) and d > 0]
                if len(fixed) == 2 and fixed[0] == fixed[1] and fixed[0] >= 64:
                    self.size = fixed[0]
                    self._fixed_size = True
                    break
        except Exception:
            pass

    @classmethod
    def _download_model(cls, cache_dir: Optional[str] = None) -> str:
        from pathlib import Path
        cache_root = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "manga_translator_models"
        cache_root.mkdir(parents=True, exist_ok=True)

        _m = _mirror_model(cls.FILE)
        if _m:
            return _m
        print(f"[*] دانلود مدل LaMa ONNX از {cls.REPO} ...")
        if hf_hub_download is None:
            raise RuntimeError("huggingface_hub لازم است")
        cand = hf_hub_download(repo_id=cls.REPO, filename=cls.FILE, cache_dir=cache_dir)
        try:
            import shutil as _sh
            _dst = os.path.join(_model_cache_dir("det_models"), cls.FILE)
            if not os.path.isfile(_dst):
                _sh.copyfile(cand, _dst)
        except Exception:
            pass
        return cand

    def _pick_size(self, w: int, h: int) -> int:
        m = max(int(w), int(h))
        if getattr(self, "_fixed_size", False):
            return self.size
        if not self.prefer_gpu:
            return 256
        if m <= 180:
            return 256
        if m <= 320:
            return 384
        return min(self.size, 512)

    def __call__(self, image, mask):
        if isinstance(image, np.ndarray):
            if image.ndim == 3 and image.shape[2] in (3, 4):
                img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = np.array(image.convert("RGB"))
        if isinstance(mask, np.ndarray):
            if mask.ndim == 3:
                mask_u8 = mask[..., 0] if mask.shape[2] == 1 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            else:
                mask_u8 = mask
        else:
            mask_u8 = np.array(mask.convert("L"))
        if mask_u8.shape != img_rgb.shape[:2]:
            raise ValueError("Image and mask dimensions must match")
        original_mask = mask_u8 > 0
        if not np.any(original_mask):
            return Image.fromarray(img_rgb.copy())
        orig_size = (img_rgb.shape[1], img_rgb.shape[0])
        run_size = self._pick_size(orig_size[0], orig_size[1])
        if not self.prefer_gpu and not getattr(self, "_fixed_size", False):
            cov = float(np.count_nonzero(original_mask)) / float(original_mask.size)
            if cov > 0.22:
                run_size = 512

        scale = run_size / max(orig_size)
        rw, rh = (max(1, round(d * scale)) for d in orig_size)
        interp = cv2.INTER_AREA if max(img_rgb.shape[:2]) > run_size else cv2.INTER_CUBIC
        img_np = cv2.resize(img_rgb, (rw, rh), interpolation=interp)
        mask_interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_NEAREST_EXACT
        msk = (cv2.resize(original_mask.astype(np.float32), (rw, rh),
                          interpolation=mask_interp) > 0).astype(np.uint8)
        img_np = cv2.copyMakeBorder(img_np, 0, run_size - rh, 0, run_size - rw, cv2.BORDER_REFLECT)

        msk = cv2.copyMakeBorder(msk, 0, run_size - rh, 0, run_size - rw, cv2.BORDER_REFLECT)
        img_np[msk > 0] = 0

        img_in = img_np.astype(np.float32) / 255.0
        mask_in = msk.astype(np.float32)
        img_in = img_in.transpose(2, 0, 1)[None]
        mask_in = mask_in[None, None]
# رویِ DML فقط زیرِ قفل (اجرایِ موازی ممنوع)
        out = _dml_run(self.session,
                       {self._in_image: img_in, self._in_mask: mask_in})[0]

        o = out[0].transpose(1, 2, 0).astype(np.float32)
        try:
            if float(np.max(o)) <= 1.5:
                o = o * 255.0
        except Exception:
            pass
        out = np.clip(o, 0, 255).astype(np.uint8)

        predicted = cv2.resize(out[:rh, :rw], orig_size, interpolation=cv2.INTER_LANCZOS4)
        result = img_rgb.copy()
        result[original_mask] = predicted[original_mask]
        return Image.fromarray(result)

class LamaMangaONNX:

    URL = ("https://github.com/amirwolf512k/Manga-AutoTranslate/"
           "releases/download/models/lama-manga-dyn.onnx")
# واریانتِ «بدونِ DFT» (همان وزنهای big-lama؛ بلوکهایِ
# Fourier به ماتمولِ کسینوسی/سینوسی صادر شدهاند — فایلِ عمومیِ
# اپِ مرجع، وزنها Apache-2.0).
# وریفایِ عددی (scripts/lama_equiv.py): خروجی در برابرِ lama-manga-dyn
# رویِ ورودیِ تصادفی 384×384 → cosine=1.0000 MAE=0.002؛ سرعتِ CPU:
# 2.0s در برابرِ 8.2s (~۴×). DFT (144 نود) رویِ CPU/ARM گوشی سم است.
    NOFFT_URL = ("https://github.com/amirwolf512k/Manga-AutoTranslate/"
                 "releases/download/models/lama-manga-nofft.onnx")
    FALLBACK_URL = "https://huggingface.co/mayocream/lama-manga-onnx/resolve/main/lama-manga.onnx"
    SIZE = 512

    @staticmethod
    def _want_nofft() -> bool:
        """: پیشفرضِ همهجا «بدونِ DFT» — همان وزنهایِ big-lama با
        بلوکهایِ Fourier به ماتمولِ کسینوسی/سینوسی؛ وریفایِ عددیِ
        scripts/lama_equiv.py: cosine=1.0000 MAE=0.002 در برابرِ dyn →
        خروجی و سبکِ پاکسازی دستنخورده، CPU چند برابر سریعتر (8.2s→2.0s).
        MANGA_LAMA_NOFFT=0 برایِ برگشتِ دستی به dyn (مثلاً GPU که DFT را
        ارزان میدهد)."""
        _env = str(os.environ.get("MANGA_LAMA_NOFFT", "") or "").strip()
        if _env == "1":
            return True
        if _env == "0":
            return False
        return True

    def __init__(self, model_path: Optional[str] = None, prefer_gpu: bool = True,
                 threads: int = 4, cache_dir: Optional[str] = None):
        self.prefer_gpu = bool(prefer_gpu)
        if not model_path or not os.path.isfile(model_path):
            model_path = self._download_model(cache_dir=cache_dir)
        self.model_path = model_path
        if not prefer_gpu:
            try:
                use_threads = int(os.environ.get("MANGA_LAMA_THREADS", "0") or 0)
            except Exception:
                use_threads = 0
            if use_threads <= 0:
# نخِ صریحِ فراهم‌شده از _get_lama(threads=…) محترم است —
# وقتی پچِ موازی کم است باید هر پچ چندنخی شود (هسته‌های بیکار نماند)
                if threads and int(threads) > 0:
                    use_threads = max(1, min(int(threads), os.cpu_count() or 4))
                else:
# PC تا ۴ نخ (با nofft چند برابر سریعتر میشود
# اندروید مثلِ قبل ۱ — گاردِ رم/بزرگ.لیتلِ خودش را دارد)
                    _cap = 1 if _on_android() else 4
                    use_threads = max(1, min(_cap, os.cpu_count() or 4))
        else:
            use_threads = max(1, int(threads or 1))
        self.thr_used = int(use_threads)
        self.ep_used = None
        try:
            self.ep_used = _resolve_lama_ep()
        except Exception:
            self.ep_used = None
        self.session = _make_ort_session(model_path, prefer_gpu=prefer_gpu,
                                         threads=use_threads, ep=self.ep_used,
                                         ep_ab=_is_auto_ep())
        self.session, use_threads = _cpu_thread_fallback(
            self.session, model_path, use_threads, allow_bump=False)
# صداقتِ ep_used: رویِ اندروید _resolve_lama_ep مثلاً
# Xnnpack/Nnapi برمی‌گرداند ولی _make_ort_session با کشِ «cpu» به
# CPUExecutionProvider سقوط می‌کند و ep_used همان EPِ درخواستی
# می‌ماند → شرطِ سوئیچِ نخِ _get_lama («فقط رویِ CPU») برای همیشه
# رد می‌شد و زمان‌بند روی «۲ پچ × ۴ نخ»یِ کند می‌ماند (لاگِ POCO F4:
# strip ۸۲.۳s!). حالا EPِ واقعیِ سشن ملاک است.
        try:
            _aps = [str(p) for p in self.session.get_providers()]
            if _aps and all(p.lower().startswith("cpu") for p in _aps):
                self.ep_used = None
        except Exception:
            pass
        self.thr_used = int(use_threads)  # fallback ممکن است نخ را عوض کند
        names = [i.name for i in self.session.get_inputs()]
        self._in_image = names[0]
        self._in_mask = names[1] if len(names) > 1 else "mask"
# باکتِ شکلِ ثابت برایِ xnnpack: هر ورودیِ LaMa دقیقاً
# _static_bucket×_static_bucket پد می‌شود تا EPِ xnnpack که با
# شکلِ داینامیک ORT_FAIL می‌دهد واقعاً کار کند (پچِ LaMa زنده
# می‌ماند → بدونِ فال‌بکِ OpenCV → بدونِ لکهٔ قرمز + سریع‌تر).
        self._static_bucket = 0
# پچِ تطبیقیِ LaMa (فقط اندروید — MANGA_LAMA_PATCH512):
# پچِ 384 کلِ ورودی را به مقیاسِ ~0.5 (بلوکِ تمامعرض) و ~0.2
# (گروهِ پراکنده) له میکند → LaMa «متنِ قلابی» میسازد (لکهٔ
# کثیف). با رمِ آزادِ ≥1200MB و ≥۶ هسته، پچِ 512 (کیفیتِ
# بالاتر) امن است؛ گوشیِ کم‌رم مثلِ قبل 384 میماند. env دستی
# (MANGA_LAMA_PATCH_SIDE) همیشه حاکم است.
        try:
            if (_on_android()
                    and not os.environ.get("MANGA_LAMA_PATCH_SIDE")
                    and _android_gate("MANGA_LAMA_PATCH512")):
                _free_mb2 = 0
                with open("/proc/meminfo", "r") as _mi2:
                    for _ln2 in _mi2:
                        if _ln2.startswith("MemAvailable:"):
                            _free_mb2 = int(_ln2.split()[1]) // 1024
                            break
                if _free_mb2 >= 1200 and (os.cpu_count() or 2) >= 6:
                    os.environ["MANGA_LAMA_PATCH_SIDE"] = "512"
                    os.environ["MANGA_LAMA_STATIC_SIDE"] = "512"
                    globals()["_LAMA_STATIC_SIDE"] = None  # بازخوانیِ کش
                    print("[*] پچِ تطبیقی LaMa: رمِ آزادِ کافی → 512",
                          flush=True)
        except Exception:
            pass
        try:
            _pv = [str(p).lower()
                     for p in (self.session.get_providers() or [])]
            if _lama_static_side() > 0 and any(
                    p.startswith("xnnpack") for p in _pv):
                self._static_bucket = int(_lama_static_side())
                print(f"[*] LaMa xnnpack → پچِ ثابتِ "
                      f"{self._static_bucket}×{self._static_bucket} "
                      f"(ضدِ ORT_FAILِ شکلِ داینامیک)", flush=True)
        except Exception:
            self._static_bucket = 0
        self._input_cap = self.SIZE
        try:
            _env_ps = int(os.environ.get("MANGA_LAMA_PATCH_SIDE", "0") or 0)
        except Exception:
            _env_ps = 0
        if _env_ps > 0:
            self._input_cap = _env_ps
        elif not prefer_gpu and _on_android():
            self._input_cap = 384
        self._fixed_size = False
        self._dyn_size = 512
        try:
            for inp in self.session.get_inputs():
                dims = list(inp.shape)[-2:]
                fixed = [d for d in dims if isinstance(d, int) and d > 0]
                if len(fixed) == 2 and fixed[0] == fixed[1] and fixed[0] >= 64:
                    self._fixed_size = True
                    self._dyn_size = int(fixed[0])
                    break
        except Exception:
            pass
        print(
            f"[+] مدل پاکسازی آماده | threads={use_threads} | size={self.SIZE}" +
            (f" | سقفِ پچ: {self._input_cap}" if self._input_cap != self.SIZE else "")
        )
# A/B با شکلِ واقعیِ پچ (یک‌بار + کشِ .epab): پروبِ قدیمی
# با شکلِ کوچک بود؛ xnnpack ممکن است «کار کند» ولی از CPUِ چندنخی
# کندتر باشد (لاگِ POCO F4: 28.4s برایِ ۲ پچِ ۳۸۴²). برنده ماندگار
# می‌شود. گیتِ رم: با رمِ آزادِ کم (دو سشن همزمان) A/B نمی‌کنیم.
        try:
            self._ep_real_shape_ab(use_threads)
        except Exception:
            pass
# ══ — dual-device (GPU + CPU همزمان) ══════════════════
# درخواستِ کاربر: «هم GPU هم CPU با هم استفاده کنه واسه پاکسازی
# سریع‌تر». وقتی EPِ سرِ سشن GPU-گونه است (CUDA/DML/NNAPI/XNNPACK)
# یک سشنِ CPUِ دوم ساخته می‌شود و پچ‌هایِ موازیِ همزمان بینِ دو
# دستگاه می‌چرخند. رویِ ساختهٔ CPU-خالص هیچ تغییری نمی‌کند (سشنِ
# دوم ساخته نمی‌شود → رگرسیونِ بیت‌به‌بیت محفوظ). گیتِ رم رویِ
# اندروید: MemAvailable < 2.5GB → نه (دو سشن جا نمی‌شود).
        self.session_cpu = None
        self._sess_rr = 0
        self._sess_rr_lock = threading.Lock()
        try:
            _ghead = _gpu_head_of(self.session)
            if _ghead and _dual_device_enabled() \
                    and (os.cpu_count() or 2) >= 4 \
                    and not _android_x86_emulator():
# رویِ شبیه‌سازِ x86_64 سشنِ CPU-خالص ممنوع است
# (CPU EPِ ORT-android آنجا می‌میرد — درسِ ؛ هنگِ
# گیتِ شبیه‌ساز)؛ رویِ گوشیِ arm64 و PC مشکلی ندارد.
                _free_mb = 0
                try:
                    with open("/proc/meminfo", "r") as _mi:
                        for _ln in _mi:
                            if _ln.startswith("MemAvailable:"):
                                _free_mb = int(_ln.split()[1]) // 1024
                                break
                except Exception:
                    _free_mb = 0
                if (not (_on_android() or _android_like_env())) or \
                        (not _free_mb or _free_mb >= 2500):
                    self.session_cpu = _lama_session_cached(
                        self.model_path,
                        _ort_session_options(max(1, int(use_threads))),
                        ["CPUExecutionProvider"])
                    print(f"[⚡] پاکسازی dual-device: {_ghead} + CPU "
                          f"همزمان (پچ‌ها می‌چرخند)", flush=True)
        except Exception as _e:
            self.session_cpu = None
            print(f"[!] dual-device پاکسازی غیرفعال ({_e})", flush=True)

    def _ep_real_shape_ab(self, threads: int) -> None:
        try:
            if os.environ.get("MANGA_LAMA_AB", "1") == "0":
                return
            _pv = [str(p).lower()
                   for p in (self.session.get_providers() or [])]
            if not any(p.startswith("xnnpack") for p in _pv):
                return
            if not _on_android():
                return
            if _lama_ep_cached(self.model_path) == "cpu":
                return
            if _on_x86():
                return  # A/B با سشنِ CPU رویِ x86 ممکن نیست (SIGFPEِ ORT)
# گیتِ رم: MemAvailable < 1.5GB → A/B نه (دو سشن جا نمی‌شود)
            _free_mb = 0
            try:
                with open("/proc/meminfo", "r") as _mi:
                    for _ln in _mi:
                        if _ln.startswith("MemAvailable:"):
                            _free_mb = int(_ln.split()[1]) // 1024
                            break
            except Exception:
                _free_mb = 0
            if _free_mb and _free_mb < 1500:
                try:
                    print(f"    [*] A/Bِ EP رد شد (رمِ آزاد {_free_mb}MB "
                          f"< 1500MB) — همان EP فعلی", flush=True)
                except Exception:
                    pass
                return
            _side = int(self._static_bucket or _lama_probe_side(True) or 384)
            t_hw = _ep_ab_time(self.session)
            if not (t_hw < float("inf")):
                return
            s_cpu = _lama_session_cached(
                self.model_path,
                _ort_session_options(threads),
                ["CPUExecutionProvider"])
            t_cpu = _ep_ab_time(s_cpu)
            try:
                print(f"    [*] A/Bِ واقعیِ {_side}²: xnnpack {t_hw:.2f}s | "
                      f"CPU {t_cpu:.2f}s", flush=True)
            except Exception:
                pass
            if t_cpu < t_hw * 0.85:
                self.session = s_cpu
                self.ep_used = None
                self._static_bucket = 0
                self.thr_used = max(1, int(threads or 1))
                _lama_ep_store(self.model_path, "cpu")
                try:
                    print(f"[+] LaMa → CPU (سریع‌تر از xnnpack رویِ این "
                          f"دستگاه — ماندگار در .epab)", flush=True)
                except Exception:
                    pass
            else:
                try:
                    del s_cpu
                except Exception:
                    pass
                _lama_ep_store(self.model_path, "xnnpack")
        except Exception:
            pass

    @classmethod
    def _download_model(cls, cache_dir: Optional[str] = None) -> str:
        from pathlib import Path
        cache_root = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "manga_translator_models"
        cache_root.mkdir(parents=True, exist_ok=True)
# واریانتِ بدونِDFT همهجا (خروجیِ عددیِ یکسان با dyn —
# وریفایِ scripts/lama_equiv.py — و CPU چند برابر سریعتر)
# MANGA_LAMA_NOFFT=0 رویِ PC برایِ dynِ قدیمی.
        _nofft = cls._want_nofft()
        dst = cache_root / ("lama-manga-nofft.onnx" if _nofft else "lama-manga-dyn.onnx")
        if dst.is_file() and dst.stat().st_size > 1_000_000:
            print(f"[*] مدل LaMa-Manga ({'بدونِDFT' if _nofft else 'داینامیک'}) از کش: {dst}")
            return str(dst)
        if _nofft:
            print("[*] دانلود مدل LaMa-Manga بدونِDFT (~۲۰۶MB، فقط بار اول) ...")
            urls = (cls.NOFFT_URL, cls.URL,
                    _RAPIDOCR_MIRROR + "lama_fp32.onnx", cls.FALLBACK_URL)
        else:
            print("[*] دانلود مدل LaMa-Manga ONNX داینامیک (~۲۰۶MB، فقط بار اول) ...")
            urls = (cls.URL,
                    _RAPIDOCR_MIRROR + "lama_fp32.onnx",
                    cls.FALLBACK_URL)
        last = None
        for url in urls:
            try:
                host = url.split("/")[2]
                print(f"    دانلود از {host} ...")
                _dl_to(url, str(dst), name="lama_fp32.onnx")
                print(f"[+] مدل LaMa-Manga ذخیره شد: {dst}")
                return str(dst)
            except Exception as e:
                last = e
                print(f"    [!] دانلود از {url.split('/')[2]} نشد: {e}")
                try:
                    if os.path.isfile(str(dst) + ".part"):
                        os.remove(str(dst) + ".part")
                except Exception:
                    pass
        raise RuntimeError(f"دانلود مدل LaMa ناموفق: {last}")

    def _prep_sample(self, image, mask):
        """-speed (SRV-G phase2) — آماده‌سازیِ ورودیِ LaMa-Manga:
        همان کدِ __call__ تا قبل از session.run (بایت‌به‌بایت همان ریاضی).
        خروجی برایِ runِ تکی و batched مشترک است."""
        if isinstance(image, np.ndarray):
            if image.ndim == 3 and image.shape[2] in (3, 4):
                img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = np.array(image.convert("RGB"))
        if isinstance(mask, np.ndarray):
            if mask.ndim == 3:
                mask_u8 = mask[..., 0] if mask.shape[2] == 1 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            else:
                mask_u8 = mask
        else:
            mask_u8 = np.array(mask.convert("L"))
        if mask_u8.shape != img_rgb.shape[:2]:
            raise ValueError("Image and mask dimensions must match")
        original_mask = mask_u8 > 0
        _has_mask = bool(np.any(original_mask))
        oh, ow = img_rgb.shape[:2]
        s = self._dyn_size if self._fixed_size else min(self.SIZE, self._input_cap)
        _mx = max(ow, oh)

        _bucket = int(getattr(self, "_static_bucket", 0) or 0)
        if _bucket and not self._fixed_size:
# همهٔ ورودی‌ها دقیقاً _bucket66×_bucket66 → شکلِ
# ثابت برایِ xnnpack (یک کامپایل، بدونِ ORT_FAILِ شکلِ تازه).
# ماسک در ناحیهٔ پد صفر است و خروجی فقط داخلِ ناحیهٔ اصلی
# برش می‌خورد — ریاضیِ خروجی مثلِ مسیرِ fixed-size است.
            s = _bucket
            scale = s / _mx
            if scale < 1.0:
                rw, rh = max(1, round(ow * scale)), max(1, round(oh * scale))
                img_np = cv2.resize(img_rgb, (rw, rh),
                                    interpolation=cv2.INTER_AREA)
                msk = (cv2.resize(original_mask.astype(np.float32), (rw, rh),
                                  interpolation=cv2.INTER_NEAREST_EXACT)
                       > 0).astype(np.uint8)
            else:
                rw, rh = ow, oh
                img_np = img_rgb.copy()
                msk = original_mask.astype(np.uint8)
            if rh < s or rw < s:
                img_np = cv2.copyMakeBorder(img_np, 0, s - rh, 0, s - rw,
                                            cv2.BORDER_REFLECT)
                msk = cv2.copyMakeBorder(msk, 0, s - rh, 0, s - rw,
                                         cv2.BORDER_CONSTANT, value=0)
        elif not self._fixed_size and _mx <= s:
            _tgt = max(_mx, 128)
            _sc = _tgt / _mx
            if abs(_sc - 1.0) < 1e-6:
                rw, rh = ow, oh
                img_np = img_rgb.copy()
                msk = original_mask.astype(np.uint8)
            else:
                rw, rh = max(1, round(ow * _sc)), max(1, round(oh * _sc))
                img_np = cv2.resize(img_rgb, (rw, rh), interpolation=cv2.INTER_CUBIC)
                msk = (cv2.resize(original_mask.astype(np.float32), (rw, rh),
                                  interpolation=cv2.INTER_NEAREST_EXACT) > 0).astype(np.uint8)
            _pw, _ph = (-rw) % 8, (-rh) % 8
            if _pw or _ph:
                img_np = cv2.copyMakeBorder(img_np, 0, _ph, 0, _pw, cv2.BORDER_REFLECT)
                msk = cv2.copyMakeBorder(msk, 0, _ph, 0, _pw,
                                         cv2.BORDER_CONSTANT, value=0)
        else:
            scale = s / _mx
            rw, rh = max(1, round(ow * scale)), max(1, round(oh * scale))
            interp = cv2.INTER_AREA if _mx > s else cv2.INTER_CUBIC
            img_np = cv2.resize(img_rgb, (rw, rh), interpolation=interp)

            mask_interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_NEAREST_EXACT
            msk = (cv2.resize(original_mask.astype(np.float32), (rw, rh),
                              interpolation=mask_interp) > 0).astype(np.uint8)
            if self._fixed_size:
                img_np = cv2.copyMakeBorder(img_np, 0, s - rh, 0, s - rw, cv2.BORDER_REFLECT)
                msk = cv2.copyMakeBorder(msk, 0, s - rh, 0, s - rw, cv2.BORDER_REFLECT)
            else:
                _pw, _ph = (-rw) % 8, (-rh) % 8
                if _pw or _ph:
                    img_np = cv2.copyMakeBorder(img_np, 0, _ph, 0, _pw,
                                                cv2.BORDER_REFLECT)
                    msk = cv2.copyMakeBorder(msk, 0, _ph, 0, _pw,
                                             cv2.BORDER_CONSTANT, value=0)
        img_np[msk > 0] = 0
        img_in = (img_np.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
        mask_in = msk.astype(np.float32)[None, None]
        return {"img_rgb": img_rgb, "original_mask": original_mask,
                "ow": int(ow), "oh": int(oh), "rw": int(rw), "rh": int(rh),
                "img_in": img_in, "mask_in": mask_in,
                "has_mask": _has_mask}

    def _next_session(self):
        """ — چرخشِ round-robin بینِ سشنِ اصلی (GPU) و سشنِ CPU
        برایِ dual-device. وقتی سشنِ دوم نیست → همان سشنِ اصلی (بدونِ
        هیچ تغییرِ رفتار)."""
        _sc = getattr(self, "session_cpu", None)
        if _sc is None:
            return self.session
        try:
            with self._sess_rr_lock:
                self._sess_rr += 1
                _odd = (self._sess_rr & 1) == 1
        except Exception:
            return self.session
        return _sc if _odd else self.session

    def _run_tensors(self, img_in, mask_in):
        feeds = {self._in_image: img_in, self._in_mask: mask_in}
        _sess = self._next_session()
        try:
# رویِ DML فقط زیرِ قفل (اجرایِ موازی ممنوع —
# پچهایِ موازیِ LaMa همه از همینجا میگذرند)
            return _dml_run(_sess, feeds)[0]
        except Exception:
            if _sess is not self.session:
# سشنِ CPU خراب شد → سشنِ اصلی (امن)
                return _dml_run(self.session, feeds)[0]
            raise

    def run_batch_tensors(self, tensors):
        """-speed (SRV-G phase2) — یک session.run برایِ N پچِ
        «هم‌شکل» (بعدِ batch=N؛ همان پدینگ/همان ترتیب). ورودی: لیستِ
        خروجیِ _prep_sample با tensorهایِ هم‌شکل. خروجی: outِ هر نمونه به
        ترتیبِ ورودی. شکست → exception (تماس‌گیرنده per-sample می‌رود)."""
        if not tensors:
            return []
        _imgs = np.concatenate([t["img_in"] for t in tensors], axis=0)
        _msks = np.concatenate([t["mask_in"] for t in tensors], axis=0)
        _out = self._run_tensors(_imgs, _msks)
        return [_out[i] for i in range(_out.shape[0])]

    def _finish_sample(self, t, out_elem):
        """پس‌پردازشِ خروجیِ مدل برایِ «یک» نمونه — دقیقاً همان کدِ
        __call__ بعد از run (بایت‌به‌بایت)."""
        o = out_elem.transpose(1, 2, 0).astype(np.float32)
        try:
            if float(np.max(o)) > 1.5:
                o = o / 255.0
        except Exception:
            pass
        o = np.clip(o, 0.0, 1.0)
        o = (o * 255).astype(np.uint8)
        predicted = cv2.resize(o[:t["rh"], :t["rw"]], (t["ow"], t["oh"]),
                               interpolation=cv2.INTER_LANCZOS4)
        result = t["img_rgb"].copy()
        result[t["original_mask"]] = predicted[t["original_mask"]]
        return Image.fromarray(result)

    def __call__(self, image, mask):
        t = self._prep_sample(image, mask)
        if not t["has_mask"]:
            return Image.fromarray(t["img_rgb"].copy())
        out = self._run_tensors(t["img_in"], t["mask_in"])
        return self._finish_sample(t, out[0])

class LamaTorch:
    FILE = "big-lama.pt"
    FALLBACK_URL = ("https://github.com/enesmsahin/simple-lama-inpainting/"
                    "releases/download/v0.1.0/big-lama.pt")
    CPU_MAX_SIDE = 1280
    ANDROID_MAX_SIDE = 768

    def __init__(self, model_path: Optional[str] = None, prefer_gpu: bool = True,
                 cache_dir: Optional[str] = None, max_side: Optional[int] = None):
        import torch
        self._torch = torch
        self.device = torch.device(
            "cuda" if (prefer_gpu and torch.cuda.is_available()) else "cpu"
        )
        if not model_path or not os.path.isfile(model_path):
            model_path = self._download_model(cache_dir=cache_dir)
        self.model_path = model_path
        self.model = torch.jit.load(model_path, map_location=self.device)
        self.model.eval()
        if max_side is not None:
            self.max_side = int(max_side)
        elif _IS_ANDROID:
            self.max_side = self.ANDROID_MAX_SIDE
        else:
            self.max_side = None if self.device.type == "cuda" else self.CPU_MAX_SIDE
        print(
            f"[+] big-LaMa (TorchScript) آماده | device={self.device.type} | "
            f"max_side={'کامل' if not self.max_side else self.max_side}"
        )

    @classmethod
    def _download_model(cls, cache_dir: Optional[str] = None) -> str:
        env_p = os.environ.get("LAMA_MODEL")
        if env_p and os.path.isfile(env_p):
            return env_p
        m = _mirror_model(cls.FILE)
        if m:
            return m
        dst = os.path.join(_model_cache_dir("det_models"), cls.FILE)
        if os.path.isfile(dst) and os.path.getsize(dst) > 1_000_000:
            print(f"[*] مدل big-lama.pt از کش: {dst}")
            return dst
        last = None
        for url in (_RAPIDOCR_MIRROR + cls.FILE, cls.FALLBACK_URL):
            try:
                print(f"[*] دانلود مدل big-lama.pt از {url.split('/')[2]} ...")
                _dl_to(url, dst, name=cls.FILE)
                return dst
            except Exception as e:
                last = e
                print(f"    [!] دانلود از {url.split('/')[2]} نشد: {e}")
                try:
                    if os.path.isfile(dst + ".part"):
                        os.remove(dst + ".part")
                except Exception:
                    pass
        raise RuntimeError(f"دانلود big-lama.pt ناموفق: {last}")

    @staticmethod
    def _ceil_mod(x: int, mod: int) -> int:
        return x if x % mod == 0 else (x // mod + 1) * mod

    def __call__(self, image, mask):
        torch = self._torch
        if isinstance(image, np.ndarray):
            if image.ndim == 3 and image.shape[2] in (3, 4):
                img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = np.array(image.convert("RGB"))
        if isinstance(mask, np.ndarray):
            if mask.ndim == 3:
                mask_u8 = mask[..., 0] if mask.shape[2] == 1 else cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            else:
                mask_u8 = mask
        else:
            mask_u8 = np.array(mask.convert("L"))
        if mask_u8.shape != img_rgb.shape[:2]:
            raise ValueError("Image and mask dimensions must match")
        m_full = mask_u8 > 0
        if not np.any(m_full):
            return Image.fromarray(img_rgb.copy())
        oh, ow = img_rgb.shape[:2]

        if max(oh, ow) > 2.5 * min(oh, ow):
            return self._call_banded(img_rgb, m_full)
        return self._call_single(img_rgb, m_full)

    _BAND_OVERLAP = 96

    def _call_banded(self, img_rgb: np.ndarray, m_full: np.ndarray):
        oh, ow = img_rgb.shape[:2]
        out = img_rgb.copy()
        vertical = oh >= ow
        L = oh if vertical else ow
        short = ow if vertical else oh
        band = int(max(1024, min(L, short * 2)))
        ov = self._BAND_OVERLAP
        step = max(1, band - ov)
        starts = list(range(0, L, step))
        if starts and starts[-1] + ov >= L and len(starts) > 1:
            starts.pop()
        for s in starts:
            e = min(L, s + band)
            if vertical:
                sub_img = img_rgb[s:e]
                sub_m = m_full[s:e]
            else:
                sub_img = img_rgb[:, s:e]
                sub_m = m_full[:, s:e]
            if not sub_m.any():
                continue
            res = np.array(self._call_single(sub_img, sub_m))
            core = np.zeros_like(sub_m)
            a = 0 if s == 0 else ov // 2
            b = (e - s) if e == L else (e - s) - ov // 2
            if a >= b:
                a, b = 0, e - s
            if vertical:
                core[a:b, :] = True
            else:
                core[:, a:b] = True
            take = sub_m & core
            if not take.any():
                continue
            if vertical:
                out[s:e][take] = res[take]
            else:
                out[:, s:e][take] = res[take]
        return Image.fromarray(out)

    def _call_single(self, img_rgb: np.ndarray, m_full: np.ndarray):
        torch = self._torch
        oh, ow = img_rgb.shape[:2]

        scale = 1.0
        if self.max_side and max(oh, ow) > self.max_side:
            scale = self.max_side / float(max(oh, ow))
        rw, rh = max(8, int(round(ow * scale))), max(8, int(round(oh * scale)))
        if scale != 1.0:
            interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
            img_np = cv2.resize(img_rgb, (rw, rh), interpolation=interp)
            m0 = cv2.resize(m_full.astype(np.uint8), (rw, rh),
                            interpolation=cv2.INTER_NEAREST) > 0
        else:
            img_np = img_rgb
            m0 = m_full

        ph, pw = self._ceil_mod(rh, 8), self._ceil_mod(rw, 8)
        if (ph, pw) != (rh, rw):
            img_p = np.pad(img_np, ((0, ph - rh), (0, pw - rw), (0, 0)), mode="symmetric")
            msk_p = np.pad(m0.astype(np.float32), ((0, ph - rh), (0, pw - rw)), mode="symmetric")
        else:
            img_p = img_np
            msk_p = m0.astype(np.float32)

        x = torch.from_numpy(np.ascontiguousarray(img_p.astype(np.float32) / 255.0)) \
                 .permute(2, 0, 1)[None].to(self.device)
        mk = torch.from_numpy((msk_p > 0).astype(np.float32))[None, None].to(self.device)
        with torch.inference_mode():
            out = self.model(x, mk)
        res = out[0].permute(1, 2, 0).detach().float().cpu().numpy()
        res = np.clip(res * 255, 0, 255).astype(np.uint8)[:rh, :rw]

        if scale != 1.0:
            res = cv2.resize(res, (ow, oh), interpolation=cv2.INTER_LANCZOS4)
        result = img_rgb.copy()
        result[m_full] = res[m_full]
        return Image.fromarray(result)

class RTDetrV2ONNXDetector:

    DET_REPO = "ogkalu/comic-text-and-bubble-detector"
# «detector-v4.onnx» حذف شد: در «هیچ» منبعی وجود ندارد
# (ریلیزِ mirror: 404؛ APIِ ریپویِ HF هم فقط detector-v4-s_int8 و
# detector.onnx و detector_int8 را دارد) — امتحانِ آن در هر استارتِ
# تازه فقط دو 404ِ بی‌فایده میساخت.
    DET_FILES = ("detector-v4-s_int8.onnx", "detector.onnx")
    CLASS_NAMES = {0: "bubble", 1: "text_bubble", 2: "text_free"}
    INPUT_SIZE = 640
    MAX_DETS = 120

    def __init__(
        self,
        model_path: Optional[str] = None,
        prefer_gpu: bool = True,
        conf_thresh: float = 0.35,
        iou_thresh: float = 0.40,
        threads: int = 4,
        multi_scale: bool = False,
        cache_dir: Optional[str] = None,
    ):
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.multi_scale = multi_scale
        self.INPUT_SIZE = 640

        def _hf_with_timeout(fname: str):
            if hf_hub_download is None:
                raise RuntimeError("huggingface_hub لازم است")
            import concurrent.futures as _cf
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                fut = _ex.submit(
                    hf_hub_download, repo_id=self.DET_REPO,
                    filename=fname, cache_dir=cache_dir,
                )
                try:
                    return fut.result(timeout=240)
                except _cf.TimeoutError:
                    raise RuntimeError("huggingface: تایم‌اوت ۲۴۰s (در ایران قطع است)") from None

        _forced = (os.environ.get("MANGA_DET_MODEL") or "").strip()

# رویِ DirectML (AMD/Intel ویندوز): مدلِ int8 سشنِ DML
# نمیسازد (80070057 — اپراتورهایِ کوانتیزه؛ لاگِ 232 رویِ RX 5700
# XT). این بلوک در «هر دو» مسیر اجرا میشود (مدلِ کش‌شده و دانلودِ
# تازه — باگِ پیشین: فقط مسیرِ دانلود بود و مدلِ int8ِ کش‌شده اصلاً
# GPU امتحان نمیکرد): کاندیدها (مدلِ محلی + fp32هایِ ریپو) با
# «پروبِ واقعی» (سشن + یک اینفرنس؛ نتیجه دیسک-کش) امتحان میشوند و
# اولینِ سالم رویِ GPU میرود. هیچکدام؟ → دیتکتور رویِ CPU (int8
# سریعتر از fp32 رویِ CPU) تا تلاشِ خرابِ GPU پرچمِ «GPU ساخته نشد»
# را قفل نکند و LaMa/OCR آزاد بمانند.
        _dml_skip = False
        try:
            _dml_head = (
                bool(prefer_gpu) and (os.name == "nt") and _ort_has_dml()
                and (_best_providers_for("det", prefer_gpu=True)
                     or [""])[0] == "DmlExecutionProvider")
        except Exception:
            _dml_head = False
        if _dml_head and not _forced:
            _cand = []
            if model_path and os.path.isfile(model_path) \
                    and os.path.getsize(model_path) > 1000:
                _cand.append((os.path.basename(model_path), model_path))
# «detector-v4.onnx» از کاندیدها حذف شد: فایلِ
# مرده — نه در ریلیزِ mirror هست (404) نه در ریپویِ HF. هر
# استارت یک mirror+HFِ بی‌فایده را امتحان میکرد و «ساکت»
            #. کاندیدِ fp32 فقط detector.onnx است
# میانداخت — ریشهٔ
# (160.7MB — همان دیتکتور، بدونِ کوانتیزه).
            for _f in ("detector.onnx",):
                _cand.append((_f, None))
            _seen = set()
            _pick = None
            for _fn, _fp in _cand:
                if not _fn or _fn in _seen:
                    continue
                _seen.add(_fn)
                _c = _fp
                if not _c:
                    try:
                        _c = _mirror_model(_fn)
                    except Exception:
                        _c = None
                if not _c:
                    try:
                        print(f"[*] دانلود {_fn} برایِ GPU (DirectML) ...")
                        _c = _hf_with_timeout(_fn)
                    except Exception as _e:
# دیگر بی‌صدا قورت داده نمیشود؛ در لاگ
# باید دیده شود چرا کاندید رد شد.
                        print(f"    [!] {_fn} از HF هم نیامد: {_e}")
                        _c = None
                if not (_c and os.path.isfile(_c)
                        and os.path.getsize(_c) > 1000):
                    continue
                if _dml_probe_model(_c):
                    _pick = _c
                    break
                print(f"    [~] {os.path.basename(_c)} رویِ DirectML "
                      "پروب نشد → کاندیدِ بعدی …")
            if _pick:
                if model_path and os.path.isfile(model_path) \
                        and os.path.abspath(_pick) != os.path.abspath(model_path):
                    _why = (" (کوانتیزهٔ int8 — 80070057)"
                               if "int8" in os.path.basename(model_path).lower()
                               else "")
                    print(f"[*] {os.path.basename(model_path)}{_why} رویِ "
                          "DirectML سشن نمی‌سازد → نسخهٔ fp32 "
                          f"({os.path.basename(_pick)}) جایگزین شد؛ حجمِ "
                          "fp32 چند برابرِ int8 است (همین دیتکتور، بدونِ "
                          "کوانتیزه) و فقط یک بار دانلود میشود.")
                print(f"[+] DirectML: دیتکتور ({os.path.basename(_pick)}) "
                      f"رویِ GPU پروب شد → همین استفاده میشود.")
                model_path = _pick
            else:
                _dml_skip = True
                print("[*] DirectML مدلِ دیتکتور را قبول نکرد → دیتکتور "
                      "رویِ CPU (همان int8)؛ LaMa/OCR همچنان GPU امتحان "
                      "میشوند.")

        if not model_path or not os.path.isfile(model_path) or os.path.getsize(model_path) < 1000:
            model_path = None
            last_err = None

            files = list(self.DET_FILES)
            if _forced:
                _fb = os.path.basename(_forced)
                files = [_fb] + [f for f in files if f != _fb]

            self.session = None
            for fname in files:
                cand = None
                try:
                    if _forced and fname == os.path.basename(_forced) \
                            and os.path.isfile(_forced):
                        cand = _forced
                    if cand is None:
                        cand = _mirror_model(fname)
                    if not cand:
                        print(f"[*] دانلود مدل RT-DETR ONNX از {self.DET_REPO}/{fname} ...")
                        cand = _hf_with_timeout(fname)
                    if not (cand and os.path.isfile(cand) and os.path.getsize(cand) > 1000):
                        print(f"    [!] {fname} خالی/ناقص بود → دانلود مستقیم...")
                        url = f"https://huggingface.co/{self.DET_REPO}/resolve/main/{fname}"
                        dest = os.path.join(
                            cache_dir or _model_cache_dir("det_models"), fname)
                        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
                        _dl_to(url, dest, name=fname)
                        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
                            cand = dest
                    if not cand:
                        continue
                    try:
                        _sess = _make_ort_session(
                            cand,
                            prefer_gpu=(False if _dml_skip else prefer_gpu),
                            threads=threads,
                            ep=_resolve_lama_ep(), ep_ab=_is_auto_ep())
                    except Exception as _se:
                        print(f"    [!] {fname} سشن ONNX نساخت ({_se}) → فایل بعدی")
                        try:
                            if os.path.isfile(cand) and cand.endswith(".onnx"):
                                os.remove(cand)
                        except Exception:
                            pass
                        continue
                    model_path, self.session = cand, _sess
                    break
                except Exception as e:
                    last_err = e
                    print(f"    [!] {fname} پیدا نشد: {e}")
            if not (model_path and self.session):
                raise RuntimeError(
                    f"نتوانست مدل RT-DETR را از {self.DET_REPO} دانلود کند: {last_err}"
                )
        else:
# اگر پروبِ DML مردود شد (int8)، حتی امتحانِ GPU هم
# نکن (ارورِ 80070057 و پیامِ گمراه‌کننده نمیآید؛ مستقیم CPU)
            self.session = _make_ort_session(
                model_path,
                prefer_gpu=(False if _dml_skip else prefer_gpu),
                threads=threads,
                ep=_resolve_lama_ep(), ep_ab=_is_auto_ep())

        self.model_path = model_path
        try:
            print(f"[+] مدل تشخیص حباب: {os.path.basename(self.model_path)}")
        except Exception:
            pass
        in_names = [i.name for i in self.session.get_inputs()]
        self._in_images = "images" if "images" in in_names else in_names[0]
        self._in_sizes = "orig_target_sizes" if "orig_target_sizes" in in_names else (
            in_names[1] if len(in_names) > 1 else None
        )

    def _preprocess(self, image_bgr: np.ndarray):
        h0, w0 = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.INPUT_SIZE, self.INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
        arr = resized.astype(np.float32) / 255.0
        arr = arr.transpose(2, 0, 1)[None]
        orig_size = np.array([[w0, h0]], dtype=np.int64)
        return arr, orig_size, h0, w0

    def _parse_outputs(self, outputs, h0: int, w0: int, threshold: float) -> List[dict]:
        if not outputs or len(outputs) < 3:
            return []

        def _squeeze(a):
            a = np.asarray(a)
            if a.ndim >= 2 and a.shape[0] == 1:
                a = a[0]
            return a

        labels = _squeeze(outputs[0])
        boxes = _squeeze(outputs[1])
        scores = _squeeze(outputs[2])
        if scores.ndim == 1 and labels.ndim == 1 and boxes.ndim == 2:
            pass
        elif boxes.ndim == 1:
            labels, boxes, scores = _squeeze(outputs[1]), _squeeze(outputs[0]), _squeeze(outputs[2])

        raw: List[dict] = []
        n = min(len(labels), len(boxes), len(scores))
        for i in range(n):
            conf = float(scores[i])
            if conf < float(threshold):
                continue
            lab = int(labels[i])
            name = self.CLASS_NAMES.get(lab, "text_bubble")
            if name == "bubble":
                if conf < 0.48:
                    continue
                name = "text_bubble"
            box = boxes[i]
            if len(box) < 4:
                continue
            x1, y1, x2, y2 = [float(v) for v in box[:4]]
            if 0.0 <= x1 <= 1.5 and 0.0 <= x2 <= 1.5 and x2 <= 2.0:
                x1, x2 = x1 * w0, x2 * w0
                y1, y2 = y1 * h0, y2 * h0
            x1 = int(max(0, min(w0 - 1, round(x1))))
            y1 = int(max(0, min(h0 - 1, round(y1))))
            x2 = int(max(0, min(w0, round(x2))))
            y2 = int(max(0, min(h0, round(y2))))
            if x2 - x1 < 12 or y2 - y1 < 12:
                continue
            bw, bh = x2 - x1, y2 - y1
            if bw * bh < 400:
                continue
            ar = bw / max(1, bh)
            if 0.75 <= ar <= 1.35:
                shape = "circle"
            elif ar > 1.6 or ar < 0.55:
                shape = "box"
            else:
                shape = "round"
            raw.append({
                "class_id": lab,
                "class_name": name,
                "confidence": conf,
                "rect": [x1, y1, x2, y2],
                "shape_type": shape,
                "mask_poly": None,
            })
        return self._nms(raw, self.iou_thresh)

    @staticmethod
    def _nms(boxes, iou_thresh: float):
        if not boxes:
            return []

        def iou(a, b):
            xA = max(a[0], b[0]); yA = max(a[1], b[1])
            xB = min(a[2], b[2]); yB = min(a[3], b[3])
            inter = max(0, xB - xA) * max(0, yB - yA)
            if inter == 0:
                return 0.0
            areaA = (a[2] - a[0]) * (a[3] - a[1])
            areaB = (b[2] - b[0]) * (b[3] - b[1])
            return inter / float(areaA + areaB - inter)

        priority = {"text_bubble": 2, "text_free": 1, "bubble": 0}
        boxes = sorted(
            boxes,
            key=lambda x: (priority.get(x["class_name"], 0), x["confidence"]),
            reverse=True,
        )
        keep, pool = [], list(boxes)
        while pool:
            best = pool.pop(0)
            keep.append(best)
            pool = [b for b in pool if iou(best["rect"], b["rect"]) < iou_thresh]
        return keep[: RTDetrV2ONNXDetector.MAX_DETS]

    def _detect_single(self, image_bgr: np.ndarray, threshold: float):
        im_data, orig_size, h0, w0 = self._preprocess(image_bgr)
        feeds = {self._in_images: im_data}
        if self._in_sizes is not None:
            feeds[self._in_sizes] = orig_size
# رویِ DML فقط زیرِ قفل (اجرایِ موازی ممنوع)
        outputs = _dml_run(self.session, feeds)
        return self._parse_outputs(outputs, h0, w0, threshold)

    TILE_HEIGHT = 1680
    TILE_OVERLAP = 520
    TILE_MIN_GAIN = 1.25

    def detect(self, image_bgr: np.ndarray, fast: bool = False):
# fast=True → فقط یک مقیاس (بدون پاس دوم multi_scale) — برای برش امن
# که فقط محل حباب‌ها را می‌خواهد؛ ~۲× سریع‌تر روی CPU.
        h = int(image_bgr.shape[0])
        if h > int(self.TILE_HEIGHT * self.TILE_MIN_GAIN):
            return self._detect_tiled(image_bgr, fast=fast)
        return self._detect_plain(image_bgr, fast=fast)

    def _detect_tiled(self, image_bgr: np.ndarray, fast: bool = False):
        h, w = image_bgr.shape[:2]
        tile_h = int(self.TILE_HEIGHT)
        overlap = int(self.TILE_OVERLAP)
        step = max(500, tile_h - overlap)

        tiles = []
        core_start = 0
        while core_start < h:
            core_end = min(core_start + tile_h, h)
            ys = max(0, core_start - (overlap if core_start > 0 else 0))
            ye = min(h, core_end + (overlap if core_end < h else 0))
            tiles.append((core_start, core_end, ys, ye))
            if core_end >= h:
                break
            core_start += step

        _tw = 1
        try:
            if len(tiles) > 1:
                if _on_android():
                    _tw = 2
                else:
                    _tw = max(2, min(3, (os.cpu_count() or 2) // 2))
        except Exception:
            _tw = 1
        _tw = max(1, min(_tw, len(tiles)))
        if _tw > 1:
            with ThreadPoolExecutor(max_workers=_tw) as _dex:
                _results = list(_dex.map(
                    lambda _t: self._detect_plain(_t, fast=fast),
                    [image_bgr[ys:ye] for (_cs, _ce, ys, ye) in tiles]))
        else:
            _results = [self._detect_plain(image_bgr[ys:ye], fast=fast)
                        for (_cs, _ce, ys, ye) in tiles]

        all_boxes: List[dict] = []
# جعبههایِ «ردشدهٔ لبهٔ کاشی» جدا جمع میشوند تا در
# پایان، اگر هیچ کاشیِ دیگری همان ناحیه را نپوشانده باشد، نجات
# بیابند (ریشهٔ «یک متن نمیبینه رد میشه»: پاراگرافِ «1. AUTHORITY
# TO IMMEDIATELY SEPARATE…» در img4 فقط در کاشیِ [0,2200] دیده
# میشد (conf=0.65) ولی مرکزش ۱۶px بعد از قلمروِ ادعای آن کاشی
# (core_end+0.35×overlap) میفتاد و کاشیِ صاحبِ ناحیه هم چیزی
# تشخیص نمیداد → متن کلاً حذف میشد؛ حالتِ تکی (عکسِ برنده-نقطه)
# همان متن را پیدا میکرد و کاربر میگفت «تکی بدم همشو پیدا
# میکنه»).
        _edge_rejects: List[dict] = []
        for (core_start, core_end, ys, ye), tile_boxes in zip(tiles, _results):
            for b in tile_boxes:
                x1, y1, x2, y2 = b["rect"]
                cy = ys + (y1 + y2) / 2.0
                margin = overlap * 0.35
                nb = dict(b)
                nb["rect"] = [x1, y1 + ys, x2, y2 + ys]
                if (core_start - margin) <= cy < (core_end + margin):
                    all_boxes.append(nb)
                else:
                    _edge_rejects.append(nb)

        merged = self._nms(all_boxes, max(0.40, self.iou_thresh))
# نجاتِ جعبهٔ لبهٔ کاشی: جعبهٔ ردشده فقط وقتی زنده
# میماند که «هیچ» جعبهٔ نگه‌داشته‌شدهای مرکزش را نپوشاند و
# همپوشانیِ IoU≥۰.۲ هم با او نداشته باشد؛ یعنی بدونِ این نجات
# آن ناحیه کلاً بی‌جعبه میماند. جعبههایِ تکراریِ عادی از همین
# پوشش رد میشوند (NMSِ پایانی هم دوباره ضدِ تکرار است).
        if _edge_rejects:
            _rescued = 0
            for _rb in _edge_rejects:
                _rx1, _ry1, _rx2, _ry2 = [float(v) for v in _rb["rect"]]
                _rw = max(1.0, _rx2 - _rx1)
                _rh = max(1.0, _ry2 - _ry1)
                _rarea = _rw * _rh
                _rcx = (_rx1 + _rx2) / 2.0
                _rcy = (_ry1 + _ry2) / 2.0
                _covered = False
                for _kb in merged:
                    _kx1, _ky1, _kx2, _ky2 = [float(v) for v in _kb["rect"]]
                    if (_ky1 - 8.0) <= _rcy <= (_ky2 + 8.0) \
                            and (_kx1 - 8.0) <= _rcx <= (_kx2 + 8.0):
                        _covered = True
                        break
                    _ix1 = max(_rx1, _kx1)
                    _iy1 = max(_ry1, _ky1)
                    _ix2 = min(_rx2, _kx2)
                    _iy2 = min(_ry2, _ky2)
                    if _ix2 > _ix1 and _iy2 > _iy1:
                        _inter = float((_ix2 - _ix1) * (_iy2 - _iy1))
                        _karea = float(max(1, _kx2 - _kx1)
                                       * max(1, _ky2 - _ky1))
                        if _inter / max(1.0, _rarea + _karea - _inter) >= 0.20:
                            _covered = True
                            break
                if not _covered:
                    merged.append(_rb)
                    _rescued += 1
            if _rescued:
                merged = self._nms(merged, max(0.40, self.iou_thresh))
        return MangaTranslator._drop_contained_boxes(merged, contain_thresh=0.65)

    def _detect_plain(self, image_bgr: np.ndarray, fast: bool = False):
        h, w = image_bgr.shape[:2]
        page_area = float(max(1, h * w))

        low_th = max(0.28, self.conf_thresh * 0.75)
        all_boxes = []
        for b in self._detect_single(image_bgr, low_th):
            x1, y1, x2, y2 = b["rect"]
            bw, bh = x2 - x1, y2 - y1
            area = bw * bh
            if b["confidence"] >= self.conf_thresh:
                all_boxes.append(b)
                continue

            if (area < page_area * 0.03 and bw < w * 0.30 and bh < h * 0.22
                    and b["confidence"] >= low_th + 0.04):
                all_boxes.append(b)

        if self.multi_scale and not fast and h >= 1100 and w >= 500:
            sw = max(1, int(w * 0.55))
            sh = max(1, int(h * 0.55))
            if sw >= 280 and sh >= 280:
                small = cv2.resize(image_bgr, (sw, sh), interpolation=cv2.INTER_AREA)
                low_th2 = max(0.30, self.conf_thresh * 0.85)
                inv = 1.0 / 0.55
                for b in self._detect_single(small, low_th2):
                    x1, y1, x2, y2 = b["rect"]
                    b["rect"] = [int(x1 * inv), int(y1 * inv), int(x2 * inv), int(y2 * inv)]
                    bw = b["rect"][2] - b["rect"][0]
                    bh = b["rect"][3] - b["rect"][1]
                    area = bw * bh
                    if (area < page_area * 0.03 and max(bw, bh) < max(w, h) * 0.30
                            and b["confidence"] >= low_th2):
                        all_boxes.append(b)

        cleaned = self._nms(all_boxes, max(0.42, self.iou_thresh))
        return MangaTranslator._drop_contained_boxes(cleaned, contain_thresh=0.68)

# speed — منبعِ اصلیِ مدل‌هایِ OCR = ریلیزِ «models» رویِ GitHub
# (همان amirwolf512k/Manga-AutoTranslate)؛ assetsها دقیقاً با همین نام‌ها
# آنجاست: PP-OCRv6_det_small.onnx (det) / PP-OCRv6_rec_small.onnx (rec
# en+ch) / korean_PP-OCRv5_rec_mobile.onnx / japan_PP-OCRv4_rec_mobile.onnx
# مجموعهٔ مرجع اضافه شد (درخواست: «از همین نسخه که مرجع استفاده
# میکنه استفاده کن»): PP-OCRv6_medium_det_onnx.onnx (59.16MiB) /
# PP-OCRv6_medium_rec_onnx.onnx (73.01MiB) / PP-OCRv5_korean_rec.onnx
# (12.80MiB) = عینِ فایلهایِ رسمیِ PaddlePaddle رویِ HuggingFace که خودِ
# مرجع دانلود میکند (حجمها مو به مو با پوشهٔ مرجع) + ch_PP-OCRv4_det_infer
# .onnx (4.53MiB) + ch_PP-OCRv4_rec_infer.onnx (10.35MiB؛ dict داخلیِ
# metadata = ppocr_keys_v1 با 6623 کاراکتر).
# / ch_ppocr_mobile_v2.0_cls_mobile.onnx (cls — در رانِ عادی استفاده
# نمی‌شود). مسیرِ دوم فقط فال‌بکِ قطعِ گیت‌هاب است (modelscope).
_RAPIDOCR_MIRROR = ("https://github.com/amirwolf512k/Manga-AutoTranslate/"
                    "releases/download/models/")
_RAPIDOCR_MS = ("https://www.modelscope.cn/models/RapidAI/RapidOCR/"
                "resolve/v3.9.2/onnx")
_RAPIDOCR_FILES = {
    "PP-OCRv6_det_small.onnx":
        _RAPIDOCR_MS + "/PP-OCRv6/det/PP-OCRv6_det_small.onnx",
    "PP-OCRv6_rec_small.onnx":
        _RAPIDOCR_MS + "/PP-OCRv6/rec/PP-OCRv6_rec_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "korean_PP-OCRv5_rec_mobile.onnx":
        _RAPIDOCR_MS + "/PP-OCRv5/rec/korean_PP-OCRv5_rec_mobile.onnx",
    "japan_PP-OCRv4_rec_mobile.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/rec/japan_PP-OCRv4_rec_mobile.onnx",
# مجموعهٔ مرجع (منبعِ فالبک = رسمیِ PaddlePaddle/modelscope
# منبعِ اصلی = ریلیزِ «models» خودمان با همین نامها)
    "PP-OCRv6_medium_det_onnx.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_det_onnx"
        "/resolve/main/inference.onnx",
    "PP-OCRv6_medium_rec_onnx.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec_onnx"
        "/resolve/main/inference.onnx",
    "PP-OCRv5_korean_rec.onnx":
        "https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec_onnx"
        "/resolve/main/inference.onnx",
    "ch_PP-OCRv4_det_infer.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx",
    "ch_PP-OCRv4_rec_infer.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx",
# موتورِ «فلاتر-پدل» (flutter-paddle-ocr) = PP-OCRv6 tiny
# github.com/mencomao/flutter-paddle-ocr همان PP-OCRv6 tinyِ ONNXِ
# خالص رویِ ONNX Runtime است، نه Paddle-Lite). منبعِ اصلی = HFِ
# رسمیِ PaddlePaddle (همان الگویِ medium)؛ فالبک = ریلیزِ modelsِ
# خودمان. det 1.7MB + rec 4.3MB — سبکترین جفتِ خانوادهٔ v6.
    "PP-OCRv6_tiny_det.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_tiny_det_onnx"
        "/resolve/main/inference.onnx",
    "PP-OCRv6_tiny_rec.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_tiny_rec_onnx"
        "/resolve/main/inference.onnx",
# dictِ مخصوصِ tiny (۶۹۰۴ نویسه — استخراجشده از inference.ymlِ مدلِ
# رسمی؛ جدا از medium ۱۸۷۰۷ی و small ۶۶۲۳ی) — فقط از ریلیزِ خودمان
    "ppocr_keys_v6_tiny_utf8.txt":
        _RAPIDOCR_MIRROR + "ppocr_keys_v6_tiny_utf8.txt",
# charsetِ رسمیِ PP-OCRv6 medium rec (paddleocr.aiِ
# android_deployment: «rec = inference.onnx + inference.yml»)
# ۱۸۷۰۸ نویسه + فاصله. — پلِ PaddleOcrBridge از
# inference.ymlِ باندلشده در assets میخواند (SDKِ رسمی) — این مدخل
# فقط برایِ سازگاریِ نگاشتِ URLهایِ قدیمی مانده است.
    "PP-OCRv6_medium_rec_inference.yml":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec_onnx"
        "/resolve/main/inference.yml",
}

def _pc_det_medium() -> bool:
    """ — سوئیچِ نجاتِ detِ سنگینِ قبلی رویِ PC.

    → پیشفرضِ PC از = عینِ ستِ گوشی (detِ
    PP-OCRv6_small ۱۰MB). با MANGA_OCR_DET_MEDIUM=1 رفتارِ
    ..190 (detِ mediumِ ۵۹MB — مرجع) برگردد (کسانی که detِ
    حداکثری میخواهند؛ CPUهایِ قوی).
    """
    _v = str(os.environ.get("MANGA_OCR_DET_MEDIUM", "") or "").strip().lower()
    return _v in ("1", "true", "yes", "on")

def _rapidocr_model_pair(lang: str, small: bool = False,
                         tiny: bool = False):
    """ — جفتِ (det, rec) بر اساسِ زبان.

     — پیشفرضِ PC = عینِ ستِ گوشی ():
      det = PP-OCRv6_det_small.onnx (۱۰MB — همان detِ گوشی؛ بنچمارکِ
            کلاسِ PCِ قدیم/۲ هسته رویِ ۹ کراپِ lang_zh.jpg:
            detِ medium ۲۹.۷s → detِ small ۱۸.۴s با همان متن — #01 حتی
            تمیزتر: «6 DIALOGUE BUBBLES» کامل)
      recِ en/zh/ja = PP-OCRv6_medium_rec_onnx.onnx (73.01MiB)
      recِ ko = PP-OCRv5_korean_rec.onnx (رسمی، 12.80MiB)
     — zh هم عینِ گوشی شد: جفتِ قدیمیِ ch_PP-OCRv4 ()
    فاصلههایِ لاتین را میبلعید («ONESOURCEART-3PANELS») و پسِ ویرگول
    تکراری میساخت («،自 自己»)؛ v6_medium مو به مو متنِ گوشی را میدهد.
    MANGA_OCR_DET_MEDIUM=1 = detِ mediumِ قبلی (مرجع — ..190).
    small=True (فقط شبیهسازِ x86_64 در CI) = مجموعهٔ سبکِ قبلی تا
    بودجهٔ زمانی و گیتهایِ CI دستنخورده بمانند.
    tiny=True = «فلاتر-پدل» ( — بدونِ تغییر).
    """
    _low = str(lang).lower()
    if tiny:
        _det = "PP-OCRv6_tiny_det.onnx"
        if _low in ("korean", "ko"):
            return _det, "korean_PP-OCRv5_rec_mobile.onnx"
        if _low in ("japan", "ja", "japanese"):
            return _det, "japan_PP-OCRv4_rec_mobile.onnx"
        return _det, "PP-OCRv6_tiny_rec.onnx"
    if small:
        _det = "PP-OCRv6_det_small.onnx"
        if _low in ("korean", "ko"):
            return _det, "korean_PP-OCRv5_rec_mobile.onnx"
        if _low in ("japan", "ja", "japanese"):
            return _det, "japan_PP-OCRv4_rec_mobile.onnx"
        return _det, "PP-OCRv6_rec_small.onnx"
# detِ PC = عینِ گوشی (small ۱۰MB؛ نه mediumِ ۵۹MB)
    _det = ("PP-OCRv6_medium_det_onnx.onnx" if _pc_det_medium()
            else "PP-OCRv6_det_small.onnx")
    if _low in ("korean", "ko"):
        return _det, "PP-OCRv5_korean_rec.onnx"
# ja هم از recِ mediumِ پیشفرض میخواند (بنچمارکِ صفحهٔ
# v6_medium ژاپنیِ مانگا را کاملتر از japan v4 میخواند —
# عینِ تصمیمِ گوشی؛ recِ جداگانهیِ ja حذف شد)
# zh هم از همین rec (عینِ گوشی — جفتِ v4 حذف شد)
    return _det, "PP-OCRv6_medium_rec_onnx.onnx"

def _pc_ocr_small() -> bool:
    """ — مجموعهٔ مدلِ OCRِ PC. → PC هم از
    مجموعهٔ کاملِ medium استفاده میکند (detِ medium + recِ medium —
    همان ستِ مرجع). MANGA_OCR_SMALL=1 یا شبیهسازِ x86_64 (CI) = ستِ سبک
    (small) تا بودجهٔ زمانیِ CI دستنخورده بماند."""
    _v = str(os.environ.get("MANGA_OCR_SMALL", "") or "").strip().lower()
    if _v in ("1", "true", "yes", "on"):
        return True
    if _v in ("0", "false", "no", "off"):
        return False
    return bool(_android_x86_emulator())

def _ocr_det_resize_policy(lang: str):
    """ — سیاستِ تغییرِ اندازهٔ detِ داخلِ RapidOCR رویِ کراپها.

    . ریشه‌یابی با بنچمارکِ واقعیِ img4
    (690×11200 — سندباکسِ ۲هسته، پایپ‌لاینِ کاملِ _extract_regions_from_
    bubbles): پیشفرضِ rapidocr پایتون یعنی Det.limit_type="min" با
    limit_side_len=736 — «هر» کراپی که ضلعِ کوتاهش <736 باشد قبل از det
    بزرگ میشود تا ضلعِ کوتاهش ۷۳۶ شود. کراپِ متعارفِ حباب (پهن اما
    کم‌ارتفاع؛ مثلِ 613×84) با نسبتِ ۸.۷۶× به detِ 736×5376 میرود!
    نتیجه: detِ داخلِ کراپ ۶۰٪+ زمانِ OCR بود (پروفایل: det 5.7s /
    rec 25.2s بعد از فیکس). این همان دلیلی است که «گوشی سریعتر از PC
    استخراج میکرد»: موتورِ اندروید (RapidOcrEngine.kt) از اول
    maxSideLen=960 با سیاستِ max بود و پایتون نه.

    سیاستِ تازه برایِ زبانهایِ لاتین = 960/max — دقیقاً پیشفرضِ رسمیِ
    PaddleOCR («The default setting of the parameters is limit_type=max,
    det_limit_side_len=960» — مستنداتِ inferenceِ PaddleOCR): بزرگنماییِ
    کراپهای کوچک دیگر انجام نمیشود؛ فقط کراپِ بلندتر از ۹۶۰ کوچک
    میشود. بنچمارکِ A/B (متنِ کاملِ مقایسه شد):
      • img4 (انگلیسی، وبتونِ ۱۱۲۰۰px): کلِ استخراج ۹۹.۹s → ۴۳.۲s
        (۲.۳×) و متنِ «بهتر»: ARTCLE9(TEACHERSAUTHORTY)/E7(STUDREPE)ی
        غلط → ARTICLE9(TEACHERS'AUTHORITY) درست + ARTICLE7ی جاافتاده
        پیدا شد (۲۴→۲۶ ناحیه، ۱۰۶→۱۰۹ خط).
      • img6 (کمیکِ انگلیسی): ۳۲.۸s → ۱۴.۷s (۲.۲×)، متنِ همارز
        (فقط جابهجاییِ ترتیبِ واژه در باکسها + ترمیمِ I'Ll→I'll).
      • lang_ja_color (پیشنمایشِ ژاپنیِ ریز 1200×675): متنِ کانجیِ ریز
        به بزرگنمایی نیاز دارد → با 960/max از ۱۰ خط به ۲ خط سقوط
        کرد. پس زبانهایِ CJK (ja/ko/zh/multi) روی همان 736/minِ
        rapidocr میمانند — کیفیتِ امروز، ریسکِ صفر؛ سرعتِ CJK از
        سمتِ مدلها تغییر نمیکند.
    نردبانِ واریانتها (raw→clahe/otsu/inv) و تقویتِ کراپ (scale تا 2.4)
    دستنخوردهاند — همان جبرانِ کیفیتِ قبلی برایِ متنِ ریز.

    اوررایدها: MANGA_OCR_DET_FAST=0 → خاموش (رفتارِ کاملِ قدیم =
    736/min برایِ همه) | MANGA_OCR_DET_LIMIT=N | MANGA_OCR_DET_TYPE=
    min|max (برایِ هر زبان — تستِ دستی). خروجی: dictِ پارامترهایِ
    rapidocr یا None (= پیشفرضِ rapidocr)."""
    try:
        _v = str(os.environ.get("MANGA_OCR_DET_FAST", "")).strip().lower()
        if _v in ("0", "false", "no", "off"):
            return None
    except Exception:
        pass
    _low = str(lang or "").lower()
    _cjk = _low in ("japan", "ja", "japanese", "ko", "korean",
                          "zh", "ch", "chinese", "ch_sim", "zh_hans",
                          "zh_hant", "zh-tw", "zh_tw", "multi")
# اوررایدهای صریحِ کاربر
    try:
        _e_lim = int(os.environ.get("MANGA_OCR_DET_LIMIT", "0") or 0)
    except Exception:
        _e_lim = 0
    _e_typ = str(os.environ.get("MANGA_OCR_DET_TYPE", "") or "").strip().lower()
    if _cjk:
# CJK: پیشفرضِ rapidocr (736/min) + اوررایدِ صریحِ کاربر
        if _e_lim > 0 or _e_typ in ("min", "max"):
            out = {}
            if _e_lim > 0:
                out["Det.limit_side_len"] = int(_e_lim)
            if _e_typ in ("min", "max"):
                out["Det.limit_type"] = _e_typ
            return out or None
        return None
# لاتین: 960/maxِ رسمیِ PaddleOCR (اورراید بر آن هم اعمال میشود)
    out = {"Det.limit_side_len": 960, "Det.limit_type": "max"}
    if _e_lim > 0:
        out["Det.limit_side_len"] = int(_e_lim)
    if _e_typ in ("min", "max"):
        out["Det.limit_type"] = _e_typ
    return out

def _latin_lang(tr) -> bool:
    """ — زبانِ صفحه لاتین است؟ (برایِ فیلترِ آشغالِ لاتین
    صفحاتِ ja/ko/zh هرگز این فیلتر را نمیگیرند.)"""
    try:
        _lg = str(getattr(getattr(tr, "ocr", None), "lang", "") or "").lower()
        if not _lg:
            _lg = str(getattr(tr, "lang", "") or "en").lower()
    except Exception:
        _lg = "en"
    return _lg not in ("ja", "japan", "japanese", "ko", "korean",
                       "zh", "ch", "chinese", "ch_sim", "zh_hans",
                       "zh_hant", "zh-tw", "zh_tw")

def _line_is_foreign(bb, block_rects, own_area: float) -> bool:
    """ — مالکیتِ خط. خطی که مرکزش داخلِ مستطیلِ «ناحیهٔ
    همسایهٔ» تنگتر است (مساحتِ همسایه < ۸۵٪ ناحیهٔ خودی) و حداقل ۴۵٪
    خط در آن افتاده، متعلق به همان همسایه است — نه این کراپ. ریشهٔ
    «چرت‌پرت» در img6: متنِ حبابِ کوچکِ «You're the real attraction
    here.» داخلِ کراپِ ناحیهٔ بزرگِ زرد نشت میکرد (rectهای RT-DETR
    همپوشانی دارند)."""
    if not block_rects or bb is None:
        return False
    try:
        cx = (float(bb[0]) + float(bb[2])) * 0.5
        cy = (float(bb[1]) + float(bb[3])) * 0.5
        lw = max(1.0, float(bb[2]) - float(bb[0]))
        lh = max(1.0, float(bb[3]) - float(bb[1]))
        la = lw * lh
    except Exception:
        return False
    for _r in (block_rects or []):
        try:
            bx1, by1, bx2, by2 = [float(v) for v in _r]
            if not (bx1 - 4.0 <= cx <= bx2 + 4.0
                    and by1 - 4.0 <= cy <= by2 + 4.0):
                continue
            ix = max(0.0, min(float(bb[2]), bx2) - max(float(bb[0]), bx1))
            iy = max(0.0, min(float(bb[3]), by2) - max(float(bb[1]), by1))
            if la <= 0 or (ix * iy) / la < 0.45:
                continue
            nb_area = max(1.0, (bx2 - bx1) * (by2 - by1))
            if nb_area < own_area * 0.85:
                return True
        except Exception:
            continue
    return False

def _clamp_lines_to_det(res, box, block_rects=None, tol: float = 10.0):
    """ — استخراج نباید از باکسِ detector بیرون بزند (). دو قاعدهٔ مالکیتِ خط:
      ۱) مرکزِ خط داخلِ باکسِ detectorِ خودِ ناحیه نیست → مالِ این ناحیه
         نیست (کراپِ گسترشیافتهٔ متنِ کج تا ۱۲۰px خطِ مجاور را میخواند؛
         فیلترِ ۱۸۸ فقط «همسایهٔ کوچکتر» را حذف میکند — خطِ همسایهٔ
         بزرگتر مثلِ تایتلِ کجِ کاغذ در ناحیهٔ حبابِ کوچک میماند →
         گسترشِ angle مستطیل را منفجر میکند و mergeِ همپوشانی سه حباب
         را یکجا میگیرد).
      ۲) اگر مرکزِ خط داخلِ باکسِ «کوچکتری» از همسایهها هم هست، خط مالِ
         همان است — دوباره‌پردازیِ deskewِ _ocr_crop از فیلترِ ۱۸۸ رد
         میشود و ناحیهٔ بزرگ (تایتل) خطِ حبابهایِ کوچکِ داخلِ باکسش را
         نگه میدارد → باز همان انفجارِ مستطیل. این قفل بعد ازِ خروجیِ
         نهاییِ _ocr_crop اجرا میشود → همهٔ مسیرها پوشش داده میشوند.
    خط/متن/زاویه/بلوکِ همترازِ خطِ حذفشده با هم میروند."""
    try:
        txt, polys, angs, texts, blks = res
        if not polys or not box or len(box) < 4:
            return res
        if not (len(polys) == len(texts) == len(angs) == len(blks)):
            return res  # ساختارِ غیرمنتظره — دستنخورده (فیلترِ ۱۸۸ پوشش میدهد)
        bx1, by1, bx2, by2 = [float(v) for v in box[:4]]
        own_area = max(1.0, (bx2 - bx1) * (by2 - by1))
        _others = []
        for _r in (block_rects or []):
            try:
                ox1, oy1, ox2, oy2 = [float(v) for v in _r[:4]]
                if ox2 - ox1 > 1.0 and oy2 - oy1 > 1.0:
                    _others.append((ox1, oy1, ox2, oy2,
                                    (ox2 - ox1) * (oy2 - oy1)))
            except Exception:
                continue
        keep = []
        for p in polys:
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                cx = float(pp[:, 0].mean())
                cy = float(pp[:, 1].mean())
            except Exception:
                keep.append(True)
                continue
            if not ((bx1 - tol) <= cx <= (bx2 + tol)
                    and (by1 - tol) <= cy <= (by2 + tol)):
                keep.append(False)  # قاعدهٔ ۱ — بیرونِ باکسِ خودِ ناحیه
                continue
            _stolen = False
            for (ox1, oy1, ox2, oy2, oa) in _others:
                if oa >= own_area:
                    continue  # فقط همسایهٔ کوچکتر مالکیت را میگیرد
                if ((ox1 - tol) <= cx <= (ox2 + tol)
                        and (oy1 - tol) <= cy <= (oy2 + tol)):
                    _stolen = True
                    break
            keep.append(not _stolen)  # قاعدهٔ ۲ — مالِ کوچکترین باکس
        if all(keep):
            return res
        _txt = " ".join(str(texts[i] or "").strip()
                        for i in range(len(polys)) if keep[i]).strip()
        return (_txt,
                [polys[i] for i in range(len(polys)) if keep[i]],
                [angs[i] for i in range(len(angs)) if keep[i]],
                [texts[i] for i in range(len(texts)) if keep[i]],
                [blks[i] for i in range(len(blks)) if keep[i]])
    except Exception:
        return res

def _latin_junk_line(text, region_has_letters: Optional[bool] = None):
    """ — خطِ آشغالِ لاتین («چرت‌پرت») — فقط کلِ خط:
      • بدونِ هیچ حرفِ لاتین و کوتاه (≤۴ نویسه): «23»، «豊»، «H/»
      • همهٔ توکنها ≤۲ حرف و هیچ واکه‌ای ندارند: «FL»، «SS»، «Px»
    خطهایِ واقعی («GO!»، «Wha!?»، «OK») میمانند؛ فقط برایِ صفحاتِ
    لاتین صدا زده میشود (_latin_lang188).

     — عدد/نماد دیگر «حذفِ خط» نیست (و «1233 نباید حذف شه»): سیاستِ عدد/نماد در «سطحِ ناحیه»
    تعیین میشود (source_has_letters + no_touch)، نه در سطحِ خط.
    در ناحیهٔ حرف‌دار، خطِ عدد = محتوای دیالوگ است («19 hi»)؛ در
    ناحیهٔ بی‌حرف، ماندنِ خطها باعث میشود ناحیه «فقط-عدد/نماد» شناخته
    شود (no_touch = دست‌نخورده) نه «OCR-خالی» که پاک میشود.
    پارامترِ region_has_letters: متنِ کلِ ناحیه حرف دارد یا نه؛
    None = رفتارِ قدیمی (برایِ فراخوانی‌های بدونِ متنِ ناحیه)."""
    s = str(text or "").strip()
    if not s:
        return True
    toks = re.findall(r"[A-Za-z]+", s)
    if not toks:
# خطِ عددِ خالص («19»، «10,000»، «۳:۳۰») محتواست:
# در ناحیهٔ حرف‌دار میماند (باید خوانده و پاک شود)؛ در ناحیهٔ
# بی‌حرف هم میماند (تا ناحیه no_touch شود). فقط سمبل/نویسهٔ
# بی‌حرفِ کوتاه (H/، ؟!) در ناحیهٔ حرف‌دار هنوز آشغال است.
        if region_has_letters is False:
            return False
# هر خطِ «دارایِ رقم» محتواست، حتی با نقطه/ویرگولِ
# چسبیده: «.85» (شمارهٔ صفحهٔ img7 روی گوشی — det جعبهٔ عدد و
# تیتر را یکی دیده بود، خطِ «.85» میافتاد ولی ناحیه پاک میشد =
# «میپاکید ولی نمیخواند»). عدد همیشه خوانده میشود؛ فقط خطِ
# بی‌رقمِ بیحرفِ کوتاه (سمبلِ خاموش) آشغال است.
        if re.search(r"\d", s):
            return False
        if re.fullmatch(
                r"[\d\u06F0-\u06F9\u0660-\u0669]"
                r"[\d\u06F0-\u06F9\u0660-\u0669\s.,:'\-]*", s):
            return False
        return len(s) <= 4
# «77,I» / «1,I» — دو digits + حرفِ تک؛ خوانشِ اشتباهِ حرفِ ایتالیک
    _alpha = [c for c in s if c.isascii() and c.isalpha()]
    if sum(c.isdigit() for c in s) >= 2 and len(_alpha) <= 2:
# اگر حرفها فقط I/i/l باشند، خط حذف نمیشود
# به «I» ترمیم میشود («77,I» = «I'll» ناخوانا — لاگ گوشی ۱۸۸).
        if _alpha and all(c in "Iil" for c in _alpha):
            return "I"
# «19 hi» / «19th»: عدد در متنِ حرف‌دار محتواست
# در ناحیهٔ بی‌حرف هم خط میماند تا ناحیه no_touch شود.
        if region_has_letters is not None:
            return False
        return True
    if all(len(t) <= 2 for t in toks):
        _vow = "AEIOUaeiou"
        if not any(any(c in _vow for c in t) for t in toks):
# در ناحیهٔ بیحرف خط نباید بیفتد: «2B» /
# «10,000G» (پسوندِ واحد — source_has_letters آنها را
# بیحرف میشمارد) باید بمانند تا ناحیه no_touch شود و
# دست‌نخورده بماند؛ در ناحیهٔ حرف‌دار همان آشغالِ
# قبلی است («FL»، «SS» — خوانشِ غلطِ هنر).
            if region_has_letters is False:
                return False
            return True
    return False

def _fmt_mb(n: float) -> str:
    return f"{n / (1024 * 1024):.1f}MB"

def _dl_progress(name: str, done: int, total: int, _last: list = [0.0, 0]) -> None:
    import time as _t
    now = _t.time()
    if total > 0:
        pct = min(100, int(done * 100 / total))
        if now - _last[0] < 0.8 and pct - _last[1] < 5 and pct < 100:
            return
        _last[0], _last[1] = now, pct
        print(f"\r    دانلود {name}: {pct}% ({_fmt_mb(done)}/{_fmt_mb(total)})"
              + (" " * 4), end="", flush=True)
    else:
        if now - _last[0] < 1.5:
            return
        _last[0] = now
        print(f"\r    دانلود {name}: {_fmt_mb(done)}", end="", flush=True)

def _dl_to(url, dst, name: str = "", attempts: int = 3):
    """ — دانلودِ مقاوم: (۱) ادامهٔ دانلودِ نیمه‌کاره با هدرِ
    Range — لاگِ کاربر: detector.onnx دو بار تا ~۷۵٪ (121MB از 160.7MB)
    آمد و ریستِ اتصالِ WinError 10054 هر دو بار همه چیز را دور ریخت چون
    .part بعد از شکست حذف میشد و دفعهٔ بعد از صفر شروع میشد؛ (۲) تا
    «attempts» تلاشِ خودکار با مکثِ ۲s — هر تلاش از همان‌جا ادامه
    مییابد (GitHub/HF هر دو به Range جوابِ 206 میدهند). (۳) نشانِِ
    url کنارِ .part (‏.part.url): ادامهٔ دانلود فقط از «همین» url مجاز
    است — الحاقِ بایتهای دو سرورِ مختلف (mirror + HF) = فایلِ خراب؛
    .partِ بی‌نشان یا از سرورِ دیگر → دور ریخته میشود. 416 =
    .partِ بی‌اعتبار → حذف و شروعِ تازه در تلاشِ بعدی."""
    import time as _t
    import urllib.error
    import urllib.request
    if not name:
        name = os.path.basename(dst)
    t0 = _t.time()
    done = 0
    total = 0
    _n = max(1, int(attempts))
    _part = dst + ".part"
    _mark = _part + ".url"
    for _try in range(_n):
        try:
            _start = 0
            if os.path.isfile(_part):
                _same = False
                try:
                    with open(_mark, "r", encoding="utf-8") as _mf:
                        _same = _mf.read().strip() == url.strip()
                except Exception:
                    _same = False
                if _same:
                    _start = os.path.getsize(_part)
                else:
# بی‌نشان یا از سرورِ دیگر → الحاق ممنوع
                    try:
                        os.remove(_part)
                    except Exception:
                        pass
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            if _start > 0:
                req.add_header("Range", f"bytes={_start}-")
            with urllib.request.urlopen(req, timeout=900) as r:
                _code = int(r.getcode() or 200)
                _clen = int(r.headers.get("Content-Length") or 0)
                if _start > 0 and _code == 206:
# ادامهٔ همان فایلِ نیمه‌کاره از همان سرور
                    total = _start + _clen
                    done = _start
                    _mode = "ab"
                else:
# .part نبود یا سرور Range را نگرفد (200) → از صفر
                    total = _clen
                    done = 0
                    _mode = "wb"
                with open(_part, _mode) as f:
# نشانِ منبع — پیش از بایتهای بعدی بنویس تا شکستِ
# میان‌راه نشان را با خود داشته باشد
                    try:
                        with open(_mark, "w", encoding="utf-8") as _mf:
                            _mf.write(url)
                    except Exception:
                        pass
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        _dl_progress(name, done, total)
            if total and done < total:
                raise RuntimeError(f"ناقص: {done}/{total} بایت")
            break
        except Exception as _e:
            if isinstance(_e, urllib.error.HTTPError) \
                    and int(getattr(_e, "code", 0) or 0) == 416 \
                    and os.path.isfile(_part):
# .part از قبل کامل/بی‌اعتبار است → دورش بریز و تازه بگیر
                for _del in (_part, _mark):
                    try:
                        if os.path.isfile(_del):
                            os.remove(_del)
                    except Exception:
                        pass
            if _try + 1 < _n:
                print(f"\n    [!] {name}: قطع شد ({_e}) → "
                      f"تلاشِ {_try + 2}/{_n} از همان‌جا ...")
                _t.sleep(2.0)
                continue
            raise
    if os.path.isfile(_part) and os.path.getsize(_part) > 1000:
        dt = _t.time() - t0
        print(f"\r    ✔ {name}: {_fmt_mb(done)} در {dt:.0f}s" + " " * 8)
        os.replace(_part, dst)
        try:
            if os.path.isfile(_mark):
                os.remove(_mark)
        except Exception:
            pass
        return dst
    raise RuntimeError("فایل ناقص")

def _model_cache_dir(sub):
    d = os.path.join(os.environ.get("MANGA_FILES_DIR") or os.getcwd(), sub)
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def _mirror_model(fname):
    loc = os.path.join(_model_cache_dir("det_models"), fname)
    if os.path.isfile(loc) and os.path.getsize(loc) > 1000:
        return loc
    try:
        print(f"    [mirror] {fname} ...")
        _dl_to(_RAPIDOCR_MIRROR + fname, loc)
        return loc
    except Exception as e:
        print(f"    [!] mirror نشد: {e}")
# .part «حفظ» میشود تا دانلودِ بعدی با Range از
# همان‌جا ادامه یابد (قبلاً حذف میشد و 121MBِ نیمه‌کاره دور
# ریخته میشد).
        return None

# قفلِ تک‌نمونهٔ دانلودِ هر فایل: دو ورکرِ همزمان که همان
# فایلِ مدل را میخواهند، هر دو «همان فایل را دانلود میکردند»؛ یکی تمام
# میشد و .part را rename میکرد، دومی وسطِ نوشتن/rename با «[Errno 2] No such
# file or directory … .part» میرفت و لاگِ «دانلود ناموفق — اینترنت/VPN
# را چک کن» میداد در حالیکه فایل سالم بود. حالا هر فایل قفلِ خودش را
# دارد؛ نفرِ دوم منتظر میماند و بعد داخلِ قفل «از قبل هست» را میبیند.
_DL_FILE_LOCKS: Dict[str, threading.Lock] = {}
_DL_FILE_LOCKS_GUARD = threading.Lock()

def _dl_file_lock(dst: str) -> threading.Lock:
    with _DL_FILE_LOCKS_GUARD:
        lk = _DL_FILE_LOCKS.get(dst)
        if lk is None:
            lk = threading.Lock()
            _DL_FILE_LOCKS[dst] = lk
        return lk

def _ensure_rapidocr_models(mdir, files=None):
    wanted = files or list(_RAPIDOCR_FILES)
    for fname in wanted:
        dst = os.path.join(mdir, fname)
# فایلهایِ dict (txt) کوچکاند (47-75KB)؛ آستانهٔ
# 100KB فقط برایِ مدلهاست وگرنه dict هر بار دوباره دانلود میشد.
        _min_sz = 100 if fname.endswith(".txt") else 100_000
        if os.path.isfile(dst) and os.path.getsize(dst) > _min_sz:
            continue
        done = False
        _lk = _dl_file_lock(dst)
        with _lk:
# داخلِ قفلِ همان فایل دوباره چک کن — شاید ورکرِ دیگر همین
# حالا آن را دانلود کرده باشد (ریشهٔ ارورِ .part)
            if os.path.isfile(dst) and os.path.getsize(dst) > _min_sz:
                continue
            for url in (_RAPIDOCR_MIRROR + fname, _RAPIDOCR_FILES.get(fname)):
                if not url:
                    continue
                try:
                    print(f"  دانلود {fname} ...")
                    _dl_to(url, dst, name=fname)
                    done = True
                    break
                except Exception as e:
# اگر ورکرِ دیگر فایل را تمام کرده، این شکست نیست
                    if os.path.isfile(dst) and os.path.getsize(dst) > _min_sz:
                        done = True
                        break
                    host = url.split("/")[2] if url else "?"
                    print(f"  [!] {fname} از {host} نشد: {e}")
            if not done:
                print(f"  [!] دانلود {fname} ناموفق — اینترنت/VPN را چک کن "
                      "(دانلودِ بعدی از همان‌جا ادامه مییابد)")
# .part حفظ میشود (ادامهٔ دانلود با Range)
