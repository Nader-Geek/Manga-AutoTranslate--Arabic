# مترجم خودکار مانگا / مانهوا (فارسی)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf512k/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[DEMO](https://demo--amrie194sm.replit.app/)

![app](https://raw.githubusercontent.com/amirwolf512k/Manga-AutoTranslate/refs/heads/main/examples/app.jpg)

ابزاری برای **ترجمه خودکار صفحات مانگا و مانهوا به فارسی**.

متن را با OCR می‌خواند، فقط حروف را از داخل حباب پاک می‌کند، با مدل‌های AI ترجمه می‌کند و متن فارسی را دوباره داخل همان حباب می‌نویسد.

---

## نمونه خروجی
![before](examples/before.jpg)
![debug](examples/debug.jpg)
![clear](examples/clear.jpg)
![after](examples/after.jpg)

---

## فرآیند کار

1. ورودی: پوشه، تصویر، ZIP، PDF یا URL — چند لینک با `,` ، بازه با `1 > 14.jpg` (از اول به آخر) یا `1 < 14.jpg` (از آخر به اول) ، همه با `*.jpg`
2. صفحات کوتاه چسبانده و بلندها تکه‌تکه می‌شوند
3. تشخیص حباب با RT-DETR (حباب / متن داخل / متن آزاد)
4. OCR با PaddleOCR یا RapidOCR — انگلیسی / کره‌ای / ژاپنی / چینی
5. بازسازی فحش‌های سانسورشده
6. ترجمه با مدل انتخابی (چند حباب در هر درخواست)
7. پاکسازی هوشمند متن (فقط حروف — حباب سالم)
8. رندر فارسی با فونت متناسب با لحن
9. خروجی: **PDF / ZIP / HTML / PSD / پوشه تصویر**

---

## ویژگی‌ها

| ویژگی | توضیح |
|---|---|
| تشخیص حباب | RT-DETR-v2 ONNX — تگ چرخیده و نیمه‌شفاف |
| OCR | PaddleOCR / RapidOCR — انگلیسی / کره‌ای / ژاپنی / چینی |
| پاکسازی | خودکار: پرکردن صاف → **big-lama.pt** (یک‌جا برای کل صفحه) → OpenCV |
| ضدلیمیت Gemini | پیسینگ نرخ + تشخیص سهمیهٔ روزانه + چرخش کلید/مدل |
| ماسک فقط حروف | آستانه‌گذاری تطبیقی + فیلتر مؤلفه |
| دور دوم جارو | حروف جامانده پاک می‌شوند |
| متن چرخیده | زاویه از خطوط OCR — فقط وقتی سازگارند |
| اندازه فونت | برابر ارتفاع واقعی خطوط اصلی (از OCR) |
| واترمارک | تشخیص و نادیده گرفتن |
| فیلتر SFX / junk | تبلیغ و افکت صوتی ترجمه نمی‌شود |
| پنجرهٔ سیستم | حباب‌های UI (Status/Quest/…) با براکت/دونقطه/کلیدواژه در انگلیسی/ژاپنی/کره‌ای/چینی — خط‌به‌خط جدا و با فونت مخصوص؛ جعبهٔ مشخصات شخصیت (NAME / AGE: 40 / RACE: …) همیشه خط‌به‌خط جدا می‌شود؛ حباب عادی هیچ‌وقت خط‌خطی نمی‌شود |
| برش امن دوطرفه | دو کارگر تشخیص — یکی از صفحهٔ اول به آخر، یکی از آخر به اول — سریع‌تر، بدون تغییر کیفیت برش |
| چند ارائه‌دهنده | Gemini, OpenAI, DeepSeek, Groq, xAI, Together, OpenRouter, Ollama |
| Fallback Gemini | زنجیره خودکار مدل‌ها |
| چند کلید API | چرخش خودکار |
| بچ ترجمه | چند حباب + قفل سراسری |
| واژه‌نامه | قفل اسامی + ذخیره خودکار |
| بریف داستان | حفظ لحن شخصیت‌ها |
| رندر فارسی | reshaper + bidi + فونت لحن |
| چندفصل | `*` همه / `,` چند لینک / `1 > 14.jpg` از اول به آخر / `1 < 14.jpg` از آخر به اول |
| **خروجی** | پوشه / ZIP / PDF / HTML / **PSD لایه‌ای** |
| نام هوشمند | از URL یا مسیر فصل |
| Resume | ادامه از کش |
| Chunk / Stitch | کاهش مصرف API |
| دیباگ | مربع رنگی + خروجی دیباگ |

---

## خروجی PSD

هر صفحه به‌صورت یک لایه جدا در فایل PSD ذخیره می‌شود (با `pytoshop`).

- لایه‌ها مرتب از پایین به بالا
- بوم مشترک با بزرگ‌ترین ابعاد صفحات
- اگر ابعاد > ۳۰۰۰۰px → **PSB**
- در `--debug` فایل `*_debug.psd` هم ساخته می‌شود
- نصب خودکار `pytoshop`

```bash
python manga.py -i input -o chapter.psd --font fonts/Vazirmatn-Bold.ttf --api-key KEY
python manga.py -i "URL" -o .psd --font fonts/Vazirmatn-Bold.ttf --api-key KEY
```

در رابط برنامه هم گزینه **PSD** در قالب خروجی وجود دارد.

---

## برنامه (`manga_app.py`)

محیط را تشخیص می‌دهد:

| محیط | رفتار |
|---|---|
| ویندوز / لینوکس / مک (دسکتاپ) | پنجرهٔ نیتیو (pywebview / WebView2) — دقیقاً همان رابط وب؛ تنظیمات و کلید API دائمی ذخیره می‌شود؛ «نمایش» داخل خود پنجرهٔ برنامه باز می‌شود (نه مرورگر) |
| Google Colab | رابط وب تیره + لینک عمومی gradio.live خودکار |
| Molab Marimo | رابط وب تیره + لینک عمومی gradio.live خودکار |
| GitHub Codespaces | رابط وب + لینک عمومی (بدون Port Forwarding) |
| GitHub Actions | رابط وب + لینک عمومی |

- لانچرها: `Manga.bat` / `manga.sh` → **App / Web / CLI / Exit** — خودشان هم با آپدیت برنامه به‌روز می‌شوند
- آپدیت خودکار: اول فقط فایل VERSION چک می‌شود (چند بایت) — اگر نسخهٔ جدید بود فایل‌ها موازی دانلود می‌شوند؛ هر ۳۰ دقیقه
- ذخیرهٔ تنظیمات: مرورگر وب ۳۰ دقیقه؛ پنجرهٔ دسکتاپ و اندروید دائمی
- «نمایش»: یک نمایش واحد — صفحه‌های جدید تا کار در جریان است سر جای‌شان پر می‌شوند؛ دکمهٔ 🔍 دیباگ داخل خود نمایش؛ نوار پیشرفت پایین؛ دکمه‌های پهنا بزرگ/کوچک؛ نوار بالا با اسکرول پایین می‌رود (ثابت نیست)
- «⬇ دانلود دیباگ»: بعد از پایان کار دیباگ‌دار، خروجی دیباگ را جدا می‌دهد
- فونت رابط از خودِ برنامه می‌آید (بدون fonts.googleapis.com) — بالا آمدن سریع در ایران
- خواننده وب تمام‌صفحه پایدار
- CLI تعاملی: ورودی، ارائه‌دهنده، کلید و قالب (شامل PSD) را می‌پرسد
- گارد: اگر `manga.py` فایل مترجم نباشد پیام واضح می‌دهد

```bash
python manga_app.py              # تشخیص خودکار
python manga_app.py --web        # اجبار وب
python manga_app.py --desktop    # اجبار پنجره برنامه
python manga_app.py --cli        # CLI تعاملی
python manga_app.py -- -i input -o out.psd --font fonts/Vazirmatn-Bold.ttf --api-key KEY --cpu --lama
```

---

## اپ اندروید(وضعیت در حال تسته)

نسخهٔ اندروید (Chaquopy — همان موتور `manga.py` روی گوشی) هم دارد:

- دانلود APK از [Releases](https://github.com/amirwolf512k/Manga-AutoTranslate/releases/tag/android) — یا بیلد از سورس با Gradle / GitHub Actions
- راهنمای کامل نصب، بیلد و رفع مشکل: [`android/README.md`](android/README.md)
- OCR روی گوشی = PP-OCRv6 ONNX فقط رویِ کراپهایِ detector-v4-s (سبکِ PC)؛ فونت‌ها و مدل‌ها بار اول خودکار دانلود می‌شوند

---

## ارائه‌دهنده‌ها

| provider | مدل پیش‌فرض | متغیر محیطی |
|---|---|---|
| gemini | gemini-3.8-flash | GEMINI_API_KEY |
| custom | — | CUSTOM_API_KEY |

**سرویس دلخواه (custom)** — ۴ فرمت API خودکار از روی خودِ لینک شناخته می‌شود؛ لینک کامل endpoint را هم می‌شود چسباند:

| فرمت | نمونه لینک |
|---|---|
| OpenAI Chat Completions | `https://opencode.ai/inference/openai/v1/chat/completions` |
| OpenAI Responses API | `https://…/v1/responses` |
| Anthropic Compatible | `https://…/v1/messages` |
| Google Generative AI | `https://…/models/gemini-2.0-flash:generateContent` |

«تست کلید» خطاها را فارسیِ واضح توضیح می‌دهد — مثلاً اگر کلید اوپن‌کد سالم باشد ولی مدل «free» فقط داخل خود برنامهٔ OpenCode اجرا شود، پیام می‌دهد که باید مدل پولی یا سرویس دیگری بگذاری.

پاکسازی: متنِ داخلِ حبابِ سفید/روشن با رنگِ خودِ حباب پر می‌شود (نه TELEA/LaMa) تا تیرگیِ حاشیه یا هافتونِ دورِ حباب هرگز به داخل کشیده نشود — لکهٔ سیاه/خاکستری وسط حباب حذف شد. متنِ روی تیغهٔ فکوس/هافتون هم امن است: هنرِ تیرهٔ اطراف حفظ می‌شود و بقایای ریز OCR (حروف جاافتاده مثل «TH») داخلِ حبابِ سفید خودکار پیدا و پاک می‌شوند. دو متنِ جدا دیگر هیچ‌وقت یکی نمی‌شوند: شکست خط (\n) از ترجمه تا رندر حفظ می‌شود و دو متن زیر هم می‌نشینند.

---

## پارامترهای مهم

| پارامتر | توضیح | پیش‌فرض |
|---|---|---|
| `-i` / `--input` | ورودی | اجباری |
| `-o` / `--output` | خروجی (`.pdf` / `.zip` / `.html` / **`.psd`** / پوشه) | اجباری |
| `--font` | فونت فارسی | اجباری |
| `--provider` | ارائه‌دهنده | gemini |
| `--api-key` | کلید API | یا env |
| `--model` | مدل | پیش‌فرض provider |
| `--ocr-lang` | زبان OCR | en |
| `--gpu` / `--cpu` | سخت‌افزار | خودکار |
| `--lama` | اجبار LaMa روی CPU (big-lama.pt) | خودکار |
| `--bubbles-per-request` | حباب در هر درخواست | 15 |
| `--batch-workers` | بسته موازی | 3 |
| `--det-confidence` | آستانه تشخیص | 0.16 |
| `--glossary` | واژه‌نامه | — |
| `--no-brief` | خاموش بریف | — |
| `--no-resume` | شروع دوباره | — |
| `--img-format` | webp / png / jpg | jpg |
| `--quality` | کیفیت ۱–۱۰۰ | 90 |
| `--max-width` | سقف عرض | 0 |
| `--debug` | دیباگ | — |

فونت‌های لحن: `--font-normal` · `--font-shout` · `--font-comedy-shout` · `--font-whisper` · `--font-thought` · `--font-system` · `--font-letter` · `--font-narrator` · `--font-free` و ...

با `-o .psd` نام فایل از URL ساخته می‌شود.

---

## پاکسازی متن

| شرایط | روش |
|---|---|
| پس‌زمینه تخت / گرادیان | پرکردن صاف (بدون مدل) |
| بقیهٔ حباب‌ها | big-lama.pt — یک بار برای کل صفحه |
| اگر LaMa نبود | OpenCV مؤلفه‌به‌مؤلفه (هر حفره با رنگ همسایگی خودش) |

- مدل‌های LaMa-Manga / LaMa ONNX فقط وقتی `torch` در دسترس نیست به‌کار می‌روند.
- نوارهای بسیار بلند (وبتون) باندبه‌باند پردازش می‌شوند.
- خطوط دیوار حباب از ماسک اینپینت محافظت می‌شوند (خط حباب پاک نمی‌شود).
- ماسک فقط حروف + دور دوم جارو.

---

## استخراج متن (PaddleOCRLite) و GPU+CPU همزمان

از **v1.14.106** موتور استخراجِ PaddleOCR (PP-OCR) با دو رانر در اختیار است:

| محیط | رانر | شتاب |
|---|---|---|
| اندروید (arm64) | PP-OCRv6 ONNX (رویِ کراپهایِ detector-v4-s) | CPU چندنخی + سشن‌هایِ مشترک |
| PC لینوکس/ویندوز/شبیه‌ساز | ONNX Runtime | CUDA/DML/OpenVINO + CPU همزمان |

- زبان‌ها: `en` | `ko` | `ja` | `zh` (مدل مخصوص هر زبان خودکار دانلود می‌شود؛ dict از مدل خوانده می‌شود).
- تست سریع روی PC: `python3 manga.py --ocr-test examples/01.jpg --ocr-lang en`
- استخراجِ متن (همهٔ پلتفرم‌ها): اول `detector-v4-s_int8.onnx` مکان‌هایِ متن را پیدا می‌کند و OCR فقط رویِ همان کراپ‌ها اجرا می‌شود؛ سبکِ قدیمیِ «استخراج و پاکسازی»ٔ گوشی (کاسکاد/ML Kit/Paddle-Lite) حذف شده است.
- **dual-device** (پیش‌فرض خودکار): وقتی GPU واقعاً در دسترس باشد، پچ‌های پاکسازی و برش‌های rec بین GPU و CPU می‌چرخند → سرعت بیشتر. با `MANGA_DUAL_DEVICE=0` خاموش می‌شود. روی سیستم CPU-خالص هیچ تغییری نمی‌کند (خروجی بیت‌به‌بیت همان قبل).

---

## لیمیت رایگان Gemini

تیر فری هر مدل flash حدود **۲۰ درخواست در روز** دارد (به‌ازای هر کلید/پروژه). برنامه خودش مدیریت می‌کند:

- فاصلهٔ امن بین درخواست‌ها رعایت می‌شود تا 429 نخورد
- روی 429: اول کلید بعدی با همان مدل، بعد مدل بعدی (به سمت lite)
- خطای «سهمیهٔ روزانه» فوراً تشخیص داده می‌شود و معطل ثانیه‌ها نمی‌ماند
- بریف داستان با مدل سبک زده می‌شود تا سهمیهٔ مدل اصلی نسوزد
- چند کلید = چند پروژه = چند برابر سهمیه

---

## پنج روش اجرا

### ۱) Google Colab (پیشنهادی)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amirwolf512k/Manga-AutoTranslate/blob/main/Manga_Translator_Colab.ipynb)

```bash
!bash manga.sh
```

لینک عمومی `gradio.live` خودکار چاپ می‌شود. ⚠ هر دو فایل `manga.py` (مترجم) و `manga_app.py` (برنامه) باید کنار هم باشند.


### 2) molab marimo

[![Open In marimo](https://marimo.io/shield.svg)](https://molab.marimo.io/github/amirwolf512k/Manga-AutoTranslate/blob/main/Manga-AutoTranslate.py/server)

```bash
bash manga.sh
```

لینک عمومی `gradio.live` خودکار چاپ می‌شود. ⚠ هر دو فایل `manga.py` (مترجم) و `manga_app.py` (برنامه) باید کنار هم باشند.

### 3) GitHub Codespaces

```bash
bash manga.sh
```

لینک عمومی خودکار می‌دهد؛ یا تب Ports → پورت 7860 → Public. برای زنده‌ماندن سرور بعد از بستن ترمینال از tmux استفاده کنید:

```bash
tmux new -s manga 'python3 manga_app.py --web'
# detach: Ctrl+B بعد D | بازگشت: tmux attach -t manga
```

### 4) GitHub Actions

ریپو را Fork کن.

از تب Actions یکی از دو ورک‌فلو را Run کن:

- **Manga Web (موقت)** — رابط وب با لینک gradio.live در لاگ؛ بعد از زمان تعیین‌شده خاموش می‌شود؛ خروجی را قبل از خاموش شدن از UI دانلود کن

Runnerهای GitHub معمولاً GPU ندارند؛ اجرا روی CPU است و برای batch/CLI مناسب‌تر است. وب فقط موقت است و لینک دائمی نمی‌دهد.

### 5) اجرای لوکال

```bash
git clone https://github.com/amirwolf512k/Manga-AutoTranslate.git
cd Manga-AutoTranslate

Manga.bat    # ویندوز — منو: App / Web / CLI
./manga.sh   # لینوکس / مک
```

یا مستقیم:

```bash
python manga_app.py          # تشخیص خودکار (دسکتاپ یا وب)
python manga_app.py --cli    # CLI تعاملی
python manga_app.py -- -i "https://...chapter-1/" -o out.psd --font fonts/Vazirmatn-Bold.ttf --api-key KEY --cpu
```

---

## محدودیت‌ها

- تایتل‌های خیلی بزرگ با هاله نورانی که با نقاشی قاطی شده‌اند ممکن است کاملاً پاک نشوند.
- روی CPU، اینپینت big-lama یک بار برای کل صفحه اجرا می‌شود (برای نوارهای خیلی بلند، باندبه‌باند).
- کیفیت ترجمه به مدل و OCR بستگی دارد؛ متن خیلی استایل‌شده گاهی ناقص خوانده می‌شود.
- SFXهای هنری ممکن است دیده نشوند؛ چون ترجمه نمی‌شوند معمولاً مشکلی نیست.
- واترمارک‌های نصفه‌کاره گاهی به‌اشتباه دیالوگ تشخیص داده می‌شوند.
- بعضی مدل‌های OpenAI-compatible ممکن است JSON را دقیق رعایت نکنند؛ با `--max-retries` بیشتر امتحان کنید.

---

## واژه‌نامه

```
Sung Jinwoo=سونگ جینوو
Cha Hae-In=چا هه این
```

یا `glossary.json` — اسامی قفل و برای فصل بعد ذخیره می‌شوند.

---

## حمایت مالی

ヾ(•ω•`)o

**TON:** `UQBScvayaxagwTfRBhlLNaqw-sZuadlnBjSvn8OJz7XZJJzT`

**TRX:** `TMmLTaCjaW1L2xWZmpR2EBeNyCawCzEkwa`

---

## لایسنس

MIT — آزاد برای استفاده شخصی و غیرتجاری.

حقوق مانگا/مانهوا متعلق به ناشر و خالق اثر است؛ این ابزار فقط برای مطالعه شخصی است.

**توسعه‌دهنده:** [amirwolf512k](https://github.com/amirwolf512k)  
**تلگرام:** [@Amir_wolf512](https://t.me/Amir_wolf512)
