#!/usr/bin/env python3
"""Tap the app's run button (شروع ترجمه) via uiautomator.
Handles stale dumps, off-screen buttons (scrolls to them), diagnostics."""
import re
import subprocess
import sys
import time

RUN_TXT = "شروع ترجمه"


def sh(*a, timeout=60):
    return subprocess.run(list(a), capture_output=True, text=True,
                          errors="replace", timeout=timeout)


def screen_size():
    r = sh("adb", "shell", "wm", "size")
    m = re.search(r"(\d+)x(\d+)", r.stdout or "")
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 1920)


def dump():
    sh("adb", "shell", "rm", "-f", "/sdcard/ui.xml")
    for _ in range(4):
        r = sh("adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml")
        out = (r.stdout or "") + (r.stderr or "")
        if "dumped" in out or "hover" in out:
            c = sh("adb", "shell", "cat", "/sdcard/ui.xml")
            if "<node" in (c.stdout or ""):
                return c.stdout
        time.sleep(3)
    return ""


def nodes(xml):
    for nm in re.finditer(r"<node[^>]*>", xml):
        tag = nm.group(0)
        mtext = re.search(r'text="([^"]*)"', tag)
        mdesc = re.search(r'content-desc="([^"]*)"', tag)
        mb = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        txt = ((mtext.group(1) if mtext else "") + " " +
               (mdesc.group(1) if mdesc else "")).strip()
        if mb:
            yield txt, tuple(int(v) for v in mb.groups())


def find_run(xml):
    best = None
    for txt, b in nodes(xml):
        if RUN_TXT in txt and (b[2] - b[0]) > 40 and (b[3] - b[1]) > 20:
            best = b
            break
    return best


def swipe_up():
    w, h = screen_size()
    sh("adb", "shell", "input", "swipe", str(w // 2), str(int(h * 0.78)),
       str(w // 2), str(int(h * 0.30)), "400")


def diagnose(xml, tag):
    try:
        with open(f"/tmp/ui_{tag}.xml", "w", encoding="utf-8") as f:
            f.write(xml)
    except Exception:
        pass
    texts = [t for t, _ in nodes(xml) if t.strip()][:40]
    print(f"[diag:{tag}] {len(texts)} texts: " + " | ".join(
        t[:28] for t in texts[:18]))


def manga_log():
    try:
        r = sh("adb", "exec-out", "run-as", "com.amirwolf.mangatranslator",
               "cat", "files/manga.log", timeout=20)
        return r.stdout or ""
    except Exception:
        return ""


def main():
    w, h = screen_size()
    print(f"[tap-run] screen {w}x{h}")
    pre_end_count = manga_log().count("END — done=")

    def job_finished_fast():
        return manga_log().count("END — done=") > pre_end_count

    # walk from the top of the form downward
    for _ in range(3):
        sh("adb", "shell", "input", "swipe", str(w // 2), str(int(h * 0.3)),
           str(w // 2), str(int(h * 0.8)), "300")
        time.sleep(1)
    for attempt in range(25):
        xml = dump()
        if not xml:
            print(f"[tap-run] dump failed (attempt {attempt})")
            time.sleep(3)
            continue
        b = find_run(xml)
        if b:
            cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            if cy < h - 60 and cy > 60:
                sh("adb", "shell", "input", "tap", str(cx), str(cy))
                print(f"[tap-run] tapped {cx},{cy}")
                time.sleep(2.5)
                xml2 = dump()
                if any("لغو ترجمه" in t for t, _ in nodes(xml2)):
                    print("[tap-run] job started ✔")
                    return 0
                if job_finished_fast():
                    print("[tap-run] job ran and finished fast (cached) ✔")
                    return 0
                b2 = find_run(xml2)
                if b2:
                    sh("adb", "shell", "input", "tap",
                       str((b2[0] + b2[2]) // 2), str((b2[1] + b2[3]) // 2))
                    time.sleep(2.5)
                    xml3 = dump()
                    if any("لغو ترجمه" in t for t, _ in nodes(xml3)):
                        print("[tap-run] job started ✔ (retry)")
                        return 0
                    if job_finished_fast():
                        print("[tap-run] job ran and finished fast (cached) ✔ (retry)")
                        return 0
            else:
                # off-screen → scroll toward it
                swipe_up()
                time.sleep(1)
        else:
            diagnose(xml, f"miss_{attempt}")
            swipe_up()
            time.sleep(1)
    sh("adb", "shell", "screencap", "-p", "/sdcard/scr.png")
    sh("adb", "pull", "/sdcard/scr.png", "/tmp/scr_fail.png")
    r = sh("adb", "logcat", "-d", "-t", "400", "*:E")
    print("[tap-run] --- logcat E tail ---")
    print((r.stdout or "")[-1800:])
    print("[tap-run] شروع ترجمه button NOT found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
