# -*- coding: utf-8 -*-
"""stylekit.py - heuristic 'register' features of Persian poems + distance to the real poet. Pure python (no torch)."""
import json, math, random, re, hashlib, statistics
from pathlib import Path

NONLET = re.compile("[^\u0621-\u06CC\u200c ]")
# poetic / archaic function words and forms (heuristic list, not a linguistic authority)
ARCH = set("ز وز کز ور چو گر ار مر همی کنون ایدون بدین بدان زین زان اندر زهی هان الا ورنه کاندر کین کان آنک زانک همیدون اندرین اندران بدو بدوست زو ازو زی کی".split())
FEATS = ["archaic_fw", "rarity", "rare_share", "ttr", "hem_len", "rhyme_div"]


def toks(s):
    return [w.strip("\u200c") for w in NONLET.sub(" ", s).split() if w.strip("\u200c")]


def features(cps, freq, N):
    cps = [c for c in cps if len(c) == 2][:7]
    ws = [w for a, b in cps for w in toks(a) + toks(b)]
    if len(cps) < 3 or len(ws) < 12:
        return None
    sur = [-math.log((freq.get(w, 0) + 0.5) / N) for w in ws]
    ends = [toks(b)[-1] for a, b in cps if toks(b)]
    return {"archaic_fw": sum(w in ARCH for w in ws) / len(ws),
            "rarity": sum(sur) / len(sur),
            "rare_share": sum(freq.get(w, 0) <= 20 for w in ws) / len(ws),
            "ttr": len(set(ws)) / len(ws),
            "hem_len": len(ws) / (2 * len(cps)),
            "rhyme_div": len(set(ends)) / max(len(ends), 1)}


def load_lex(data_dir):
    freq = json.load(open(Path(data_dir) / "lexicon.json", encoding="utf-8"))
    return freq, max(sum(freq.values()), 1)


def find_parsed(data_dir, script_dir):
    for p in (Path(data_dir) / "parsed.jsonl", Path(script_dir) / "data" / "parsed.jsonl", Path("data/parsed.jsonl")):
        if p.is_file() and p.stat().st_size > 1e5:
            return p
    raise FileNotFoundError("parsed.jsonl not found (expected data/parsed.jsonl)")


def get_baseline(poet, form, data_dir, script_dir, nmax=600):
    data_dir = Path(data_dir)
    cache = data_dir / ("style_base_" + hashlib.md5(f"{poet}|{form}".encode()).hexdigest()[:10] + ".json")
    if cache.exists():
        return json.load(open(cache, encoding="utf-8"))
    freq, N = load_lex(data_dir)
    pool = []
    with open(find_parsed(data_dir, script_dir), encoding="utf-8") as f:
        for line in f:
            _, p, fm, cps = json.loads(line)
            if (not poet or p == poet) and (not form or form in fm):
                pool.append(cps)
    random.Random(1).shuffle(pool)
    rows = [x for x in (features(c, freq, N) for c in pool[:nmax * 2]) if x][:nmax]
    if len(rows) < 20:
        raise ValueError(f"only {len(rows)} real poems for poet={poet!r} form={form!r}")
    base = {"n": len(rows), "mean": {}, "std": {}}
    for k in FEATS:
        v = [r[k] for r in rows]
        base["mean"][k] = statistics.fmean(v)
        base["std"][k] = max(statistics.pstdev(v), 1e-6)
    json.dump(base, open(cache, "w", encoding="utf-8"))
    return base


def zscores(feat, base):
    return {k: (feat[k] - base["mean"][k]) / base["std"][k] for k in FEATS}


def distance(cps, base, data_dir=None, _cache={}):
    """mean |z| over features; lower = closer to the real poet's register (a random real poem scores ~0.8)."""
    key = str(data_dir)
    if key not in _cache:
        _cache[key] = load_lex(data_dir)
    freq, N = _cache[key]
    f = features(cps, freq, N)
    if f is None:
        return 4.0
    return sum(min(abs(z), 4.0) for z in zscores(f, base).values()) / len(FEATS)
