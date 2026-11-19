# -*- coding: utf-8 -*-
"""stylecheck.py - compare the register of generated poems with REAL poems of the same poet.
   python stylecheck.py --poet حافظ --form غزلیات  old.txt new.txt ...
   (txt files = output of 'poet.py gen' or poet3/poems.txt). Lower 'distance' = closer to the real poet."""
import sys, argparse, statistics
from pathlib import Path
import stylekit as sk

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+")
ap.add_argument("--poet", default="")
ap.add_argument("--form", default="غزلیات")
ap.add_argument("--data", default=str(Path(__file__).with_name("poet3") / "data"))
a = ap.parse_args()
here = Path(__file__).parent


def parse(path):
    poems, cur = [], []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("---"):
            if cur:
                poems.append(cur)
            cur = []
        elif " | " in line:
            p = [x.strip() for x in line.split(" | ")]
            if len(p) == 2 and p[0] and p[1]:
                cur.append((p[0], p[1]))
    if cur:
        poems.append(cur)
    return poems


base = sk.get_baseline(a.poet, a.form, a.data, here)
freq, N = sk.load_lex(a.data)
print(f"real baseline: {base['n']} poems of {a.poet or 'all poets'} / {a.form}\n")
cols = {}
for f in a.files:
    rows = [x for x in (sk.features(p, freq, N) for p in parse(f)) if x]
    cols[f] = rows
    print(f"{Path(f).name}: {len(rows)} poems")
print(f"\n{'feature':<12}{'real':>14}" + "".join(f"{Path(f).name[:14]:>16}" for f in a.files))
for k in sk.FEATS:
    line = f"{k:<12}{base['mean'][k]:>8.3f}±{base['std'][k]:.3f}"
    for f in a.files:
        v = [r[k] for r in cols[f]]
        line += f"{statistics.fmean(v):>16.3f}" if v else f"{'-':>16}"
    print(line)
print(f"\n{'distance':<12}{'(~0.8 = a real poem)':>14}")
for f in a.files:
    d = [sum(min(abs(z), 4.0) for z in sk.zscores(r, base).values()) / len(sk.FEATS) for r in cols[f]]
    print(f"  {Path(f).name:<30} mean {statistics.fmean(d):.2f}" if d else f"  {Path(f).name}: no poems parsed")
print("\nReading: for each feature the closer a column is to 'real', the more it looks like the real poet's register.\n"
      "'distance' is the average standardized gap over all features (lower = closer). It is a heuristic, not a quality score.")
