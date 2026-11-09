#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dump_fingerprint.py — اثرانگشتِ کاملِ یک ماژولِ manga برایِ مقایسهٔ A/B.

هر نامِ عمومی ماژول + هر عضوِ کلاسِ MangaTranslator:
  • تابع/متد → hash بایت‌کد + co_names + co_consts (بازگشتی)
  • کلاس → اثرانگشتِ تک‌تکِ اعضای __dict__
  • چیزِ دیگر → sha256(repr)
خروجی: JSON رویِ stdout.
"""
import hashlib
import importlib.util
import json
import sys
import types


def _c(x):
    if isinstance(x, types.CodeType):
        return {"t": "code", "h": fp(x)}
    if isinstance(x, (set, frozenset)):
        return {"t": "set", "h": hashlib.sha256(
            "|".join(sorted(map(repr, x))).encode("utf-8", "surrogatepass")
        ).hexdigest()}
    tn = type(x).__name__
    if tn in ("lock", "_thread.lock", "_thread.RLock", "RLock"):
        return {"t": "lock", "h": "lock"}   # repr آدرسِ حافظه دارد
    try:
        r = repr(x)
    except Exception:
        r = "<repr-error:%s>" % tn
    if " at 0x" in r and tn not in ("str", "int", "float", "bool", "tuple",
                                    "list", "dict", "NoneType", "type"):
        return {"t": tn, "h": "addr-obj:" + tn}  # آبجکت با آدرس — فقط نوعش مقایسه شود
    return {"t": tn,
            "h": hashlib.sha256(r.encode("utf-8", "surrogatepass")).hexdigest()}


def fp(code):
    h = hashlib.sha256()
    h.update(code.co_code)
    h.update(b"\x00" + b"\x01".join(n.encode("utf-8", "surrogatepass")
                                    for n in code.co_names))
    h.update(b"\x00" + b"\x01".join(n.encode("utf-8", "surrogatepass")
                                    for n in code.co_varnames))
    for c in code.co_consts:
        v = json.dumps(_c(c), sort_keys=True)
        h.update(b"\x00" + v.encode("utf-8", "surrogatepass"))
    return h.hexdigest()


def val_fp(v):
    if isinstance(v, (types.FunctionType, types.BuiltinFunctionType)):
        if isinstance(v, types.FunctionType):
            return {"t": "func", "fp": fp(v.__code__)}
        return {"t": "builtin", "h": repr(v)}
    if isinstance(v, staticmethod):
        return {"t": "static", "fp": fp(v.__func__.__code__)}
    if isinstance(v, classmethod):
        return {"t": "classmethod", "fp": fp(v.__func__.__code__)}
    if isinstance(v, property):
        out = {"t": "property"}
        for k in ("fget", "fset", "fdel"):
            f = getattr(v, k)
            out[k] = fp(f.__code__) if f else None
        return out
    if isinstance(v, type):
        out = {"t": "class", "name": v.__name__, "members": {}}
        for k, mv in vars(v).items():
            if k.startswith("__") and k not in ("__doc__",):
                continue
            out["members"][k] = val_fp(mv)
        return out
    return _c(v)


def main(argv):
    path, out_path = argv[1], argv[2]
    spec = importlib.util.spec_from_file_location("manga", path)
    m = importlib.util.module_from_spec(spec)
    sys.modules["manga"] = m   # کدِ داخلِ manga خودش sys.modules را میخواند
    spec.loader.exec_module(m)
    out = {"__version__": getattr(m, "APP_VER", "?"), "names": {}}
    for k in sorted(vars(m)):
        if k.startswith("__"):
            continue
        try:
            out["names"][k] = val_fp(getattr(m, k))
        except Exception as e:
            out["names"][k] = {"t": "ERROR", "err": "%s: %s" % (type(e).__name__, e)}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
