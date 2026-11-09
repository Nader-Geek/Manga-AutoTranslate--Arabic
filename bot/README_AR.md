# 🤖 بوت ديسكورد — مترجم المانجا العربي

أوامر البوت (كلها تعمل عبر طابور في PostgreSQL ويشغّل `manga.py` كعملية منفصلة):

| الأمر | الوظيفة | الناتج |
|---|---|---|
| `/clean` | مسح النص من الفقاعات | ZIP صفحات نظيفة |
| `/extract` | استخراج النصوص الأصلية | `extract.txt` + `extract.json` |
| `/typer` | تنظيف + إحداثيات الفقاعات | `typer.zip` (للاستيراد في TypeR Web) |
| `/translate` | ترجمة عربية كاملة عبر Ollama | ZIP أو PDF |
| `/status` `/history` `/cancel` `/queue` `/ping` | متابعة وإدارة | — |

بعد كل مهمة يعرض البوت: عدد الصفحات (والفارغة منها)، الفقاعات، توزيعها (حوار / مؤثرات / إعلانات)،
النبرات، الحوارات المترجمة، طريقة المسح، المدة وحجم الناتج. تُحذف الملفات من السيرفر بعد 20 دقيقة.

## التشغيل
```bash
pip install -r requirements.txt -r bot/requirements.txt
cp bot/.env.example bot/.env      # عبّئ DISCORD_TOKEN و DATABASE_URL
createdb mangabot                 # PostgreSQL (الجداول تُنشأ تلقائياً)
python -m bot
```
ادعُ البوت بـ scopes: `bot` و`applications.commands` (لا يحتاج أي privileged intents).
للترجمة شغّل Ollama (`ollama pull qwen2.5:7b-instruct`)، أو وجّه `OLLAMA_URL` لجهاز آخر.

## للتجربة بدون جهاز
- `notebooks/Manga_Bot_Kaggle.ipynb` — يجرّب كل الأوامر ويشغّل البوت (Ollama + PostgreSQL مضمّن).
- `notebooks/Manga_Bot_Colab.ipynb` — نفس الشيء على Google Colab (T4 مجاني، أسرار من 🔑).
- `notebooks/molab_manga.py` — واجهة marimo لتجربة الأوامر ومعاينة قبل/بعد.

## الاختبارات
```bash
python tests/test_bot_stats.py && python tests/test_bot_runner.py && python tests/test_bot_ui.py
python tests/test_bot_localrun.py
TEST_DATABASE_URL=postgresql://user@localhost/testdb python tests/test_bot_worker.py   # يمسح جدول jobs!
```
الاختبارات تستخدم `tests/fake_manga.py` بدل الموديلات الحقيقية.
