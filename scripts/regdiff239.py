# مقایسهٔ رگرسیونِ قدیم/جدید — تفاوتهای معنادار و توضیحشان
import json, sys

old = json.load(open(sys.argv[1]))
new = json.load(open(sys.argv[2]))

def key(r):
    return (tuple(r["r"]), r["k"], r["t"], r.get("e", False))

n_diff_files = 0
for f in sorted(old.keys()):
    o, n = old[f], new.get(f)
    if n is None:
        print(f"## {f}: فقط در قدیم!")
        continue
    if "error" in o or "error" in n:
        print(f"## {f}: ERROR old={o.get('error')} new={n.get('error')}")
        continue
    ro = [key(r) for r in o["regions"]]
    rn = [key(r) for r in n["regions"]]
    same = ro == rn
    if same:
        print(f"== {f}: یکسان (n={n['n']}, {o['t']}s→{n['t']}s)")
        continue
    n_diff_files += 1
    print(f"## {f}: تفاوت! old n={o['n']} new n={n['n']} ({o['t']}s→{n['t']}s)")
    so, sn = set(ro), set(rn)
    for r in sorted(so - sn, key=lambda x: x[0]):
        print(f"   - فقط قدیم: {r[0]} {r[1]} empty={r[3]} | {r[2][:70]!r}")
    for r in sorted(sn - so, key=lambda x: x[0]):
        print(f"   + فقط جدید: {r[0]} {r[1]} empty={r[3]} | {r[2][:70]!r}")
print(f"\nفایلهای متفاوت: {n_diff_files}")
