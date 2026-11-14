import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import sysinfo
m = sysinfo.CpuMeter(); time.sleep(0.3); sum(i * i for i in range(10 ** 6))
line = sysinfo.monitor_line(m, gpu=True)
assert line.startswith("[monitor] cpu=") and "ram=" in line, line
h = sysinfo.header_lines(sys.executable, False, ["python", "x.py"])
assert h[0].startswith("[bot] start") and "requested device: CPU" in h[1] and h[2] == "[bot] argv: python x.py"
assert any(l.startswith("[bot] GPU:") for l in h), h
h2 = sysinfo.header_lines(sys.executable, True, [])
if not sysinfo.nvidia_smi():
    assert any("WARNING: GPU requested" in l for l in h2), h2     # asked for GPU, none present -> says so
print("test_bot_sysinfo OK")
