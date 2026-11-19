# -*- coding: utf-8 -*-
"""Core logic of the poem bot (no telegram imports): env, logging, credits, command builder, parser, saver."""
import os, sys, re, json, shlex, logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
POEMS_DIR = BASE / "poems"
LOGS_DIR = BASE / "logs"
DATA_DIR = BASE / "bot_data"
TMP_DIR = DATA_DIR / "tmp"
for _d in (POEMS_DIR, LOGS_DIR, DATA_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def load_env():
    p = BASE / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PROXY_URL = os.environ.get("PROXY_URL", "").strip()
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
MAX_CREDITS = 10**12                                              # a user can never hold more than this
MAX_POEMS = 100                                                # max poems generated per request
START_CREDITS = int(os.environ.get("START_CREDITS", "200"))      # -1 = unlimited for everyone
if START_CREDITS > MAX_CREDITS:
    START_CREDITS = MAX_CREDITS
GEN_TIMEOUT_PER = int(os.environ.get("GEN_TIMEOUT_PER", "90"))  # seconds allowed per generated poem (safety net)
CONTACT = "@allirezaseza"


def gen_timeout(make):
    return 300 + GEN_TIMEOUT_PER * make


# ----------------------------------------------------------------------------- logging
def setup_logging():
    log = logging.getLogger("bot")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = RotatingFileHandler(LOGS_DIR / "bot.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    # httpx logs full URLs (they contain the bot token!) -> keep it quiet
    for n in ("httpx", "httpcore", "telegram", "apscheduler"):
        logging.getLogger(n).setLevel(logging.WARNING)
    return log


LOG = setup_logging()


def ev(user, action, detail=""):
    """One log line: who did what."""
    who = "-"
    if user is not None:
        who = f"{user.id} @{user.username or '-'} ({user.full_name})"
    LOG.info(f"{who} | {action} | {detail}".rstrip(" |"))


# ----------------------------------------------------------------------------- users / credits
_USERS_FILE = DATA_DIR / "users.json"
_users = {}
if _USERS_FILE.exists():
    try:
        _users = json.loads(_USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        _users = {}


def _save_users():
    _USERS_FILE.write_text(json.dumps(_users, ensure_ascii=False, indent=1), encoding="utf-8")


def get_user(user):
    k = str(user.id)
    if k not in _users:
        _users[k] = {"lang": "", "credits": START_CREDITS, "poems": 0, "first_seen": datetime.now().isoformat(timespec="seconds")}
    _users[k]["name"] = user.full_name
    _users[k]["username"] = user.username or ""
    return _users[k]


def save_users():
    _save_users()


def is_admin(uid):
    return uid in ADMIN_IDS


def unlimited(user):
    return is_admin(user.id) or START_CREDITS < 0


def has_credit(user, n=1):
    return unlimited(user) or get_user(user)["credits"] >= n


def max_poems(user):
    """Biggest number of poems this user may ask for in one request."""
    return MAX_POEMS if unlimited(user) else min(MAX_POEMS, get_user(user)["credits"])


def spend_credit(user, n=1):
    u = get_user(user)
    if not unlimited(user):
        u["credits"] -= n
    u["poems"] += n
    save_users()


def refund_credit(user, n=1):
    u = get_user(user)
    if not unlimited(user):
        u["credits"] = min(MAX_CREDITS, u["credits"] + n)
    u["poems"] = max(0, u["poems"] - n)
    save_users()


def add_credit(uid, n):
    """Returns (new_total, really_added) or None for an unknown user. Never goes above MAX_CREDITS."""
    k = str(uid)
    if k not in _users:
        return None
    before = _users[k]["credits"]
    _users[k]["credits"] = min(MAX_CREDITS, before + n)
    save_users()
    return _users[k]["credits"], _users[k]["credits"] - before


def can_request(user, cooldown=600):
    """Anti-spam for credit requests: True (and stamps the time) if the last one is older than `cooldown` s."""
    import time
    u = get_user(user)
    now = time.time()
    if now - u.get("last_req", 0) < cooldown:
        return False
    u["last_req"] = now
    save_users()
    return True


def credits_text(user):
    u = get_user(user)
    return "∞" if unlimited(user) else str(u["credits"])


# ----------------------------------------------------------------------------- generator command
# exactly the commands you gave, as plain option strings
BASE_ARGS = {
    "hafez":    "--poet حافظ --form غزلیات --polish --temp 0.7 --top-p 0.9 --top-k 40 --rep 1.05 --min-couplets 6 --min-word-count 3 --retries 12",
    "ferdowsi": "--poet فردوسی --pair-rhyme --polish --temp 0.75 --top-p 0.9 --top-k 40 --rep 1.1 --max-tokens 400 --min-couplets 5 --min-word-count 3 --retries 12",
    "masnavi":  "--form مثنویات --pair-rhyme --polish --temp 0.75 --top-p 0.9 --top-k 40 --rep 1.1 --max-tokens 400 --min-couplets 5 --min-word-count 3 --retries 12",
    "molavi":   "--poet مولانا --pair-rhyme --polish --temp 0.75 --top-p 0.9 --top-k 40 --rep 1.1 --max-tokens 400 --min-couplets 5 --min-word-count 3 --retries 12",
    "mix":      "--polish --temp 0.85 --top-p 0.92 --rep 1.05 --min-couplets 5 --min-word-count 3 --retries 12",
}


def validate_prompt(raw):
    """Returns (cleaned, error). Uses the project's own cleaner so the bot never crashes generate.py."""
    try:
        from textutil import clean_hemistich
        s, why = clean_hemistich(raw)
        return s, why
    except Exception:
        words = raw.split()
        return (raw.strip(), None) if len(words) >= 2 else (None, "one_word")


MOLAVI_FORMS = ['دفتر  سوم', 'دفتر  ششم', 'دفتر  پنجم', 'دفتر  اول', 'دفتر  دوم', 'دفتر  چهارم']   # Molavi: masnavi only (a random daftar is used as the form tag)


FERDOWSI_STORIES = ["داستان رستم و اسفندیار", "جنگ بزرگ کیخسرو با افراسیاب", "پادشاهی خسرو پرویز",
                    "پادشاهی بهرام گور", "پادشاهی اسکندر", "داستان دوازده رخ"]   # forms of Ferdowsi that exist in the data


def build_cmd(kind, make, top, ghazal=True, pair=True, first="", out="out.txt", mf="", fs=0):
    toks = shlex.split(BASE_ARGS[kind])
    if kind == "molavi":                          # no questions: always masnavi, rhyme in every hemistich
        import random
        toks += ["--form", random.choice(MOLAVI_FORMS)]
    if kind == "ferdowsi":                        # no question: a random form of Ferdowsi is used (like Molavi)
        import random
        toks += ["--form", random.choice(FERDOWSI_STORIES)]
    if kind == "hafez" and not ghazal:          # not a ghazal -> drop --form غزلیات
        i = toks.index("--form")
        del toks[i:i + 2]
    if kind == "mix" and mf == "gh":              # mix of all poets, but ghazals only (the rhyme type question does not apply)
        toks += ["--form", "غزلیات"]
        pair = False
    elif kind == "mix" and mf == "ms":            # mix of all poets, masnavi only
        toks += ["--form", "مثنویات"]
    if kind in ("masnavi", "ferdowsi", "mix"):  # the user chooses: rhyme only at the end of the couplet, or every hemistich
        if pair and "--pair-rhyme" not in toks:
            toks.append("--pair-rhyme")
        elif not pair and "--pair-rhyme" in toks:
            toks.remove("--pair-rhyme")
    if first:
        toks += ["--first", first]
    toks += ["--n", str(top), "--best-of", str(make), "--out", str(out)]
    return [sys.executable, "generate_fast.py"] + toks


def cmd_text(cmd):
    return "python " + " ".join(shlex.quote(c) if " " in c else c for c in cmd[1:])


# ----------------------------------------------------------------------------- parse / save
def parse_output(path):
    """generate.py output -> list of dicts {head, poet, form, qaf, rad, lines:[(a,b)]}"""
    txt = Path(path).read_text(encoding="utf-8").strip()
    poems = []
    for block in re.split(r"\n\s*\n", txt):
        rows = [r for r in block.strip().split("\n") if r.strip()]
        if not rows or not rows[0].startswith("---"):
            continue
        head = rows[0].strip("- ").strip()
        parts = [p.strip() for p in head.split(" | ")]
        qaf = (re.search(r"قافیه:\s*(\S+)", head) or [None, "-"])[1]
        rad = (re.search(r"ردیف:\s*(\S+)", head) or [None, "-"])[1]
        lines = []
        for r in rows[1:]:
            if " | " in r:
                a, b = r.split(" | ", 1)
                lines.append((a.strip(), b.strip()))
        poems.append({"head": head, "poet": parts[1] if len(parts) > 1 else "", "form": parts[2] if len(parts) > 2 else "",
                      "qaf": qaf, "rad": rad, "lines": lines})
    return poems


def save_request(user, lang, opts, cmd, poems, raw_out, seconds):
    now = datetime.now().astimezone()
    name = f"{now:%Y-%m-%d_%H-%M-%S}_{user.id}.txt"
    L = ["=" * 60,
         f"time      : {now:%Y-%m-%d %H:%M:%S %z}",
         f"user id   : {user.id}",
         f"username  : @{user.username or '-'}",
         f"name      : {user.full_name}",
         f"language  : {lang}",
         f"duration  : {seconds:.1f}s",
         "--- what the user chose ---"]
    L += [f"{k:10}: {v}" for k, v in opts.items()]
    L += ["--- exact command ---", cmd_text(cmd), "=" * 60, ""]
    for i, p in enumerate(poems, 1):
        L.append(f"##### poem {i}  [{p['head']}]")
        L += [f"{a}\n{b}\n" for a, b in p["lines"]]
        L.append("")
    (POEMS_DIR / name).write_text("\n".join(L), encoding="utf-8")
    return name
