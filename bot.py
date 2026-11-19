# -*- coding: utf-8 -*-
import asyncio, os, re, time, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup as Kb
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler, MessageHandler,
                          ContextTypes, filters)
from telegram.request import HTTPXRequest

import core
from core import (LOG, ev, get_user, save_users, has_credit, max_poems, spend_credit, refund_credit,
                  add_credit, can_request, credits_text, is_admin, build_cmd, cmd_text, parse_output,
                  save_request, validate_prompt, gen_timeout, BASE, TMP_DIR, CONTACT, MAX_CREDITS, MAX_POEMS)
from texts import T, STICKERS

HTML = ParseMode.HTML
SPIN = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
EMOJI = ["🌹", "🌙", "🍷", "🕊", "🌌", "📜", "🔥", "🌺"]
STATE = {"lock": None, "waiting": 0, "tasks": set(), "jobs": {}}

# coloured buttons (Bot API 9.4+). Set COLOR_BUTTONS=0 in .env to turn them off.
COLOR = os.environ.get("COLOR_BUTTONS", "1") != "0"
P, S, D = "primary", "success", "danger"      # blue, green, red


def Btn(text, callback_data=None, style=None):
    if style and COLOR:
        return InlineKeyboardButton(text, callback_data=callback_data, api_kwargs={"style": style})
    return InlineKeyboardButton(text, callback_data=callback_data)


def lang_of(user):
    return get_user(user)["lang"] or "fa"


def esc(s):
    return html.escape(str(s))


async def show(update, text, rows):
    """Edit the button message if there is one, otherwise send a new message."""
    kb = Kb(rows)
    q = update.callback_query
    if q:
        try:
            await q.edit_message_text(text, parse_mode=HTML, reply_markup=kb)
            return
        except BadRequest as e:
            if "not modified" in str(e).lower():
                return
    await update.effective_chat.send_message(text, parse_mode=HTML, reply_markup=kb)


async def sticker(bot, chat_id, key):
    fid = STICKERS.get(key)
    if fid:
        try:
            await bot.send_sticker(chat_id, fid)
        except Exception:
            pass


def chunk_rows(btns, n=3):
    return [btns[i:i + n] for i in range(0, len(btns), n)]


# ----------------------------------------------------------------------------- screens
async def screen_lang(update):
    await show(update, T["fa"]["choose_lang"], [[Btn("🇮🇷 فارسی", "lang:fa", P), Btn("🇬🇧 English", "lang:en", P)]])


async def screen_menu(update, user):
    t = T[lang_of(user)]
    await show(update, t["menu"].format(credits=credits_text(user)), [
        [Btn(t["b_poem"], "poem", S)],
        [Btn(t["b_about"], "about", P), Btn(t["b_credit"], "credit", P)],
        [Btn(t["b_contact"], "contact"), Btn(t["b_lang"], "lang:" + ("en" if lang_of(user) == "fa" else "fa"))],
    ])


async def screen_poets(update, t):
    await show(update, t["pick_poet"], [
        [Btn(t["b_hafez"], "poet:hafez", P), Btn(t["b_ferdowsi"], "poet:ferdowsi", P)],
        [Btn(t["b_molavi"], "poet:molavi", P), Btn(t["b_mix"], "poet:mix", P)],
        [Btn(t["b_menu"], "menu")],
    ])


async def screen_prompt_mode(update, t):
    await show(update, t["ask_prompt"], [
        [Btn(t["b_prompt_rnd"], "pm:rnd", S)],
        [Btn(t["b_prompt_own"], "pm:own")],
        [Btn(t["b_back"], "go:q")],
    ])


async def screen_about(update, t):
    await show(update, t["about"], [[Btn(t["b_tech"], "tech:0", P)], [Btn(t["b_menu"], "menu")]])


async def screen_tech(update, t, i):
    pages = t["tech"]
    i = max(0, min(i, len(pages) - 1))
    nav = []
    if i > 0:
        nav.append(Btn(t["b_prev"], f"tech:{i - 1}", P))
    if i < len(pages) - 1:
        nav.append(Btn(t["b_next"], f"tech:{i + 1}", P))
    await show(update, pages[i].format(contact=CONTACT), [nav, [Btn(t["b_about_back"], "about"), Btn(t["b_menu"], "menu")]])


def make_options(user):
    m = max_poems(user)
    opts = [n for n in (5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100) if n <= m]
    if not opts or (m not in opts and m < MAX_POEMS):
        opts.append(m)                       # "everything I can afford"
    return opts


async def screen_make(update, t, user):
    rows = chunk_rows([Btn(f"🏭 {n}", f"mk:{n}", P) for n in make_options(user)], 3)
    rows.append([Btn(t["b_back"], "go:prompt")])
    await show(update, t["ask_make"].format(credits=credits_text(user)), rows)


async def screen_top(update, t, make):
    opts = [n for n in (1, 2, 3, 5, 10) if n <= make] or [1]
    await show(update, t["ask_top"].format(make=make), [[Btn(f"🏆 {n}", f"top:{n}", S) for n in opts],
                                                         [Btn(t["b_back"], "go:make")]])


async def screen_kind_q(update, t, kind, w=None):
    """the question right after choosing a style: ghazal or not (Hafez), poem type (Mix), rhyme type (the others)"""
    w = w or {}
    if kind in ("molavi", "hafez"):               # (reached by the back button) there is no question for these two
        return await screen_poets(update, t)
    if kind == "mix" and w.get("mf") in (None, "gh"):
        return await show(update, t["ask_mixform"], [[Btn(t["b_mf_gh"], "mf:gh", S)], [Btn(t["b_mf_ms"], "mf:ms", P)],
                                                     [Btn(t["b_mf_all"], "mf:all", P)], [Btn(t["b_back"], "poem")]])
    if kind == "hafez":
        return await show(update, t["ask_ghazal"], [[Btn(t["b_ghazal_yes"], "gh:1", S), Btn(t["b_ghazal_no"], "gh:0")],
                                                    [Btn(t["b_back"], "poem")]])
    return await show(update, t["ask_pair"].format(label=t["label_" + kind]), [[Btn(t["b_pair_end"], "pair:0", P)],
                                                                              [Btn(t["b_pair_each"], "pair:1", P)],
                                                                              [Btn(t["b_back"], "go:mf" if kind == "mix" else "poem")]])


# ----------------------------------------------------------------------------- commands
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user)
    ev(user, "START" if not u["lang"] else "menu", "/start")
    save_users()
    context.user_data.clear()
    await sticker(context.bot, update.effective_chat.id, "welcome")
    if not u["lang"]:
        await screen_lang(update)
    else:
        await screen_menu(update, user)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ev(update.effective_user, "myid")
    await update.message.reply_text(f"🆔 <code>{update.effective_user.id}</code>", parse_mode=HTML)


async def grant(bot, admin_user, uid, n):
    """Give credits (capped at MAX_CREDITS) and notify the user. Returns (total, added) or None."""
    res = add_credit(uid, n)
    ev(admin_user, "ADD_CREDIT", f"to={uid} asked={n} result={res}")
    if res is None:
        return None
    total, added = res
    if added > 0:
        try:
            lang = core._users[str(uid)]["lang"] or "fa"
            await bot.send_message(uid, T[lang]["credit_added"].format(n=added, total=total), parse_mode=HTML)
        except Exception:
            pass
    return res


async def cmd_addcredit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    try:
        uid, n = int(context.args[0]), int(context.args[1])
    except Exception:
        await update.message.reply_text("usage: /addcredit <user_id> <amount>")
        return
    res = await grant(context.bot, user, uid, n)
    if res is None:
        await update.message.reply_text("❌ unknown user (they must press /start first)")
    else:
        await update.message.reply_text(f"✅ {uid}: +{res[1]} → {res[0]}" + (f"  (max {MAX_CREDITS})" if res[1] < n else ""))


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    us = core._users
    await update.message.reply_text(f"👥 users: {len(us)}\n📜 poems: {sum(x.get('poems', 0) for x in us.values())}\n"
                                    f"📁 files: {len(list(core.POEMS_DIR.glob('*.txt')))}")


async def on_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id) and update.message.sticker:
        await update.message.reply_text(f"sticker file_id:\n<code>{update.message.sticker.file_id}</code>", parse_mode=HTML)


# ----------------------------------------------------------------------------- credit request (user -> admin)
def admin_kb(uid):
    return Kb([[Btn("+10", f"ag:{uid}:10", S), Btn("+25", f"ag:{uid}:25", S), Btn("+50", f"ag:{uid}:50", S)],
               [Btn("+100", f"ag:{uid}:100", S), Btn("+200", f"ag:{uid}:200", S), Btn("+500", f"ag:{uid}:500", S)],
               [Btn("✏️ custom", f"ac:{uid}", P), Btn("❌ reject", f"ar:{uid}", D)]])


async def send_credit_request(bot, user):
    u = get_user(user)
    uname = f"@{user.username}" if user.username else "-"
    text = (f"🔔 <b>Credit request</b>\n\n👤 {esc(user.full_name)}  {esc(uname)}\n🆔 <code>{user.id}</code>\n"
            f"🪙 credits: <b>{u['credits']}</b>   📜 poems made: {u['poems']}   🌐 {u['lang'] or '-'}\n\n"
            f"Tap a button to give credits, or use custom for any amount:")
    sent = 0
    for aid in core.ADMIN_IDS:
        try:
            await bot.send_message(aid, text, parse_mode=HTML, reply_markup=admin_kb(user.id))
            sent += 1
        except Exception as e:
            LOG.error(f"could not message admin {aid}: {e!r}")
    return sent


async def admin_action(update, context, d):
    """ag:<uid>:<n> grant | ac:<uid> custom amount | ar:<uid> reject"""
    q, admin = update.callback_query, update.effective_user
    if not is_admin(admin.id):
        return
    parts = d.split(":")
    uid = int(parts[1])
    kind = parts[0]
    msg = q.message
    if kind == "ag":
        res = await grant(context.bot, admin, uid, int(parts[2]))
        line = "❌ unknown user" if res is None else (f"✅ +{res[1]} → total {res[0]}" if res[1] else f"⚠️ already at the max ({MAX_CREDITS})")
        await msg.edit_text(msg.text_html + f"\n{line}", parse_mode=HTML, reply_markup=admin_kb(uid))
    elif kind == "ac":
        context.user_data["adm_wait"] = uid
        await msg.reply_text(f"✏️ Send the number of credits for <code>{uid}</code> (1-{MAX_CREDITS}):", parse_mode=HTML)
    elif kind == "ar":
        await msg.edit_text(msg.text_html + "\n❌ rejected", parse_mode=HTML)
        ev(admin, "REJECT_CREDIT", str(uid))
        try:
            lang = core._users[str(uid)]["lang"] or "fa"
            await context.bot.send_message(uid, T[lang]["credit_denied"].format(contact=CONTACT))
        except Exception:
            pass


# ----------------------------------------------------------------------------- buttons
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user = update.effective_user
    u = get_user(user)
    d = q.data
    lang = u["lang"] or "fa"
    t = T[lang]

    if d == "cancel":                                    # stop a running / queued generation
        job = STATE["jobs"].get(user.id)
        ev(user, "button", "cancel")
        if job:
            job["cancel"].set()
            return await q.answer(t["cancelling"])
        return await q.answer()
    await q.answer()
    ev(user, "button", d)

    if d[:3] in ("ag:", "ac:", "ar:"):
        return await admin_action(update, context, d)
    if d.startswith("lang:"):
        u["lang"] = d[5:]
        save_users()
        return await screen_menu(update, user)

    w = context.user_data.setdefault("w", {})
    if d == "menu":
        w.clear()
        return await screen_menu(update, user)
    if d == "about":
        return await screen_about(update, t)
    if d.startswith("tech:"):
        return await screen_tech(update, t, int(d[5:]))
    if d == "contact":
        return await show(update, t["contact"].format(contact=CONTACT), [[Btn(t["b_menu"], "menu")]])
    if d == "credit":
        back = [[Btn(t["b_menu"], "menu")]]
        fmt = dict(credits=credits_text(user), contact=CONTACT, uid=user.id)
        if not core.ADMIN_IDS:
            return await show(update, t["credit_nofwd"].format(**fmt), back)
        if not can_request(user):
            return await show(update, t["credit_wait"].format(**fmt), back)
        sent = await send_credit_request(context.bot, user)
        ev(user, "CREDIT_REQUEST", f"delivered_to_admins={sent}")
        return await show(update, t["credit" if sent else "credit_nofwd"].format(**fmt), back)
    if d == "poem":
        w.clear()
        if not has_credit(user):
            ev(user, "NO_CREDIT")
            return await show(update, t["no_credit"], [[Btn(t["b_credit"], "credit", S)], [Btn(t["b_menu"], "menu")]])
        return await screen_poets(update, t)
    if d.startswith("poet:"):
        w.clear()
        w["kind"] = d[5:]
        if w["kind"] in ("molavi", "hafez"):      # no question: Molavi = masnavi, Hafez = ghazal -> straight to the prompt choice
            w["pair"] = True
            w["ghazal"] = True
            return await screen_prompt_mode(update, t)
        return await screen_kind_q(update, t, w["kind"], w)

    if "kind" not in w:                      # stale button (e.g. after a bot restart)
        return await screen_menu(update, user)

    if d.startswith("mf:"):
        w["mf"] = d[3:]
        if w["mf"] == "gh":
            w["pair"] = False
            return await screen_prompt_mode(update, t)
        return await screen_kind_q(update, t, w["kind"], w)
    if d == "go:mf":
        w.pop("mf", None)
        return await screen_kind_q(update, t, w["kind"], w)
    if d == "go:q":
        w["wait"] = False
        return await screen_kind_q(update, t, w["kind"], w)
    if d == "go:prompt":
        w["wait"] = False
        return await screen_prompt_mode(update, t)
    if d == "go:make":
        return await screen_make(update, t, user)
    if d.startswith("gh:"):
        w["ghazal"] = d[3:] == "1"
        return await screen_prompt_mode(update, t)
    if d.startswith("pair:"):
        w["pair"] = d[5:] == "1"
        return await screen_prompt_mode(update, t)
    if d == "pm:own":
        w["wait"] = True
        return await show(update, t["own_info"], [[Btn(t["b_prompt_rnd"], "pm:rnd", S)], [Btn(t["b_back"], "go:prompt")]])
    if d == "pm:rnd":
        w["wait"], w["first"] = False, ""
        return await screen_make(update, t, user)
    if d.startswith("mk:"):
        w["make"] = max(1, min(int(d[3:]), MAX_POEMS))
        return await screen_top(update, t, w["make"])
    if d.startswith("top:") and "make" in w:
        w["top"] = min(int(d[4:]), w["make"])
        return await launch(update, context, dict(w))
    if d == "again" and context.user_data.get("last"):
        return await launch(update, context, dict(context.user_data["last"]))
    return await screen_menu(update, user)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    uid = context.user_data.get("adm_wait")
    if uid and is_admin(user.id):                        # admin typed a custom credit amount
        if text.isdigit() and 1 <= int(text) <= MAX_CREDITS:
            context.user_data.pop("adm_wait")
            res = await grant(context.bot, user, uid, int(text))
            await update.message.reply_text("❌ unknown user" if res is None else f"✅ {uid}: +{res[1]} → total {res[0]}")
        else:
            await update.message.reply_text(f"Send a number between 1 and {MAX_CREDITS}.")
        return
    w = context.user_data.get("w", {})
    t = T[lang_of(user)]
    if not w.get("wait"):
        ev(user, "text(ignored)", text[:80])
        return await screen_menu(update, user)
    first, why = validate_prompt(text)
    ev(user, "own_prompt", f"{text!r} -> {'OK' if first else 'REJECTED ' + str(why)}")
    if not first:
        await update.message.reply_text(t["prompt_bad"].get(why, t["prompt_bad"]["not_text"]))
        return
    w["first"], w["wait"] = first, False
    await update.message.reply_text(t["prompt_ok"].format(first=esc(first)), parse_mode=HTML)
    await screen_make(update, t, user)


# ----------------------------------------------------------------------------- generation
async def launch(update, context, w):
    user = update.effective_user
    t = T[lang_of(user)]
    if context.user_data.get("busy"):
        return await update.callback_query.answer(t["busy"], show_alert=True)
    if not has_credit(user, w["make"]):
        return await show(update, t["no_credit"], [[Btn(t["b_credit"], "credit", S)], [Btn(t["b_menu"], "menu")]])
    context.user_data["busy"] = True
    context.user_data["last"] = dict(w)
    task = asyncio.create_task(run_generation(context.bot, update.effective_chat.id, update.callback_query.message, user, w, context.user_data))
    STATE["tasks"].add(task)
    task.add_done_callback(STATE["tasks"].discard)


async def safe_edit(msg, text, kb=None):
    try:
        await msg.edit_text(text, parse_mode=HTML, reply_markup=kb)
    except Exception:
        pass


def fmt_poem(i, p, t, label):
    meta = [label]
    if p["qaf"] not in ("", "-"):
        meta.append(f"{t['qaf']}: {p['qaf']}")
    if p["rad"] not in ("", "-"):
        meta.append(f"{t['rad']}: {p['rad']}")
    head = f"{EMOJI[(i - 1) % len(EMOJI)]} <b>{t['poem_n']} {i}</b>\n<i>{esc(' · '.join(meta))}</i>\n"
    chunks, cur = [], head
    for a, b in p["lines"]:
        piece = f"\n{esc(a)}\n{esc(b)}\n"
        if len(cur) + len(piece) > 3800:
            chunks.append(cur)
            cur = ""
        cur += piece
    chunks.append(cur)
    return chunks


async def run_generation(bot, chat_id, status, user, w, ud):
    lang = lang_of(user)
    t = T[lang]
    make, top = w["make"], w["top"]
    label = t["label_" + w["kind"]]
    out = TMP_DIR / f"{user.id}_{int(time.time())}.txt"
    cmd = build_cmd(w["kind"], make, top, w.get("ghazal", True), w.get("pair", True), w.get("first", ""), out, w.get("mf", ""), w.get("fs", 0))
    opts = {"style": w["kind"], "ghazal": w.get("ghazal", "-"), "pair-rhyme": w.get("pair", "-"), "mix type": w.get("mf", "-"), "story": w.get("fs", "-"),
            "prompt": w.get("first") or "(random)", "generate": make, "show top": top, "credits spent": make}
    cancel_kb = Kb([[Btn(t["b_cancel"], "cancel", D)]])
    end_kb = Kb([[Btn(t["b_new"], "poem", P), Btn(t["b_menu"], "menu")]])
    job = {"cancel": asyncio.Event()}
    STATE["jobs"][user.id] = job
    spend_credit(user, make)
    ev(user, "GENERATE_REQUEST", f"{opts}")
    ev(user, "command", cmd_text(cmd))
    t0 = time.time()
    prog = {"c": 0, "tail": ""}
    ticker = reader = None
    proc = None
    outcome = "ok"
    try:
        await safe_edit(status, t["working"].format(spin=SPIN[0], label=label, sec=0, c=0, n=make), cancel_kb)
        # ---- wait for our turn (or be cancelled while queued)
        STATE["waiting"] += 1
        if STATE["lock"].locked():
            await safe_edit(status, t["queued"].format(pos=STATE["waiting"]), cancel_kb)
        acq = asyncio.ensure_future(STATE["lock"].acquire())
        cn = asyncio.ensure_future(job["cancel"].wait())
        done, _ = await asyncio.wait({acq, cn}, return_when=asyncio.FIRST_COMPLETED)
        STATE["waiting"] -= 1
        if acq not in done:
            acq.cancel()
            outcome = "cancelled"
        else:
            cn.cancel()
            try:
                t0 = time.time()
                ev(user, "GENERATE_START")
                env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
                proc = await asyncio.create_subprocess_exec(*cmd, cwd=str(BASE), env=env,
                                                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)

                async def read_out():
                    while True:
                        chunk = await proc.stdout.read(512)
                        if not chunk:
                            break
                        s = chunk.decode("utf-8", "replace")
                        prog["tail"] = (prog["tail"] + s)[-3000:]
                        m = re.findall(r"candidate (\d+)/\d+", s)
                        if m:
                            prog["c"] = int(m[-1])

                async def tick():
                    i = 0
                    while True:
                        await safe_edit(status, t["working"].format(spin=SPIN[i % len(SPIN)], label=label, sec=int(time.time() - t0), c=prog["c"], n=make), cancel_kb)
                        try:
                            await bot.send_chat_action(chat_id, ChatAction.TYPING)
                        except Exception:
                            pass
                        i += 1
                        await asyncio.sleep(6)

                reader, ticker = asyncio.create_task(read_out()), asyncio.create_task(tick())
                pw = asyncio.ensure_future(proc.wait())
                cn2 = asyncio.ensure_future(job["cancel"].wait())
                done, _ = await asyncio.wait({pw, cn2}, timeout=gen_timeout(make), return_when=asyncio.FIRST_COMPLETED)
                if pw not in done:                      # cancelled by the user, or timed out
                    outcome = "cancelled" if cn2 in done else "timeout"
                    proc.kill()
                    await pw
                cn2.cancel()
                await reader
            finally:
                if ticker:
                    ticker.cancel()
                STATE["lock"].release()
        secs = time.time() - t0

        # ---- results
        if outcome == "cancelled":
            refund_credit(user, make)
            ev(user, "GENERATE_CANCELLED", f"after {secs:.0f}s")
            return await safe_edit(status, t["cancelled"], end_kb)
        poems = parse_output(out) if (outcome == "ok" and out.exists() and proc.returncode == 0) else []
        if not poems:
            refund_credit(user, make)
            ev(user, "GENERATE_FAILED", f"{outcome} rc={proc.returncode if proc else None} tail={prog['tail'][-600:]!r}")
            await sticker(bot, chat_id, "fail")
            return await safe_edit(status, t["timeout"] if outcome == "timeout" else t["failed"], end_kb)
        await sticker(bot, chat_id, "done")
        await safe_edit(status, t["done"].format(sec=int(secs)))
        for i, p in enumerate(poems, 1):
            for chunk in fmt_poem(i, p, t, label):
                await bot.send_message(chat_id, chunk, parse_mode=HTML)
            await asyncio.sleep(0.4)
        fname = save_request(user, lang, opts, cmd, poems, out, secs)
        ev(user, "GENERATE_DONE", f"{secs:.1f}s poems={len(poems)} saved={fname}")
        await bot.send_message(chat_id, t["after"], reply_markup=Kb([
            [Btn(t["b_again"], "again", S)],
            [Btn(t["b_new"], "poem", P), Btn(t["b_menu"], "menu")]]))
    except Exception as e:
        LOG.exception("generation crashed")
        refund_credit(user, make)
        ev(user, "GENERATE_CRASH", repr(e))
        await safe_edit(status, t["failed"], end_kb)
    finally:
        for task in (ticker, reader):
            if task and not task.done():
                task.cancel()
        if proc and proc.returncode is None:
            proc.kill()
        out.unlink(missing_ok=True)
        STATE["jobs"].pop(user.id, None)
        ud["busy"] = False


# ----------------------------------------------------------------------------- main
async def on_error(update, context):
    LOG.error(f"ERROR | {context.error!r}")


async def post_init(app):
    STATE["lock"] = asyncio.Lock()
    me = await app.bot.get_me()
    LOG.info(f"BOT STARTED | @{me.username} | proxy={'ON' if core.PROXY_URL else 'OFF'} | start_credits={core.START_CREDITS} "
             f"| admins={sorted(core.ADMIN_IDS)} | colors={'ON' if COLOR else 'OFF'}")


def main():
    if not core.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is empty. Put it in the .env file.")
    px = core.PROXY_URL or None
    app = (Application.builder().token(core.BOT_TOKEN)
           .request(HTTPXRequest(proxy=px, connect_timeout=30, read_timeout=30, write_timeout=30, pool_timeout=30))
           .get_updates_request(HTTPXRequest(proxy=px, connect_timeout=30, read_timeout=60, write_timeout=30, pool_timeout=30))
           .post_init(post_init).build())
    app.add_handler(CommandHandler(["start", "menu", "help"], cmd_start))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("addcredit", cmd_addcredit))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.Sticker.ALL, on_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    app.run_polling(drop_pending_updates=True)
    LOG.info("BOT STOPPED")


if __name__ == "__main__":
    main()
