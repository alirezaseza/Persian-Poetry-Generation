# -*- coding: utf-8 -*-
"""poet.py v3 - Persian poet pipeline: prose pretraining -> Ganjoor finetuning -> verified generation (KV cache).
Needs poet_text.py next to it.
  python -u poet.py selftest                 (30 s check: model/KV-cache/text utils)
  python -u poet.py all --smoke              (short end-to-end test)
  python -u poet.py all --hours 16           (real run; resumable: run the same command again)
  python -u poet.py gen --poet حافظ --form غزلیات --qafiye ان --radif ما --n 3 --best-of 8
"""
import os, sys, re, json, math, time, gc, random, signal, hashlib, argparse, collections, tarfile, threading, queue, shutil, difflib, warnings, subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from poet_text import *          # text utils (torch-free, also imported by worker processes)

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

SCRIPT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("POET_DIR", str(SCRIPT / "poet3")))
DATA = ROOT / "data"
W_CAP = 2.0     # cap on the per-poet sampling weight (set per stage by --wcap)
WORKERS = max(1, min((os.cpu_count() or 4) - 1, 8))
TOP_POETS = {"حافظ": 6.0, "سعدی": 5.0, "صائب": 0.5, "بیدل دهلوی": 0.5, "مولوی": 3.0, "مولانا": 3.0, "خیام": 2.0, "نظامی": 2.0, "عطار": 2.0, "سنایی": 1.5,
             "جامی": 1.5, "فردوسی": 1.5, "باباطاهر": 1.5, "انوری": 1.2, "خاقانی": 1.2, "ناصرخسرو": 1.2, "عراقی": 1.5, "وحشی": 1.2}


def jdump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ============================================================================ prose download + cleaning (runs in poet_text.py as a
# separate light process: on Windows, worker processes re-import the main script, and importing torch 7 times is slow)
def build_prose(cap_chars):
    out_path = DATA / "prose.txt"
    if out_path.exists() and out_path.stat().st_size > 1e6:
        print(f"Prose already cleaned ({out_path.stat().st_size / 1e6:.0f} MB). Delete {out_path} to redo.")
        return out_path.stat().st_size
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    subprocess.run([sys.executable, "-u", str(SCRIPT / "poet_text.py"), "prose", str(DATA), str(int(cap_chars))], env=env)
    return out_path.stat().st_size if out_path.exists() else 0


# ============================================================================ Ganjoor poems
def extract_pairs(poem, obj):
    verses = poem.get("verses") or obj.get("verses")
    if isinstance(verses, list) and verses:
        rows = []
        for i, v in enumerate(verses):
            if not isinstance(v, dict):
                continue
            pos, order = v.get("versePosition", v.get("position")), v.get("vOrder", v.get("order", i))
            try:
                pos = int(pos)
            except (TypeError, ValueError):
                pos = None
            try:
                order = int(order)
            except (TypeError, ValueError):
                order = i
            rows.append((order, pos, v.get("text")))
        if rows and any(r[1] is not None for r in rows):
            rows.sort(key=lambda r: r[0])
            pairs, pend = [], None
            for _, pos, t in rows:
                if pos in (0, 2):
                    pend = t
                elif pos in (1, 3) and pend is not None:
                    pairs.append((pend, t))
                    pend = None
                else:
                    pend = None
            return pairs
    text = poem.get("plainText")
    if isinstance(text, str):
        lines = [l for l in text.replace("\r", "").split("\n") if l.strip()]
        if len(lines) >= 2 and len(lines) % 2 == 0:
            return [(lines[i], lines[i + 1]) for i in range(0, len(lines), 2)]
    return []


def process_poem(path, obj):
    if not isinstance(obj, dict):
        return None
    poem = obj.get("poem") if isinstance(obj.get("poem"), dict) else obj
    pairs = extract_pairs(poem, obj)
    kept = []
    for a, b in pairs:
        ca, cb = clean_hemistich(a), clean_hemistich(b)
        if ca is None or cb is None or ca == cb or not (0.4 <= len(ca) / len(cb) <= 2.5):
            continue
        kept.append((ca, cb))
    if len(kept) < 2 or len(kept) < 0.5 * len(pairs):
        return None
    ft = poem.get("fullTitle")
    parts = [p.strip() for p in ft.split("»") if p.strip()] if isinstance(ft, str) else []
    seg = path.split("/")
    poet = parts[0] if parts else (seg[1] if len(seg) > 1 else "")
    form = parts[-2] if len(parts) >= 3 else ""
    return [path, clean_text(poet) or "", clean_text(form) or "", kept]


def load_ganjoor():
    cache = DATA / "parsed.jsonl"
    for p in (cache, SCRIPT / "data" / "parsed.jsonl", Path("data/parsed.jsonl"), SCRIPT / "poet2" / "data" / "parsed.jsonl"):
        if p.is_file() and p.stat().st_size > 1e6:
            try:
                recs = []
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        path, poet, form, cps = json.loads(line)
                        recs.append((path, poet, form, [tuple(c) for c in cps]))
                print(f"Using cached Ganjoor parse: {p} ({len(recs):,} poems)")
                return recs
            except Exception as e:
                print(f"  [warn] cannot use {p}: {type(e).__name__}: {e}")
    cands = [Path(sys.argv[-1])] if sys.argv[-1].endswith(".zst") else []
    for d in (Path.cwd(), SCRIPT, Path.home() / "Downloads", Path.home() / "Desktop", Path.home(), SCRIPT.parent):
        cands.append(d / "ganjoor-data.tar.zst")
    arch = next((c for c in cands if c.is_file()), None)
    if arch is None:
        raise SystemExit("ganjoor-data.tar.zst not found. Put it next to poet.py (or in Downloads) or run: python poet.py data /path/ganjoor-data.tar.zst")
    import zstandard
    print(f"Parsing {arch} (single process, a few minutes)...")
    recs, n = [], 0
    with open(arch, "rb") as f, open(DATA / "parsed.jsonl", "w", encoding="utf-8") as out:
        with tarfile.open(fileobj=zstandard.ZstdDecompressor().stream_reader(f), mode="r|") as tar:
            for m in tar:
                if not m.isfile() or not m.name.endswith(".json"):
                    continue
                fo = tar.extractfile(m)
                if fo is None:
                    continue
                n += 1
                try:
                    r = process_poem(m.name, json.loads(fo.read()))
                except Exception:
                    r = None
                if r:
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
                    recs.append((r[0], r[1], r[2], [tuple(c) for c in r[3]]))
                if n % 5000 == 0:
                    sys.stdout.write(f"\r  files {n:,} | poems {len(recs):,}   ")
    print()
    return recs


def prepare_poems(tol_filter=3):
    """Ganjoor -> cleaned, deduplicated, rhyme- and rhythm-checked items (poet, form, qaf, rad, cps, weight)."""
    recs = load_ganjoor()
    recs.sort(key=lambda r: r[0])
    ck = lambda a, b: hashlib.blake2b((a + "|" + b).replace(" ", "").replace("\u200c", "").encode(), digest_size=8).digest()
    seen, kept = set(), []
    for path, poet, form, cps in recs:                       # 1) exact + near-duplicate poems
        keys = [ck(a, b) for a, b in cps]
        if sum(1 for k in keys if k in seen) / len(keys) >= 0.6:
            continue
        seen.update(keys)
        kept.append((poet, form, cps))
    wc = collections.Counter(w for _, _, cps in kept for a, b in cps for w in (a + " " + b).split())
    kept2, hap = [], 0
    for poet, form, cps in kept:                             # 2) couplets with one-off words (typos / junk) are dropped
        good = [c for c in cps if all(wc[w] >= 2 for w in (c[0] + " " + c[1]).split())]
        hap += len(cps) - len(good)
        if len(good) >= 2 and len(good) >= 0.6 * len(cps):
            kept2.append((poet, form, good))
    # 3) rhythm: hemistichs of one poem share one meter -> estimated syllable counts must stay close to the poem's median
    counts = [[(syl_count(a), syl_count(b)) for a, b in cps] for _, _, cps in kept2]
    meds = [sorted(x for pr in cs for x in pr)[len(cs)] for cs in counts]
    tot = sum(2 * len(cs) for cs in counts)
    near = sum(1 for cs, m in zip(counts, meds) for pr in cs for x in pr if abs(x - m) <= 2)
    frac = near / max(tot, 1)
    kept3, dropped_rhythm = [], 0
    if frac >= 0.75:
        for (poet, form, cps), cs, m in zip(kept2, counts, meds):
            good = [c for c, (x, y) in zip(cps, cs) if abs(x - m) <= tol_filter and abs(y - m) <= tol_filter]
            dropped_rhythm += len(cps) - len(good)
            if len(good) >= 2 and len(good) >= 0.6 * len(cps):
                kept3.append((poet, form, good))
    else:
        print(f"  [warn] syllable estimate is noisy on this data ({frac:.0%} within +-2) -> rhythm filter skipped")
        kept3 = kept2
    print(f"  rhythm check: {frac:.0%} of hemistichs within +-2 syllables of their poem's median; removed {dropped_rhythm:,} outlier couplets")
    poems, st = [], collections.Counter()
    for poet, form, cps in kept3:                            # 4) rhyme analysis, drop couplets that break the rhyme
        qaf, rad, cov = detect_rhyme(cps)
        if qaf or rad:
            if cov >= 0.75:
                good = [c for c in cps if rhyme_match(c[1], qaf, rad)]
                if len(good) < 2:
                    st["bad_rhyme"] += 1
                    continue
                cps = good
            else:
                qaf = rad = ""
        if not (qaf or rad) and any(k in form for k in RHYME_FORMS):
            st["no_rhyme"] += 1
            continue
        poems.append((poet, form, qaf, rad, cps))
    pc, fc = collections.Counter(p[0] for p in poems), collections.Counter(p[1] for p in poems)
    items = []
    for poet, form, qaf, rad, cps in poems:
        pt = poet if (poet and len(poet) <= 30 and pc[poet] >= 20) else UNKNOWN_POET
        ft = form if (form and len(form) <= 30 and fc[form] >= 30) else UNKNOWN_FORM
        items.append((pt, ft, qaf, rad, cps, TOP_POETS.get(pt, 1.0)))
    print(f"Ganjoor: {len(recs):,} poems -> {len(items):,} kept | dup-removed {len(recs) - len(kept):,} | "
          f"rare-word couplets dropped {hap:,} | broken-rhyme poems {st['bad_rhyme']:,} | no-rhyme ghazals {st['no_rhyme']:,}")
    return items, wc


def presplit(it, maxc=12):
    poet, form, qaf, rad, cps, w = it
    k = max(1, math.ceil(len(cps) / maxc))
    size = math.ceil(len(cps) / k)
    return [(poet, form, qaf, rad, cps[i:i + size], w) for i in range(0, len(cps), size)]


def encode_items(items, tok, label):
    import numpy as np
    out, todo, total = [], items, len(items)
    while todo:
        nxt = []
        for i in range(0, len(todo), 4000):
            part = todo[i:i + 4000]
            for it, e in zip(part, tok.encode_batch([build_text(*it[:5]) for it in part])):
                if len(e.ids) <= 500:
                    out.append((np.asarray(e.ids, dtype=np.uint16), it[5]))
                elif len(it[4]) >= 2:
                    h = len(it[4]) // 2
                    nxt.append(it[:4] + (it[4][:h], it[5]))
                    nxt.append(it[:4] + (it[4][h:], it[5]))
            sys.stdout.write(f"\r  encoding {label}: {len(out):,}/{total:,}+   ")
        todo = nxt
    print()
    return out


def write_bin(pairs, name):
    import numpy as np
    arrs = [a for a, _ in pairs]
    lens = np.fromiter((len(a) for a in arrs), dtype=np.int64, count=len(arrs))
    starts = np.concatenate([[0], np.cumsum(lens)[:-1]]).astype(np.int64)
    with open(DATA / f"{name}.bin", "wb") as f:
        for i in range(0, len(arrs), 20000):
            f.write(np.concatenate(arrs[i:i + 20000]).tobytes())
    np.save(DATA / f"{name}_starts.npy", starts)
    np.save(DATA / f"{name}_weights.npy", np.asarray([w for _, w in pairs], dtype=np.float64))
    return int(lens.sum())


def encode_prose(tok, vocab, classic_min):
    """prose.txt -> prose_train.bin / prose_val.bin. Paragraphs whose words are mostly unknown to the poems' vocabulary
    (modern technical text) are dropped, so pretraining leans towards language close to the poems."""
    import numpy as np
    src = DATA / "prose.txt"
    fr = []
    with open(src, encoding="utf-8") as f:
        for line in f:
            w = line.split()
            fr.append(sum(1 for x in w if x in vocab) / max(1, len(w)))
    fr = np.asarray(fr, dtype=np.float32)
    thr = min(classic_min, float(np.quantile(fr, 0.5)))        # never drop more than half
    print(f"  prose paragraphs: {len(fr):,} | closeness to poem vocabulary: median {np.median(fr):.2f} | keep >= {thr:.2f} "
          f"-> {(fr >= thr).mean():.0%} kept")
    r3, ptok, pvtok = random.Random(5), 0, 0
    with open(src, encoding="utf-8") as f, open(DATA / "prose_train.bin", "wb") as ft, open(DATA / "prose_val.bin", "wb") as fv:
        buf = []

        def flush():
            nonlocal ptok, pvtok
            for e in tok.encode_batch(["<|prose|>" + l + "<|end|>" for l in buf]):
                a = np.asarray(e.ids, dtype=np.uint16).tobytes()
                if r3.random() < 0.01:
                    fv.write(a)
                    pvtok += len(e.ids)
                else:
                    ft.write(a)
                    ptok += len(e.ids)
            buf.clear()
            sys.stdout.write(f"\r  prose tokens: {ptok / 1e6:,.1f}M   ")

        for i, line in enumerate(f):
            if fr[i] >= thr:
                buf.append(line.rstrip("\n"))
                if len(buf) >= 5000:
                    flush()
        if buf:
            flush()
    print()
    return ptok, pvtok


def prepare_data(args):
    import numpy as np
    from tokenizers import Tokenizer, models, trainers, pre_tokenizers
    DATA.mkdir(parents=True, exist_ok=True)
    need = ("meta.json", "tokenizer.json", "poems_train.bin", "poems_val.bin")
    if args.rebuild:
        for f in DATA.glob("*"):
            if f.name not in ("prose.txt", "parsed.jsonl"):
                f.unlink()
    if all((DATA / f).exists() for f in need):
        print("Data already prepared (use --rebuild to redo).")
        return
    if not args.smoke and not args.no_prose and not (DATA / "prose.txt").exists():     # reuse the cleaned prose of the old run
        old = SCRIPT / "poet2" / "data" / "prose.txt"
        if old.is_file() and old.stat().st_size > 1e6:
            print(f"Reusing cleaned prose from {old}")
            shutil.copyfile(old, DATA / "prose.txt")
    prose_size = 0 if args.no_prose else build_prose(int(args.prose_chars))
    if not args.no_prose and prose_size == 0:
        raise SystemExit("Persian text is missing or the download failed (network?). Run the SAME command again - finished downloads are cached. "
                         "To train on Ganjoor only, add --no-prose.")
    items, wc = prepare_poems()
    rnd = random.Random(0)
    tr, va = [], []
    for it in items:                                          # split by poem
        key = it[0] + "|" + it[4][0][0] + "|" + it[4][0][1]
        h = int.from_bytes(hashlib.blake2b(key.encode(), digest_size=4).digest(), "little")
        (va if h % 50 == 0 else tr).append(it)
    if not va:
        va.append(tr.pop())
    lex = collections.Counter(w for it in tr for a, b in it[4] for w in (a + " " + b).split())
    jdump({w: c for w, c in lex.items() if c >= 2}, DATA / "lexicon.json")
    pcnt, fcnt = collections.Counter(it[0] for it in tr), collections.Counter(it[1] for it in tr)
    (DATA / "poets.txt").write_text("\n".join(k for k, _ in pcnt.most_common() if k != UNKNOWN_POET), encoding="utf-8")
    (DATA / "forms.txt").write_text("\n".join(k for k, _ in fcnt.most_common() if k != UNKNOWN_FORM), encoding="utf-8")
    print("Top poets:", ", ".join(f"{k}:{v}" for k, v in pcnt.most_common(12)))
    with open(DATA / "clean_sample.txt", "w", encoding="utf-8") as f:
        for p, fo, q, r, cps, _ in rnd.sample(tr, min(30, len(tr))):
            f.write(f"## {p} | {fo} | {q or '-'} | {r or '-'} | syl {poem_syl(cps)}\n" + "\n".join(f"{a} | {b}" for a, b in cps[:8]) + "\n\n")
    tr = [((UNKNOWN_POET if rnd.random() < 0.15 else it[0]),) + it[1:] for it in tr]   # light poet masking

    print("Training BPE tokenizer (16k) on poems + prose sample...")
    p_keep = min(1.0, 80e6 / max(prose_size / 1.9, 1))

    def it_text():
        for poet, form, qaf, rad, cps, _ in tr:
            yield poet
            yield form
            if qaf:
                yield qaf
            if rad:
                yield rad
            for a, b in cps:
                yield a
                yield b
        if prose_size:
            r2 = random.Random(3)
            with open(DATA / "prose.txt", encoding="utf-8") as f:
                for line in f:
                    if r2.random() < p_keep:
                        yield line.rstrip("\n")

    tok = Tokenizer(models.BPE(unk_token="<|unk|>"))
    tok.pre_tokenizer = pre_tokenizers.Metaspace(replacement="▁", prepend_scheme="always")
    tok.train_from_iterator(it_text(), trainers.BpeTrainer(vocab_size=16000, min_frequency=2, special_tokens=SPECIALS,
                            initial_alphabet=sorted(set(LETTERS) | {"\u200c", "▁"}), show_progress=False))
    tok.save(str(DATA / "tokenizer.json"))
    sp = {n: tok.token_to_id(n) for n in SPECIALS}
    unk = sp["<|unk|>"]
    chunks_tr = [c for it in tr for c in presplit(it)]
    chunks_va = [c for it in va for c in presplit(it)]
    etr, eva = encode_items(chunks_tr, tok, "poems train"), encode_items(chunks_va, tok, "poems val")
    random.Random(1).shuffle(etr)
    random.Random(2).shuffle(eva)
    ntr, nva = write_bin(etr, "poems_train"), write_bin([(a, 1.0) for a, _ in eva], "poems_val")
    n_unk = sum(int((a == unk).sum()) for a, _ in etr)
    ptok = pvtok = 0
    if prose_size:
        print("Encoding prose...")
        vocab = {w for w, c in lex.items() if c >= 10}
        ptok, pvtok = encode_prose(tok, vocab, args.classic_min)
    jdump({"vocab_size": tok.get_vocab_size(), "specials": sp, "poem_train_tokens": ntr, "poem_val_tokens": nva,
           "prose_train_tokens": ptok, "prose_val_tokens": pvtok, "poems_train": len(tr), "poems_val": len(va)}, DATA / "meta.json")
    print(f"READY | poem tokens {ntr / 1e6:.1f}M (unk {n_unk}) | prose tokens {ptok / 1e6:.1f}M | vocab {tok.get_vocab_size()}")


# ============================================================================ model (Llama style: RMSNorm, RoPE, GQA, SwiGLU, QK-norm, tied embeddings)
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import ops
ops.STATE["triton"] = False   # switched on in train_stage after a self-test


@dataclass
class Config:
    vocab_size: int = 16000
    dim: int = 640
    n_layers: int = 12
    n_heads: int = 10
    n_kv_heads: int = 5
    hidden_dim: int = 1728
    max_seq_len: int = 512
    dropout: float = 0.0
    rope_theta: float = 10000.0
    n_id: int = 5
    rhyme_w: float = 1.0


SIZES = {"small": (512, 10, 8, 4, 1408), "base": (640, 12, 10, 5, 1728), "large": (768, 12, 12, 6, 2048),
         "xl": (896, 14, 14, 7, 2432), "xxl": (1024, 16, 16, 8, 2752)}  # dim, layers, heads, kv, hidden


class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        if ops.STATE["triton"] and x.is_cuda:
            od = ops.ACT["dtype"] if (x.dtype == torch.float32 and torch.is_autocast_enabled()) else x.dtype
            return ops.rms_norm(x, self.weight, self.eps, od)
        xf = x.float()
        return (xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + self.eps) * self.weight).to(x.dtype)


def rope_tables(T, hd, theta):
    ang = torch.outer(torch.arange(T).float(), 1.0 / (theta ** (torch.arange(0, hd, 2).float() / hd)))
    return torch.cos(ang), torch.sin(ang)


def apply_rope(x, cos, sin):  # x: (B, T, H, D); cos/sin already sliced to (T, D/2)
    d = x.size(-1) // 2
    xf = x.float()
    x1, x2 = xf[..., :d], xf[..., d:]
    c, s = cos[None, :, None, :], sin[None, :, None, :]
    return torch.cat((x1 * c - x2 * s, x2 * c + x1 * s), dim=-1).to(x.dtype)


class Attention(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.h, self.kv, self.hd = c.n_heads, c.n_kv_heads, c.dim // c.n_heads
        self.rep = self.h // self.kv
        self.pdrop = c.dropout
        self.wqkv = nn.Linear(c.dim, (self.h + 2 * self.kv) * self.hd, bias=False)
        self.wo = nn.Linear(self.h * self.hd, c.dim, bias=False)
        self.qn, self.kn = RMSNorm(self.hd), RMSNorm(self.hd)
        self.rdrop = nn.Dropout(c.dropout)

    def _qkv(self, x, cos, sin):
        B, T, _ = x.shape
        q, k, v = self.wqkv(x).split([self.h * self.hd, self.kv * self.hd, self.kv * self.hd], dim=-1)
        q = apply_rope(self.qn(q.reshape(B, T, self.h, self.hd)), cos, sin).transpose(1, 2)
        k = apply_rope(self.kn(k.reshape(B, T, self.kv, self.hd)), cos, sin).transpose(1, 2)
        return q, k, v.reshape(B, T, self.kv, self.hd).transpose(1, 2)

    def forward(self, x, cos, sin):
        B, T, _ = x.shape
        q, k, v = self._qkv(x, cos[:T], sin[:T])
        if self.rep > 1:
            k, v = k.repeat_interleave(self.rep, dim=1), v.repeat_interleave(self.rep, dim=1)
        o = F.scaled_dot_product_attention(q, k, v, is_causal=True, dropout_p=self.pdrop if self.training else 0.0)
        return self.rdrop(self.wo(o.transpose(1, 2).reshape(B, T, -1)))

    def step(self, x, cos, sin, past):
        """incremental attention with a KV cache; cos/sin are the tables of the NEW positions; the cache holds un-repeated k/v."""
        B, T, _ = x.shape
        q, k, v = self._qkv(x, cos, sin)
        if past is not None:
            k, v = torch.cat([past[0], k], 2), torch.cat([past[1], v], 2)
        new = (k, v)
        if self.rep > 1:
            k, v = k.repeat_interleave(self.rep, dim=1), v.repeat_interleave(self.rep, dim=1)
        S = k.size(2)
        if T == 1:
            o = F.scaled_dot_product_attention(q, k, v)
        elif S == T:
            o = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            mask = torch.ones(T, S, dtype=torch.bool, device=x.device).tril(diagonal=S - T)
            o = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        return self.wo(o.transpose(1, 2).reshape(B, T, -1)), new


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.n1, self.attn, self.n2 = RMSNorm(c.dim), Attention(c), RMSNorm(c.dim)
        self.gu = nn.Linear(c.dim, 2 * c.hidden_dim, bias=False)
        self.down = nn.Linear(c.hidden_dim, c.dim, bias=False)
        self.drop = nn.Dropout(c.dropout)

    def _mlp(self, x):
        return self.down(ops.swiglu(self.gu(self.n2(x))))

    def forward(self, x, cos, sin):
        x = x + self.attn(self.n1(x), cos, sin)
        return x + self.drop(self._mlp(x))

    def step(self, x, cos, sin, past):
        a, new = self.attn.step(self.n1(x), cos, sin, past)
        x = x + a
        return x + self._mlp(x), new


class PoetGPT(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.cfg = c
        self.emb = nn.Embedding(c.vocab_size, c.dim)  # tied with the output head
        self.drop = nn.Dropout(c.dropout)
        self.layers = nn.ModuleList([Block(c) for _ in range(c.n_layers)])
        self.norm = RMSNorm(c.dim)
        cos, sin = rope_tables(c.max_seq_len, c.dim // c.n_heads, c.rope_theta)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, 0.0, 0.02)
        for n, p in self.named_parameters():
            if n.endswith("wo.weight") or n.endswith("down.weight"):
                nn.init.normal_(p, 0.0, 0.02 / math.sqrt(2 * c.n_layers))

    def set_dropout(self, p):
        self.cfg.dropout = p
        for m in self.modules():
            if isinstance(m, nn.Dropout):
                m.p = p
            elif isinstance(m, Attention):
                m.pdrop = p

    def _weights(self, targets):  # extra weight on the last tokens of every couplet (qafiye + radif)
        isn = targets == self.cfg.n_id
        hit = isn.clone()
        for k in range(1, 6):
            hit[:, :-k] |= isn[:, k:]
        return (1.0 + self.cfg.rhyme_w * hit.float()).reshape(-1)

    def forward(self, idx, targets=None):
        x = self.drop(self.emb(idx))
        for b in self.layers:
            x = b(x, self.cos, self.sin)
        x = self.norm(x)
        if targets is None:
            return F.linear(x[:, -1], self.emb.weight).float()
        logits = F.linear(x, self.emb.weight).reshape(-1, self.cfg.vocab_size)
        if ops.STATE["triton"] and logits.is_cuda:
            row, nll = ops.fused_ce(logits, targets.reshape(-1), 0.0)
            return (row * self._weights(targets)).sum() / row.numel(), nll.mean().detach()
        nll = F.cross_entropy(logits.float(), targets.reshape(-1), reduction="none")
        return (nll * self._weights(targets)).sum() / nll.numel(), nll.mean().detach()

    def forward_cached(self, idx, cache, start):
        """idx: (B, t) NEW tokens at absolute positions start..start+t-1. Returns (logits of the last token, new cache)."""
        t = idx.size(1)
        x = self.emb(idx)
        cos, sin = self.cos[start:start + t], self.sin[start:start + t]
        new = []
        for i, b in enumerate(self.layers):
            x, kv = b.step(x, cos, sin, cache[i] if cache is not None else None)
            new.append(kv)
        return F.linear(self.norm(x)[:, -1], self.emb.weight).float(), new


# ============================================================================ data loading
class Loader:
    """Mixes prose windows (random offsets) and poem windows (start at a poem chunk, sampled by weight)."""
    def __init__(self, B, T, p_prose, seed, workers=2, depth=16):
        pf, qf = DATA / "prose_train.bin", DATA / "poems_train.bin"
        self.prose = np.memmap(pf, dtype=np.uint16, mode="r") if (pf.exists() and pf.stat().st_size > 1e6 and p_prose > 0) else None
        self.poem = np.memmap(qf, dtype=np.uint16, mode="r")
        st = np.load(DATA / "poems_train_starts.npy")
        w = np.minimum(np.load(DATA / "poems_train_weights.npy"), W_CAP)
        ok = st + T + 1 <= len(self.poem)
        self.starts, w = st[ok], w[ok]
        self.probs = w / w.sum()
        self.B, self.T = B, T
        self.p_prose = p_prose if self.prose is not None else 0.0
        self.offs = np.arange(T + 1)
        self.q = queue.Queue(maxsize=depth)
        self.stop = threading.Event()
        for i in range(workers):
            threading.Thread(target=self._run, args=(np.random.default_rng(seed * 7 + i),), daemon=True).start()

    def _run(self, rng):
        while not self.stop.is_set():
            isp = rng.random(self.B) < self.p_prose
            arr = np.empty((self.B, self.T + 1), dtype=np.int64)
            n = int(isp.sum())
            if n:
                o = rng.integers(0, len(self.prose) - self.T - 1, size=n)
                arr[isp] = self.prose[o[:, None] + self.offs]
            if n < self.B:
                s = self.starts[rng.choice(len(self.starts), size=self.B - n, p=self.probs)]
                arr[~isp] = self.poem[s[:, None] + self.offs]
            t = torch.from_numpy(arr).pin_memory()
            while not self.stop.is_set():
                try:
                    self.q.put(t, timeout=0.5)
                    break
                except queue.Full:
                    pass

    def get(self):
        return self.q.get()

    def close(self):
        self.stop.set()


def build_val(T, B=8):
    out = {}
    for name in ("poems", "prose"):
        f = DATA / f"{name}_val.bin"
        if not f.exists() or f.stat().st_size < 4 * (T + 2):
            continue
        d = np.fromfile(f, dtype=np.uint16)
        if name == "poems":
            st = np.load(DATA / "poems_val_starts.npy")
            st = st[st + T + 1 <= len(d)]
            if len(st) == 0:
                continue
            st = st[np.unique(np.linspace(0, len(st) - 1, num=min(192, len(st))).astype(np.int64))]
        else:
            st = np.linspace(0, len(d) - T - 1, num=96).astype(np.int64)
        arr = np.stack([d[s:s + T + 1] for s in st]).astype(np.int64)
        n = (len(arr) // B) * B
        if n:
            out[name] = list(torch.from_numpy(arr[:n]).view(n // B, B, T + 1))
    return out


@torch.no_grad()
def evaluate(model, batches, dev, amp):
    model.eval()
    tot = torch.zeros((), device=dev)
    for b in batches:
        b = b.to(dev)
        with torch.autocast("cuda", dtype=amp):
            _, ce = model(b[:, :-1].contiguous(), b[:, 1:].contiguous())
        tot += ce
    model.train()
    return (tot / len(batches)).item()


# ============================================================================ training
class EMA:
    def __init__(self, model, decay=0.999):
        self.decay = decay
        self.pdata = [p.data for p in model.parameters()]
        self.shadow = [p.data.clone() for p in model.parameters()]

    @torch.no_grad()
    def update(self, step):
        torch._foreach_lerp_(self.shadow, self.pdata, float(1.0 - min(self.decay, (1.0 + step) / (10.0 + step))))

    @torch.no_grad()
    def swap(self):
        for p, s in zip(self.pdata, self.shadow):
            t = p.clone()
            p.copy_(s)
            s.copy_(t)


def hms(s):
    s = max(0, int(s))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def atomic_save(obj, path):
    tmp = Path(str(path) + ".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def tune_micro_batch(model, cfg, dev, amp, n_params):
    """Biggest micro-batch that fits in the memory that is really free (Windows keeps ~0.4 GB of a 4 GB laptop GPU for the desktop)."""
    free0, _ = torch.cuda.mem_get_info()
    limit = torch.cuda.memory_allocated() + 0.85 * free0 - 3 * n_params * 4     # minus AdamW states + EMA that come later
    model.train()
    bs = 1
    for bs in (16, 12, 8, 6, 4, 3, 2, 1):
        ok = False
        try:
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            x = torch.randint(0, cfg.vocab_size, (bs, cfg.max_seq_len), device=dev)
            with torch.autocast("cuda", dtype=amp):
                loss, _ = model(x, x)
            loss.backward()
            torch.cuda.synchronize()
            ok = torch.cuda.max_memory_allocated() <= limit
        except torch.cuda.OutOfMemoryError:
            ok = False
        finally:
            model.zero_grad(set_to_none=True)
            x = loss = None
            gc.collect()
        if ok:
            break
    torch.cuda.empty_cache()
    return bs


def bench(model, cfg, bs, dev, amp):
    x = torch.randint(0, cfg.vocab_size, (bs, cfg.max_seq_len), device=dev)
    for i in range(6):
        if i == 2:
            torch.cuda.synchronize()
            t0 = time.perf_counter()
        with torch.autocast("cuda", dtype=amp):
            loss, _ = model(x, x)
        loss.backward()
    torch.cuda.synchronize()
    model.zero_grad(set_to_none=True)
    return 4 * bs * cfg.max_seq_len / (time.perf_counter() - t0)


def make_cfg(name, meta):
    dim, L, H, KV, HID = SIZES[name]
    return Config(vocab_size=((meta["vocab_size"] + 63) // 64) * 64, dim=dim, n_layers=L, n_heads=H, n_kv_heads=KV,
                  hidden_dim=HID, n_id=meta["specials"]["<|n|>"])


def choose_size(a, meta, dev, amp):
    """Pick the biggest model that still gets >= 12 training tokens per parameter in the time budget (compute-optimal is ~20;
    12 is the practical floor) and sees its prose at most ~6 times. Measured on THIS GPU, not guessed."""
    if a.size != "auto":
        return a.size
    f = ROOT / "size.txt"
    if f.exists():
        return f.read_text().strip()
    print("Choosing model size by measuring this GPU (1-2 minutes)...")
    uniq = meta["prose_train_tokens"] + meta["poem_train_tokens"]
    best = "small"
    for name in SIZES:
        torch.manual_seed(0)
        m = PoetGPT(make_cfg(name, meta)).to(dev)
        n = sum(p.numel() for p in m.parameters())
        free_now, _ = torch.cuda.mem_get_info()
        if n * 20 > 0.8 * free_now:                    # fp32 weights + grads + AdamW (2x) + EMA = ~20 bytes per parameter
            print(f"  {name:5s}: {n / 1e6:5.1f}M params | does not fit in {free_now / 1e9:.1f} GB free GPU memory -> skipped")
            del m
            gc.collect()
            torch.cuda.empty_cache()
            continue
        try:
            mbs = tune_micro_batch(m, m.cfg, dev, amp, n)
            tps = bench(m, m.cfg, mbs, dev, amp)
        except Exception as e:
            print(f"  {name}: failed ({type(e).__name__})")
            del m
            gc.collect()
            torch.cuda.empty_cache()
            continue
        budget = tps * 0.85 * a.hours * 3600
        ratio, epochs = budget / n, budget / max(uniq, 1)
        print(f"  {name:5s}: {n / 1e6:5.1f}M params | micro-batch {mbs} | {tps / 1000:.1f}k tok/s | {budget / 1e6:,.0f}M tokens in budget | "
              f"{ratio:.1f} tok/param | {epochs:.1f} epochs over the data")
        if ratio >= a.min_ratio and epochs <= 6 + 0.5 * (name == "small"):
            best = name
        del m
        gc.collect()
        torch.cuda.empty_cache()
    f.write_text(best)
    print(f"  -> using '{best}'")
    return best


def log_row(stage, kind, row):
    try:
        d = ROOT / "logs"
        d.mkdir(exist_ok=True)
        f = d / f"{stage}_{kind}.csv"
        hdr = "step,elapsed,loss,lr,tok_s,gnorm" if kind == "train" else "step,elapsed,poems_raw,poems_ema,prose_raw,prose_ema,best"
        new = not f.exists()
        with open(f, "a", encoding="utf-8") as fh:
            if new:
                fh.write(hdr + "\n")
            fh.write(",".join(str(x) for x in row) + "\n")
    except Exception:
        pass


def make_chart():
    import csv
    import math
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def rd(name):
        f = ROOT / "logs" / name
        rows = {}
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    try:
                        rows[int(r["step"])] = {k: (float(v) if v not in ("", None) else None) for k, v in r.items()}
                    except Exception:
                        pass
        return [rows[k] for k in sorted(rows)]

    def smooth(v, w=25):
        return [sum(v[max(0, i - w + 1):i + 1]) / len(v[max(0, i - w + 1):i + 1]) for i in range(len(v))]

    parts, off = [], 0.0
    for stage in ("pretrain", "finetune", "style"):
        tr, ev = rd(f"{stage}_train.csv"), rd(f"{stage}_eval.csv")
        if not tr and not ev:
            continue
        parts.append((stage, off, tr, ev))
        off += max(r["elapsed"] for r in tr + ev) / 3600.0
    if not parts:
        return
    fig, ax = plt.subplots(2, 3, figsize=(18, 9))
    ax = ax.ravel()
    for stage, o, tr, ev in parts:
        hx = lambda rows: [o + r["elapsed"] / 3600.0 for r in rows]
        if tr:
            x = hx(tr)
            ax[0].plot(x, smooth([r["loss"] for r in tr]), color="#1f77b4", lw=1.4, label="train loss")
            ax[3].plot(x, [r["lr"] for r in tr], color="#2ca02c", lw=1.2)
            ax[4].plot(x, smooth([r["tok_s"] for r in tr], 10), color="#9467bd", lw=1.2)
            ax[5].plot(x, smooth([r["gnorm"] for r in tr], 10), color="#d62728", lw=1.0)
        for key, col, lab in (("poems_ema", "#ff7f0e", "val poems (EMA)"), ("prose_ema", "#17becf", "val prose (EMA)")):
            pts = [(o + r["elapsed"] / 3600.0, r[key]) for r in ev if r.get(key) is not None]
            if pts:
                ax[0].plot(*zip(*pts), marker="o", ms=3, color=col, lw=1.2, label=lab)
        for key, col, lab in (("poems_raw", "#999999", "raw"), ("poems_ema", "#ff7f0e", "EMA")):
            pts = [(o + r["elapsed"] / 3600.0, r[key]) for r in ev if r.get(key) is not None]
            if pts:
                ax[2].plot(*zip(*pts), marker="o", ms=3, color=col, lw=1.2, label="poems " + lab)
                if key == "poems_ema":
                    ax[1].plot([p[0] for p in pts], [math.exp(min(p[1], 12)) for p in pts], marker="o", ms=3, color="#ff7f0e", lw=1.2)
        if stage != "pretrain" and o > 0:
            for a in ax:
                a.axvline(o, color="#888888", ls="--", lw=0.8)
    titles = ["Loss (train + validation)", "Validation perplexity (poems, EMA)", "Validation loss on poems",
              "Learning rate", "Speed (k tokens/s)", "Gradient norm"]
    for a, ti in zip(ax, titles):
        a.set_title(ti)
        a.set_xlabel("training hours (dashed line = start of finetune)")
        a.grid(alpha=0.3)
    for i in (0, 2):
        h, l = ax[i].get_legend_handles_labels()
        if h:
            ax[i].legend(dict(zip(l, h)).values(), dict(zip(l, h)).keys())
    fig.tight_layout()
    fig.savefig(SCRIPT / "training_curves.png", dpi=110)
    plt.close(fig)


def train_stage(stage, hours, a):
    from tokenizers import Tokenizer
    if not torch.cuda.is_available():
        raise SystemExit("CUDA not available - install the CUDA build of PyTorch.")
    meta = jload(DATA / "meta.json")
    tok = Tokenizer.from_file(str(DATA / "tokenizer.json"))
    lex = {w for w, c in jload(DATA / "lexicon.json").items() if c >= a.min_word_count}
    sdir = ROOT / stage
    sdir.mkdir(parents=True, exist_ok=True)
    if (sdir / "DONE").exists():
        print(f"[{stage}] already finished (delete {sdir}/DONE to continue it).")
        return
    has_prose = meta["prose_train_tokens"] > 1e6
    globals()["W_CAP"] = getattr(a, "wcap", 2.0)
    if stage == "pretrain" and not has_prose:
        print("[pretrain] no prose data -> skipped.")
        return
    dev = torch.device("cuda")
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.set_float32_matmul_precision("high")
    amp = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    scaler = torch.amp.GradScaler("cuda", enabled=(amp == torch.float16))
    ops.ACT["dtype"] = amp
    _ok, _msg = ops.selftest()
    ops.STATE["triton"] = _ok
    print(f"  triton kernels: {'ON (' + _msg + ')' if _ok else 'OFF -> plain PyTorch (' + _msg + ')'}")
    p_prose = 0.85 if stage == "pretrain" else (0.15 if has_prose else 0.0)     # finetune keeps 15% prose as a regulariser
    if getattr(a, "prose_mix", -1.0) >= 0 and stage != "pretrain":
        p_prose = a.prose_mix if has_prose else 0.0
    lr_max = a.lr or (6e-4 if stage == "pretrain" else 1.5e-4)
    warm = 300 if stage == "pretrain" else 100
    eval_every = a.eval_every or (500 if stage == "pretrain" else 250)
    patience = 0 if stage == "pretrain" else a.patience
    drop = 0.05 if stage == "pretrain" else 0.15

    cks = sorted(sdir.glob("ck_*.pt"), key=lambda p: int(p.stem[3:]), reverse=True)
    ck = None
    for f in cks:
        try:
            ck = torch.load(f, map_location="cpu", weights_only=False)
            break
        except Exception as e:
            print(f"  [warn] cannot read {f.name}: {e}")
    init_w = None
    if ck is not None:
        cfg = Config(**ck["config"])
    elif stage == "style" and (ROOT / "finetune" / "best.pt").exists():
        b = torch.load(ROOT / "finetune" / "best.pt", map_location="cpu", weights_only=False)
        cfg, init_w = Config(**b["config"]), b["model"]
    elif stage == "finetune" and (ROOT / "pretrain" / "best.pt").exists():
        b = torch.load(ROOT / "pretrain" / "best.pt", map_location="cpu", weights_only=False)
        cfg, init_w = Config(**b["config"]), b["model"]
    else:
        cfg = make_cfg(choose_size(a, meta, dev, amp), meta)
    torch.manual_seed(1337)
    model = PoetGPT(cfg).to(dev)
    if init_w is not None:
        model.load_state_dict(init_w)
    model.set_dropout(drop)
    n_params = sum(p.numel() for p in model.parameters())
    mbs = tune_micro_batch(model, cfg, dev, amp, n_params)
    accum = max(1, round(a.batch_tokens / (mbs * cfg.max_seq_len)))
    tok_step = mbs * accum * cfg.max_seq_len
    tps = bench(model, cfg, mbs, dev, amp)
    dec = [p for p in model.parameters() if p.dim() >= 2]
    nodec = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": dec, "weight_decay": 0.1}, {"params": nodec, "weight_decay": 0.0}], lr=lr_max,
                            betas=(0.9, 0.95), eps=1e-8, fused=True)
    ema = EMA(model)
    step, elapsed, best, bad = 0, 0.0, float("inf"), 0
    how = "fresh"
    if ck is not None:
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["optimizer"])
        for s, c in zip(ema.shadow, ck["ema"]):
            s.copy_(c.to(dev))
        step, elapsed, best, bad = ck["step"], ck["elapsed"], ck["best"], ck["bad"]
        how = f"RESUMED step {step:,} elapsed {hms(elapsed)}"
    del ck
    gc.collect()
    loader = Loader(mbs, cfg.max_seq_len, p_prose, seed=1000 + step)
    val = build_val(cfg.max_seq_len)
    total = hours * 3600.0
    print(f"\n=== {stage.upper()} | {n_params / 1e6:.1f}M params dim {cfg.dim} x {cfg.n_layers}L | batch {mbs}x{accum} = {tok_step:,} tok | "
          f"~{tps / 1000:.1f}k tok/s | budget {hours:.2f}h ~ {tps * 0.9 * total / 1e9:.2f}B tokens | prose mix {p_prose:.0%} | {how}")
    print("    Stop: Ctrl+C once (saves) or create a file named STOP. Run the same command again to resume.")
    stopflag = {"v": False}
    signal.signal(signal.SIGINT, lambda *_: (stopflag.__setitem__("v", True), print("\n[stop requested] saving...")))
    stopfile = Path("STOP")
    stopfile.unlink(missing_ok=True)

    def save_best(src):
        atomic_save({"model": model.state_dict(), "config": asdict(model.cfg), "step": step, "val": best, "src": src}, sdir / "best.pt")

    def do_eval():
        nonlocal best, bad
        res_raw = {k: evaluate(model, v, dev, amp) for k, v in val.items()}
        ema.swap()                                   # model now holds EMA weights
        res_ema = {k: evaluate(model, v, dev, amp) for k, v in val.items()}
        if stage in ("finetune", "style") and "poems" in val:
            key = lambda r: r["poems"]
        elif stage == "pretrain" and "prose" in val:
            key = lambda r: r["prose"]               # poems are only a small part of the pretrain mix
        else:
            key = lambda r: sum(r.values()) / max(len(r), 1)
        vr, ve = key(res_raw), key(res_ema)
        use_ema = ve < vr
        if not use_ema:
            ema.swap()                               # model back to raw weights (the better ones)
        cand = min(vr, ve)
        improved = cand < best - 1e-4
        if improved:
            best = cand
            save_best("ema" if use_ema else "raw")
        bad = 0 if improved else bad + 1
        sample = ""
        if stage in ("finetune", "style"):
            try:
                sample = sample_demo(model, tok, dev, amp, lex)
            except Exception as e:
                sample = f"(sample failed: {e})"
        if use_ema:
            ema.swap()                               # restore raw weights for training
        print(f"\n  EVAL step {step:,} | {hms(elapsed)} | " + " ".join(f"{k}: raw {res_raw[k]:.3f} ema {res_ema[k]:.3f}" for k in val) +
              f" | best {best:.4f}{' *NEW BEST*' if improved else ''} | no-improve {bad}/{patience or '-'}")
        log_row(stage, "eval", [step, f"{elapsed:.0f}", res_raw.get("poems", ""), res_ema.get("poems", ""),
                                 res_raw.get("prose", ""), res_ema.get("prose", ""), f"{best:.5f}"])
        try:
            make_chart()
        except Exception as e:
            print(f"  (chart failed: {e})")
        if sample:
            print(sample)
            with open(ROOT / "samples.txt", "a", encoding="utf-8") as f:
                f.write(f"=== {stage} step {step} | {hms(elapsed)} | val {best:.4f}\n{sample}\n\n")

    def save_ck():
        atomic_save({"step": step, "elapsed": elapsed, "best": best, "bad": bad, "config": asdict(model.cfg), "model": model.state_dict(),
                     "optimizer": opt.state_dict(), "ema": [s.detach().cpu() for s in ema.shadow]}, sdir / f"ck_{step:07d}.pt")
        for old in sorted(sdir.glob("ck_*.pt"), key=lambda p: int(p.stem[3:]), reverse=True)[2:]:
            old.unlink(missing_ok=True)

    lsum = torch.zeros((), device=dev)
    gsum = torch.zeros((), device=dev)
    nlog, oom, reason = 0, 0, None
    nan_run = 0
    t_log, last = time.perf_counter(), time.perf_counter()
    model.train()
    while True:
        if stopflag["v"] or stopfile.exists():
            reason = "stop"
            break
        now = time.perf_counter()
        elapsed += min(now - last, 120.0)
        last = now
        if elapsed >= total:
            reason = "done"
            break
        prog = elapsed / total
        lr = lr_max * (step + 1) / warm if step < warm else 0.1 * lr_max + 0.5 * 0.9 * lr_max * (1 + math.cos(math.pi * min(1.0, prog)))
        for g in opt.param_groups:
            g["lr"] = lr
        try:
            ce_acc = torch.zeros((), device=dev)
            for _ in range(accum):
                b = loader.get().to(dev, non_blocking=True)
                with torch.autocast("cuda", dtype=amp):
                    loss, ce = model(b[:, :-1].contiguous(), b[:, 1:].contiguous())
                ce_acc += ce
                scaler.scale(loss / accum).backward()
            scaler.unscale_(opt)
            gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            if amp == torch.bfloat16 and not torch.isfinite(gn):
                opt.zero_grad(set_to_none=True)
                nan_run += 1
                if nan_run >= 50:
                    raise SystemExit('Gradient was NaN/Inf 50 steps in a row: weights are probably corrupted. '
                                     'Delete the newest ck_*.pt file and run the same command again.')
                continue
            nan_run = 0
            scaler.step(opt)
            scaler.update()
            opt.zero_grad(set_to_none=True)
        except torch.cuda.OutOfMemoryError:
            opt.zero_grad(set_to_none=True)
            gc.collect()
            torch.cuda.empty_cache()
            oom += 1
            if oom >= 5:
                raise SystemExit("Repeated out-of-memory: close other GPU programs (browser/games) or use --batch-tokens 24576")
            continue
        oom = 0
        step += 1
        ema.update(step)
        lsum += ce_acc / accum
        gsum += gn.detach().float()
        nlog += 1
        if step % 20 == 0:
            dt = time.perf_counter() - t_log
            l_avg, g_avg, spd = (lsum / nlog).item(), (gsum / nlog).item(), tok_step * nlog / dt / 1000
            print(f"\r  step {step:,} | loss {l_avg:.3f} | lr {lr:.2e} | {spd:.1f}k tok/s | "
                  f"{prog * 100:.1f}% | left {hms(total - elapsed)}   ", end="")
            log_row(stage, "train", [step, f"{elapsed:.0f}", f"{l_avg:.5f}", f"{lr:.3e}", f"{spd:.2f}", f"{g_avg:.4f}"])
            lsum.zero_()
            gsum.zero_()
            nlog, t_log = 0, time.perf_counter()
        if step % eval_every == 0:
            do_eval()
            save_ck()
            t_log = time.perf_counter()
            if patience and bad >= patience:
                reason = "early"
                break
    if reason in ("done", "early"):
        print(f"\n[{stage}] finished ({reason}): best val {best:.4f} | steps {step:,}")
        do_eval()
        save_ck()
        (sdir / "DONE").write_text(reason)
    else:
        save_ck()
        print(f"\n[{stage}] stopped at step {step:,}. Run the same command to resume.")
    loader.close()
    del model, opt, ema
    gc.collect()
    torch.cuda.empty_cache()
    return reason


# ============================================================================ generation (KV cache + couplet-level sample / verify / rerank)
STOP_WORDS = frozenset(["این", "آن", "که", "را", "از", "به", "با", "تا", "بر", "چون", "همه", "هر", "بود", "است", "هست", "نیز", "اندر",
                        "باشد", "شود", "شد", "کنم", "کند", "من", "تو", "او", "ما", "هم", "وی", "نیست", "نه", "زین", "زان", "چو"])


def join_ids(tok, ids):
    return " ".join("".join(tok.id_to_token(i) or "" for i in ids).replace("▁", " ").split())


def qaf_word(b, rad):
    w = b.split(" ")
    if rad:
        r = rad.split(" ")
        if len(w) > len(r) and w[-len(r):] == r:
            w = w[:-len(r)]
    return w[-1] if w else ""


def _zw(s):
    return s.replace("\u200c", "")


def _strip_rad(h, rad):
    w, r = h.split(), (rad.split() if rad else [])
    return " ".join(w[:-len(r)]) if r and len(w) > len(r) and w[-len(r):] == r else h


def has_repeat(h):
    ws = [w for w in h.split() if len(_zw(w)) >= 3 and w not in STOP_WORDS]
    return len(ws) != len(set(ws))


def repeat_bad(A, B, hist, rad):
    ha, hb = _strip_rad(A, rad), _strip_rad(B, rad)
    wa, wb = ha.split(), hb.split()
    if not wa or not wb or has_repeat(ha) or has_repeat(hb):
        return True
    sa, sb = set(map(_zw, wa)), set(map(_zw, wb))
    if len(sa & sb) / max(1, min(len(sa), len(sb))) > 0.8:
        return True
    for h in (wa, wb):
        g1 = {tuple(h[i:i + 3]) for i in range(len(h) - 2)}
        s1 = {_zw(w) for w in h if len(_zw(w)) >= 2}
        for old in hist:
            wo = _strip_rad(old, rad).split()
            if len(h) >= 3 and len(wo) >= 3 and h[:3] == wo[:3]:
                return True
            if g1 & {tuple(wo[i:i + 3]) for i in range(len(wo) - 2)}:
                return True
            s2 = {_zw(w) for w in wo if len(_zw(w)) >= 2}
            if s1 and s2 and len(s1 & s2) / min(len(s1), len(s2)) >= 0.75:
                return True
    return False


def pair_rhyme_ok(a, b, k=2):
    wa, wb = _zw(a.split()[-1]), _zw(b.split()[-1])
    n = min(k, len(wa), len(wb))
    return wa != wb and n > 0 and wa[-n:] == wb[-n:]


def nucleus(lg, temp, top_p):
    p = torch.softmax(lg / temp, -1)
    sp_, si = p.sort(-1, descending=True)
    sp_[(sp_.cumsum(-1) - sp_) > top_p] = 0.0
    sp_ = sp_ / sp_.sum(-1, keepdim=True)
    return si.gather(1, torch.multinomial(sp_, 1))


class Gen:
    def __init__(self, model, tok, dev, amp, lex=None):
        self.m, self.tok, self.dev, self.amp, self.lex = model, tok, dev, amp, lex
        self.sp = {n: tok.token_to_id(n) for n in SPECIALS}
        self.V = tok.get_vocab_size()
        self.syl_ids = {self.sp[t]: i for t, i in zip(SYL_TOKENS, range(SYL_MIN, SYL_MAX + 1)) if self.sp[t] is not None}
        self.ban = [self.sp[n] for n in ("<|pad|>", "<|unk|>", "<|poem|>", "<|sep|>", "<|rhy|>", "<|rad|>", "<|end|>", "<|prose|>")] + list(self.syl_ids)

    def enc(self, s):
        return self.tok.encode(s).ids if s else []

    def _ctx(self):
        if self.dev.type == "cuda":
            return torch.autocast("cuda", dtype=self.amp)
        return torch.autocast("cpu", enabled=False)

    def _logits(self, x):                      # slow path (no cache): full forward over the last max_seq_len tokens
        with self._ctx():
            return self.m(x[:, -self.m.cfg.max_seq_len:])

    def _prefill(self, prefix):
        with self._ctx():
            return self.m.forward_cached(torch.tensor([prefix], device=self.dev), None, 0)

    def _step(self, tokens, cache, pos):
        with self._ctx():
            return self.m.forward_cached(tokens, cache, pos)

    @torch.no_grad()
    def sample_header(self, poet, form, temp=0.9, top_p=0.95):
        """-> (qafiye, radif, syllable estimate)"""
        sp = self.sp
        ids = [sp["<|poem|>"]] + self.enc(poet or UNKNOWN_POET) + [sp["<|sep|>"]] + self.enc(form or UNKNOWN_FORM) + [sp["<|rhy|>"]]
        gen = []
        no = [sp[n] for n in ("<|pad|>", "<|unk|>", "<|poem|>", "<|sep|>", "<|rhy|>", "<|end|>", "<|prose|>", "<|m|>")]
        for _ in range(16):
            lg = self._logits(torch.tensor([ids + gen], device=self.dev))
            lg[:, self.V:] = float("-inf")
            lg[:, no] = float("-inf")
            has_syl = any(t in self.syl_ids for t in gen)
            if has_syl:
                keep = lg[:, sp["<|n|>"]].clone()
                lg[:] = float("-inf")
                lg[:, sp["<|n|>"]] = keep
            if not gen:
                lg[:, sp["<|n|>"]] = float("-inf")
            if sp["<|rad|>"] in gen:
                lg[:, sp["<|rad|>"]] = float("-inf")
            t = int(nucleus(lg, temp, top_p)[0, 0])
            if t == sp["<|n|>"]:
                break
            gen.append(t)
        syl = next((self.syl_ids[t] for t in gen if t in self.syl_ids), None)
        gen = [t for t in gen if t not in self.syl_ids]
        rd = sp["<|rad|>"]
        if rd in gen:
            i = gen.index(rd)
            return join_ids(self.tok, gen[:i]), join_ids(self.tok, gen[i + 1:]), syl
        return join_ids(self.tok, gen), "", syl

    @torch.no_grad()
    def pick_syl(self, ids, temp=0.8):
        lg = self._logits(torch.tensor([ids], device=self.dev))
        mask = torch.full_like(lg, float("-inf"))
        keep = list(self.syl_ids)
        mask[:, keep] = lg[:, keep]
        t = int(nucleus(mask, temp, 0.95)[0, 0])
        return t, self.syl_ids[t]

    @torch.no_grad()
    def sample_couplets(self, prefix, seen_m, K, temp, top_p, max_steps=64):
        M, N = self.sp["<|m|>"], self.sp["<|n|>"]
        cached = len(prefix) + max_steps + 1 <= self.m.cfg.max_seq_len
        if cached:
            lg0, cache = self._prefill(prefix)
            cache = [(k.expand(K, -1, -1, -1), v.expand(K, -1, -1, -1)) for k, v in cache]
            lg, pos = lg0.expand(K, -1).clone(), len(prefix)
        else:
            base = torch.tensor(prefix, device=self.dev)[None].repeat(K, 1)
            gen = torch.empty((K, 0), dtype=torch.long, device=self.dev)
        seqs, seen, seg, done, lp = [[] for _ in range(K)], [seen_m] * K, [0] * K, [False] * K, [0.0] * K
        ninf = float("-inf")
        for _ in range(max_steps):
            if all(done):
                break
            if not cached:
                lg = self._logits(torch.cat([base, gen], 1))
            lg[:, self.V:] = ninf
            lg[:, self.ban] = ninf
            for r in range(K):
                if done[r]:
                    continue
                if seg[r] >= 36:                        # hemistich too long -> force the separator
                    keep = N if seen[r] else M
                    lg[r] = ninf
                    lg[r, keep] = 0.0
                    continue
                lg[r, N if not seen[r] else M] = ninf   # exactly one <|m|> then <|n|>
                if seg[r] < 3:
                    lg[r, M if not seen[r] else N] = ninf
            logp = torch.log_softmax(lg, -1)
            nxt = nucleus(lg, temp, top_p)
            lps = logp.gather(1, nxt)[:, 0].tolist()
            for r, t in enumerate(nxt[:, 0].tolist()):
                if done[r]:
                    continue
                seqs[r].append(t)
                lp[r] += lps[r]
                if t == M:
                    seen[r], seg[r] = True, 0
                elif t == N:
                    done[r] = True
                else:
                    seg[r] += 1
            if cached:
                if all(done):
                    break
                lg, cache = self._step(nxt, cache, pos)
                pos += 1
            else:
                gen = torch.cat([gen, nxt], 1)
        out = []
        for r in range(K):
            if not done[r]:
                continue
            s = seqs[r]
            if seen_m:
                a_ids, b_ids = None, s[:-1]
            else:
                if M not in s:
                    continue
                mi = s.index(M)
                a_ids, b_ids = s[:mi], s[mi + 1:-1]
            out.append((s, a_ids, b_ids, lp[r] / len(s)))
        return out

    def valid(self, A, B, idx, qaf, rad, ghazal, used, hist, pair, syl=None, tol=2, user_first=False):
        wa, wb = A.split(), B.split()
        if not (2 <= len(wa) <= 15 and 2 <= len(wb) <= 15) or not (0.5 <= len(A) / max(len(B), 1) <= 2.0):
            return None
        if self.lex is not None and not all(w in self.lex for w in (wb if user_first else wa + wb)):
            return None
        if syl is not None and (abs(syl_count(B) - syl) > tol or (not user_first and abs(syl_count(A) - syl) > tol)):
            return None                                 # rhythm: estimated syllable count must stay near the poem's target
        words = []
        if qaf or rad:
            if not rhyme_match(B, qaf, rad):
                return None
            matla = rhyme_match(A, qaf, rad)
            if idx == 0 and ghazal and not matla:       # first couplet of a ghazal/qasida: both hemistichs rhyme
                return None
            if qaf:
                wB, new = qaf_word(B, rad), []
                if idx == 0 and matla:
                    new.append(qaf_word(A, rad))
                if wB in used or wB in new:
                    return None
                words = new + [wB]
        elif pair:
            if not pair_rhyme_ok(A, B) or _zw(wb[-1]) in used:
                return None
            words = [_zw(wb[-1])]
        return None if repeat_bad(A, B, hist, rad) else words

    def poem(self, poet, form, qaf, rad, first="", n_couplets=7, K=8, temp=0.8, top_p=0.92, pair=False, max_fail=12,
             syl=None, tol=2, deadline=None):
        sp = self.sp
        M, N = sp["<|m|>"], sp["<|n|>"]
        n_couplets = min(n_couplets, 8)
        ghazal = any(k in (form or "") for k in RHYME_FORMS)
        first_c = (clean_text(first) or "") if first else ""
        if len(first_c.split()) < 2:
            first_c = ""
        if first_c and not qaf and not rad and ghazal:   # rhyme taken from the user's first hemistich (last 2 letters of its last word)
            lw = _zw(first_c.split()[-1])
            qaf = lw[-2:] if len(lw) >= 3 else ""
        syl_tok = None
        if not qaf and not rad and ghazal:               # let the model choose a rhyme (and a rhythm)
            for _ in range(10):
                qaf, rad, s0 = self.sample_header(poet, form)
                if qaf or rad:
                    syl = syl or s0
                    break
        base = [sp["<|poem|>"]] + self.enc(poet or UNKNOWN_POET) + [sp["<|sep|>"]] + self.enc(form or UNKNOWN_FORM) + [sp["<|rhy|>"]] + \
               self.enc(qaf) + ([sp["<|rad|>"]] + self.enc(rad) if rad else [])
        if syl is not None and syl_token(syl) in sp and sp[syl_token(syl)] is not None:
            syl_tok = sp[syl_token(syl)]
            syl = max(SYL_MIN, min(SYL_MAX, int(syl)))
        else:
            syl_tok, syl = self.pick_syl(base)
        ids = base + [syl_tok, N]
        hist, used, stack, couplets, scores = [], set(), [], [], []
        fails = rounds = 0
        while len(couplets) < n_couplets:
            if deadline and time.time() > deadline:
                break
            idx = len(couplets)
            use_first = bool(first_c) and idx == 0
            pre = ids + (self.enc(first_c) + [M] if use_first else [])
            okc = []
            t_eff = temp + 0.03 * min(rounds, 8)
            for s, a_ids, b_ids, mlp in self.sample_couplets(pre, use_first, K, t_eff, top_p):
                A = first_c if use_first else join_ids(self.tok, a_ids)
                B = join_ids(self.tok, b_ids)
                w = self.valid(A, B, idx, qaf, rad, ghazal, used, hist, pair, syl, tol + (rounds >= 3), use_first)
                if w is not None:
                    okc.append((mlp, s, A, B, w))
            okc.sort(key=lambda x: -x[0])
            best = random.choice(okc[:3]) if okc else None
            if best is None:
                rounds += 1
                if rounds >= 6:
                    fails, rounds = fails + 1, 0
                    if fails > max_fail:
                        break
                    if couplets:                          # backtrack: drop the last accepted couplet
                        L, H, w, _ = stack.pop()
                        ids, hist = ids[:L], hist[:H]
                        used -= set(w)
                        couplets.pop()
                        scores.pop()
                continue
            mlp, s, A, B, w = best
            stack.append((len(ids), len(hist), w, mlp))
            ids = pre + s
            hist += [A, B]
            used.update(w)
            couplets.append((A, B))
            scores.append(mlp)
            rounds = 0
        if len(couplets) < min(3, n_couplets):
            return None
        return {"poet": poet or UNKNOWN_POET, "form": form or UNKNOWN_FORM, "qaf": qaf, "rad": rad, "couplets": couplets,
                "syl": syl, "score": sum(scores) / len(scores)}


def fmt_poem(r, idx=1):
    """one block in the format the Telegram bot parses:  --- i | poet | form | قافیه: x | ردیف: y | ... ---  then  'a | b'  lines"""
    if r is None:
        return "(no valid poem - try again or a different rhyme)"
    head = f"--- {idx} | {r['poet']} | {r['form']} | قافیه: {r['qaf'] or '-'} | ردیف: {r['rad'] or '-'} | syl {r['syl']} | score {r['score']:.2f} ---"
    return head + "\n" + "\n".join(f"{a} | {b}" for a, b in r["couplets"])


@torch.no_grad()
def sample_demo(model, tok, dev, amp, lex):
    rs = (torch.get_rng_state(), torch.cuda.get_rng_state())
    torch.manual_seed(7)
    model.eval()
    try:
        r = Gen(model, tok, dev, amp, lex).poem("حافظ", "غزلیات", "ان", "", n_couplets=4, K=6, max_fail=3, deadline=time.time() + 40)
    finally:
        model.train()
        torch.set_rng_state(rs[0])
        torch.cuda.set_rng_state(rs[1])
    return fmt_poem(r)


def load_model(path, dev):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    cfg = Config(**ck["config"])
    cfg.dropout = 0.0
    m = PoetGPT(cfg)
    m.load_state_dict(ck["model"])
    m.set_dropout(0.0)
    return m.to(dev).eval(), ck


def cmd_gen(a):
    from tokenizers import Tokenizer
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    path = Path(a.ckpt) if a.ckpt else next((p for p in (ROOT / "finetune" / "best.pt", ROOT / "pretrain" / "best.pt") if p.exists()), None)
    if path is None or not path.exists():
        raise SystemExit(f"No trained model found ({ROOT / 'finetune' / 'best.pt'}). Run: python -u poet.py all")
    model, ck = load_model(path, dev)
    tok = Tokenizer.from_file(str(DATA / "tokenizer.json"))
    lex = None
    if not a.no_lexicon:
        lex = {w for w, c in jload(DATA / "lexicon.json").items() if c >= a.min_word_count}
    poet, form = clean_text(a.poet) or "", clean_text(a.form) or ""
    qaf, rad = clean_text(a.qafiye) or "", clean_text(a.radif) or ""
    pf = DATA / "poets.txt"
    known = pf.read_text(encoding="utf-8").split("\n") if pf.exists() else []
    if poet and known and poet not in known:
        print(f"WARNING: poet '{poet}' is not a known tag (it will act like noise). Did you mean: {difflib.get_close_matches(poet, known, n=5) or known[:8]}")
    if a.seed >= 0:
        torch.manual_seed(a.seed)
    amp = torch.bfloat16 if (dev.type == "cuda" and torch.cuda.is_bf16_supported()) else torch.float16
    g = Gen(model, tok, dev, amp, lex)
    best_of = max(a.best_of, a.n)
    print(f"model {path} (step {ck.get('step')}, val {ck.get('val')}) | generating {best_of} candidates, keeping {a.n}")
    res = []
    for i in range(best_of):
        t0 = time.time()
        r = g.poem(poet, form, qaf, rad, a.first, a.couplets, a.cands, a.temp, a.top_p, a.pair, syl=(a.syl or None), tol=a.tol,
                   deadline=time.time() + a.max_seconds)
        print(f"  candidate {i + 1}/{best_of}: {'ok' if r else 'failed'} ({time.time() - t0:.1f}s)")
        if r:
            res.append(r)
    res.sort(key=lambda r: -r["score"])
    if getattr(a, "style_weight", 0.0) > 0 and res:
        try:
            import stylekit
            base = stylekit.get_baseline(poet, form, DATA, SCRIPT)
            for r in res:
                r["style_dist"] = stylekit.distance(r["couplets"], base, DATA)
            res.sort(key=lambda r: -(r["score"] - a.style_weight * r["style_dist"]))
            print("  style distance of the candidates, best first (lower = closer to the real poet): " + ", ".join(f"{r['style_dist']:.2f}" for r in res))
        except Exception as e:
            print(f"  (style re-rank skipped: {e})")
    out = [fmt_poem(r, i + 1) for i, r in enumerate(res[:a.n])]
    for t in out:
        print("\n" + t)
    with open(a.out, "a" if getattr(a, "append", False) else "w", encoding="utf-8") as f:
        f.write(("\n\n".join(out) + "\n\n") if out else "")
    print(f"\nsaved to {a.out}")
    return len(out)


def cmd_all(a):
    prepare_data(a)
    meta = jload(DATA / "meta.json")
    has_prose = meta["prose_train_tokens"] > 1e6
    pre_h = a.hours * a.pre_frac if has_prose else 0.0
    if has_prose and train_stage("pretrain", pre_h, a) == "stop":
        return
    if train_stage("finetune", a.hours - pre_h, a) == "stop":
        return
    print(f"\nFinal poems -> {ROOT / 'final_poems.txt'}")
    (ROOT / "final_poems.txt").write_text("", encoding="utf-8")
    for poet, form in (("حافظ", "غزلیات"), ("سعدی", "غزلیات"), ("مولانا", "غزلیات"), ("", "غزلیات")):
        a.poet, a.form, a.qafiye, a.radif, a.first = poet, form, "", "", ""
        a.n, a.best_of, a.out, a.append = 2, 6, str(ROOT / "final_poems.txt"), True
        cmd_gen(a)


# ============================================================================ self test (no data needed)
def cmd_selftest(a):
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {info}")

    print("selftest:")
    check("syllable estimate", syl_count("کتاب") == 2 and syl_count("دوست") == 1 and 13 <= syl_count("الا یا ایها الساقی ادر کاسا و ناولها") <= 17)
    check("clean_text", clean_text("كتاب  ‌ها") == "کتاب ها" and clean_text("abc") is None)
    cps = [("ز روی دلبران ما", "به شعر دلستان ما"), ("چو بی تو شد زمان ما", "ز عشق جاودان ما"), ("به دیده آسمان ما", "ز دل آشیان ما")]
    check("rhyme detect", detect_rhyme(cps)[:2] == ("ان", "ما") and rhyme_match("به شعر دلستان ما", "ان", "ما"))
    torch.manual_seed(0)
    cfg = Config(vocab_size=64, dim=64, n_layers=2, n_heads=4, n_kv_heads=2, hidden_dim=128, max_seq_len=64, n_id=5)
    m = PoetGPT(cfg).eval()
    x = torch.randint(0, 64, (3, 24))
    with torch.no_grad():
        lg, cache = m.forward_cached(x[:, :10], None, 0)
        err = (lg - m(x[:, :10])).abs().max().item()
        for t in range(10, 24):
            lg, cache = m.forward_cached(x[:, t:t + 1], cache, t)
            err = max(err, (lg - m(x[:, :t + 1])).abs().max().item())
        lg2, c2 = m.forward_cached(x[:, :8], None, 0)                      # multi-token chunk with a cache
        lg2, c2 = m.forward_cached(x[:, 8:14], c2, 8)
        err = max(err, (lg2 - m(x[:, :14])).abs().max().item())
    check("KV cache == full forward", err < 1e-3, f"(max diff {err:.2e})")
    loss, ce = m(x[:, :-1].contiguous(), x[:, 1:].contiguous())
    loss.backward()
    check("loss/backward", math.isfinite(loss.item()) and math.isfinite(ce.item()))
    print("ALL OK" if ok else "SOME CHECKS FAILED - send me this output")


def main():
    global ROOT, DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["data", "train", "gen", "all", "selftest"])
    ap.add_argument("archive", nargs="?", default="")
    ap.add_argument("--hours", type=float, default=16.0, help="total training time (pretrain + finetune)")
    ap.add_argument("--pre-frac", type=float, default=0.65, help="share of --hours for pretraining on prose")
    ap.add_argument("--stage", choices=["pretrain", "finetune", "style"], default=None)
    ap.add_argument("--wcap", type=float, default=2.0, help="cap on the per-poet sampling weight (Hafez/Saadi are 6/5 before capping)")
    ap.add_argument("--prose-mix", type=float, default=-1.0, help="finetune/style: share of prose windows (-1 = stage default)")
    ap.add_argument("--style-weight", type=float, default=0.0, help="gen: re-rank candidates by closeness to the real poet's register (try 0.3)")
    ap.add_argument("--size", choices=["auto", "small", "base", "large", "xl", "xxl"], default="auto")
    ap.add_argument("--min-ratio", type=float, default=12.0, help="auto size: minimum training tokens per parameter (lower = bigger model, less trained)")
    ap.add_argument("--batch-tokens", type=int, default=49152)
    ap.add_argument("--lr", type=float, default=0.0)
    ap.add_argument("--eval-every", type=int, default=0)
    ap.add_argument("--patience", type=int, default=5, help="finetune: stop after N evals without a new best")
    ap.add_argument("--prose-chars", type=float, default=0.0, help="max characters taken from Wikisource (Wikipedia gets 60%% of it)")
    ap.add_argument("--classic-min", type=float, default=0.85, help="prose paragraphs need this share of words known from the poems")
    ap.add_argument("--no-prose", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="tiny end-to-end test in poet3_smoke/")
    ap.add_argument("--min-word-count", type=int, default=3, help="a word must occur this often in the poems to be allowed")
    ap.add_argument("--no-lexicon", action="store_true")
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--poet", default="")
    ap.add_argument("--form", default="غزلیات")
    ap.add_argument("--qafiye", default="")
    ap.add_argument("--radif", default="")
    ap.add_argument("--first", default="", help="first hemistich (2+ words)")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--best-of", type=int, default=6)
    ap.add_argument("--couplets", type=int, default=7)
    ap.add_argument("--cands", type=int, default=8, help="candidate couplets sampled per step")
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--top-p", type=float, default=0.92)
    ap.add_argument("--syl", type=int, default=0, help="force the syllable count per hemistich (0 = model decides)")
    ap.add_argument("--tol", type=int, default=2, help="allowed deviation of the estimated syllable count")
    ap.add_argument("--max-seconds", type=float, default=90.0, help="time limit per poem")
    ap.add_argument("--pair", action="store_true", help="masnavi mode: both hemistichs of a couplet must rhyme")
    ap.add_argument("--seed", type=int, default=-1)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.prose_chars <= 0:                      # ~75M cleaned characters per training hour (min 450M)
        a.prose_chars = max(450e6, a.hours * 7.5e7)
    if a.smoke:
        ROOT = SCRIPT / "poet3_smoke"
        DATA = ROOT / "data"
        a.hours, a.prose_chars, a.eval_every, a.batch_tokens, a.patience, a.pre_frac = 0.2, 25e6, 40, 16384, 3, 0.5
        if a.size == "auto":
            a.size = "small"
    ROOT.mkdir(exist_ok=True)
    if not a.out:
        a.out = str(ROOT / "poems.txt")
    if a.cmd == "selftest":
        cmd_selftest(a)
    elif a.cmd == "data":
        prepare_data(a)
    elif a.cmd == "train":
        meta = jload(DATA / "meta.json")
        has_prose = meta["prose_train_tokens"] > 1e6
        if a.stage == "pretrain":
            train_stage("pretrain", a.hours, a)
        elif a.stage == "finetune":
            train_stage("finetune", a.hours, a)
        elif a.stage == "style":
            train_stage("style", a.hours, a)
        else:
            if has_prose and train_stage("pretrain", a.hours * a.pre_frac, a) == "stop":
                return
            train_stage("finetune", a.hours * (1 - a.pre_frac) if has_prose else a.hours, a)
    elif a.cmd == "gen":
        cmd_gen(a)
    else:
        cmd_all(a)


if __name__ == "__main__":
    main()
