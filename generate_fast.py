# -*- coding: utf-8 -*-
"""generate_fast.py - drop-in replacement used by the Telegram bot (core.py calls it with the OLD options).
Translates the old command line to poet.py's generator; output format is identical, so bot.py/core.py stay unchanged."""
import sys, argparse
ap = argparse.ArgumentParser()
for o in ("--poet", "--form", "--qafiye", "--radif", "--first", "--out", "--ckpt"):
    ap.add_argument(o, default="")
for o in ("--n", "--best-of", "--min-couplets", "--seed", "--min-word-count"):
    ap.add_argument(o, type=int, default=None)
for o in ("--temp", "--top-p"):
    ap.add_argument(o, type=float, default=None)
ap.add_argument("--pair-rhyme", action="store_true")
a, _ignored = ap.parse_known_args()          # --top-k --rep --polish --retries --max-tokens --pair-k --no-graph ... are not needed any more
argv = ["poet.py", "gen", "--form", a.form or "غزلیات"]
for flag, val in (("--poet", a.poet), ("--qafiye", a.qafiye), ("--radif", a.radif), ("--first", a.first), ("--out", a.out), ("--ckpt", a.ckpt),
                  ("--n", a.n), ("--best-of", a.best_of), ("--seed", a.seed), ("--min-word-count", a.min_word_count),
                  ("--temp", a.temp), ("--top-p", a.top_p)):
    if val not in ("", None):
        argv += [flag, str(val)]
if a.pair_rhyme:
    argv.append("--pair")
if a.min_couplets:
    argv += ["--couplets", str(a.min_couplets + 1)]
sys.argv = argv
import poet
poet.main()
