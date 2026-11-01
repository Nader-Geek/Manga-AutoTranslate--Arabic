#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.159 — بازگشتِ fetch_paddle.py (الگویِ v1.14.106).

v1.14.158 ارجاعِ libs/PaddlePredictor.jar را به build.gradle.kts برگرداند
ولی خودِ فایلها نه در مخزن بودند نه fetch میشدند → Build اندروید رویِ CI
با «File/directory does not exist» فیل میشد. این اسکریپت jarِ API و
libpaddle_lite_jni.so (هر دو ABI) را از ریلیزِ رسمیِ Paddle-Lite v2.14-rc
(همان نسخهای که nbهایِ فقط-CPU با optِ همان ورژن ساخته شدند) دانلود و
سر جایشان میگذارد:
  android/app/libs/PaddlePredictor.jar
  android/app/src/main/jniLibs/arm64-v8a/libpaddle_lite_jni.so
  android/app/src/main/jniLibs/armeabi-v7a/libpaddle_lite_jni.so

اگر فایلها از قبل باشند (اندازه درست) رد میشود — idempotent.
"""
import os
import sys
import tarfile
import tempfile
import urllib.request

BASE = ("https://github.com/PaddlePaddle/Paddle-Lite/releases/"
        "download/v2.14-rc/")
PKG = {
    "arm64-v8a": "inference_lite_lib.android.armv8.clang.c++_static.with_extra.tar.gz",
    "armeabi-v7a": "inference_lite_lib.android.armv7.clang.c++_static.with_extra.tar.gz",
}
JAR_MIN = 5000          # jarِ واقعی ~9KB
SO_MIN = 1_000_000      # soهای واقعی ~3-5MB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
LIBS = os.path.join(APP, "libs")
JNI = os.path.join(APP, "src", "main", "jniLibs")
JAR = os.path.join(LIBS, "PaddlePredictor.jar")


def ok(path, min_size):
    return os.path.isfile(path) and os.path.getsize(path) >= min_size


def fetch(url, dest):
    print(f"[*] دانلود {os.path.basename(url)} ...")
    tmp = dest + ".part"
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, dest)


def extract_so(tgz, member_dir, dest):
    with tarfile.open(tgz, "r:gz") as tf:
        for m in tf.getmembers():
            if m.name.endswith("java/so/libpaddle_lite_jni.so"):
                m.name = os.path.basename(m.name)
                tf.extract(m, os.path.dirname(dest))
                src = os.path.join(os.path.dirname(dest), m.name)
                if os.path.abspath(src) != os.path.abspath(dest):
                    os.replace(src, dest)
                return True
    return False


def main():
    os.makedirs(LIBS, exist_ok=True)
    os.makedirs(JNI, exist_ok=True)

    if not ok(JAR, JAR_MIN):
        tgz = os.path.join(tempfile.gettempdir(), "plite_armv8.tgz")
        fetch(BASE + PKG["arm64-v8a"], tgz)
        # jar داخل java/jar/PaddlePredictor.jar است
        with tarfile.open(tgz, "r:gz") as tf:
            for m in tf.getmembers():
                if m.name.endswith("java/jar/PaddlePredictor.jar"):
                    m.name = os.path.basename(m.name)
                    tf.extract(m, LIBS)
                    break
        if not ok(JAR, JAR_MIN):
            print("[!] استخراج jar ناموفق", file=sys.stderr)
            return 1
    else:
        print("[+] jar از قبل هست")

    for abi, pkg in PKG.items():
        dest = os.path.join(JNI, abi, "libpaddle_lite_jni.so")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if ok(dest, SO_MIN):
            print(f"[+] {abi}: so از قبل هست")
            continue
        tgz = os.path.join(tempfile.gettempdir(),
                           f"plite_{abi}.tgz")
        fetch(BASE + pkg, tgz)
        if not extract_so(tgz, pkg, dest):
            print(f"[!] استخراج soِ {abi} ناموفق", file=sys.stderr)
            return 1
        print(f"[+] {abi}: libpaddle_lite_jni.so ذخیره شد "
              f"({os.path.getsize(dest)} B)")

    print("[✓] Paddle-Lite آماده است")
    return 0


if __name__ == "__main__":
    sys.exit(main())
