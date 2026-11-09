# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 پاکسازِ LaMa — کلاسهای LamaONNX / LamaMangaONNX / LamaTorch
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
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
        # v1.14.233 — رویِ DML فقط زیرِ قفل (اجرایِ موازی ممنوع)
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
    # v1.14.115 — واریانتِ «بدونِ DFT» (همان وزنهای big-lama؛ بلوکهایِ
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
        """v1.14.147: پیشفرضِ همهجا «بدونِ DFT» — همان وزنهایِ big-lama با
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
                # v1.14.45: نخِ صریحِ فراهم‌شده از _get_lama(threads=…) محترم است —
                # وقتی پچِ موازی کم است باید هر پچ چندنخی شود (هسته‌های بیکار نماند)
                if threads and int(threads) > 0:
                    use_threads = max(1, min(int(threads), os.cpu_count() or 4))
                else:
                    # v1.14.147: PC تا ۴ نخ (با nofft چند برابر سریعتر میشود؛
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
        # v1.14.52 — صداقتِ ep_used: رویِ اندروید _resolve_lama_ep مثلاً
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
        # v1.14.66 — باکتِ شکلِ ثابت برایِ xnnpack: هر ورودیِ LaMa دقیقاً
        # _static_bucket×_static_bucket پد می‌شود تا EPِ xnnpack که با
        # شکلِ داینامیک ORT_FAIL می‌دهد واقعاً کار کند (پچِ LaMa زنده
        # می‌ماند → بدونِ فال‌بکِ OpenCV → بدونِ لکهٔ قرمز + سریع‌تر).
        self._static_bucket = 0
        # v1.14.135 — پچِ تطبیقیِ LaMa (فقط اندروید — MANGA_LAMA_PATCH512):
        # پچِ 384 کلِ ورودی را به مقیاسِ ~0.5 (بلوکِ تمامعرض) و ~0.2
        # (گروهِ پراکنده) له میکند → LaMa «متنِ قلابی» میسازد (لکهٔ
        # کثیف). با رمِ آزادِ ≥1200MB و ≥۶ هسته، پچِ 512 (کیفیتِ
        # بالاتر) امن است؛ گوشیِ کم‌رم مثلِ قبل 384 میماند. env دستی
        # (MANGA_LAMA_PATCH_SIDE) همیشه حاکم است.
        try:
            if (_on_android()
                    and not os.environ.get("MANGA_LAMA_PATCH_SIDE")
                    and _android_gate("MANGA_LAMA_PATCH512")):
                _free_mb135 = 0
                with open("/proc/meminfo", "r") as _mi135:
                    for _ln135 in _mi135:
                        if _ln135.startswith("MemAvailable:"):
                            _free_mb135 = int(_ln135.split()[1]) // 1024
                            break
                if _free_mb135 >= 1200 and (os.cpu_count() or 2) >= 6:
                    os.environ["MANGA_LAMA_PATCH_SIDE"] = "512"
                    os.environ["MANGA_LAMA_STATIC_SIDE"] = "512"
                    globals()["_LAMA_STATIC_SIDE"] = None  # بازخوانیِ کش
                    print("[*] پچِ تطبیقی LaMa: رمِ آزادِ کافی → 512",
                          flush=True)
        except Exception:
            pass
        try:
            _pv66 = [str(p).lower()
                     for p in (self.session.get_providers() or [])]
            if _lama_static_side() > 0 and any(
                    p.startswith("xnnpack") for p in _pv66):
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
        # v1.14.67 — A/B با شکلِ واقعیِ پچ (یک‌بار + کشِ .epab): پروبِ قدیمی
        # با شکلِ کوچک بود؛ xnnpack ممکن است «کار کند» ولی از CPUِ چندنخی
        # کندتر باشد (لاگِ POCO F4: 28.4s برایِ ۲ پچِ ۳۸۴²). برنده ماندگار
        # می‌شود. گیتِ رم: با رمِ آزادِ کم (دو سشن همزمان) A/B نمی‌کنیم.
        try:
            self._ep_real_shape_ab(use_threads)
        except Exception:
            pass
        # ══ v1.14.106 — dual-device (GPU + CPU همزمان) ══════════════════
        # درخواستِ کاربر: «هم GPU هم CPU با هم استفاده کنه واسه پاکسازی
        # سریع‌تر». وقتی EPِ سرِ سشن GPU-گونه است (CUDA/DML/NNAPI/XNNPACK)،
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
                # v1.14.108 — رویِ شبیه‌سازِ x86_64 سشنِ CPU-خالص ممنوع است
                # (CPU EPِ ORT-android آنجا می‌میرد — درسِ v1.14.67؛ هنگِ
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
        # v1.14.147 — واریانتِ بدونِDFT همهجا (خروجیِ عددیِ یکسان با dyn —
        # وریفایِ scripts/lama_equiv.py — و CPU چند برابر سریعتر)؛
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
        """v1.14.96-speed (SRV-G phase2) — آماده‌سازیِ ورودیِ LaMa-Manga:
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

        _bucket66 = int(getattr(self, "_static_bucket", 0) or 0)
        if _bucket66 and not self._fixed_size:
            # v1.14.66 — همهٔ ورودی‌ها دقیقاً _bucket66×_bucket66 → شکلِ
            # ثابت برایِ xnnpack (یک کامپایل، بدونِ ORT_FAILِ شکلِ تازه).
            # ماسک در ناحیهٔ پد صفر است و خروجی فقط داخلِ ناحیهٔ اصلی
            # برش می‌خورد — ریاضیِ خروجی مثلِ مسیرِ fixed-size است.
            s = _bucket66
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
        """v1.14.106 — چرخشِ round-robin بینِ سشنِ اصلی (GPU) و سشنِ CPU
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
            # v1.14.233 — رویِ DML فقط زیرِ قفل (اجرایِ موازی ممنوع —
            # پچهایِ موازیِ LaMa همه از همینجا میگذرند)
            return _dml_run(_sess, feeds)[0]
        except Exception:
            if _sess is not self.session:
                # سشنِ CPU خراب شد → سشنِ اصلی (امن)
                return _dml_run(self.session, feeds)[0]
            raise

    def run_batch_tensors(self, tensors):
        """v1.14.96-speed (SRV-G phase2) — یک session.run برایِ N پچِ
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


