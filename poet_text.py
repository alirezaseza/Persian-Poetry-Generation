# -*- coding: utf-8 -*-
"""poet_text.py - text utilities of the Persian poet project (NO torch import, so worker processes start fast on Windows)."""
import re, math, unicodedata, collections
import os, sys, hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import time
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
WORKERS = max(1, min((os.cpu_count() or 4) - 1, 8))


LETTERS = "ءآؤئابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
SYL_MIN, SYL_MAX = 6, 22
SYL_TOKENS = [f"<|s{i}|>" for i in range(SYL_MIN, SYL_MAX + 1)]
SPECIALS = ["<|pad|>", "<|unk|>", "<|poem|>", "<|sep|>", "<|m|>", "<|n|>", "<|end|>", "<|rhy|>", "<|rad|>", "<|prose|>"] + SYL_TOKENS
UNKNOWN_POET, UNKNOWN_FORM = "ناشناس", "متفرقه"
CHAR_MAP = {"ك": "ک", "ڪ": "ک", "ي": "ی", "ى": "ی", "ې": "ی", "ۍ": "ی", "ێ": "ی", "ے": "ی", "ة": "ه", "ھ": "ه", "ہ": "ه",
            "ۀ": "ه", "ۂ": "ه", "\u06d5": "ه", "أ": "ا", "إ": "ا", "ٱ": "ا", "\u200b": "\u200c", "\u200d": "", "\u200e": "",
            "\u200f": "", "\u202a": "", "\u202b": "", "\u202c": "", "\ufeff": "", "\u00ad": "", "ـ": ""}
TRANS = str.maketrans(CHAR_MAP)
HARAKAT_RE = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7\u06e8\u06ea-\u06ed]")
FOREIGN_RE = re.compile(r"[A-Za-z\d]")
NONALLOWED_RE = re.compile("[^" + LETTERS + " \u200c]")
RUN_RE = re.compile(r"(.)\1{3,}")
WS_ZWNJ_RE = re.compile(r"\u200c*\s+\u200c*")
MULTI_ZWNJ_RE = re.compile("\u200c{2,}")
BRACKET_RE = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|\{[^{}]*\}|<[^<>]*>")
SENT_SPLIT = re.compile(r"[.!?؟…؛:]+|\n+")
ALLOWED = set(LETTERS) | {" ", "\u200c"}
PUNCT = set(" \t\r\n.,،؛:!?؟()[]{}«»\"'`-–—…/\\|*_#=+<>%$@^&~٪٫٬·•")
RHYME_FORMS = ("غزل", "قصید", "قصاید")


def normalize_text(s):
    return HARAKAT_RE.sub("", unicodedata.normalize("NFKC", s).translate(TRANS))


def clean_text(s):
    s = normalize_text(s)
    if FOREIGN_RE.search(s):
        return None
    s = NONALLOWED_RE.sub(" ", s)
    s = MULTI_ZWNJ_RE.sub("\u200c", s)
    return WS_ZWNJ_RE.sub(" ", s).strip(" \u200c")


def clean_hemistich(raw):
    if not isinstance(raw, str):
        return None
    s = clean_text(raw)
    if s is None:
        return None
    if len(s.replace(" ", "").replace("\u200c", "")) < 6 or len(s) > 80:
        return None
    n = s.count(" ") + 1
    if n < 2 or n > 15 or RUN_RE.search(s):
        return None
    return s


def clean_sentence(sent):
    sent = sent.strip()
    if len(sent) < 15 or FOREIGN_RE.search(sent):
        return None
    bad = sum(1 for ch in sent if ch not in ALLOWED and ch not in PUNCT)
    if bad > 0.02 * len(sent):
        return None
    sent = NONALLOWED_RE.sub(" ", sent)
    sent = WS_ZWNJ_RE.sub(" ", MULTI_ZWNJ_RE.sub("\u200c", sent)).strip(" \u200c")
    w = sent.split()
    n = len(w)
    if n < 5 or n > 80:
        return None
    avg = sum(len(x) for x in w) / n
    if avg > 9 or avg < 2.3 or max(len(x) for x in w) > 22 or RUN_RE.search(sent):
        return None
    if n >= 8 and len(set(w)) / n < 0.5:
        return None
    return sent


def prose_paragraphs(text):
    """raw article text -> clean paragraphs made of consecutive good sentences."""
    out = []
    for para in text.split("\n"):
        if len(para) < 50:
            continue
        s = BRACKET_RE.sub(" ", normalize_text(para))
        runs, run = [], []
        for sent in SENT_SPLIT.split(s):
            if not sent.strip():
                continue
            c = clean_sentence(sent)
            if c:
                run.append(c)
            elif run:
                runs.append(run)
                run = []
        if run:
            runs.append(run)
        for r in runs:
            t = " ".join(r)
            if len(t.split()) >= 12:
                out.append(t)
    return out


def prose_worker(texts):
    out = []
    for t in texts:
        if t:
            out.extend(prose_paragraphs(t))
    return out


# ============================================================================ rhyme
def rhyme_match(b, qaf, rad):
    if not qaf and not rad:
        return True
    words = b.split(" ")
    if rad:
        r = rad.split(" ")
        if len(words) <= len(r) or words[-len(r):] != r:
            return False
        words = words[:-len(r)]
    return True if not qaf else (bool(words) and words[-1].endswith(qaf))


def detect_rhyme(cps):
    n = len(cps)
    if n < 2:
        return "", "", 0.0
    ends = [b.split(" ") for _, b in cps]
    need = max(2, math.ceil(0.6 * n))
    rad = ()
    for k in (3, 2, 1):
        c = collections.Counter(tuple(w[-k:]) for w in ends if len(w) > k)
        if c:
            suf, cnt = c.most_common(1)[0]
            if cnt >= need:
                rad = suf
                break
    keys = [(w[-len(rad) - 1] if (len(w) > len(rad) and tuple(w[-len(rad):]) == rad) else "") if rad else w[-1] for w in ends]
    qaf = ""
    for k in (3, 2, 1):
        c = collections.Counter(x[-k:] for x in keys if len(x) >= k)
        if c:
            suf, cnt = c.most_common(1)[0]
            if cnt >= (max(2, math.ceil(0.75 * n)) if k > 1 else max(2, math.ceil(0.8 * n))):
                qaf = suf
                break
    rad_s = " ".join(rad)
    if not qaf and not rad_s:
        return "", "", 0.0
    return qaf, rad_s, sum(1 for _, b in cps if rhyme_match(b, qaf, rad_s)) / n


# ============================================================================ approximate syllable counter (rhythm proxy)
# Persian is written without short vowels, so the exact arud meter cannot be read from the spelling.
# This is a *heuristic* syllable estimate (error of +-1..2 per hemistich is normal). Hemistichs of one poem share one meter,
# so their estimated counts stay close to each other; we use that for (1) removing broken lines, (2) a length/rhythm header
# token the model learns to condition on, (3) a rhythm check while generating.
FINAL_CL = frozenset(["رد", "ست", "فت", "ند", "خت", "شت", "رت", "رف", "رم", "رن", "رز", "رگ", "رب", "رس", "رق", "رش", "رج",
                      "لب", "لم", "لد", "لف", "نگ", "نج", "مب", "سب", "شم", "قت"])
SYL1 = frozenset(["شهر", "مهر", "دهر", "قهر", "بحر", "عشق", "صبر", "فکر", "ذکر", "شعر", "نظم", "جسم", "روح", "وقت", "ظلم", "علم",
                  "عقل", "نصر", "حمد", "رحم", "فخر", "قدر", "صدر", "نهر", "زهر", "ابر", "عمر", "شکر", "صفر", "نشر", "کبر"])
SYL2 = frozenset(["خرد", "ببر", "بکن", "بشر"])
_PIECE_SPLIT = re.compile("[ \u200c]+")


def _piece(p):
    if p in SYL1:
        return 1
    if p in SYL2:
        return 2
    n, typ = len(p), []
    for i, ch in enumerate(p):
        pv = bool(typ) and typ[-1] == "V"
        nx = p[i + 1] if i + 1 < n else ""
        if ch in "اآؤ":
            t = "V"
        elif ch == "و":
            if n == 1:
                t = "V"
            elif i == 0 or pv:
                t = "C"
            elif nx in ("ا", "آ"):
                t = "S"                      # silent waw (خواب)
            else:
                t = "V"
        elif ch == "ی":
            t = "C" if (i == 0 or pv or nx in ("ا", "آ")) else "V"
        elif ch == "ه" and i == n - 1 and i >= 2 and not pv:
            t = "V"                          # final -e (نامه)
        else:
            t = "C"
        typ.append(t)
    cs = [t for t in typ if t != "S"]
    nv = cs.count("V")
    if nv == 0:
        k = len(cs)
        if k <= 2:
            return 1
        if k == 3:
            return 1 if p[-2:] in FINAL_CL else 2
        if k == 4:
            return 2
        return 2 if p[-2:] in FINAL_CL else 3
    runs, r = [], 0
    for t in cs:
        if t == "C":
            r += 1
        else:
            runs.append(r)
            r = 0
    runs.append(r)
    s = nv
    if runs[0] >= 2:
        s += 1 + (runs[0] >= 4)              # inserted short vowel(s): کتاب = ke-taab
    s += sum(1 for m in runs[1:-1] if m >= 4)
    f = runs[-1]
    if f >= 3 or (f == 2 and p[-2:] not in FINAL_CL):
        s += 1                               # کودک = koo-dak
    return s


def syl_count(h):
    return sum(_piece(p) for p in _PIECE_SPLIT.split(h) if p)


def poem_syl(cps):
    c = sorted(syl_count(h) for a, b in cps for h in (a, b))
    m = c[len(c) // 2] if c else 12
    return max(SYL_MIN, min(SYL_MAX, int(m)))


def syl_token(n):
    return f"<|s{max(SYL_MIN, min(SYL_MAX, int(n)))}|>"


def build_text(poet, form, qaf, rad, cps):
    head = ("<|poem|>" + poet + "<|sep|>" + form + "<|rhy|>" + qaf + ("<|rad|>" + rad if rad else "") +
            syl_token(poem_syl(cps)) + "<|n|>")
    return head + "".join(a + "<|m|>" + b + "<|n|>" for a, b in cps) + "<|end|>"


# ============================================================================ prose download + cleaning (run as: python poet_text.py prose DATA_DIR CAP)
def _retry(fn, what, tries=10):
    """network calls: retry with growing pauses (5s, 10s, 20s ... max 60s). Partial downloads are resumed by huggingface_hub."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if any(x in str(e) for x in ("401", "403", "gated")):
                raise
            wait = min(60, 5 * 2 ** i)
            print(f"\n  [net] {what} failed ({type(e).__name__}: {str(e)[:100]}) - retry {i + 1}/{tries} in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"{what}: gave up after {tries} tries")


def fetch_hf_parquets(repo):
    from huggingface_hub import HfApi, hf_hub_download
    files = _retry(lambda: HfApi().list_repo_files(repo, repo_type="dataset"), f"list {repo}")
    cand = {}
    for f in files:
        m = re.match(r"^(\d{8})\.fa/.*\.parquet$", f)
        if m:
            cand.setdefault(m.group(1), []).append(f)
    if not cand:
        raise RuntimeError(f"no Persian parquet files found in {repo}")
    best = sorted(cand)[-1]
    print(f"  {repo}: dump {best}, {len(cand[best])} file(s)")
    return [_retry(lambda f=f: hf_hub_download(repo, f, repo_type="dataset"), f"download {f}") for f in sorted(cand[best])]


def hf_blocks(repo):
    import pyarrow.parquet as pq
    for path in fetch_hf_parquets(repo):
        for b in pq.ParquetFile(path).iter_batches(batch_size=400, columns=["text"]):
            yield b.column(0).to_pylist()


def local_blocks():
    d = Path(__file__).resolve().parent / "extra_text"
    for p in (sorted(d.glob("*.txt")) if d.is_dir() else []):
        with open(p, encoding="utf-8", errors="ignore") as f:
            buf = []
            for line in f:
                buf.append(line.rstrip("\n"))
                if len(buf) >= 400:
                    yield ["\n".join(buf)]
                    buf = []
            if buf:
                yield ["\n".join(buf)]


def naab_blocks(n_shards=126):
    """SLPL/naab: 126 shuffled text shards of ~1 GB each (every shard is a random sample of the whole corpus), so we simply take as many as needed."""
    from huggingface_hub import hf_hub_download
    import random
    order = list(range(n_shards))
    random.Random(7).shuffle(order)
    for i in order:
        fn = f"data/train-{i:05d}-of-{n_shards:05d}.txt"
        path = _retry(lambda fn=fn: hf_hub_download("SLPL/naab", fn, repo_type="dataset"), f"download naab {fn}")
        with open(path, encoding="utf-8", errors="ignore") as f:
            buf = []
            for line in f:
                buf.append(line.rstrip("\n"))
                if len(buf) >= 400:
                    yield ["\n".join(buf)]
                    buf = []
            if buf:
                yield ["\n".join(buf)]


def run_source(name, blocks, cap, out, seen, ex):
    pend = collections.deque()
    st = {"chars": 0, "n": 0}

    def drain(fut):
        for p in fut.result():
            h = hashlib.blake2b(p.replace(" ", "").encode("utf-8"), digest_size=8).digest()
            if h in seen:
                continue
            seen.add(h)
            out.write(p + "\n")
            st["chars"] += len(p) + 1
            st["n"] += 1

    for blk in blocks:
        pend.append(ex.submit(prose_worker, blk))
        while len(pend) >= WORKERS * 3:
            drain(pend.popleft())
            sys.stdout.write(f"\r  {name}: {st['n']:,} paragraphs | {st['chars'] / 1e6:,.0f}M chars   ")
        if cap and st["chars"] >= cap:
            break
    while pend:
        drain(pend.popleft())
    print(f"\r  {name}: {st['n']:,} paragraphs | {st['chars'] / 1e6:,.0f}M chars   ")
    return st["chars"]


def build_prose(data_dir, cap_chars):
    out_path = Path(data_dir) / "prose.txt"
    if out_path.exists() and out_path.stat().st_size > 1e6:
        print(f"Prose already cleaned ({out_path.stat().st_size / 1e6:.0f} MB). Delete {out_path} to redo.")
        return out_path.stat().st_size
    print("Downloading + cleaning Persian prose (Wikisource = classical-style first, local extra_text/*.txt, Wikipedia)...")
    seen, total = set(), 0
    srcs = [("wikisource", lambda: hf_blocks("wikimedia/wikisource"), cap_chars),
            ("local-files", local_blocks, 0),
            ("wikipedia", lambda: hf_blocks("wikimedia/wikipedia"), cap_chars),
            ("naab", naab_blocks, cap_chars)]
    tmp_path = out_path.with_name("prose.txt.part")
    failed = []
    with open(tmp_path, "w", encoding="utf-8") as out, ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for name, mk, cap in srcs:
            if name in ("wikipedia", "naab"):               # fill up to the target; web text only if the better sources are not enough
                cap = cap_chars - total
                if cap <= 0:
                    print(f"  {name}: skipped (target {cap_chars / 1e6:,.0f}M chars already reached)")
                    continue
            try:
                total += run_source(name, mk(), cap, out, seen, ex)
            except Exception as e:
                print(f"\n  [warn] {name} failed: {type(e).__name__}: {str(e)[:200]}")
                if name == "naab" and any(x in str(e) for x in ("401", "403", "gated", "restricted")):
                    print("  naab needs a Hugging Face login (huggingface-cli login) - skipped")
                elif name != "local-files":
                    failed.append(name)
                    print("  hint: HF blocked? set a proxy (export HTTPS_PROXY=...) or mirror (export HF_ENDPOINT=https://hf-mirror.com),")
                    print("        or put Persian .txt files in the folder extra_text/ (classical prose is ideal) and run again.")
    if failed:
        tmp_path.unlink(missing_ok=True)
        print(f"\n  [ERROR] download incomplete ({', '.join(failed)}). Nothing was saved. Fix the connection and run the SAME command again "
              f"(files that finished downloading are cached).")
        return 0
    if total < 5e6:
        tmp_path.unlink(missing_ok=True)
        print("  [warn] not enough prose obtained.")
        return 0
    os.replace(tmp_path, out_path)
    return total




if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "prose":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        build_prose(sys.argv[2], int(sys.argv[3]))
