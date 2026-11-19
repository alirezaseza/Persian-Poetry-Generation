import re, math, unicodedata, collections

LETTERS = "ءآؤئابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
SPECIALS = ["<|pad|>", "<|unk|>", "<|poem|>", "<|sep|>", "<|m|>", "<|n|>", "<|end|>", "<|rhy|>", "<|rad|>"]
UNKNOWN_POET = "ناشناس"
UNKNOWN_FORM = "متفرقه"

CHAR_MAP = {
    "ك": "ک", "ڪ": "ک", "ي": "ی", "ى": "ی", "ې": "ی", "ۍ": "ی", "ێ": "ی", "ے": "ی",
    "ة": "ه", "ھ": "ه", "ہ": "ه", "ۀ": "ه", "ۂ": "ه", "\u06d5": "ه",
    "أ": "ا", "إ": "ا", "ٱ": "ا",
    "\u200b": "\u200c", "\u200d": "", "\u200e": "", "\u200f": "",
    "\u202a": "", "\u202b": "", "\u202c": "", "\ufeff": "", "\u00ad": "", "ـ": "",
}
TRANS = str.maketrans(CHAR_MAP)
HARAKAT_RE = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7\u06e8\u06ea-\u06ed]")
FOREIGN_RE = re.compile(r"[A-Za-z\d]")
NONALLOWED_RE = re.compile("[^" + LETTERS + " \u200c]")
RUN_RE = re.compile(r"(.)\1{3,}")
WS_ZWNJ_RE = re.compile(r"\u200c*\s+\u200c*")
MULTI_ZWNJ_RE = re.compile("\u200c{2,}")


def normalize_text(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(TRANS)
    return HARAKAT_RE.sub("", s)


def clean_text(s):
    """Cleaned text, or None if it contains Latin letters or digits."""
    s = normalize_text(s)
    if FOREIGN_RE.search(s):
        return None
    s = NONALLOWED_RE.sub(" ", s)
    s = MULTI_ZWNJ_RE.sub("\u200c", s)
    s = WS_ZWNJ_RE.sub(" ", s)
    return s.strip(" \u200c")


def clean_hemistich(raw):
    if not isinstance(raw, str):
        return None, "not_text"
    s = clean_text(raw)
    if s is None:
        return None, "foreign_char"
    core = len(s.replace(" ", "").replace("\u200c", ""))
    if core < 6:
        return None, "too_short"
    if len(s) > 80:
        return None, "too_long"
    n_words = s.count(" ") + 1
    if n_words < 2:
        return None, "one_word"
    if n_words > 15:
        return None, "too_many_words"
    if RUN_RE.search(s):
        return None, "char_run"
    return s, None


def rhyme_match(b, qaf, rad):
    """Does hemistich b end with the given radif and qafiye? (no tag -> True)"""
    if not qaf and not rad:
        return True
    words = b.split(" ")
    if rad:
        r = rad.split(" ")
        if len(words) <= len(r) or words[-len(r):] != r:
            return False
        words = words[:-len(r)]
    if qaf:
        return bool(words) and words[-1].endswith(qaf)
    return True


def detect_rhyme(cps):
    """Returns (qafiye, radif, coverage). Empty strings = no consistent rhyme."""
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
    keys = []
    for w in ends:
        if rad:
            keys.append(w[-len(rad) - 1] if (len(w) > len(rad) and tuple(w[-len(rad):]) == rad) else "")
        else:
            keys.append(w[-1])
    qaf = ""
    for k in (3, 2, 1):
        c = collections.Counter(x[-k:] for x in keys if len(x) >= k)
        if c:
            suf, cnt = c.most_common(1)[0]
            thr = max(2, math.ceil(0.75 * n)) if k > 1 else max(2, math.ceil(0.8 * n))
            if cnt >= thr:
                qaf = suf
                break
    rad_s = " ".join(rad)
    if not qaf and not rad_s:
        return "", "", 0.0
    cov = sum(1 for _, b in cps if rhyme_match(b, qaf, rad_s)) / n
    return qaf, rad_s, cov


def build_text(poet, form, qaf, rad, cps):
    head = "<|poem|>" + poet + "<|sep|>" + form + "<|rhy|>" + qaf + ("<|rad|>" + rad if rad else "") + "<|n|>"
    body = "".join(a + "<|m|>" + b + "<|n|>" for a, b in cps)
    return head + body + "<|end|>"
