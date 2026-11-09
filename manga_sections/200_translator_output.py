# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۱۱ از ۱۳) — قالبهای خروجی: PDF/ZIP/PSD/HTML/تصویر + پاکسازیِ خروجیهای قبلی
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_200:
# BUILD-STRIP-END
    @staticmethod
    def _pdf_to_images(pdf_path: str, dest_dir: str) -> List[str]:
        import fitz
        os.makedirs(dest_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        zoom = 200 / 72
        matrix = fitz.Matrix(zoom, zoom)
        files = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_file = os.path.join(dest_dir, f"page_{i + 1:03d}.png")
            pix.save(out_file)
            files.append(out_file)
        doc.close()
        return files

    def _save_as_pdf(self, image_paths_in_order: List[str], out_path: str) -> None:
        images = []
        for p in image_paths_in_order:
            im = Image.open(p).convert("RGB")

            if im.size[0] < 8 or im.size[1] < 8:
                print(f"    [!] رد تصویر خیلی کوچک در PDF: {os.path.basename(p)} {im.size}")
                continue
            images.append(im)
        if not images:
            raise ValueError("هیچ تصویری برای ساخت PDF وجود نداره.")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)


        q = max(92, int(np.clip(int(getattr(self, "img_quality", 90) or 90), 40, 100)))
        images[0].save(
            out_path,
            save_all=True,
            append_images=images[1:],
            resolution=150.0,
            quality=q,
            optimize=True,
        )

    @staticmethod
    def _save_as_zip(folder: str, out_path: str) -> None:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)


        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
            for name in sorted(os.listdir(folder), key=MangaTranslator._natural_sort_key):
                zf.write(os.path.join(folder, name), arcname=name)

    def _save_as_psd(self, image_paths_in_order: List[str], out_path: str) -> None:

        try:
            from pytoshop.user.nested_layers import Image as PsdLayer
            from pytoshop.user.nested_layers import nested_layers_to_psd
            from pytoshop import enums as psd_enums
            from pytoshop.image_data import ImageData
        except ImportError:
            print("[*] نصب pytoshop برای خروجی PSD ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-q", "pytoshop"],
            )
            from pytoshop.user.nested_layers import Image as PsdLayer
            from pytoshop.user.nested_layers import nested_layers_to_psd
            from pytoshop import enums as psd_enums
            from pytoshop.image_data import ImageData

        pages: List[np.ndarray] = []
        for p in image_paths_in_order:
            im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if im is None:
                print(f"    [!] رد تصویر در PSD: {os.path.basename(p)}")
                continue
            if im.ndim == 2:
                im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            elif im.shape[2] == 4:
                bgr = im[:, :, :3].astype(np.float32)
                a = im[:, :, 3:4].astype(np.float32) / 255.0
                im = (bgr * a + 255.0 * (1.0 - a)).astype(np.uint8)
            elif im.shape[2] > 4:
                im = im[:, :, :3]
            pages.append(im)
        if not pages:
            raise ValueError("هیچ تصویری برای ساخت PSD وجود ندارد.")

        max_h = max(im.shape[0] for im in pages)
        max_w = max(im.shape[1] for im in pages)
        use_psb = max_h > 30000 or max_w > 30000
        version = psd_enums.Version.version_2 if use_psb else psd_enums.Version.version_1

        def _place_on_canvas(bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:

            h, w = bgr.shape[:2]
            canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
            alpha = np.zeros((max_h, max_w), dtype=np.uint8)
            x0 = max(0, (max_w - w) // 2)
            canvas[:h, x0:x0 + w] = bgr
            alpha[:h, x0:x0 + w] = 255
            rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
            return rgb, alpha

        def _to_layer(name: str, bgr: np.ndarray) -> "PsdLayer":
            rgb, alpha = _place_on_canvas(bgr)
            return PsdLayer(
                name=name[:250],
                channels={
                    -1: np.ascontiguousarray(alpha),
                    0: np.ascontiguousarray(rgb[:, :, 0]),
                    1: np.ascontiguousarray(rgb[:, :, 1]),
                    2: np.ascontiguousarray(rgb[:, :, 2]),
                },
                opacity=255,
                visible=True,
            )

        layers = [_to_layer(f"page_{i + 1:03d}", im) for i, im in enumerate(pages)]
        layers = list(reversed(layers))

        print(
            f"[*] ساخت PSD: {len(pages)} لایه | بوم {max_w}×{max_h}"
            f"{' | PSB' if use_psb else ''} ..."
        )
        psd = nested_layers_to_psd(
            layers,
            color_mode=psd_enums.ColorMode.rgb,
            version=version,
            compression=psd_enums.Compression.raw,
        )


        preview_bgr = pages[0]
        preview_rgb, _ = _place_on_canvas(preview_bgr)
        comp = np.stack(
            [
                np.ascontiguousarray(preview_rgb[:, :, 0]),
                np.ascontiguousarray(preview_rgb[:, :, 1]),
                np.ascontiguousarray(preview_rgb[:, :, 2]),
            ],
            axis=0,
        )

        nch = int(getattr(psd, "num_channels", 3) or 3)
        if nch >= 4:
            alpha = np.zeros((max_h, max_w), dtype=np.uint8)
            h0, w0 = preview_bgr.shape[:2]
            x0 = max(0, (max_w - w0) // 2)
            alpha[:h0, x0:x0 + w0] = 255
            comp = np.concatenate([comp, alpha[None, ...]], axis=0)
        psd.image_data = ImageData(
            channels=comp,
            compression=psd_enums.Compression.raw,
        )

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "wb") as f:
            psd.write(f)
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"  - PSD ذخیره شد ({size_mb:.1f} MB): {out_path}")
        print("  - پیش‌نمایش ترکیبی = صفحه ۱ (برای IrfanView/ویندوز)")

    def _write_image(self, image: np.ndarray, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()

        out_image = image
        try:
            _pp = os.environ.get("MANGA_PROBE_REPAIR", "")
            if _pp and getattr(self, "_probe_repair_pts", None):
                for (_px, _py) in self._probe_repair_pts:
                    print(f"  [PROBE] write @{_px},{_py} "
                          f"val={image[_py, _px]} shape={image.shape} "
                          f"path={os.path.basename(path)}", flush=True)
        except Exception:
            pass
        if os.environ.get("MANGA_DEBUG_LEFTOVER") == "1":
            try:
                cv2.imwrite("/tmp/ct38/write_input_debug.png", out_image)
            except Exception:
                pass
        if out_image is None or out_image.size == 0:
            raise ValueError(f"تصویر خالی برای ذخیره: {path}")
        if out_image.dtype != np.uint8:
            out_image = np.clip(out_image, 0, 255).astype(np.uint8)
        out_image = np.ascontiguousarray(out_image)

        if self.max_output_width and self.max_output_width > 0:
            target_w = int(self.max_output_width)
            if out_image.shape[1] != target_w:
                scale = target_w / float(out_image.shape[1])
                new_h = max(1, int(round(out_image.shape[0] * scale)))
                interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                out_image = cv2.resize(out_image, (target_w, new_h), interpolation=interp)
                out_image = np.ascontiguousarray(out_image)
        if os.environ.get("MANGA_DEBUG_LEFTOVER") == "1":
            import traceback as _tbw
            print(f"    [dbg-write] path={path} shape={out_image.shape} "
                  f"q={int(np.clip(int(self.img_quality), 40, 100))}")
            _tbw.print_stack(limit=6)

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        q = int(np.clip(int(self.img_quality), 40, 100))
        rgb = cv2.cvtColor(out_image, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)

        if ext == ".webp":

            pil.save(
                path, format="WEBP", quality=q, method=6,
                exact=False,
            )
        elif ext in (".jpg", ".jpeg"):


            sub = 0 if q >= 90 else 2
            pil.save(
                path, format="JPEG", quality=q, optimize=True,
                progressive=True, subsampling=sub,
            )
        elif ext == ".png":

            pil.save(path, format="PNG", optimize=True, compress_level=9)
        else:
            cv2.imwrite(path, out_image)

    @staticmethod
    def _save_as_html(image_paths: List[str], out_path: str, title: str = "مانهوا ترجمه شده") -> None:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #0a0a0b; }
.strip {
  max-width: 900px;
  margin: 0 auto;
  background: #000;
}
.strip img {
  width: 100%;
  height: auto;
  display: block;
  vertical-align: top;
}
"""

        parts = [
            "<!DOCTYPE html>",
            '<html lang="fa" dir="rtl">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="color-scheme" content="dark">',
            '<meta name="theme-color" content="#0a0a0b">',
            f"<title>{title}</title>",
            "<style>",
            css.strip(),
            "</style>",
            "</head>",
            "<body>",
            '<div class="strip">',
        ]

        for i, p in enumerate(image_paths, 1):
            with open(p, "rb") as f:
                data = f.read()
            ext = os.path.splitext(p)[1].lower().lstrip(".")
            mime = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
            }.get(ext, "image/jpeg")
            b64 = base64.b64encode(data).decode("ascii")
            parts.append(
                f'<img src="data:{mime};base64,{b64}" alt="" '
                f'loading="{"eager" if i <= 2 else "lazy"}" decoding="async">'
            )

        parts.append("</div>")
        parts.append("</body></html>")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))

    @staticmethod
    def _cleanup_previous_artifacts(output_path: str, keep_outputs: bool = False) -> None:
        abs_out = os.path.abspath(output_path)
        parent = os.path.dirname(abs_out) or "."
        current_base = os.path.basename(abs_out)
        current_cache = abs_out + ".cache"
        current_stem = os.path.splitext(current_base)[0]

        if not os.path.isdir(parent):
            return

        series_prefix = current_stem
        for marker in ("-chapter-", "_chapter_", "-ch-", "_ch-"):
            if marker in current_stem.lower():
                idx = current_stem.lower().index(marker)
                series_prefix = current_stem[:idx]
                break
        if len(series_prefix) < 3:
            series_prefix = current_stem[: max(4, len(current_stem) // 2)]

        removed = 0
        for name in os.listdir(parent):
            path = os.path.join(parent, name)

            if name.endswith(".cache") and os.path.isdir(path):
                if os.path.abspath(path) != os.path.abspath(current_cache):
                    print(f"[*] پاک کردن کش قدیمی: {name}")
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
                continue

            if keep_outputs:
                continue

            low = name.lower()
            if not low.endswith((".pdf", ".html", ".zip", ".psd")):
                continue
            if os.path.abspath(path) == abs_out:
                continue
            if not os.path.isfile(path):
                continue

            stem = os.path.splitext(name)[0]
            if series_prefix and series_prefix.lower() in stem.lower():
                try:
                    print(f"[*] پاک کردن خروجی قدیمی: {name}")
                    os.remove(path)
                    removed += 1
                except OSError as e:
                    print(f"    [!] نتوانست پاک شود ({name}): {e}")

        if removed:
            print(f"[*] {removed} مورد قدیمی پاک شد.")
        else:
            print("[*] مورد قدیمی برای پاک کردن پیدا نشد.")

    @staticmethod
    def _extract_title_skips_from_path(path_or_url: str) -> List[str]:
        from urllib.parse import urlparse, unquote

        raw = path_or_url.strip()
        if MangaTranslator._is_url(raw):
            path = unquote(urlparse(raw).path)
        else:
            path = raw


        parts = [p for p in re.split(r"[/\\]+", path) if p]
        skip: List[str] = []
        noise = {
            "comics", "comic", "manga", "manhwa", "reader", "en", "chapter",
            "chapters", "series", "title", "www", "http", "https", "cdn",
            "asurascans", "asura", "mgeko", "webtoon", "page", "pages",
        }

        candidates = []
        for p in parts:
            pl = p.lower()
            if re.fullmatch(r"\d+", pl):
                continue
            if pl in noise:
                continue
            if pl.endswith((".jpg", ".png", ".webp", ".jpeg", ".html", ".pdf")):
                continue

            cleaned = re.sub(r"^[a-z]{0,4}\d+-", "", pl)
            cleaned = re.sub(r"-[a-f0-9]{6,}$", "", cleaned)
            if cleaned and cleaned not in noise:
                candidates.append(cleaned)
            if pl not in candidates and pl not in noise:
                candidates.append(pl)

        for c in candidates:

            compact = re.sub(r"[^a-z0-9]", "", c)
            if len(compact) >= 5:
                skip.append(compact)
            tokens = [t for t in re.split(r"[-_]+", c) if t and t not in noise and not t.isdigit()]
            if len(tokens) >= 2:

                for n in range(2, min(len(tokens), 4) + 1):
                    for i in range(0, len(tokens) - n + 1):
                        chunk = "".join(tokens[i:i + n])
                        if len(chunk) >= 5:
                            skip.append(chunk)

                full = "".join(tokens)
                if len(full) >= 5:
                    skip.append(full)

        seen = set()
        out = []
        for s in skip:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

