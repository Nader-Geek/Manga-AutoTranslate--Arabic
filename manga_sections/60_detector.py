# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 تشخیصِ حباب — کلاس RTDetrV2ONNXDetector
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
class RTDetrV2ONNXDetector:

    DET_REPO = "ogkalu/comic-text-and-bubble-detector"
    # v1.14.234 — «detector-v4.onnx» حذف شد: در «هیچ» منبعی وجود ندارد
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

        # v1.14.233 — رویِ DirectML (AMD/Intel ویندوز): مدلِ int8 سشنِ DML
        # نمیسازد (80070057 — اپراتورهایِ کوانتیزه؛ لاگِ 232 رویِ RX 5700
        # XT). این بلوک در «هر دو» مسیر اجرا میشود (مدلِ کش‌شده و دانلودِ
        # تازه — باگِ پیشین: فقط مسیرِ دانلود بود و مدلِ int8ِ کش‌شده اصلاً
        # GPU امتحان نمیکرد): کاندیدها (مدلِ محلی + fp32هایِ ریپو) با
        # «پروبِ واقعی» (سشن + یک اینفرنس؛ نتیجه دیسک-کش) امتحان میشوند و
        # اولینِ سالم رویِ GPU میرود. هیچکدام؟ → دیتکتور رویِ CPU (int8
        # سریعتر از fp32 رویِ CPU) تا تلاشِ خرابِ GPU پرچمِ «GPU ساخته نشد»
        # را قفل نکند و LaMa/OCR آزاد بمانند.
        _dml_skip233 = False
        try:
            _dml_head233 = (
                bool(prefer_gpu) and (os.name == "nt") and _ort_has_dml()
                and (_best_providers_for("det", prefer_gpu=True)
                     or [""])[0] == "DmlExecutionProvider")
        except Exception:
            _dml_head233 = False
        if _dml_head233 and not _forced:
            _cand233 = []
            if model_path and os.path.isfile(model_path) \
                    and os.path.getsize(model_path) > 1000:
                _cand233.append((os.path.basename(model_path), model_path))
            # v1.14.234 — «detector-v4.onnx» از کاندیدها حذف شد: فایلِ
            # مرده — نه در ریلیزِ mirror هست (404) نه در ریپویِ HF. هر
            # استارت یک mirror+HFِ بی‌فایده را امتحان میکرد و «ساکت»
            # میانداخت — ریشهٔ پرسشِ سازنده: «سیستمم داشتم چرا رفت
            # detector.onnx گرفت؟». کاندیدِ fp32 فقط detector.onnx است
            # (160.7MB — همان دیتکتور، بدونِ کوانتیزه).
            for _f233 in ("detector.onnx",):
                _cand233.append((_f233, None))
            _seen233 = set()
            _pick233 = None
            for _fn233, _fp233 in _cand233:
                if not _fn233 or _fn233 in _seen233:
                    continue
                _seen233.add(_fn233)
                _c233 = _fp233
                if not _c233:
                    try:
                        _c233 = _mirror_model(_fn233)
                    except Exception:
                        _c233 = None
                if not _c233:
                    try:
                        print(f"[*] دانلود {_fn233} برایِ GPU (DirectML) ...")
                        _c233 = _hf_with_timeout(_fn233)
                    except Exception as _e234:
                        # v1.14.234 — دیگر بی‌صدا قورت داده نمیشود؛ در لاگ
                        # باید دیده شود چرا کاندید رد شد.
                        print(f"    [!] {_fn233} از HF هم نیامد: {_e234}")
                        _c233 = None
                if not (_c233 and os.path.isfile(_c233)
                        and os.path.getsize(_c233) > 1000):
                    continue
                if _dml_probe_model(_c233):
                    _pick233 = _c233
                    break
                print(f"    [~] {os.path.basename(_c233)} رویِ DirectML "
                      "پروب نشد → کاندیدِ بعدی …")
            if _pick233:
                if model_path and os.path.isfile(model_path) \
                        and os.path.abspath(_pick233) != os.path.abspath(model_path):
                    _why234 = (" (کوانتیزهٔ int8 — 80070057)"
                               if "int8" in os.path.basename(model_path).lower()
                               else "")
                    print(f"[*] {os.path.basename(model_path)}{_why234} رویِ "
                          "DirectML سشن نمی‌سازد → نسخهٔ fp32 "
                          f"({os.path.basename(_pick233)}) جایگزین شد؛ حجمِ "
                          "fp32 چند برابرِ int8 است (همین دیتکتور، بدونِ "
                          "کوانتیزه) و فقط یک بار دانلود میشود.")
                print(f"[+] DirectML: دیتکتور ({os.path.basename(_pick233)}) "
                      f"رویِ GPU پروب شد → همین استفاده میشود.")
                model_path = _pick233
            else:
                _dml_skip233 = True
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
                            prefer_gpu=(False if _dml_skip233 else prefer_gpu),
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
            # v1.14.233 — اگر پروبِ DML مردود شد (int8)، حتی امتحانِ GPU هم
            # نکن (ارورِ 80070057 و پیامِ گمراه‌کننده نمیآید؛ مستقیم CPU)
            self.session = _make_ort_session(
                model_path,
                prefer_gpu=(False if _dml_skip233 else prefer_gpu),
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
        # v1.14.233 — رویِ DML فقط زیرِ قفل (اجرایِ موازی ممنوع)
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
        # v1.14.214 — جعبههایِ «ردشدهٔ لبهٔ کاشی» جدا جمع میشوند تا در
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
        # v1.14.214 — نجاتِ جعبهٔ لبهٔ کاشی: جعبهٔ ردشده فقط وقتی زنده
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


# v1.14.96-speed — منبعِ اصلیِ مدل‌هایِ OCR = ریلیزِ «models» رویِ GitHub
# (همان amirwolf512k/Manga-AutoTranslate)؛ assetsها دقیقاً با همین نام‌ها
# آنجاست: PP-OCRv6_det_small.onnx (det) / PP-OCRv6_rec_small.onnx (rec
# en+ch) / korean_PP-OCRv5_rec_mobile.onnx / japan_PP-OCRv4_rec_mobile.onnx
# v1.14.152 — مجموعهٔ مرجع اضافه شد (درخواست: «از همین نسخه که مرجع استفاده
# میکنه استفاده کن»): PP-OCRv6_medium_det_onnx.onnx (59.16MiB) /
# PP-OCRv6_medium_rec_onnx.onnx (73.01MiB) / PP-OCRv5_korean_rec.onnx
# (12.80MiB) = عینِ فایلهایِ رسمیِ PaddlePaddle رویِ HuggingFace که خودِ
# مرجع دانلود میکند (حجمها مو به مو با پوشهٔ مرجع) + ch_PP-OCRv4_det_infer
# .onnx (4.53MiB) + ch_PP-OCRv4_rec_infer.onnx (10.35MiB؛ dict داخلیِ
# metadata = ppocr_keys_v1 با 6623 کاراکتر).
# / ch_ppocr_mobile_v2.0_cls_mobile.onnx (cls — در رانِ عادی استفاده
# نمی‌شود). مسیرِ دوم فقط فال‌بکِ قطعِ گیت‌هاب است (modelscope).
