# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 سختافزار و ORT — RAM/CPU/GPU، انتخابِ Provider، تورنمنتِ EP، ساختِ session
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
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
    """v1.14.96-speed (SRV-G) — «امولاتورِ» واقعی: محیطِ اندروید + CPU
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
    """v1.14.96-speed (SRV-G) — A/Bِ XNNPACK: فقط با env
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
    """v1.14.96-speed (SRV-G) — هسته‌هایِ فیزیکی (برایِ XNNPACK
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
    # v1.14.96-speed — فیکسِ باگِ تک‌نخیِ x86_64: محدودیتِ «نخ=۱» فقط برایِ
    # اندروید بود (ORT-androidِ x86_64 در زمان‌بندِ thread-pool تقسیم‌برِصفر
    # /SIGFPE می‌دهد) ولی چون فقط machine را چک می‌کرد، رویِ «همهٔ»
    # میزبان‌هایِ x86_64 (PC/سرورِ لینوکس/ویندوز) هم اعمال می‌شد → LaMa/
    # دیتکتور/OCR رویِ PC تک‌نخ می‌شدند و چند برابر کند بودند. حالا فقط
    # وقتی فعال است که واقعاً اندروید باشیم (Chaquopy یا نشانه‌هایِ محیطِ
    # اندروید مثل /system/build.prop یا ANDROID_ROOT) و معماری x86_64
    # (یعنی امولاتور).
    # v1.14.99 (SRV-H4) — بازگشتِ دقیق به معنایِ e32bccf: مقدارِ «پاس‌شده»
    # (پیش‌فرضِ ۴) رویِ همهٔ میزبان‌هایِ غیرِ امولاتور استفاده می‌شود؛
    # «۰ = ORT auto»یِ SRV-G رویِ سرور کندتر بود (SRV-H2: +30..+67٪ CPU)
    # و حذف شد. امولاتورِ x86_64 همان قراردادِ SRV-F (intra=1).
    # MANGA_ORT_THREADS=N همچنان اوررایدِ صریح دارد (اولاً بعد از cap1).
    _cap1_67 = _android_x86_emulator()
    _xnn67 = _cpu_ep_xnnpack()
    try:
        _env_t67 = int(os.environ.get("MANGA_ORT_THREADS", "0") or 0)
    except Exception:
        _env_t67 = 0
    if _cap1_67:
        threads = 1
    elif _env_t67 > 0:
        threads = _env_t67
    elif _xnn67:
        # کانفیگِ رسمیِ XNNPACK (فقط MANGA_CPU_EP=xnnpack): threadpoolِ ORT
        # تک‌نخی؛ XNNPACK خودش threadpoolِ هسته‌هایِ فیزیکی را می‌سازد.
        threads = 1
    else:
        # v1.14.99-speed (SRV-L) — هیوریستیکِ میزبان به‌جایِ مقدارِ ثابتِ
        # «پاس‌شده»: رویِ PC/سرورِ واقعیِ x86_64 با ≥۸ هسته، برندهٔ سوییپِ
        # SRV-K (t8: CPU ۳۲.۲s / GPU ۱۸.۷s) پیش‌فرضِ fastest-mode می‌شود؛
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
        _t67 = int(threads)
    except Exception:
        _t67 = 4
    # v1.14.99-speed (SRV-L) — گاردِ SIGABRTِ مسیرِ CUDA: با نخِ ۲۰ رویِ
    # سشن‌هایِ CUDA/TRT، per-patchِ LaMa رویِ سرورِ تازه ORT را با
    # SIGABRT (exit=134) می‌کشد (SRV-K g20). سقفِ سختِ ۱۶ فقط وقتی
    # سشنِ GPU خواسته شده؛ مسیرِ CPU دست‌نخورده می‌ماند.
    try:
        if prefer_gpu and _t67 > 16:
            _t67 = 16
    except Exception:
        pass
    so.intra_op_num_threads = _t67 if _t67 > 0 else 0
    so.inter_op_num_threads = 1
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    # پچ‌های موازی LaMa + OCR هم‌زمان اجرا می‌شوند؛ spin-wait هسته‌ها را می‌سوزاند
    # v1.14.67 — رویِ x86_64 این کانفیگ SIGFPE می‌دهد (حدس: شمارشِ spin=۰
    # → تقسیم بر صفر در مسیرِ x86) — فقط رویِ arm خاموش می‌شود
    if not _on_x86():
        try:
            so.add_session_config_entry(
                "session.intra_op.allow_spinning", "0")
        except Exception:
            pass
    # v1.14.96-speed (SRV-G phase2) — tuningِ spin برایِ threadpoolِ CPU
    # چندنخی (کمبوِ رسمیِ مستنداتِ threadingِ onnxruntime):
    #   spin_duration_us=1000 + spin_backoff_max=8
    # v1.14.99 (SRV-H4) — پیش‌فرضِ خاموش (رویِ میزبانِ gVisor کندتر بود؛
    # SRV-H2)؛ فقط با MANGA_SPIN=1 و وقتی pool چندنخی است (۰ یا >۱)،
    # رویِ میزبانِ غیرِ اندروید و خارج از XNNPACK فعال می‌شود.
    try:
        _spin_h4 = str(os.environ.get("MANGA_SPIN", "")).strip() == "1"
    except Exception:
        _spin_h4 = False
    if _spin_h4 and (not _cap1_67) and (not _xnn67) \
            and (not _android_like_env()) and (_t67 == 0 or _t67 > 1):
        try:
            so.add_session_config_entry(
                "session.intra_op.spin_duration_us", "1000")
            so.add_session_config_entry(
                "session.intra_op.spin_backoff_max", "8")
        except Exception:
            pass
    if _xnn67:
        # کانفیگِ رسمیِ XNNPACK: spinning خاموش (نخِ ORT فقط هماهنگ می‌کند)
        try:
            so.add_session_config_entry(
                "session.intra_op.allow_spinning", "0")
        except Exception:
            pass
    if low_mem is None:
        _av = _sys_avail_ram_gb()
        # v1.14.105 — MANGA_LOW_MEM=1: اجبارِ حالتِ کم‌رم (آرنا/الگوی
        # حافظه خاموش) — برایِ دستگاه‌هایِ ۴GB و نوارهایِ بلندِ وبتون که
        # به مرزِ OOM می‌رسند
        low_mem = bool(_on_android()
                       or (_av is not None and _av < 3.0)
                       or os.environ.get("MANGA_LOW_MEM", "") == "1")
    so.enable_cpu_mem_arena = (not low_mem)
    so.enable_mem_pattern = (not low_mem)
    return so


def _trt_ep_usable() -> bool:
    """v1.14.96-speed — TensorrtExecutionProvider فقط وقتی «واقعاً» قابلِ
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
    """v1.14.96-speed — انتخابگرِ مرکزیِ EP از آنچه واقعاً نصب/موجود است.

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
        # --cpu: x86_64 → فقط CPU (همان EPِ همیشگی، نتیجهٔ بیت‌به‌بیت یکسان)
        # v1.14.238 — OpenVINO دیگر «به‌طورِ پیش‌فرض» ترجیح نمیشود:
        # بنچمارکِ واقعی (scripts/bench_out/ov238_results.json) رویِ
        # ورودیهایِ ضبطشده از ۱۰ عکسِ تست: onnxruntime-openvino (۱.۲۴.۱ —
        # تنها نسخهٔ PyPI) در rec ۲۳٪ «کندتر» (۱۰۳s در برابرِ ۸۴s)، در
        # LaMa ۱۶٪ کندتر و فقط در det ۲.۴× سریع‌تر است (سهمِ det از OCR
        # ~۱۸٪) → سوییچِ بی‌صدا = ضررِ خالص. فقط با MANGA_ALLOW_OV=1.
        try:
            _allow_ov238 = str(os.environ.get(
                "MANGA_ALLOW_OV", "")).strip().lower() == "1"
        except Exception:
            _allow_ov238 = False
        if _allow_ov238 and "OpenVINOExecutionProvider" in avail:
            out.append("OpenVINOExecutionProvider")
        # v1.14.96-speed (SRV-G) — A/Bِ XNNPACK (فقط MANGA_CPU_EP=xnnpack):
        # سشن‌هایِ CPU-EP از XNNPACK+CPU می‌روند با کانفیگِ رسمی
        # (ORT intra=1 + XNNPACK intra=فیزیکی + spin خاموش) — پیش‌فرضِ خاموش.
        if _cpu_ep_xnnpack() and "XnnpackExecutionProvider" in avail:
            out.append("XnnpackExecutionProvider")
    # امولاتورِ اندرویدِ x86_64: CPU-EPِ ORT-android می‌میرد (SIGFPE)
    # → XNNPACK اجباری (همان رفتارِ v1.14.67)
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
    """v1.14.99 (SRV-H4) — الگوریتمِ جست‌وجویِ cudnn برایِ convها.

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
    """v1.14.96-speed (SRV-G phase2) — provider options برایِ سشن‌هایِ GPU:
    CUDA → {"cudnn_conv_use_max_workspace": "1"} (صریح؛ پیش‌فرضِ ORT هم 1
    است ولی این‌طور به آن اعتماد نمی‌کنیم). cudnn_conv_algo_search دست
    نمی‌خورد (EXHAUSTIVE می‌ماند) و CUDA graphs روشن نمی‌شود (شکل‌هایِ
    داینامیک). XNNPACK (فقط MANGA_CPU_EP=xnnpack) → intra_op_num_threads =
    هسته‌هایِ فیزیکی (کانفیگِ رسمی). خروجی None رویِ لیستِ بدونِ CUDA/XNNPACK
    → دقیقاً رفتارِ قبلی (سشنِ CPU خالص).
    v1.14.99 (SRV-H4) — کلیدِ «cudnn_conv_algo_search»: "HEURISTIC"
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
                # v1.14.99 (SRV-H4) — HEURISTIC پیش‌فرض (حذفِ re-searchِ
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


# ── v1.14.69 — کشِ «مدلِ بهینه‌شده» برایِ LaMa ──────────────────────────
# لاگِ POCO F4 (1.14.68): [TIME] lama-wait=67.3s → کلِ زمان در
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
    v1.14.96-speed (SRV-G): provider_options اختیاری است (CUDA EP:
    cudnn_conv_use_max_workspace=1). None = دقیقاً رفتارِ قبل."""
    _t69 = time.time()
    _opt69 = None
    try:
        if str(os.environ.get("MANGA_LAMA_OPT_CACHE", "1")).strip() == "1" \
                and isinstance(model_path, str):
            _opt69 = _lama_opt_cache_path(model_path, providers)
    except Exception:
        _opt69 = None
    if _opt69 and os.path.isfile(_opt69) \
            and os.path.getsize(_opt69) > 1_000_000:
        try:
            # v1.14.233 — ساختِ سشنِ DML هم زیرِ قفلِ سراسری: هم‌زمانیِ
            # ساختِ سشن با runِ سشنِ دیگر رویِ درایورهایِ AMD همان
            # 887A0006 را میدهد (سشن CPU بدونِ قفل — بی‌تغییر)
            if "DmlExecutionProvider" in (providers or []):
                with _DML_RUN_LOCK:
                    _s69 = ort.InferenceSession(_opt69, sess_options=so,
                                                providers=providers,
                                                provider_options=provider_options)
            else:
                _s69 = ort.InferenceSession(_opt69, sess_options=so,
                                            providers=providers,
                                            provider_options=provider_options)
            try:
                print(f"[TIME] lama-create={time.time() - _t69:.1f}s "
                      f"(از کشِ بهینه‌شده)", flush=True)
            except Exception:
                pass
            return _s69
        except Exception:
            try:
                os.remove(_opt69)
            except Exception:
                pass
    # بارِ اول: مدلِ بهینه‌شده ذخیره می‌شود (اگر ORT پشتیبانی نکرد،
    # بی‌صدا مثلِ قبل). رویِ اندروید سطحِ بهینه‌سازی BASIC — بهینه‌سازِ
    # ALLِ تک‌نخی بخشِ بزرگی از همان ۶۷s است و XNNPACKِ سنگین‌کارِ
    # اصلی را خودش انجام می‌دهد (رویِ PC: ALL→BASIC فقط ‎+۴٪ زمانِ
    # اجرا؛ ساخت ×۲.۵ سریع‌تر).
    _part69 = None
    try:
        _android69 = _on_android()
    except Exception:
        _android69 = False
    if _opt69 and _android69:
        try:
            so.graph_optimization_level = \
                ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        except Exception:
            pass
    if _opt69:
        _part69 = _opt69 + ".part"
        try:
            so.optimized_model_filepath = _part69
        except Exception:
            _part69 = None
    try:
        # v1.14.233 — ساختِ سشنِ DML زیرِ قفلِ سراسری (توضیح: بالا)
        if "DmlExecutionProvider" in (providers or []):
            with _DML_RUN_LOCK:
                _s69 = ort.InferenceSession(model_path, sess_options=so,
                                            providers=providers,
                                            provider_options=provider_options)
        else:
            _s69 = ort.InferenceSession(model_path, sess_options=so,
                                        providers=providers,
                                        provider_options=provider_options)
    finally:
        try:
            if _part69 and os.path.isfile(_part69):
                with _LAMA_OPT_LOCK:
                    try:
                        os.replace(_part69, _opt69)
                        try:
                            print(f"[TIME] lama-create={time.time() - _t69:.1f}s "
                                  f"(مدلِ بهینه‌شده ذخیره شد → کش)", flush=True)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            os.remove(_part69)
                        except Exception:
                            pass
        except Exception:
            pass
    try:
        print(f"[TIME] lama-create={time.time() - _t69:.1f}s", flush=True)
    except Exception:
        pass
    return _s69


_ORT_CUDA_OK = None

# v1.14.233 — DirectML (AMD/Intel رویِ ویندوز): مستنداتِ رسمیِ ORT:
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
    """v1.14.233 — سرِ providersِ سشن DML است؟"""
    try:
        _p233 = list(sess.get_providers())
        return bool(_p233) and _p233[0] == "DmlExecutionProvider"
    except Exception:
        return False


def _dml_run(sess, feeds):
    """v1.14.233 — session.run رویِ سشنِ DML فقط زیرِ قفلِ سراسری
    (اجرایِ موازیِ DML ممنوع است — 887A0006 رویِ AMD). سشنهایِ CPU/CUDA
    بدونِ قفل و بدونِ سربار میروند."""
    if _dml_sess(sess):
        with _DML_RUN_LOCK:
            return sess.run(None, feeds)
    return sess.run(None, feeds)


def _dml_run_outs(sess, outs, feeds):
    """v1.14.233 — همان _dml_run ولی با لیستِ خروجیهایِ صریح (پروبهایِ
    داخلی مثلِ _ort_probe_ok)."""
    if _dml_sess(sess):
        with _DML_RUN_LOCK:
            return sess.run(outs, feeds)
    return sess.run(outs, feeds)


def _dml_probe_cache_get(model_path: str):
    """v1.14.233 — کشِ دیسکِ نتیجهٔ پروبِ DML (کنارِ فایلِ مدل،
    .dmlprobe). پروبِ هر مدل چند ثانیه ساختِ سشن رویِ GPU است؛ بدونِ
    کش هر استارت تکرار میشد. MANGA_ORT_EP_REPROBE=1 → بی‌اعتنا به کش
    (همان قراردادِ پروبِ LaMa). کلید: حجمِ فایل + نسخهٔ ORT."""
    try:
        if os.environ.get("MANGA_ORT_EP_REPROBE", "").strip() == "1":
            return None
        _f233 = str(model_path) + ".dmlprobe"
        if not os.path.isfile(_f233):
            return None
        import json as _json233
        with open(_f233, "r", encoding="utf-8") as _fh233:
            _d233 = _json233.load(_fh233)
        if int(_d233.get("size", -1)) != int(os.path.getsize(model_path)):
            return None
        if str(_d233.get("ort", "")) != str(getattr(ort, "__version__", "")):
            return None
        return bool(_d233.get("ok"))
    except Exception:
        return None


def _dml_probe_cache_set(model_path: str, ok: bool) -> None:
    try:
        import json as _json233
        _f233 = str(model_path) + ".dmlprobe"
        with open(_f233, "w", encoding="utf-8") as _fh233:
            _json233.dump({"ok": bool(ok),
                          "size": int(os.path.getsize(model_path)),
                          "ort": str(getattr(ort, "__version__", ""))},
                         _fh233)
    except Exception:
        pass


def _dml_probe_model(model_path: str) -> bool:
    """v1.14.233 — پروبِ واقعیِ DML رویِ یک فایلِ مدل: ساختِ سشن +
    «یک اینفرنسِ واقعی» با فیدِ دامی از رویِ شکلِ ورودیها. «سشن ساخته
    شد» کافی نیست — لاگِ 232: سشنهایِ det/rec ساخته شدند ولی اولین
    Run با 887A0006 مرد. False = این مدل رویِ این GPU/DirectML کار
    نمیکند (مثلاً int8 کوانتیزه — 80070057). نتیجه در دیسک کش
    میشود (.dmlprobe) تا استارتِ بعدی پروبِ مجاز نخواهد."""
    _c233 = _dml_probe_cache_get(model_path)
    if _c233 is not None:
        return _c233
    _ok233 = _dml_probe_model_live(model_path)
    _dml_probe_cache_set(model_path, _ok233)
    return _ok233


def _dml_probe_model_live(model_path: str) -> bool:
    try:
        if not model_path or not os.path.isfile(model_path):
            return False
        _so233 = _ort_session_options(2, prefer_gpu=True)
        try:
            # مستنداتِ DML: الگویِ حافظه باید خاموش باشد
            _so233.enable_mem_pattern = False
        except Exception:
            pass
        # ساختِ سشن و run «هر دو» زیرِ قفل: در لحظهٔ پروب ممکن است
        # پیش‌بارگذاریِ پس‌زمینهٔ LaMa همینجا سشنِ DML بسازد/اجرا کند
        with _DML_RUN_LOCK:
            _ps233 = ort.InferenceSession(
                model_path, sess_options=_so233,
                providers=["DmlExecutionProvider", "CPUExecutionProvider"])
            if not _dml_sess(_ps233):
                return False
            _feed233 = _ep_ab_feed(_ps233, side=320)
            if not _feed233:
                return False
            # فیکسِ RT-DETR: ورودیِ int64ِ (B,2)ِ orig_target_sizes باید
            # هم‌بُعدِ batchِ تصویر باشد — فیدِ خام (2,2) میسازد که با
            # تصویرِ (1,...) mismatch میدهد و پروبِ سالم هم «مردود»
            # میشود. batch همهٔ ورودیها را با بزرگ‌ترین batchِ 4بُعدی
            # هم‌تراز میکنیم.
            _b233 = 1
            for _v233 in _feed233.values():
                if getattr(_v233, "ndim", 0) == 4:
                    _b233 = max(_b233, int(_v233.shape[0]))
            for _k233, _v233 in list(_feed233.items()):
                if getattr(_v233, "ndim", 0) == 2 \
                        and _v233.dtype in (np.int64, np.int32) \
                        and int(_v233.shape[0]) != _b233:
                    _feed233[_k233] = np.full(
                        (_b233, int(_v233.shape[1])), 320, dtype=_v233.dtype)
            _outs233 = [o.name for o in _ps233.get_outputs()][:1]
            _ps233.run(_outs233, _feed233)
        try:
            del _ps233
        except Exception:
            pass
        import gc as _gc233
        _gc233.collect()
        return True
    except Exception:
        return False


def _prepare_ort_cuda_dlls() -> None:
    # v1.14.230 — ویندوز: DLLهایِ CUDA/cuDNN که pip در site-packages/nvidia
    # میگذارد باید با add_dll_directory معرفی شوند تا سشنِ CUDA واقعاً
    # بالا بیاید (ریشهٔ «GPU صفر درصد»: بیلدِ GPU نصب است ولی سشن
    # بیصدا به CPU برمی‌گشت). لینوکس: LD_LIBRARY_PATH را خودِ pip-wheels
    # هندل میکنند — این بلوک فقط ویندوز است.
    try:
        if os.name == "nt":
            import site as _site230
            import glob as _glob230
            for _sp230 in set(_site230.getsitepackages() or []):
                for _nd230 in sorted(_glob230.glob(
                        os.path.join(_sp230, "nvidia", "*", "bin"))):
                    try:
                        os.add_dll_directory(_nd230)
                    except Exception:
                        pass
                for _nd230b in sorted(_glob230.glob(
                        os.path.join(_sp230, "nvidia", "cuda_runtime", "bin"))):
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
    """v1.14.67 — فقط «امولاتورِ x86_64» (اندروید + x86): CPU-EPِ
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
    """v1.14.66 — شکلِ ثابتِ پچِ LaMa برایِ EPهایی که با شکلِ داینامیک
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
    _t70 = time.time()
    # v1.14.70 — کشِ نتیجهٔ پروب: پروبِ سلامت/سریالی تا ۵ اینفرنسِ
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
        # v1.14.70 — اندروید: فقط اعتبارسنجی (۱ ران کافی است)؛
        # مقایسهٔ سریال/موازی ۴ اینفرنسِ اضافه می‌خواهد و رویِ گوشیِ
        # کم‌رم ده‌ها ثانیه به استارت اضافه می‌کند، درحالی‌که A/Bِ
        # واقعی (.epab) جداگانه EP را با CPU مقایسه کرده است.
        try:
            _and70 = _on_android()
        except Exception:
            _and70 = False
        if _and70:
            try:
                print(f"[TIME] lama-probe={time.time() - _t70:.1f}s "
                      f"(اندروید: فقط اعتبارسنجی)", flush=True)
            except Exception:
                pass
            _lama_probeok_store(model_path, ep_name)
            return True
        # v1.14.67 — امولاتورِ x86_64: رانِ موازیِ همزمان در libonnxruntimeِ
        # x86_64 SIGFPE می‌دهد (تقسیمِ صحیحِ صفر در زمان‌بندِ thread-pool) —
        # پروبِ موازی رویِ x86 بی‌معناست (CI فقط درستی می‌سنجد) → پرش.
        try:
            import platform as _pf67
            if _pf67.machine().lower() in ("x86_64", "amd64"):
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
            print(f"[TIME] lama-probe={time.time() - _t70:.1f}s", flush=True)
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
            # v1.14.99-speed (SRV-L) — کاندیدِ CUDA تورنمنت هم گاردِ سقفِ
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
            # v1.14.98-speed (SRV-H3) — کاندیدِ CUDA در تورنمنت هم همان
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
        # v1.14.67 — سشنِ CPU رویِ x86 ساخته می‌شود ولی run نمی‌شود
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
    # v1.14.67 — امولاتورِ x86_64: مقایسه با CPU (سشنِ CPU) خودش کرش
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
    # v1.14.67 — امولاتورِ x86_64 (CI): CPU-EPِ ORT-android در createSession
    # SIGFPE می‌دهد و تورنمنت هم پروب را رد می‌کند → سشنِ دومِ fallback
    # کرشِ نیتیو می‌دهد. تجربهٔ ران ۲۴: ساختِ اولینِ سشنِ XNNPACK سالم بود؛
    # پس: هیچ تورنمنت، هیچ پروب، هیچ سشنِ دوم — فقط یک سشنِ مستقیمِ
    # XNNPACK+CPU (گره‌هایِ پشتیبانی‌نشده خودکار به CPU برمی‌گردند).
    try:
        import platform as _pf86
        if _on_android() and _pf86.machine().lower() in ("x86_64", "amd64"):
            so86 = _ort_session_options(1)
            try:
                so86.append_execution_provider("XnnpackExecutionProvider")
            except Exception:
                try:
                    so86._eps = [("XnnpackExecutionProvider", {})]
                except Exception:
                    pass
            sess86 = ort.InferenceSession(
                model_path, sess_options=so86,
                providers=["XnnpackExecutionProvider", "CPUExecutionProvider"])
            try:
                print("[*] x86_64: سشنِ مستقیمِ XNNPACK (بدونِ تورنمنت/پروب)")
            except Exception:
                pass
            return sess86
    except Exception as e:
        try:
            print(f"[!] x86_64 سشنِ مستقیمِ XNNPACK ناموفق: {str(e)[:110]}")
        except Exception:
            pass
    # v1.14.99-speed (SRV-L) — «want» قبل از ساختِ سشن محاسبه می‌شود تا
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
            # v1.14.99-speed (SRV-L) — مسیرِ EPِ اجباری: اگر CUDA اجباری
            # است، گاردِ سقفِ نخِ GPU اعمال شود
            so_ep = _ort_session_options(
                threads, prefer_gpu=(ep == "CUDAExecutionProvider"))
            if ep == "DmlExecutionProvider":
                # v1.14.233 — مستنداتِ DML: الگویِ حافظه خاموش
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
                # v1.14.98-speed (SRV-H3) — مسیرِ EPِ اجباری هم optionsِ
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

    # v1.14.96-speed — EPها از انتخابگرِ مرکزیِ _best_providers_for
    # می‌آیند (TensorRT/CUDA/ROCm/MIGraphX/Dml/… بر اساسِ آنچه واقعاً
    # نصب است + XNNPACKِ امولاتور + CPU همیشه آخر) — به‌جای چکِ
    # هاردکدِ CUDA که بقیهٔ EPهایِ GPU را از قلم می‌انداخت.
    providers = _best_providers_for("lama", prefer_gpu=want)
    # v1.14.233 — مستنداتِ رسمیِ DirectML: «بهینه‌سازیِ الگویِ حافظه
    # (enable_mem_pattern) برایِ سشنهایِ DML باید خاموش باشد» — پیشفرضِ
    # PC روشن است و سشنِ DML را ناپایدار میکند.
    if "DmlExecutionProvider" in providers:
        try:
            so.enable_mem_pattern = False
        except Exception:
            pass
    # v1.14.96-speed (SRV-G phase2) — CUDA EP options
    # (cudnn_conv_use_max_workspace=1) + XNNPACKِ A/B (intra=فیزیکی)
    _popts = _build_provider_options(providers)

    try:
        # v1.14.69 — کشِ مدلِ بهینه‌شده (گوشی: createSession تا 67s طول
        # می‌کشد؛ بارهایِ بعدی از فایلِ بهینه‌شده ساخته می‌شوند)
        sess = _lama_session_cached(model_path, so, providers,
                                    provider_options=_popts)
    except Exception as e:
        print(f"[!] InferenceSession GPU ناموفق ({e}) → CPU")
        if "DmlExecutionProvider" in (providers or []):
            # v1.14.233 — شکستِ «همین مدل» رویِ DML نباید پرچمِ سراسری را
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
    # v1.14.233 — پروبِ واقعیِ اینفرنس رویِ سشنِ DML: «ساخته‌شدنِ سشن»
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
    # v1.14.232 — DML هم مثلِ CUDA «سشنِ GPUِ موفق» است (AMD/Intel رویِ
    # ویندوز): قبلاً سشنِ سالمِ Dml باعثِ چاپِ «CUDA ساخته نشد» و
    # قفلِ _ORT_CUDA_OK=False → همهٔ سشنهایِ بعدی CPU میشدند.
    if want and ("CUDAExecutionProvider" in active
                 or "DmlExecutionProvider" in active):
        _ORT_CUDA_OK = True
    elif want:
        _ORT_CUDA_OK = False
        if "DmlExecutionProvider" in (providers or []):
            # v1.14.233 — پیامِ مخصوصِ DML (قبلاً راهنمایِ cuDNNِ CUDA
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
        # v1.14.67 — x86_64: بازسازیِ سشنِ CPU = SIGFPE → دست‌نخورده برگرد
        import platform as _pf86
        if _on_android() and _pf86.machine().lower() in ("x86_64", "amd64"):
            return session, use_threads
        provs = list(session.get_providers())
        _cap = 4 if _on_android() else 8
        cpu_n = max(1, min(_cap, os.cpu_count() or 4))
        # v1.14.99 (SRV-H4) — شرطِ e32bccf بازگشت (گاردِ use_threads>0یِ
        # SRV-G حذف شد؛ use_threads در تماس‌گیرنده‌ها همیشه ≥1 clamp شده)
        if (allow_bump and "CUDAExecutionProvider" not in provs
                and use_threads < cpu_n):
            print(f"    [*] اینپینت روی CPU است → threads: {use_threads} → {cpu_n}")
            return _make_ort_session(model_path, prefer_gpu=False, threads=cpu_n), cpu_n
    except Exception:
        pass
    return session, use_threads


