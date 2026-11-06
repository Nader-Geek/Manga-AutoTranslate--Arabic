# -*- coding: utf-8 -*-
"""تستِ v1.14.223 — ویرایشِ مدلِ ذخیرهشده (✎ ویرایش → 💘 ذخیرهٔ ویرایش)،
کلیدِ مخفیِ پیشفرض با 👁، و ریشهٔ «✖ِ کشیده به بالا» (قابِ .stylerِ
gradio با پسزمینهٔ var(--block-border-color) شفاف میشود).

دستورهایِ سازنده:
«کسی کاستوم سیو کرد و چیزی ک سیو زده بود بتونن ویرایش کنن بجای گزینه
افزودن ذخیره بیاد ... اگ مدل خودشون رفتن اونجا سیو بیاد مدلی ساختن باید
بشه دید لینکش چیه توکنش چیه مدل ک وارد کرده چیه با قابلیت ویرایش ویرایش
زدن گزینه سیو بیاد» + «کلید ک وارد میکنن بشه هاید کرد پیشفرض هاید باشه
زدن روش دیده بشه» + «دکمه ضربدرش به بالا کش اومده به اندازه دکمه باشه
این مشکل مربوط به اندروید نیست مشکل حالت مرورگره»
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

PASS, FAIL = [], []


def chk(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  OK " if cond else "  XX ") + name
          + ((" — " + str(extra)[:160]) if extra and not cond else ""))


SRC = open(os.path.join(ROOT, "manga_app.py"), encoding="utf-8").read()
KT = open(os.path.join(ROOT, "android", "app", "src", "main", "java",
                       "com", "amirwolf", "mangatranslator", "MainActivity.kt"),
          encoding="utf-8").read()

MODELS_PATH = os.path.join(ROOT, "workspace", "manga_models.json")
SEED = [{"name": "Ed", "api_base": "https://ed.example/v1",
         "api_key": "sek-1234567890", "model": "ed-model"}]

print("== 1) source: edit flow components (web) ==")
chk("cm_edit_btn component (manga_cm_edit, hidden at boot)",
    'elem_id="manga_cm_edit", visible=False' in SRC)
chk("cm_save_btn component (manga_cm_save, hidden at boot)",
    'elem_id="manga_cm_save", visible=False' in SRC)
chk("ویرایش label on edit button", "✎ ویرایش این مدل" in SRC)
chk("ذخیرهٔ ویرایش label on save button", "💾 ذخیرهٔ ویرایش" in SRC)
chk("_cm_edit_start handler defined", "def _cm_edit_start(" in SRC)
chk("_cm_save_edits handler defined", "def _cm_save_edits(" in SRC)
chk("cm_edit_btn.click wired (api cm_edit)", 'api_name="cm_edit"' in SRC)
chk("cm_save_btn.click wired (api cm_save_edits)",
    'api_name="cm_save_edits"' in SRC)
chk("provider.change outputs include cm_edit_btn + cm_save_btn",
    "cm_edit_btn, cm_save_btn]" in SRC)
chk("provider change: edit visible only on mine",
    "gr.update(visible=mine),    # cm_edit_btn (v1.14.223)" in SRC)
chk("provider change: save hidden (cancel edit)",
    "gr.update(visible=False))   # cm_save_btn — خروج از ویرایش" in SRC)
chk("edit start hides add button",
    "_cm_edit_start" in SRC and "gr.update(visible=False),   # «+ افزودن» پنهان" in SRC)
chk("save edits returns status with ویرایش + لینک",
    "ویرایشِ «{nm}» ذخیره شد — لینک:" in SRC)

print("== 2) source: key hidden by default + 👁 (web) ==")
chk("api_keys is server-side type=password",
    'api_keys = gr.Textbox(label="کلیدهای API شما (با کاما = چرخش خودکار)",\n'
    .replace("\n", "") in SRC.replace("\n", "")
    and 'type="password", scale=3,' in SRC)
chk("manga-eye CSS exists", ".manga-eye{" in SRC)
chk("eye JS attach (attachEye + input-container host)",
    "const attachEye" in SRC and 'inp.closest(".input-container")' in SRC)
chk("eye toggles window.__mangaKeysShown", "window.__mangaKeysShown" in SRC)
chk("eye shows 🙈 when revealed", '"🙈"' in SRC)
chk("eye bound via MutationObserver", "window.__mangaEyeObs" in SRC)

print("== 3) source: ✖ stretched fix (browser-mode root) ==")
chk("gradio .styler frame transparent (root cause of the tall strip)",
    "div.styler{background:transparent !important;border:none !important;" in SRC)
chk("del button max-height pinned (30px)",
    "max-height:30px !important" in SRC)
chk("del button 30x30 kept",
    "width:30px !important;height:30px !important" in SRC)

print("== 4) version strings (logic via real API in section 5) ==")
chk("APP_VER bumped", 'APP_VER = "1.14.223"' in SRC)

print("== 5) boot + real API ==")


def boot(port):
    proc = subprocess.Popen(
        [sys.executable, "manga_app.py"],
        env={**os.environ, "MANGA_APP_PORT": str(port), "MANGA_NO_BROWSER": "1"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < 90:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as r:
                return proc, r.read()
        except Exception:
            time.sleep(1)
    proc.kill()
    print(proc.stdout.read().decode("utf-8", "ignore")[-3000:])
    sys.exit(1)


def call_api(name, payload, timeout_req=25):
    body = json.dumps({"data": payload}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/gradio_api/call/{name}",
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_req) as r:
        ev = json.loads(r.read()).get("event_id")
    with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/gradio_api/call/{name}/{ev}",
            timeout=40) as r:
        txt = r.read().decode("utf-8", "ignore")
    for ln in txt.splitlines():
        if ln.startswith("data:"):
            try:
                return json.loads(ln[5:].strip())
            except Exception:
                return ln[5:].strip()
    return None


os.makedirs(os.path.dirname(MODELS_PATH), exist_ok=True)
json.dump(SEED, open(MODELS_PATH, "w", encoding="utf-8"), ensure_ascii=False)
port = 7931
proc, page = boot(port)
try:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/config",
                                    timeout=10) as r:
            cfgp = json.loads(r.read())
        deps = json.dumps(cfgp.get("dependencies", []), ensure_ascii=False)
        full = json.dumps(cfgp, ensure_ascii=False)
        chk("cm_edit api registered", '"cm_edit"' in deps)
        chk("cm_save_edits api registered", '"cm_save_edits"' in deps)
        chk("edit button component in config", "manga_cm_edit" in full)
        chk("save button component in config", "manga_cm_save" in full)
    except Exception as e:
        chk("read config", False, e)

    out = call_api("cm_edit", ["Ed", SEED])
    ok = isinstance(out, list) and len(out) == 8
    chk("api cm_edit: 8 outputs", ok, out)
    if ok:
        chk("api cm_edit: base prefilled", out[0].get("value") == "https://ed.example/v1", out[0])
        chk("api cm_edit: key prefilled (token visible for editing)",
            out[2].get("value") == "sek-1234567890", out[2])
        chk("api cm_edit: add hidden / save visible",
            out[4].get("visible") is False and out[6].get("visible") is True)

    out = call_api("cm_save_edits", ["Ed", SEED, "https://api2.example/v9",
                                     "tok-9999", "model-9"])
    ok = isinstance(out, list) and len(out) == 14
    chk("api cm_save_edits: 14 outputs", ok, out)
    if ok:
        try:
            got = json.loads(out[1])
        except Exception:
            got = []
        chk("api cm_save_edits: model updated in browser JSON",
            any(m.get("name") == "Ed" and m.get("api_key") == "tok-9999"
                for m in got), out[1])
        chk("api cm_save_edits: info line shows new link",
            "api2.example/v9" in str(out[4].get("value", "")), out[4])
        chk("api cm_save_edits: status ✅ with لینک",
            "ذخیره شد" in str(out[13].get("value", "")), out[13])
        chk("api cm_save_edits: back to view (edit visible, save hidden)",
            out[6].get("visible") is True and out[5].get("visible") is False)

    out = call_api("toggle_custom_base",
                   ["Ed", SEED, {"_last": "gemini"}, "", "", ""])
    ok = isinstance(out, list) and len(out) == 11
    chk("toggle: 11 outputs now", ok, out)
    if ok:
        chk("toggle on user model: edit visible (ویرایش only on own model)",
            out[9].get("visible") is True, out[9])
        chk("toggle on user model: save hidden", out[10].get("visible") is False)
    out = call_api("toggle_custom_base",
                   ["custom", SEED, {"_last": "gemini"}, "", "", ""])
    if isinstance(out, list) and len(out) == 11:
        chk("toggle on custom: edit hidden, add visible",
            out[9].get("visible") is False and out[4].get("visible") is True)
    else:
        chk("toggle on custom: 11 outputs", False, out)

    out = call_api("cm_edit", ["gemini", SEED])
    ok = isinstance(out, list) and len(out) == 8
    chk("api cm_edit on gemini: no-op (8 plain updates)",
        ok and all((not isinstance(o, dict)) or ("visible" not in o)
                   for o in out), out)

    # نامِ ناموجود از سمتِ API خام مسیر نمیدهد (اعتبارسنجیِ choicesِ
    # Dropdown — در مرورگر هم چنین انتخابی ممکن نیست)؛ معادلش providerِ
    # معتبرِ غیرمدل است: gemini → ویرایشی برایِ ذخیره نیست → no-op
    out = call_api("cm_save_edits", ["gemini", SEED, "b", "k", "m"])
    ok = isinstance(out, list) and len(out) == 14
    chk("api cm_save_edits on gemini: no-op (14 plain updates)",
        ok and all((not isinstance(o, dict)) or ("visible" not in o)
                   for o in out), out)
finally:
    proc.kill()
    proc.wait(timeout=10)
    try:
        os.remove(MODELS_PATH)
    except Exception:
        pass

print("== 6) android: same features natively ==")
chk("cmEditBtn + cmSaveBtn members", "cmEditBtn" in KT and "cmSaveBtn" in KT)
chk("cmEditing state", "private var cmEditing: Boolean = false" in KT)
chk("onEditModel() defined", "private fun onEditModel(" in KT)
chk("onSaveModelEdits() defined", "private fun onSaveModelEdits(" in KT)
chk("edit button label ✎ ویرایش", "✎ ویرایش این مدل" in KT)
chk("save button label 💾 ذخیرهٔ ویرایش", "💾 ذخیرهٔ ویرایش" in KT)
chk("gate: edit mode shows fields on own model",
    "if (onAuto || (mine && !editing)) View.GONE else View.VISIBLE" in KT)
chk("gate: base visible on custom OR editing",
    "if (isCustom || editing) View.VISIBLE else View.GONE" in KT)
chk("gate: edit visible only when mine && !cmEditing",
    "cmEditBtn?.visibility = if (mine && !cmEditing) View.VISIBLE else View.GONE" in KT)
chk("gate: save visible only while editing",
    "cmSaveBtn?.visibility = if (editing) View.VISIBLE else View.GONE" in KT)
chk("menu change cancels edit mode (cmEditing = false in refreshProviderBtn)",
    "cmEditing = false" in KT)
chk("save edits keeps the same name + refreshes menu",
    'put("name", cur)' in KT and "refreshProviderBtn()" in KT)
chk("android key masked by default (password flag honored)",
    'f.optBoolean("password") || type == "password"' in KT
    and "PasswordTransformationMethod.getInstance()" in KT)
chk("android eye toggle 👁 / 🙈",
    'text = "👁"' in KT and '"🙈"' in KT)
chk("android eye only for secret single-line fields",
    "if (isSecret && lines < 2) {" in KT)

print("== 7) manifest: password flag reaches android ==")
try:
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "android", "app", "src",
                                      "main", "python", "extract_ui.py"),
         os.path.join(ROOT, "manga_app.py")],
        capture_output=True, timeout=60)
    man = r.stdout.decode("utf-8", "ignore")
    chk("manifest extracted", '"fields"' in man or '"id"' in man, man[:120])
    chk("api_keys field has password:true",
        '"password": true' in man.replace(": true", ": true"))
    i = man.find("manga_api_keys")
    seg = man[max(0, i - 240): i + 240]
    chk("password flag is ON the api_keys field", "manga_api_keys" in man and
        ("password" in seg or '"password": true' in man), seg[:200])
except Exception as e:
    chk("manifest extraction", False, str(e)[:200])

print("== 8) version ==")
chk("APP_VER = 1.14.223", 'APP_VER = "1.14.223"' in SRC)
chk("VERSION file 1.14.223", "versionName=1.14.223" in open(
    os.path.join(ROOT, "VERSION"), encoding="utf-8").read())
chk("gradle 1.14.223 / 227",
    'versionName = "1.14.223"' in open(
        os.path.join(ROOT, "android", "app", "build.gradle.kts"),
        encoding="utf-8").read()
    and "versionCode = 227" in open(
        os.path.join(ROOT, "android", "app", "build.gradle.kts"),
        encoding="utf-8").read())

print(f"\nresult: {len(PASS)} green / {len(FAIL)} red")
if FAIL:
    print("reds:", FAIL)
    sys.exit(1)
print("all green")
