# مهمة: إضافة دعم اللغة العربية + تصدير PSD متعدد الطبقات
## مشروع Manga-AutoTranslate

اقرأ التعليمات دي كاملة الأول، وبعدين ابدأ التنفيذ خطوة بخطوة. بعد كل
خطوة كبيرة، شغّل اختبار سريع للتأكد إن حاجة تانية معطلتش قبل ما تكمل.

---

## الخطوة 0: الاستكشاف (اعمل الأول قبل أي تعديل)

اقرأ `manga.py` كامل ولاقي واستخرج أماكن الحاجات دي بالظبط (اكتب أرقام
الأسطر و imports و signatures عشان تستخدمهم بعدين):

1. أي مكان فيه نص عربي/فارسي ثابت (hardcoded) بيتبعت كـ prompt/تعليمات
   لموديل الترجمة (Gemini/OpenAI/DeepSeek/Groq/...) — دوّر على كلمات
   زي "فارسی" أو "محاوره" أو "ترجم" جوه أي string أو f-string.
2. الدالة اللي بترسم النص المترجم فوق كل حبابة (PIL.ImageDraw على الأغلب)
   — هتلاقي فيها استخدام `arabic_reshaper` و `bidi.algorithm.get_display`
   ودوران النص وحساب حجم الفونت.
3. الدالة/الكلاس اللي بيحدد الفونت الافتراضي ومسارات فونتات اللحن
   (`--font`, `--font-shout`, `--font-whisper`, ...).
4. `argparse.ArgumentParser` — كل تعريفات `add_argument` الموجودة،
   خصوصًا أي حاجة متعلقة باللغة (`--ocr-lang` مثلًا).
5. الدالة/الدوال المسؤولة عن حفظ المخرجات النهائية (PDF / ZIP / صورة /
   HTML) — دوّر على أسماء زي `save_output`, `export_page`,
   `build_pdf`, `write_zip`, أو أي دالة بتاخد قائمة صفحات وتحفظها.
6. الـ dataclass أو الـ dict اللي بيمثّل "حبابة" واحدة بعد الكشف
   (bounding box, نص OCR, نص مترجم, زاوية الدوران, حجم الخط...) —
   على الأغلب قريب من `RTDetrV2ONNXDetector` أو مرحلة الترجمة.

اكتب ملخص قصير بالنتايج دي قبل ما تكمل للخطوة اللي بعدها.

---

## الخطوة 1: دعم اللغة العربية (`--target-lang`)

### 1.1 ديكشنري الإعدادات
ضيف بعد الـ imports مباشرة (بعد استيراد `arabic_reshaper` و `bidi`):

```python
LANG_CONFIG = {
    "fa": {
        "label": "فارسی",
        "reshaper_language": "Farsi",
        "default_font": "fonts/Vazirmatn-Bold.ttf",
        "prompt_instruction": (
            "متن حباب‌ها را به فارسیِ محاوره‌ای و طبیعی ترجمه کن؛ "
            "لحن شخصیت‌ها را حفظ کن."
        ),
    },
    "ar": {
        "label": "العربية",
        "reshaper_language": "Arabic",
        "default_font": "fonts/Cairo-Bold.ttf",
        "prompt_instruction": (
            "ترجم نص الحبابات إلى العربية الفصحى المبسطة أو العامية "
            "الواضحة، بأسلوب طبيعي يحافظ على نبرة كل شخصية ومزاجها."
        ),
    },
}

def get_lang_config(code: str) -> dict:
    if code not in LANG_CONFIG:
        raise ValueError(f"لغة غير مدعومة: {code} (المتاح: {list(LANG_CONFIG)})")
    return LANG_CONFIG[code]
```

### 1.2 باراميتر CLI جديد
في نفس مكان تعريفات `add_argument` الموجودة، ضيف:

```python
parser.add_argument(
    "--target-lang", "-tl",
    choices=list(LANG_CONFIG.keys()),
    default="fa",
    help="اللغة الهدف للترجمة (fa = فارسی، ar = العربية)",
)
```

اتأكد إن `args.target_lang` بيتمرر لكل الدوال اللي محتاجاه (بناء الـ
prompt، اختيار الفونت، الـ reshaping) — إما كـ parameter صريح أو عن
طريق كائن config عام لو الكود بيستخدم حاجة زي `self.config` بالفعل.

### 1.3 تعديل الـ prompt
في الدالة اللي لقيتها في الخطوة 0.1، استبدل النص الثابت بـ:

```python
lang_cfg = get_lang_config(target_lang)   # target_lang جاي من args أو self
instruction = lang_cfg["prompt_instruction"]
```

وادمجه في نفس مكان النص القديم بدون ما تغيّر باقي بنية الـ prompt
(الـ JSON schema، الـ glossary، تعليمات الـ SFX... كلها تفضل زي ما هي).

### 1.4 الفونت الافتراضي
في الدالة اللي بتحدد الفونت (الخطوة 0.3)، لو `args.font` فاضي:

```python
font_path = args.font or lang_cfg["default_font"]
```

نفس المنطق لفونتات اللحن (`--font-shout` إلخ) لو مفيش نسخة عربية —
خليها ترجع لـ `default_font` كـ fallback بدل ما تكسر.

**اعمل placeholder** لملف فونت عربي (مثلاً حمّل خط Cairo أو Amiri أو
Noto Naskh Arabic مجاني ومفتوح المصدر) وحطه في `fonts/`، وسمّيه زي ما
كتبت في `default_font` بالظبط.

### 1.5 الـ reshaping
اتأكد إن استدعاء `arabic_reshaper` بيستخدم `lang_cfg["reshaper_language"]`
لو الكود بيبني `ArabicReshaper(configuration=...)` بنفسه. لو بيستخدم
`arabic_reshaper.reshape(text)` مباشرة (الإعداد الافتراضي)، سيبه زي ما
هو — الإعداد الافتراضي شغال مع العربي كويس، وممكن تسيبه كده وتختبر.

### 1.6 اختبار
```bash
python manga.py -i examples/before.png -o test_ar.pdf --target-lang ar --font fonts/Cairo-Bold.ttf --api-key $GEMINI_API_KEY --cpu
```
تأكد إن الناتج فيه نص عربي متشكّل صح (متصل، من اليمين لليسار، من غير
حروف منفصلة أو مقلوبة).

---

## الخطوة 2: تصدير PSD متعدد الطبقات

عندي موديول جاهز اسمه `psd_export.py` (هرفقه/هبعته منفصل) فيه:
- `PageForPSD` — dataclass للصفحة (خلفية + قائمة حبابات)
- `BubbleLayer` — dataclass لكل حبابة (صورة RGBA شفافة + إحداثيات)
- `export_page_to_psd(page, out_path)` — بيبني الملف فعليًا

**نبّهني/الوكيل:** الموديول ده اتكتب من غير اختبار فعلي لمكتبة
`pytoshop` (كانت من غير إنترنت وقت الكتابة) — أول حاجة تعملها:

```bash
pip install pytoshop
python psd_export.py    # لازم يعمل test_output.psd من غير error
```

لو فيه خطأ في أسماء الباراميترات بتاعة `nested_layers.Image(...)`،
راجع `pytoshop` docs/source المثبتة عندك (`python -c "import pytoshop; help(pytoshop.user.nested_layers.Image)"`)
واصلح الأسماء تبعًا لكده.

### 2.1 التكامل مع manga.py

في الدالة اللي بترسم النص فوق كل حبابة (خطوة 0.2)، بدل ما ترسم مباشرة
على الصورة النهائية:

1. لكل حبابة، ارسم النص على `Image.new("RGBA", (bw, bh), (0,0,0,0))`
   بحجم الـ bounding box بتاعها (زوّد هامش شوية لو النص بيدور بزاوية
   عشان مايتقصش عند الحواف).
2. اجمع كل الحبابات دي في list من `BubbleLayer` (من `psd_export.py`)
   مع `left`, `top` = إحداثيات الـ bbox الأصلية على الصفحة.
3. خزّن الخلفية المنظفة (الصورة بعد الـ inpainting، قبل ما يتلزق فيها
   أي نص) كـ `PageForPSD.background`.

### 2.2 باراميتر إخراج جديد

ضيف قيمة جديدة لأي منطق موجود بيحدد صيغة الإخراج (PDF/ZIP/HTML/folder):

```python
parser.add_argument(
    "--psd", action="store_true",
    help="صدّر كل صفحة كملف PSD متعدد الطبقات بجانب/بدل الصيغة العادية",
)
```

وفي نفس مكان حفظ كل صفحة (خطوة 0.5)، لو `args.psd`:

```python
from psd_export import PageForPSD, BubbleLayer, export_page_to_psd

page = PageForPSD(background=cleaned_bg_image, bubbles=bubble_layers)
psd_path = os.path.join(output_dir, f"{page_name}.psd")
export_page_to_psd(page, psd_path)
```

خليه إضافي (additive) — يعني ميبوظش مسار PDF/ZIP العادي إلا لو
المستخدم طلب `--psd` صراحةً.

### 2.3 اختبار
```bash
python manga.py -i examples/before.png -o out --psd --font fonts/Cairo-Bold.ttf --api-key $GEMINI_API_KEY --cpu
```
افتح ملف الـ `.psd` الناتج بفوتوشوب (أو GIMP لو مفيش فوتوشوب) وتأكد إن:
- فيه طبقة خلفية منفصلة
- فيه طبقة منفصلة لكل حبابة نص، بمكانها الصح فوق الخلفية
- تقدر تخفي/تحرك أي طبقة نص لوحدها من غير ما تأثر على الباقي

---

## ملاحظات عامة للوكيل

- متلمسش أي منطق خاص بـ OCR أو الكشف (RT-DETR) أو الـ inpainting
  (LaMa) — الميزتين دول بس إضافة على مرحلتي "الترجمة/الرندر" و"الحفظ
  النهائي".
- حافظ على التوافق العكسي: لو حد شغّل البرنامج من غير `--target-lang`
  أو `--psd`، السلوك الافتراضي يفضل بالظبط زي ما كان (فارسي + PDF/ZIP
  العاديين).
- بعد كل تعديل، شغّل نسخة صغيرة (صورة واحدة) للتأكد إن حاجة معطلتش
  قبل ما تكمل للخطوة اللي بعدها.
