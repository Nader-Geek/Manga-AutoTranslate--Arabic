# -*- coding: utf-8 -*-
"""Hardware facts for the job log: which device the work really runs on, plus live CPU/RAM/GPU.

No third-party dependency: /proc for CPU+RAM, `nvidia-smi` (when present) for the GPU.
Every function is best-effort and never raises.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

_PROBE = r"""
import json
out = {}
try:
    import onnxruntime as o; out["onnx"] = o.get_available_providers()
except Exception as e: out["onnx_err"] = str(e)[:80]
try:
    import torch; out["torch"] = torch.__version__; out["cuda"] = bool(torch.cuda.is_available())
    if out["cuda"]: out["cuda_name"] = torch.cuda.get_device_name(0)
except Exception as e: out["torch_err"] = str(e)[:80]
print(json.dumps(out))
"""


def _run(argv: List[str], timeout: float) -> str:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def nvidia_smi() -> Optional[Dict[str, Any]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    raw = _run([exe, "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"], 5)
    if not raw:
        return None
    try:
        name, util, used, total = [x.strip() for x in raw.splitlines()[0].split(",")]
        return {"name": name, "util": int(util), "mem_used": int(used), "mem_total": int(total)}
    except ValueError:
        return None


class CpuMeter:
    """CPU % since the previous call (from /proc/stat)."""

    def __init__(self) -> None:
        self._last = self._read()

    @staticmethod
    def _read() -> Optional[Tuple[int, int]]:
        try:
            with open("/proc/stat") as fh:
                p = [int(x) for x in fh.readline().split()[1:]]
            return sum(p), p[3] + (p[4] if len(p) > 4 else 0)   # total, idle+iowait
        except Exception:
            return None

    def percent(self) -> Optional[float]:
        cur, last = self._read(), self._last
        self._last = cur
        if not cur or not last or cur[0] == last[0]:
            return None
        return max(0.0, min(100.0, 100.0 * (1 - (cur[1] - last[1]) / (cur[0] - last[0]))))


def ram_gb() -> Optional[Tuple[float, float]]:
    try:
        m = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                k, v = line.split(":")
                m[k] = int(v.split()[0])
        total = m["MemTotal"] / 1024 ** 2
        return total - m["MemAvailable"] / 1024 ** 2, total
    except Exception:
        return None


def monitor_line(meter: CpuMeter, gpu: bool = True) -> str:
    """One log line: '[monitor] cpu=37% ram=2.1/7.7GB gpu=84% vram=3120/15360MB'."""
    parts = []
    c = meter.percent()
    parts.append(f"cpu={c:.0f}%" if c is not None else "cpu=?")
    r = ram_gb()
    if r:
        parts.append(f"ram={r[0]:.1f}/{r[1]:.1f}GB")
    n = os.cpu_count()
    if n:
        parts.append(f"cores={n}")
    if gpu:
        g = nvidia_smi()
        if g:
            parts.append(f"gpu={g['util']}% vram={g['mem_used']}/{g['mem_total']}MB")
    return "[monitor] " + " ".join(parts)


_probe_cache: Dict[str, Dict[str, Any]] = {}


def probe(python: str) -> Dict[str, Any]:
    """Which ONNX providers / torch+CUDA the engine's interpreter has (slow: imports torch; cached)."""
    if python not in _probe_cache:
        raw = _run([python, "-c", _PROBE], 60)
        try:
            import json
            _probe_cache[python] = json.loads(raw.splitlines()[-1])
        except Exception:
            _probe_cache[python] = {}
    return _probe_cache[python]


def header_lines(python: str, use_gpu: bool, argv: List[str], wait_probe: bool = True) -> List[str]:
    """Written at the top of run.log, before the engine starts."""
    out = [f"[bot] start {time.strftime('%Y-%m-%d %H:%M:%S')} | python {sys.version.split()[0]} "
           f"| cpus={os.cpu_count()}",
           f"[bot] requested device: {'GPU (USE_GPU=1)' if use_gpu else 'CPU (--cpu)'}",
           "[bot] argv: " + " ".join(argv)]
    d = probe(python) if (wait_probe or python in _probe_cache) else {}
    if not d:
        out.append("[bot] (python package probe not ready yet: onnxruntime/torch providers unknown)")
    if d.get("onnx"):
        gpu_ep = [p for p in d["onnx"] if p in ("CUDAExecutionProvider", "TensorrtExecutionProvider",
                                                 "DmlExecutionProvider", "ROCMExecutionProvider")]
        out.append(f"[bot] onnxruntime providers: {', '.join(d['onnx'])}"
                   + ("" if gpu_ep else "  (no GPU provider installed -> OCR/ONNX run on CPU)"))
    elif d.get("onnx_err"):
        out.append(f"[bot] onnxruntime: not importable ({d['onnx_err']})")
    if "torch" in d:
        out.append(f"[bot] torch {d['torch']} | cuda_available={d.get('cuda')}"
                   + (f" | {d.get('cuda_name')}" if d.get("cuda_name") else ""))
    g = nvidia_smi()
    out.append(f"[bot] GPU: {g['name']} ({g['mem_total']}MB)" if g else "[bot] GPU: none detected (nvidia-smi)")
    if use_gpu and not g:
        out.append("[bot] WARNING: GPU requested but no NVIDIA GPU was found — the engine will fall back to CPU")
    return out


async def aheader_lines(python: str, use_gpu: bool, argv: List[str]) -> List[str]:
    """Never blocks a job on the slow torch import: uses the cached probe when ready."""
    return await asyncio.to_thread(header_lines, python, use_gpu, argv, False)


def warm_probe(python: str) -> None:
    """Start the slow probe in the background (call once at startup)."""
    import threading
    threading.Thread(target=probe, args=(python,), daemon=True).start()
