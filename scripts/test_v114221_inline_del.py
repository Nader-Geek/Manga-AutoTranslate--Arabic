# -*- coding: utf-8 -*-
"""تستِ v1.14.221 — ✖ِ حذفِ چسبیده به خودِ منویِ انتخابِ AI (بدونِ لیستِ
چیپیِ پایین)، «auto» فقط با مدل، قفلِ فیلدها رویِ auto، و بازگشتِ
دراپ‌داونِ زبان (ocr_lang) که قانونِ CSSِ `.manga-hide-channel + *`
ناپدیدش کرده بود.
نکتهٔ API: gradio مقدارِ ورودیِ Dropdown را در choicesِ همان نشسته‌ست
اعتبارسنجی میکند — پس بوتِ اول با یک مدلِ از قبل رویِ دیسک انجام میشود
تا «auto» و نامِ مدلِ، مقدارهایِ مجاز باشند؛ بوتِ دومِ بدونِ مدل فقط
برایِ چکِ منویِ «gemini|custom» است."""
import json
import os
import shutil
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
    print(("  OK " if cond else "  XX ") + name + ((" — " + str(extra)[:140]) if extra and not cond else ""))


MODELS_PATH = os.path.join(ROOT, "workspace", "manga_models.json")
SEED = [{"name": "M1", "api_base": "https://m1.example/v1",
         "api_key": "k1", "model": "m-1"},
        {"name": "M2", "api_base": "https://m2.example/v1",
         "api_key": "k2", "model": "m-2"}]


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


def provider_choices_from_config(port):
    """منویِ provider را از /config میخواند (کامپوننتها با props)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/config",
                                    timeout=10) as r:
            cfgp = json.loads(r.read())
    except Exception:
        return None
    for c in cfgp.get("components", []):
        props = c.get("props") or {}
        if props.get("label") == "منوی انتخاب AI":
            ch = props.get("choices") or []
            return [x[-1] if isinstance(x, (list, tuple)) else str(x)
                    for x in ch]
    return None


shutil.os.makedirs(os.path.dirname(MODELS_PATH), exist_ok=True)
with open(MODELS_PATH, "w", encoding="utf-8") as f:
    json.dump(SEED, f, ensure_ascii=False)

print("== 1) boot (with seeded model M1) ==")
port = 7929
proc, page_raw = boot(port)
page = page_raw.decode("utf-8", "ignore")
chk("APP_VER = 1.14.221", "1.14.221" in page)

print("== 2) UI structure (rendered HTML) ==")
chk("del button component next to AI menu (manga_cm_del_btn)", "manga_cm_del_btn" in page)
chk("provider row wrapper (manga_provider_row)", "manga_provider_row" in page)
chk("old chips CSS/classes fully removed", ".cm-chips{" not in page and "cm-chip-n" not in page and "cm-x" not in page)
chk("old models list holder removed (manga_cm_list)", "manga_cm_list" not in page)
chk("LANGUAGE DROPDOWN BACK (manga_ocr_lang)", "manga_ocr_lang" in page)
chk("root-cause CSS rule removed (.manga-hide-channel + *)",
    ".manga-hide-channel + *" not in page)
chk("hide-channel base rule still present (channels stay hidden)",
    ".manga-hide-channel{display:none" in page)
chk("ocr lang choices rendered (multi)", "چندزبانه" in page)
chk("AI menu label present", "منوی انتخاب AI" in page)
chk("add-to-list button present", "افزودن به لیست مدل\u200cها" in page or "افزودن به لیست مدل‌ها" in page)
chk("backup accordion present", "بکاپ و بازیابی" in page)
chk("backup button present", "manga_backup_btn" in page)
chk("Import = UploadButton (manga_import_file)", "manga_import_file" in page)

print("== 3) config channels ==")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/config", timeout=10) as r:
        cfgp = json.loads(r.read())
    deps = json.dumps(cfgp.get("dependencies", []), ensure_ascii=False)
    chk("cm_add channel in config", "manga_cm_add_box" in deps)
    chk("restore channel in config", "manga_cm_restore" in deps)
    chk("OLD cm_del_box channel fully removed", "manga_cm_del_box" not in deps)
    chk("api_base field in config", "manga_api_base" in deps)
except Exception as e:
    chk("read config", False, e)

print("== 4) boot menu with models: auto present first ==")
ch = provider_choices_from_config(port)
chk("menu at boot (2 models): auto|gemini|M1|M2|custom",
    ch == ["auto", "gemini", "M1", "M2", "custom"], ch)


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


print("== 5) server model APIs ==")
try:
    out = call_api("cm_add", [json.dumps({"name": "تستC", "api_base": "https://x.example/v1",
                                          "api_key": "k12345678", "model": "m-9"},
                                         ensure_ascii=False), [], "gemini"])
    outs = json.dumps(out, ensure_ascii=False)
    chk("cm_add registered model + returned browser JSON", "تستC" in outs, outs[:220])
    prov_upd = out[2] if isinstance(out, list) and len(out) >= 4 else {}
    ch = [c[-1] if isinstance(c, (list, tuple)) else str(c)
          for c in (prov_upd.get("choices") or [])]
    chk("menu after add: auto|gemini|M1|M2|تستC|custom (auto first)",
        ch == ["auto", "gemini", "M1", "M2", "تستC", "custom"], ch)
    chk("del button update returned (dict with visible)",
        isinstance(out[3], dict) and "visible" in out[3], out[3])

    out = call_api("cm_del_sel", ["M1", []])
    outs = json.dumps(out, ensure_ascii=False)
    chk("cm_del_sel removed the SELECTED model (M1)",
        isinstance(out, list) and "M1" not in outs, outs[:220])
    prov_upd = out[2] if isinstance(out, list) and len(out) >= 3 else {}
    ch = [c[-1] if isinstance(c, (list, tuple)) else str(c)
          for c in (prov_upd.get("choices") or [])]
    # نکتهٔ API: هر فراخوانیِ بدونِ نشست، Stateِ تازهای با مقدارِ بوت
    # میگیرد — پس تستC (که با cm_add در نشستِ همان رویداد بود) اینجا نیست.
    chk("menu after delete (M1 gone): auto|gemini|M2|custom",
        ch == ["auto", "gemini", "M2", "custom"], ch)
    chk("del button hidden after menu fell back to auto",
        isinstance(out[3], dict) and out[3].get("visible") is False, out[3])

    out = call_api("cm_restore", [json.dumps([{"name": "R1", "api_base": "",
                                               "api_key": "", "model": ""}],
                                             ensure_ascii=False), [], "gemini"])
    prov_upd = out[2] if isinstance(out, list) and len(out) >= 3 else {}
    ch = [c[-1] if isinstance(c, (list, tuple)) else str(c)
          for c in (prov_upd.get("choices") or [])]
    chk("cm_restore merged browser model into menu",
        ch == ["auto", "gemini", "M1", "M2", "R1", "custom"], ch)

    try:
        call_api("cm_del_row", ["x", [], "auto"], timeout_req=10)
        chk("old cm_del_row api removed", False, "still callable")
    except Exception:
        chk("old cm_del_row api removed", True)
except Exception as e:
    chk("model APIs", False, str(e)[:220])

print("== 6) provider change gate (fields locked on auto) ==")
try:
    out = call_api("toggle_custom_base", ["auto", []])
    vis = [o.get("visible") if isinstance(o, dict) else None for o in out]
    chk("on auto: api_base hidden", vis[0] is False, vis)
    chk("on auto: api row hidden", vis[1] is False, vis)
    chk("on auto: add button hidden", vis[2] is False, vis)
    chk("on auto: hint hidden", vis[3] is False, vis)
    chk("on auto: del button hidden", vis[4] is False, vis)

    out = call_api("toggle_custom_base", ["custom", []])
    vis = [o.get("visible") if isinstance(o, dict) else None for o in out]
    chk("on custom: api_base visible", vis[0] is True, vis)
    chk("on custom: entry fields visible", vis[1] is True and vis[2] is True, vis)
    chk("on custom: del button hidden", vis[4] is False, vis)

    out = call_api("toggle_custom_base", ["M1", []])
    vis = [o.get("visible") if isinstance(o, dict) else None for o in out]
    chk("on user model: del button visible NEXT TO menu", vis[4] is True, vis)
    chk("on user model: api_base still hidden", vis[0] is False, vis)
    chk("on user model: entry fields visible", vis[1] is True, vis)

    out = call_api("toggle_custom_base", ["gemini", []])
    vis = [o.get("visible") if isinstance(o, dict) else None for o in out]
    chk("on gemini: entry fields visible, del hidden",
        vis[1] is True and vis[4] is False, vis)
except Exception as e:
    chk("provider gate", False, str(e)[:220])

proc.kill()
proc.wait(timeout=10)

print("== 7) boot WITHOUT models: no auto in menu ==")
try:
    os.remove(MODELS_PATH)
except Exception:
    pass
port2 = 7930
proc2, page2 = boot(port2)
ch = provider_choices_from_config(port2)
chk("menu without models: gemini|custom — auto ABSENT",
    ch == ["gemini", "custom"], ch)
chk("language dropdown present on clean boot too", "manga_ocr_lang" in page2.decode("utf-8", "ignore"))
proc2.kill()
proc2.wait(timeout=10)

print("== 8) python logic ==")
import importlib
ma = importlib.import_module("manga_app")
ch = ma._ai_choices([{"name": "مدلِ من"}])
chk("choices with model: auto|gemini|model|custom",
    ch == ["auto", "gemini", "مدلِ من", "custom"], ch)
ch0 = ma._ai_choices([])
chk("choices without model: gemini|custom (no auto)",
    ch0 == ["gemini", "custom"], ch0)
chk("_cm_names dedupes", ma._cm_names([{"name": "a"}, {"name": "a"}, {"name": ""}]) == ["a"])
r = ma.resolve_ai_named([{"name": "مدلِ من", "api_base": "https://b/v1",
                          "api_key": "k", "model": "m"}], "مدلِ من", "pk", "pm")
chk("resolve named model -> custom with own fields",
    r and r[0] == "custom" and r[1] == "https://b/v1" and r[2] == "k" and r[3] == "m", r)

print(f"\nresult: {len(PASS)} green / {len(FAIL)} red")
if FAIL:
    print("reds:", FAIL)
    sys.exit(1)
print("all green")
