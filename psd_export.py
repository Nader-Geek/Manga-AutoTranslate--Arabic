#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
psd_export.py
==============
موديول إضافي لمشروع Manga-AutoTranslate بيصدّر كل صفحة كملف PSD متعدد
الطبقات (Photoshop) بدل/بجانب PDF و ZIP و HTML الموجودين أصلاً.

الفكرة
------
كل صفحة بتتحوّل لملف PSD فيه:
    1) طبقة "الخلفية المنظفة" (الصورة بعد ما اتشالت منها الكلمات الأصلية
       عن طريق LaMa / inpainting) — طبقة raster عادية RGB.
    2) طبقة منفصلة لكل حبابة نص متحطّة فوق الخلفية، بشفافية (RGBA) —
       كده أي مصمم فاتح فوتوشوب يقدر يحرك/يعدّل/يمسح أي حبابة لوحدها من
       غير ما يلمس الباقي.

المتطلبات
---------
    pip install pytoshop numpy pillow

طريقة الدمج مع manga.py
------------------------
جوه manga.py في المكان اللي بيتم فيه رسم النص المترجم فوق كل حبابة
(هتلاقيه غالبًا في دالة زي render_bubble_text / draw_translated_text
اللي بتستخدم PIL.ImageDraw + arabic_reshaper + bidi.algorithm.get_display)،
بدل ما ترسم النص مباشرة على الصورة النهائية:

    1. لكل حبابة، ارسم النص على طبقة PIL منفصلة شفافة (RGBA) بنفس حجم
       الـ bounding box بتاعها (أو الصفحة كلها لو النص بيخرج بره الحدود
       بسبب الدوران).
    2. اجمع كل الطبقات دي في list واحدة مع الخلفية المنظفة.
    3. في نهاية الصفحة، نادِ export_page_to_psd(...) بدل / بجانب حفظ
       الصورة النهائية العادية.

مثال استخدام مبسّط في نهاية الملف (__main__).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

try:
    import pytoshop
    import pytoshop.codecs
    from pytoshop.user import nested_layers
    from pytoshop.enums import ColorMode, BlendMode

    # Provide pure-Python packbits fallback if Cython extension was not built
    if not hasattr(pytoshop.codecs, "packbits"):
        import types

        def _packbits_encode(data):
            if hasattr(data, "tobytes"):
                data = data.tobytes()
            elif isinstance(data, memoryview):
                data = data.tobytes()
            elif not isinstance(data, (bytes, bytearray)):
                data = bytes(data)
            input_size = len(data)
            if input_size == 0:
                return b""
            if input_size == 1:
                return b"\x00" + data
            output = bytearray()
            buffer = bytearray()
            input_pos = 0
            state = 0
            repeat_count = 0
            while input_pos < input_size - 1:
                current_byte = data[input_pos]
                next_byte = data[input_pos + 1]
                if current_byte == next_byte:
                    if state:
                        if repeat_count == 127:
                            output.append(256 - (repeat_count - 1))
                            output.append(current_byte)
                            repeat_count = 0
                        repeat_count += 1
                    else:
                        if buffer:
                            output.append(len(buffer) - 1)
                            output.extend(buffer)
                            buffer.clear()
                        state = 1
                        repeat_count = 1
                else:
                    if state:
                        repeat_count += 1
                        output.append(256 - (repeat_count - 1))
                        output.append(current_byte)
                        state = 0
                        repeat_count = 0
                    else:
                        if len(buffer) == 127:
                            output.append(len(buffer) - 1)
                            output.extend(buffer)
                            buffer.clear()
                        buffer.append(current_byte)
                input_pos += 1
            if state:
                repeat_count += 1
                output.append(256 - (repeat_count - 1))
                output.append(data[input_pos])
            else:
                buffer.append(data[input_pos])
                output.append(len(buffer) - 1)
                output.extend(buffer)
            return bytes(output)

        _pb = types.ModuleType("packbits")
        _pb.encode = _packbits_encode
        pytoshop.codecs.packbits = _pb

    # Fix NumPy 2.x overflow error with negative integer default transparency (-1 -> 255)
    _orig_compress_image = pytoshop.codecs.compress_image
    def _patched_compress_image(fd, image, compression, shape, num_channels, depth, version):
        if isinstance(image, int) and image == -1:
            image = 255
        return _orig_compress_image(fd, image, compression, shape, num_channels, depth, version)
    pytoshop.codecs.compress_image = _patched_compress_image

except ImportError as e:  # pragma: no cover
    raise ImportError(
        "محتاج مكتبة pytoshop عشان تصدير PSD يشتغل:\n"
        "    pip install pytoshop\n"
        f"(الخطأ الأصلي: {e})"
    )


@dataclass
class BubbleLayer:
    """يمثّل طبقة نص واحدة (حبابة واحدة) هتتحط في ملف الـ PSD."""

    name: str                       # اسم الطبقة (هيظهر في فوتوشوب) — مثلاً "حبابة 1"
    image: Image.Image              # صورة PIL بصيغة RGBA، النص مرسوم عليها وباقيها شفاف
    left: int                       # إحداثية X اللي الطبقة هتتحط فيها فوق الصفحة
    top: int                        # إحداثية Y اللي الطبقة هتتحط فيها فوق الصفحة
    visible: bool = True
    opacity: int = 255              # 0-255
    text_raw: str = ""              # النص المترجم الخام (مفيد لو حبيت تحفظه كـ metadata/اسم)


@dataclass
class PageForPSD:
    """كل البيانات المطلوبة لتصدير صفحة واحدة كملف PSD."""

    background: Image.Image                 # الخلفية المنظفة (بعد الـ inpainting) — RGB
    bubbles: List[BubbleLayer] = field(default_factory=list)
    background_name: str = "الخلفية المنظفة"


def _pil_to_channels_rgb(img: Image.Image) -> dict:
    """يحوّل صورة PIL (RGB) لديكشنري قنوات زي ما pytoshop محتاج."""
    arr = np.array(img.convert("RGB"))
    return {0: arr[:, :, 0], 1: arr[:, :, 1], 2: arr[:, :, 2]}


def _pil_to_channels_rgba(img: Image.Image) -> dict:
    """يحوّل صورة PIL (RGBA) لديكشنري قنوات فيها قناة الشفافية."""
    arr = np.array(img.convert("RGBA"))
    return {
        0: arr[:, :, 0],
        1: arr[:, :, 1],
        2: arr[:, :, 2],
        -1: arr[:, :, 3],  # -1 = قناة الـ alpha في pytoshop
    }


def export_page_to_psd(page: PageForPSD, out_path: str, compression=None) -> str:
    """
    بيبني ملف PSD فيه طبقة خلفية + طبقة منفصلة لكل حبابة، ويحفظه في out_path.

    Parameters
    ----------
    page : PageForPSD
        بيانات الصفحة (الخلفية + كل الحبابات).
    out_path : str
        المسار اللي هيتحفظ فيه ملف الـ .psd
    compression : pytoshop.enums.Compression or str, optional
        نوع الضغط: Compression.rle (الافتراضي: حجم أصغر) أو Compression.raw (فائق السرعة).

    Returns
    -------
    str
        نفس out_path (تسهيلًا للاستخدام المتسلسل).
    """
    from pytoshop.enums import Compression

    comp = Compression.rle
    if compression is not None:
        if isinstance(compression, str):
            comp = Compression.raw if compression.lower() == "raw" else Compression.rle
        else:
            comp = compression

    w, h = page.background.size

    layers_bottom_to_top = []

    # طبقة الخلفية (لازم تبقى في القاع)
    bg_layer = nested_layers.Image(
        name=page.background_name,
        visible=True,
        opacity=255,
        blend_mode=BlendMode.normal,
        top=0,
        left=0,
        channels=_pil_to_channels_rgb(page.background),
        color_mode=ColorMode.rgb,
    )
    layers_bottom_to_top.append(bg_layer)

    # طبقة لكل حبابة نص، فوق بعض بترتيب ظهورها في الصفحة
    for b in page.bubbles:
        layer = nested_layers.Image(
            name=b.name,
            visible=b.visible,
            opacity=max(0, min(255, int(b.opacity))),
            blend_mode=BlendMode.normal,
            top=int(b.top),
            left=int(b.left),
            channels=_pil_to_channels_rgba(b.image),
            color_mode=ColorMode.rgb,
        )
        layers_bottom_to_top.append(layer)

    psd_file = nested_layers.nested_layers_to_psd(
        layers_bottom_to_top,
        color_mode=ColorMode.rgb,
        size=(h, w),
        depth=8,
        compression=comp,
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "wb") as fd:
        psd_file.write(fd)

    return out_path


def make_bubble_layer_from_render(
    name: str,
    page_size: Tuple[int, int],
    bbox: Tuple[int, int, int, int],
    rendered_text_img: Image.Image,
    text_raw: str = "",
) -> BubbleLayer:
    """
    دالة مساعدة: لو عندك بالفعل صورة النص المرسوم (rendered_text_img) بحجم
    الـ bbox بتاع الحبابة، الدالة دي بتحطها في مكانها الصح فوق الصفحة كلها
    (transparent كانفس) وترجعلك BubbleLayer جاهزة.

    بدل ما تبني كانفس بحجم الصفحة كلها لكل حبابة (بطيء لو الحبابات كتير)،
    ممكن كمان تسيب rendered_text_img بحجم الـ bbox وتحدد top/left بس —
    pytoshop مش لازم الطبقة تبقى بحجم الصفحة الكلية، بيقبل طبقات أصغر.
    """
    x1, y1, x2, y2 = bbox
    return BubbleLayer(
        name=name,
        image=rendered_text_img.convert("RGBA"),
        left=x1,
        top=y1,
        text_raw=text_raw,
    )


if __name__ == "__main__":
    # مثال تجريبي بسيط: خلفية بيضا + حبابتين نص، للتأكد إن كل حاجة شغالة
    W, H = 900, 1300

    background = Image.new("RGB", (W, H), (255, 255, 255))

    bubble1_img = Image.new("RGBA", (300, 120), (0, 0, 0, 0))
    bubble2_img = Image.new("RGBA", (260, 90), (0, 0, 0, 0))

    from PIL import ImageDraw

    d1 = ImageDraw.Draw(bubble1_img)
    d1.text((10, 40), "مرحباً بالعالم", fill=(0, 0, 0, 255))

    d2 = ImageDraw.Draw(bubble2_img)
    d2.text((10, 30), "هذا اختبار", fill=(0, 0, 0, 255))

    page = PageForPSD(
        background=background,
        bubbles=[
            BubbleLayer(name="حبابة 1", image=bubble1_img, left=120, top=180, text_raw="مرحباً بالعالم"),
            BubbleLayer(name="حبابة 2", image=bubble2_img, left=500, top=700, text_raw="هذا اختبار"),
        ],
    )

    out = export_page_to_psd(page, "test_output.psd")
    print(f"[+] اتحفظ: {out}")
