# -*- coding: utf-8 -*-
"""
DevParser v1 - Telegram Bot (Telethon Edition)
Uses Telethon MTProto for native premium animated emoji support via <tg-emoji> tags
Bot owner MUST have Telegram Premium
"""
import os, sys, time, re, random, threading, queue, asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityCustomEmoji
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bot_engine import DorkEngine, COUNTRY_CODES
from bot_keys import (is_admin, generate_key, redeem_key, get_license, list_keys, ADMIN_IDS,
                      list_users, suspend_user, unsuspend_user, delete_user)

CONTACT = "@devtronex"

# ==================== CONFIG ====================
API_ID = int(os.environ.get("API_ID", "21124241"))          # Get from https://my.telegram.org/apps
API_HASH = os.environ.get("API_HASH", 'b7ddce3d3683f54be788fddae73fa468')
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8877962549:AAHSJDIc9CGim7bjGCk3iYZKtCmcDmrTve8")
# Telethon session dir (use a mounted volume dir on Railway for persistence)
SESSION_DIR = os.environ.get("BOT_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

# ==================== PREMIUM EMOJI IDs ====================
# Sourced from: CenterOfEmoji, TONEmoji, EVERYONExKSK, Iam_Hacker7 packs
PE = {
    "check": "5877684893722349121",       # ✅ CenterOfEmoji Vector Icon
    "fire": "5877531812497984738",        # 🔥 CenterOfEmoji Vector Icon
    "cross": "6151988941495997348",       # ❌ EVERYONExKSK
    "zap": "5879955595687103790",         # ⚡ CenterOfEmoji Vector Icon
    "money": "6154686984116769646",       # � EVERYONExKSK
    "globe": "6154314146595738391",       # 🌐 EVERYONExKSK
    "target": "5461009483314517035",      # 🎯 TONEmoji
    "robot": "6154506501001057160",       # �‍💻 EVERYONExKSK Developer
    "crown": "6235252066554484059",       # 👑 Iam_Hacker7
    "pause": "6242510612824332116",       # 🕐 Iam_Hacker7 Clock
    "play": "6235307467337635626",        # ⏩ Iam_Hacker7 Fast Forward
    "stop": "6192475150064034649",        # ⛔ Iam_Hacker7 No Entry
    "chart": "5203993413346680064",       # 📊 TONEmoji
    "package": "5879926634722626804",     # 💼 CenterOfEmoji Briefcase
    "clipboard": "6154222749691679144",   # 📋 EVERYONExKSK
    "refresh": "6154226958759628850",     # 🔄 EVERYONExKSK
    "rocket": "5188481279963715781",      # 🚀 TONEmoji
    "warning": "6242010768825391425",     # ⚠️ Iam_Hacker7
    "gem": "5877751010448903974",         # 💎 CenterOfEmoji
    "upload": "6235373579769222419",      # ➡ Iam_Hacker7 Arrow Right
    "download": "6235234890980269200",    # ↪ Iam_Hacker7 Return Arrow
    "settings": "5877548425431486558",    # 🔧 CenterOfEmoji Wrench
    "like": "6147698410901214769",        # � Iam_Hacker7 Thumbs Up
    "bell": "6154195867491373457",        # 🔔 EVERYONExKSK
    "bulb": "5877478400284692055",        # ✨ CenterOfEmoji Sparkles
    "search": "6154626644121228293",      # 🔍 EVERYONExKSK
    "key": "6154565990593073474",         # 🔓 EVERYONExKSK Unlock
    "lock": "6154387470277414903",        # 🔒 EVERYONExKSK
    "trash": "5879475774825696887",       # � CenterOfEmoji Prohibited
    "info": "5879651065325949080",        # ❓ CenterOfEmoji Question
    "star": "6235403472741603087",        # ⭐ Iam_Hacker7
    "folder": "6154222749691679144",      # 📋 EVERYONExKSK (as folder)
    "file": "6154233835002271015",        # ✏ EVERYONExKSK Pencil
    "link": "5440410042773824003",        # 🔗 TONEmoji
    "pin": "6237585097084638739",         # 📌 Iam_Hacker7
    "hammer": "5877548425431486558",      # 🔧 CenterOfEmoji Wrench
    "back": "6235234890980269200",        # ↪ Iam_Hacker7 Return Arrow
    "home": "6237757385402752314",        # 🏡 Iam_Hacker7 Home
    "satellite": "5879997647711899401",   # ✈ CenterOfEmoji Airplane
    "battery": "6154329144621535496",     # 🔋 EVERYONExKSK
    "bug": "6237775175157292231",         # 🐍 Iam_Hacker7 Snake
    "dork": "6154380594034775608",        # 🧠 EVERYONExKSK Brain
    "sparkles": "5877478400284692055",    # ✨ CenterOfEmoji
    "gear": "5877548425431486558",        # 🔧 CenterOfEmoji
    "shield": "6154387470277414903",      # 🔒 EVERYONExKSK Lock
    "chart_up": "5298614648138919107",    # 📈 TONEmoji Chart Up
    "megaphone": "6154718341672997377"    # 📣 EVERYONExKSK
}

def pe(text):
    """Replace Unicode emojis with <tg-emoji> tags for premium custom emojis.
    Uses the same approach as the working Shopiii bot."""
    if not text: return text
    mapping = {
        "✅": PE["check"], "🔥": PE["fire"], "❌": PE["cross"], "⚡": PE["zap"],
        "💰": PE["money"], "🌐": PE["globe"], "🎯": PE["target"], "🤖": PE["robot"],
        "👑": PE["crown"], "⏸️": PE["pause"], "▶️": PE["play"], "🛑": PE["stop"],
        "📊": PE["chart"], "📦": PE["package"], "📋": PE["clipboard"],
        "🔄": PE["refresh"], "🚀": PE["rocket"], "⚠️": PE["warning"],
        "💎": PE["gem"], "📤": PE["upload"], "📥": PE["download"],
        "⚙️": PE["settings"], "👍": PE["like"], "🔔": PE["bell"],
        "💡": PE["bulb"], "🔍": PE["search"], "🔑": PE["key"],
        "🔒": PE["lock"], "🗑": PE["trash"], "ℹ️": PE["info"],
        "⭐": PE["star"], "📁": PE["folder"], "📄": PE["file"],
        "🔗": PE["link"], "📌": PE["pin"], "🔨": PE["hammer"],
        "🔙": PE["back"], "🏠": PE["home"], "🛰": PE["satellite"],
        "🔋": PE["battery"], "🐛": PE["bug"], "🧠": PE["dork"],
        "✨": PE["sparkles"], "🛡": PE["lock"], "🔓": PE["lock"],
        "❤": PE["fire"], "❓": PE["info"], "📝": PE["clipboard"],
        "📢": PE["bell"], "💬": PE["info"], "⏹": PE["stop"],
        "⏰": PE["pause"], "📅": PE["clipboard"], "♻": PE["refresh"],
        "💻": PE["robot"], "🌍": PE["globe"],
    }
    result = text
    # Use placeholders to avoid double-replacement
    phs = []
    for i, (emoji, doc_id) in enumerate(mapping.items()):
        ph = f"\x00PE{i:02d}\x00"
        phs.append((ph, doc_id, emoji))
        result = result.replace(emoji, ph)
    for ph, doc_id, emoji in phs:
        result = result.replace(ph, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

# ==================== BOT SETUP ====================
bot = TelegramClient(os.path.join(SESSION_DIR, 'devparser_bot'), API_ID, API_HASH).start(bot_token=BOT_TOKEN)
_bot_loop = bot.loop  # Main event loop reference for thread-safe calls

# ----- Thread-safe coroutine scheduling -----
def _safe_edit(chat_id, msg_id, text, buttons=None):
    """Schedule edit_message from any thread. Won't block."""
    async def _do():
        try:
            await bot.edit_message(chat_id, msg_id, text, buttons=buttons, parse_mode='html')
        except Exception as e:
            print(f"[safe_edit] {e}")
    _bot_loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_do()))

def _safe_send(chat_id, text):
    """Schedule send_message from any thread."""
    async def _do():
        try:
            await bot.send_message(chat_id, text, parse_mode='html')
        except Exception as e:
            print(f"[safe_send] {e}")
    _bot_loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_do()))

user_states = {}
user_engines = {}

def get_engine(uid):
    if uid not in user_engines:
        user_engines[uid] = DorkEngine()
        user_engines[uid].output_file = f"results_{uid}"
        user_engines[uid].output_ext = ".txt"
        user_engines[uid].search_engine = "yahoojp"   # default engine
        user_engines[uid].proxy_protocol = "all"       # default protocol
    return user_engines[uid]

def get_state(uid):
    if uid not in user_states:
        user_states[uid] = {}
    return user_states[uid]

def fmt(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)

# ==================== KEYBOARD BUILDERS ====================

def main_buttons(uid=None):
    btns = [
        [Button.inline("▶️ Start Parsing", b"menu_start_parse"),
         Button.inline("📤 Upload Dorks", b"menu_upload_dorks")],
        [Button.inline("🌐 Proxy Manager", b"menu_proxies"),
         Button.inline("⚙️ Settings", b"menu_settings")],
        [Button.inline("📊 View Results", b"menu_results"),
         Button.inline("🔑 License", b"menu_license")],
        [Button.inline("ℹ️ Info", b"menu_info"),
         Button.inline("❓ Help", b"menu_help")],
    ]
    if is_admin(uid):
        btns.append([Button.inline("🛠 Generate Key", b"admin_genkey"),
                     Button.inline("👥 Users", b"usr_list")])
    return btns

def proxy_buttons():
    return [
        [Button.inline("🛰 Scrape Free Proxies", b"proxy_scrape"),
         Button.inline("📤 Upload Proxy File", b"proxy_upload")],
        [Button.inline("🔍 Test Proxies", b"proxy_test"),
         Button.inline("🗑 Clear Proxies", b"proxy_clear")],
        [Button.inline("📊 Proxy Status", b"proxy_status")],
        [Button.inline("🔙 Back", b"menu_home")],
    ]

def engine_buttons():
    btns = []
    row = []
    for eng, label in [("google","Google"), ("bing","Bing"), ("yahoojp","YahooJP"),
                       ("duckduckgo","DDG"), ("brave","Brave"), ("startpage","Startpage"),
                       ("all","ALL 6")]:
        row.append(Button.inline(f"🌐 {label}", f"eng_{eng}".encode()))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([Button.inline("🔙 Back", b"menu_settings")])
    return btns

def settings_buttons():
    return [
        [Button.inline("🌐 Search Engine", b"settings_engine"),
         Button.inline("📄 Pages per Dork", b"settings_pages")],
        [Button.inline("⚡ Threads", b"settings_threads"),
         Button.inline("🎯 Country Filter", b"settings_country")],
        [Button.inline("🔋 Auto-Scrape", b"settings_autoscrape"),
         Button.inline("🛰 Protocol", b"settings_protocol")],
        [Button.inline("🔨 Filters", b"settings_filters"),
         Button.inline("📥 Output", b"settings_output")],
        [Button.inline("🔙 Back", b"menu_home")],
    ]

def country_buttons(page=0):
    countries = list(COUNTRY_CODES.items())
    per_page = 8
    start = page * per_page
    chunk = countries[start:start + per_page]
    btns = []
    row = []
    for code, name in chunk:
        row.append(Button.inline(f"{name} ({code.upper()})", f"country_{code}".encode()))
        if len(row) == 2:
            btns.append(row); row = []
    if row: btns.append(row)
    nav = []
    if page > 0: nav.append(Button.inline("◀ Prev", f"country_page_{page-1}".encode()))
    if start + per_page < len(countries): nav.append(Button.inline("Next ▶", f"country_page_{page+1}".encode()))
    if nav: btns.append(nav)
    btns.append([Button.inline("🔙 Back", b"menu_settings")])
    return btns

def proto_buttons():
    btns = []
    row = []
    for v, l in [("http","HTTP"), ("socks4","SOCKS4"), ("socks5","SOCKS5"), ("all","ALL"), ("none","NONE")]:
        row.append(Button.inline(f"🛰 {l}", f"proto_{v}".encode()))
        if len(row) == 3: btns.append(row); row = []
    if row: btns.append(row)
    btns.append([Button.inline("🔙 Back", b"menu_settings")])
    return btns

# ==================== COMMANDS ====================

@bot.on(events.NewMessage(pattern='/start'))
async def cmd_start(event):
    uid = event.sender_id
    get_engine(uid); get_state(uid)
    lic = get_license(uid)
    lic_line = "👑 <b>Admin</b>" if lic.get("admin") else (
        "✅ <b>Licensed</b>" if lic.get("valid") else "🔒 <b>No license</b> — get a free key")
    txt = pe(f"🚀 <b>DevParser v1</b> 🚀\n\n"
             f"Welcome, <b>{event.sender.first_name}</b>!\n"
             f"I convert Google Dorks into targeted URLs.\n\n"
             f"⚡ <b>Features:</b>\n"
             f"🌐 6 Search Engines\n"
             f"🛰 Auto Proxy Scrape + Country\n"
             f"⚙️ Smart Filters + Dedup\n"
             f"📄 Export results as file\n\n"
             f"🔑 Status: {lic_line}\n\n"
             f"✨ <b>Coming in DevParser v2:</b>\n"
             f"🧠 Built-in Keyword & Dork Making\n\n"
             f"💬 This bot is <b>completely FREE for a limited time</b>.\n"
             f"Get your license key from {CONTACT}\n"
             f"ℹ️ Use the menu or /help")
    await event.reply(txt, buttons=main_buttons(uid), parse_mode='html')

def _help_text(uid):
    admin_extra = ""
    if is_admin(uid):
        admin_extra = ("\n<b>Admin:</b>\n"
                       "/genkey [days] — generate a license key (default 30, 0 = lifetime)\n"
                       "/keys — list generated keys\n"
                       "/users — list key holders (suspend/delete via buttons)\n"
                       "/suspend <id> — suspend a user (kills their key)\n"
                       "/unsuspend <id> — re-activate a user\n"
                       "/delete <id> — permanently delete user + key\n")
    return pe(f"❓ <b>DevParser v1 — Help</b>\n\n"
              f"<b>Quick Start:</b>\n"
              f"1️⃣ Get a free license key from {CONTACT}, then send it here (or /redeem KEY)\n"
              f"2️⃣ 📤 Upload your dork file (one dork per line)\n"
              f"3️⃣ 🌐 Proxy Manager → Scrape / Upload proxies (default protocol: ALL)\n"
              f"4️⃣ ⚙️ Settings → pick engine (default: YahooJP), threads, pages, filters\n"
              f"5️⃣ ▶️ Start Parsing → live progress → 📊 Download results\n\n"
              f"<b>Engines:</b> Google, Bing, YahooJP, DuckDuckGo, Brave, Startpage, or ALL\n"
              f"<b>Proxies:</b> HTTP / SOCKS4 / SOCKS5 / ALL / NONE (proxyless)\n\n"
              f"<b>Commands:</b>\n"
              f"/start — main menu\n"
              f"/license — your license & account info\n"
              f"/redeem KEY — activate a license key\n"
              f"/info — bot & account info\n"
              f"/settings /proxies /results /status /stop\n"
              f"{admin_extra}\n"
              f"⚠️ Free proxies = 30-50% success. YahooJP/DDG block less than Google.\n\n"
              f"✨ <b>Coming in v2:</b> keyword & dork making inside the bot!\n"
              f"💬 Questions? Contact {CONTACT}")

@bot.on(events.NewMessage(pattern='/help'))
async def cmd_help(event):
    await event.reply(_help_text(event.sender_id), buttons=main_buttons(event.sender_id), parse_mode='html')

def _license_text(uid, sender):
    lic = get_license(uid)
    name = (sender.first_name or "") + ((" " + sender.last_name) if getattr(sender, "last_name", None) else "")
    uname = f"@{sender.username}" if getattr(sender, "username", None) else "—"
    header = "🔑 <b>License / Account</b>\n\n"
    body = (f"👤 Name: <b>{name or '—'}</b>\n"
            f"🆔 Username: <b>{uname}</b>\n"
            f"🆔 User ID: <code>{uid}</code>\n")
    if lic.get("admin"):
        body += "👑 License: <b>ADMIN (lifetime)</b>\n"
    elif lic.get("valid"):
        if lic.get("lifetime"):
            body += "✅ License: <b>ACTIVE — LIFETIME</b>\n"
        else:
            exp = datetime.fromtimestamp(lic["expiry"]).strftime("%Y-%m-%d %H:%M")
            body += (f"✅ License: <b>ACTIVE</b>\n"
                     f"⏰ Expires: <b>{exp}</b> ({lic.get('days_left',0)} days left)\n")
        if lic.get("key"):
            body += f"🗝 Key: <code>{lic['key']}</code>\n"
    else:
        body += (f"🔒 License: <b>NOT ACTIVE</b>\n\n"
                 f"{lic.get('message','')}\n"
                 f"Send your key here or use /redeem KEY\n")
    body += f"\n💬 Get a FREE key / support: {CONTACT}"
    return pe(header + body)

@bot.on(events.NewMessage(pattern='/license'))
async def cmd_license(event):
    await event.reply(_license_text(event.sender_id, event.sender), buttons=main_buttons(event.sender_id), parse_mode='html')

def _info_text(uid, sender):
    lic = get_license(uid)
    if lic.get("admin"):
        status = "👑 Admin (lifetime)"
    elif lic.get("valid"):
        status = "✅ Licensed — LIFETIME" if lic.get("lifetime") else f"✅ Licensed — {lic.get('days_left',0)} days left"
    else:
        status = "🔒 Not licensed"
    return pe(f"ℹ️ <b>DevParser v1 — Info</b>\n\n"
              f"🤖 <b>Bot:</b> Google Dork → URL parser\n"
              f"🌐 6 engines • 🛰 auto proxy scrape • ⚙️ smart filters\n\n"
              f"👤 <b>Your account:</b>\n"
              f"Name: <b>{sender.first_name or '—'}</b>\n"
              f"Username: <b>{('@'+sender.username) if getattr(sender,'username',None) else '—'}</b>\n"
              f"License: <b>{status}</b>\n\n"
              f"💎 <b>Completely FREE for a limited time.</b>\n"
              f"Get your license key from {CONTACT}\n\n"
              f"✨ <b>Coming in DevParser v2:</b>\n"
              f"🧠 Keyword & Dork Making inside the bot\n\n"
              f"💬 Any questions? Message {CONTACT}")

@bot.on(events.NewMessage(pattern='/info'))
async def cmd_info(event):
    await event.reply(_info_text(event.sender_id, event.sender), buttons=main_buttons(event.sender_id), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'/genkey'))
async def cmd_genkey(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe("🔒 Admin only.")); return
    parts = event.text.split()
    days = 30
    if len(parts) > 1:
        try: days = int(parts[1])
        except: days = 30
    key = generate_key(days)
    dur = "LIFETIME" if days <= 0 else f"{days} days"
    await event.reply(pe(f"🗝 <b>New Key Generated</b>\n\n"
                         f"<code>{key}</code>\n\n"
                         f"⏰ Valid: <b>{dur}</b> (after redeem)\n"
                         f"Share it. User redeems with /redeem or by sending it."),
                      parse_mode='html')

@bot.on(events.NewMessage(pattern=r'/keys'))
async def cmd_keys(event):
    if not is_admin(event.sender_id):
        await event.reply(pe("🔒 Admin only.")); return
    ks = list_keys()
    if not ks:
        await event.reply(pe("📭 No keys generated yet.")); return
    lines = []
    for k in ks[-30:]:
        used = f"used by {k['redeemed_by']}" if k['redeemed_by'] else "free"
        d = "life" if k['days'] <= 0 else f"{k['days']}d"
        lines.append(f"<code>{k['key']}</code> — {d} — {used}")
    await event.reply(pe("🗝 <b>Keys</b>\n\n" + "\n".join(lines)), parse_mode='html')

# ---------- Admin: user management ----------
_STATUS_ICON = {"active": "✅", "suspended": "⛔", "expired": "⌛"}

def _users_view():
    users = list_users()
    if not users:
        return pe("📭 <b>No users yet.</b>\nUsers appear here only after they redeem a key."), None
    lines = ["👥 <b>Users</b> (only key holders)\n"]
    btns = []
    for u in users[:25]:
        uname = f"@{u['username']}" if u['username'] else (u['name'] or u['user_id'])
        icon = _STATUS_ICON.get(u['status'], "•")
        lines.append(f"{icon} <b>{uname}</b>\n   🗝 <code>{u['key']}</code> — {u['status']}")
        uid_b = u['user_id'].encode()
        if u['status'] == "suspended":
            row = [Button.inline(f"♻ Unsuspend {uname[:10]}", b"usr_unsusp_" + uid_b)]
        else:
            row = [Button.inline(f"⛔ Suspend {uname[:10]}", b"usr_susp_" + uid_b)]
        row.append(Button.inline("🗑 Delete", b"usr_del_" + uid_b))
        btns.append(row)
    btns.append([Button.inline("🔄 Refresh", b"usr_list")])
    return pe("\n".join(lines)), btns

@bot.on(events.NewMessage(pattern=r'/users'))
async def cmd_users(event):
    if not is_admin(event.sender_id):
        await event.reply(pe("🔒 Admin only.")); return
    txt, btns = _users_view()
    await event.reply(txt, buttons=btns, parse_mode='html')

@bot.on(events.NewMessage(pattern=r'/suspend'))
async def cmd_suspend(event):
    if not is_admin(event.sender_id):
        await event.reply(pe("🔒 Admin only.")); return
    parts = event.text.split()
    if len(parts) < 2:
        await event.reply(pe("Usage: /suspend <user_id>")); return
    r = suspend_user(parts[1].strip())
    await event.reply(pe(f"{'⛔' if r['ok'] else '❌'} {r['message']}"
                         + (f"\n🗝 Key affected: <code>{r.get('key','')}</code>" if r['ok'] else "")),
                      parse_mode='html')

@bot.on(events.NewMessage(pattern=r'/unsuspend'))
async def cmd_unsuspend(event):
    if not is_admin(event.sender_id):
        await event.reply(pe("🔒 Admin only.")); return
    parts = event.text.split()
    if len(parts) < 2:
        await event.reply(pe("Usage: /unsuspend <user_id>")); return
    r = unsuspend_user(parts[1].strip())
    await event.reply(pe(f"{'♻' if r['ok'] else '❌'} {r['message']}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'/delete'))
async def cmd_delete(event):
    if not is_admin(event.sender_id):
        await event.reply(pe("🔒 Admin only.")); return
    parts = event.text.split()
    if len(parts) < 2:
        await event.reply(pe("Usage: /delete <user_id>  (permanent, also kills the key)")); return
    r = delete_user(parts[1].strip())
    await event.reply(pe(f"{'🗑' if r['ok'] else '❌'} {r['message']}"
                         + (f"\n🗝 Key deleted: <code>{r.get('key','')}</code>" if r['ok'] else "")),
                      parse_mode='html')

@bot.on(events.NewMessage(pattern=r'/redeem'))
async def cmd_redeem(event):
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2:
        await event.reply(pe("Usage: /redeem YOUR-KEY\nOr just send the key.")); return
    await _do_redeem(event, parts[1].strip())

async def _do_redeem(event, key):
    s = event.sender
    uname = s.username or ""
    name = (s.first_name or "") + ((" " + s.last_name) if getattr(s, "last_name", None) else "")
    res = redeem_key(key, event.sender_id, name, uname)
    if res.get("ok"):
        if res.get("expiry", 0) == 0:
            msg = "✅ <b>License activated — LIFETIME!</b>"
        else:
            exp = datetime.fromtimestamp(res["expiry"]).strftime("%Y-%m-%d %H:%M")
            msg = f"✅ <b>License activated!</b>\n⏰ Expires: <b>{exp}</b>"
        await event.reply(pe(msg), buttons=main_buttons(event.sender_id), parse_mode='html')
    else:
        await event.reply(pe(f"❌ {res.get('message','Invalid key')}\n💬 Need a key? {CONTACT}"),
                          parse_mode='html')

# ==================== CALLBACK HANDLER ====================

@bot.on(events.CallbackQuery())
async def on_callback(event):
    uid = event.sender_id
    data = event.data.decode() if isinstance(event.data, bytes) else event.data
    engine = get_engine(uid)
    state = get_state(uid)

    try:
        if data == "menu_home":
            await event.edit(pe("🤖 <b>Main Menu</b>"), buttons=main_buttons(uid), parse_mode='html')

        elif data == "menu_proxies":
            alive = engine.get_alive_proxies()
            total = len(engine.raw_proxies)
            txt = pe(f"🌐 <b>Proxy Manager</b>\n\n"
                     f"🛰 Protocol: <b>{engine.proxy_protocol.upper()}</b>\n"
                     f"🎯 Country: <b>{engine.country.upper()}</b>\n"
                     f"🔋 Auto: <b>{'ON' if engine.auto_scrape else 'OFF'}</b>\n"
                     f"📊 Proxies: <b>{alive} alive / {total} total</b>")
            await event.edit(txt, buttons=proxy_buttons(), parse_mode='html')

        elif data == "menu_settings":
            txt = pe(f"⚙️ <b>Settings</b>\n\n"
                     f"🌐 Engine: <b>{engine.search_engine.upper()}</b>\n"
                     f"📄 Pages/Dork: <b>{engine.pages_per_dork}</b>\n"
                     f"⚡ Threads: <b>{engine.threads}</b>\n"
                     f"🎯 Country: <b>{engine.country.upper()}</b>\n"
                     f"🔋 Auto-Scrape: <b>{'ON' if engine.auto_scrape else 'OFF'}</b>\n"
                     f"🛰 Protocol: <b>{engine.proxy_protocol.upper()}</b>\n"
                     f"🔨 PF: <b>{'ON' if engine.param_filter else 'OFF'}</b> | "
                     f"DD: <b>{'ON' if engine.domain_dedup else 'OFF'}</b> | "
                     f"AP: <b>{'ON' if engine.antipublic else 'OFF'}</b>")
            await event.edit(txt, buttons=settings_buttons(), parse_mode='html')

        elif data == "menu_start_parse":
            if not engine.dorks:
                await event.edit(pe("❌ <b>No dorks!</b> Upload first."), buttons=main_buttons(), parse_mode='html')
                return
            alive = engine.get_alive_proxies()
            total_p = len(engine.raw_proxies)
            txt = pe(f"▶️ <b>Ready to Parse</b>\n\n"
                     f"🧠 Dorks: <b>{fmt(len(engine.dorks))}</b>\n"
                     f"🌐 Engine: <b>{engine.search_engine.upper()}</b>\n"
                     f"🌐 Proxies: <b>{alive} alive / {total_p} total</b>\n\n"
                     f"⚠️ Click START to begin.")
            btns = [
                [Button.inline("▶️ START PARSING", b"parse_start")],
                [Button.inline("⚡ START (Proxyless)", b"parse_start_noproxy")],
                [Button.inline("🔙 Back", b"menu_home")],
            ]
            await event.edit(txt, buttons=btns, parse_mode='html')

        elif data == "menu_upload_dorks":
            state['waiting_for'] = 'dorks'
            await event.edit(pe("📤 <b>Send dork file (.txt)</b>\nOne dork per line."),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_home")]], parse_mode='html')

        elif data == "menu_results":
            fname = f"{engine.output_file}{engine.output_ext}"
            if os.path.exists(fname):
                size = os.path.getsize(fname)
                with open(fname, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                txt = pe(f"📊 <b>Results</b>\n\n🔗 URLs: <b>{fmt(lines)}</b>\n📥 Size: <b>{size/1024:.1f} KB</b>")
                btns = [
                    [Button.inline("📥 Download Results", b"results_download")],
                    [Button.inline("🗑 Clear Results", b"results_clear")],
                    [Button.inline("🔙 Back", b"menu_home")],
                ]
            else:
                txt = pe("❌ <b>No results yet!</b>")
                btns = [[Button.inline("🔙 Back", b"menu_home")]]
            await event.edit(txt, buttons=btns, parse_mode='html')

        elif data == "menu_license":
            await cmd_license(event)

        elif data == "menu_info":
            await cmd_info(event)

        elif data == "admin_genkey":
            if not is_admin(uid):
                await event.answer(pe("🔒 Admin only")); return
            key = generate_key(30)
            await event.answer(pe("🗝 Key generated!"))
            await event.reply(pe(f"🗝 <b>New Key (30 days)</b>\n\n<code>{key}</code>\n\n"
                                 f"Send /genkey [days] for custom duration."), parse_mode='html')

        elif data == "usr_list" or data.startswith("usr_susp_") or data.startswith("usr_unsusp_") or data.startswith("usr_del_"):
            if not is_admin(uid):
                await event.answer(pe("🔒 Admin only")); return
            if data.startswith("usr_susp_"):
                r = suspend_user(data[len("usr_susp_"):]); await event.answer(pe(r['message']))
            elif data.startswith("usr_unsusp_"):
                r = unsuspend_user(data[len("usr_unsusp_"):]); await event.answer(pe(r['message']))
            elif data.startswith("usr_del_"):
                r = delete_user(data[len("usr_del_"):]); await event.answer(pe(r['message']))
            else:
                await event.answer(pe("🔄 Refreshed"))
            txt, btns = _users_view()
            await event.edit(txt, buttons=btns, parse_mode='html')

        elif data == "menu_help":
            await cmd_help(event)

        # ── PROXY ──

        elif data == "proxy_scrape":
            await event.answer(pe("🛰 Scraping proxies..."))
            await event.edit(pe("🛰 <b>Scraping proxies...</b>\n📥 Found: <b>0</b>"),
                             buttons=[[Button.inline("🔙 Back", b"menu_proxies")]], parse_mode='html')
            def do():
                engine.proxy_protocol = engine.proxy_protocol or "http"
                stop = threading.Event()
                def progress():
                    last = -1
                    while not stop.is_set():
                        time.sleep(1)
                        c = getattr(engine, '_scraping_count', 0)
                        if c != last:
                            last = c
                            _safe_edit(event.chat_id, event.message_id,
                                pe(f"🛰 <b>Scraping proxies...</b>\n📥 Found: <b>{c}</b>"),
                                buttons=[[Button.inline("🔙 Back", b"menu_proxies")]])
                threading.Thread(target=progress, daemon=True).start()
                count = engine.scrape_proxies(engine.proxy_protocol)
                stop.set()
                _safe_edit(event.chat_id, event.message_id,
                    pe(f"✅ <b>Scraped {fmt(count)} proxies!</b>\n🎯 Country: {engine.country.upper()}"),
                    buttons=proxy_buttons())
            threading.Thread(target=do, daemon=True).start()

        elif data == "proxy_upload":
            state['waiting_for'] = 'proxy_file'
            await event.edit(pe("📤 <b>Send proxy file (.txt)</b>\nip:port format."),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_proxies")]], parse_mode='html')

        elif data == "proxy_test":
            if not engine.raw_proxies:
                await event.answer(pe("❌ No proxies!")); return
            await event.answer(pe("🔍 Testing..."))
            total = len(engine.raw_proxies)
            await event.edit(pe(f"🔍 <b>Testing proxies...</b>\n📊 Tested: <b>0/{min(total,5000)}</b> | ✅ Alive: <b>0</b>"),
                             buttons=[[Button.inline("🔙 Back", b"menu_proxies")]], parse_mode='html')
            def do():
                stop = threading.Event()
                def progress():
                    lt = la = -1
                    while not stop.is_set():
                        time.sleep(1)
                        t = getattr(engine, '_tested_count', 0)
                        a = getattr(engine, '_tested_alive', 0)
                        if t != lt or a != la:
                            lt, la = t, a
                            _safe_edit(event.chat_id, event.message_id,
                                pe(f"🔍 <b>Testing proxies...</b>\n📊 Tested: <b>{t}/{min(total,5000)}</b> | ✅ Alive: <b>{a}</b>"),
                                buttons=[[Button.inline("🔙 Back", b"menu_proxies")]])
                threading.Thread(target=progress, daemon=True).start()
                engine.test_all_proxies()
                stop.set()
                alive = engine.get_alive_proxies()
                _safe_edit(event.chat_id, event.message_id,
                    pe(f"✅ <b>Tested! {alive} alive.</b>"),
                    buttons=proxy_buttons())
            threading.Thread(target=do, daemon=True).start()

        elif data == "proxy_clear":
            engine.raw_proxies = []; engine.dead_proxies = set(); engine.proxies_from_file = False
            await event.edit(pe("🗑 <b>Proxies cleared!</b>"), buttons=proxy_buttons(), parse_mode='html')

        elif data == "proxy_status":
            alive = engine.get_alive_proxies(); total = len(engine.raw_proxies)
            pct = int(alive/total*100) if total > 0 else 0
            await event.edit(pe(f"📊 <b>Proxy Status</b>\nTotal: {total} | Alive: {alive} | {pct}%"),
                             buttons=proxy_buttons(), parse_mode='html')

        # ── SETTINGS ──

        elif data == "settings_engine":
            await event.edit(pe(f"🌐 <b>Select Engine</b>\nCurrent: <b>{engine.search_engine.upper()}</b>"),
                             buttons=engine_buttons(), parse_mode='html')

        elif data.startswith("eng_"):
            eng = data[4:]; engine.search_engine = eng
            await event.answer(pe(f"✅ Engine: {eng.upper()}"))
            await event.edit(pe(f"✅ Engine: <b>{eng.upper()}</b>"), buttons=engine_buttons(), parse_mode='html')

        elif data == "settings_pages":
            state['waiting_for'] = 'pages'
            await event.edit(pe(f"📄 <b>Pages per Dork</b>\nCurrent: <b>{engine.pages_per_dork}</b>\nSend 1-10:"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_settings")]], parse_mode='html')

        elif data == "settings_threads":
            state['waiting_for'] = 'threads'
            await event.edit(pe(f"⚡ <b>Threads</b>\nCurrent: <b>{engine.threads}</b>\nSend 10-300:"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_settings")]], parse_mode='html')

        elif data == "settings_country":
            await event.edit(pe(f"🎯 <b>Country Filter</b>\nCurrent: <b>{engine.country.upper()}</b>"),
                             buttons=country_buttons(), parse_mode='html')

        elif data.startswith("country_"):
            code = data[8:]; engine.country = code; engine.raw_proxies = []; engine.dead_proxies = set()
            await event.answer(pe(f"✅ Country: {code.upper()}"))
            await event.edit(pe(f"✅ Country: <b>{COUNTRY_CODES.get(code, code.upper())}</b>"),
                             buttons=country_buttons(), parse_mode='html')

        elif data.startswith("country_page_"):
            page = int(data.split("_")[-1])
            await event.edit(pe("🎯 <b>Country Filter</b>"), buttons=country_buttons(page), parse_mode='html')

        elif data == "settings_autoscrape":
            engine.auto_scrape = not engine.auto_scrape
            await event.answer(pe(f"🔋 Auto-Scrape: {'ON' if engine.auto_scrape else 'OFF'}"))
            await event.edit(pe(f"🔋 Auto-Scrape: <b>{'ON' if engine.auto_scrape else 'OFF'}</b>"),
                             buttons=settings_buttons(), parse_mode='html')

        elif data == "settings_protocol":
            await event.edit(pe(f"🛰 <b>Protocol</b>\nCurrent: <b>{engine.proxy_protocol.upper()}</b>"),
                             buttons=proto_buttons(), parse_mode='html')

        elif data.startswith("proto_"):
            val = data[6:]; engine.proxy_protocol = val
            await event.answer(pe(f"✅ Protocol: {val.upper()}"))
            await event.edit(pe(f"✅ Protocol: <b>{val.upper()}</b>"), buttons=proto_buttons(), parse_mode='html')

        elif data == "settings_filters":
            btns = []
            for name, attr in [("Parameter Filter","param_filter"),("Domain Dedup","domain_dedup"),("Antipublic","antipublic")]:
                val = getattr(engine, attr)
                btns.append([Button.inline(f"{'✅' if val else '❌'} {name}", f"filter_{attr}".encode())])
            btns.append([Button.inline("🔙 Back", b"menu_settings")])
            await event.edit(pe("🔨 <b>Filters</b>"), buttons=btns, parse_mode='html')

        elif data.startswith("filter_"):
            attr = data[7:]; setattr(engine, attr, not getattr(engine, attr))
            btns = []
            for name, attr2 in [("Parameter Filter","param_filter"),("Domain Dedup","domain_dedup"),("Antipublic","antipublic")]:
                val = getattr(engine, attr2)
                btns.append([Button.inline(f"{'✅' if val else '❌'} {name}", f"filter_{attr2}".encode())])
            btns.append([Button.inline("🔙 Back", b"menu_settings")])
            await event.edit(pe("🔨 <b>Filters</b>"), buttons=btns, parse_mode='html')

        elif data == "settings_output":
            state['waiting_for'] = 'output'
            await event.edit(pe(f"📥 <b>Output Format</b>\nCurrent: <b>{engine.output_ext}</b>\nSend .txt, .csv etc:"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_settings")]], parse_mode='html')

        # ── PARSE ──

        elif data in ("parse_start", "parse_start_noproxy"):
            if not get_license(uid).get("valid"):
                await event.answer(pe("🔒 License required"))
                await event.edit(pe(f"🔒 <b>License required to parse!</b>\n\n"
                                     f"This bot is <b>FREE for a limited time</b>.\n"
                                     f"Get your key from {CONTACT}, then send it here."),
                                  buttons=main_buttons(uid), parse_mode='html'); return
            if not engine.dorks:
                await event.answer(pe("❌ No dorks!")); return
            if data == "parse_start_noproxy":
                engine.proxy_protocol = "none"
            state['running'] = True
            await event.answer(pe("🚀 Starting parser!"))
            eng_label = "ALL" if engine.search_engine == "all" else engine.search_engine.upper()
            await event.edit(
                pe(f"🚀 <b>PARSING STARTING...!</b>\n🧠 {fmt(len(engine.dorks))} dorks | {eng_label} | Threads: {engine.threads}"),
                buttons=[[Button.inline("🛑 STOP", b"parse_stop")]], parse_mode='html'
            )

            def run_parser():
                try:
                    if engine.get_alive_proxies() == 0 and engine.proxy_protocol != "none":
                        _safe_edit(event.chat_id, event.message_id,
                            pe("🛰 <b>No proxies! Auto-scraping...</b>"),
                            buttons=[[Button.inline("🛑 STOP", b"parse_stop")]])
                        engine.auto_scrape = True
                        engine.scrape_proxies(engine.proxy_protocol)

                    outfile = f"{engine.output_file}{engine.output_ext}"
                    with open(outfile, 'w', encoding='utf-8') as f: pass
                    engine.results = set(); engine.filtered = set(); engine.dorks_done = 0
                    engine.start_time = time.time(); engine.running = True; engine.dead_proxies = set()
                    engine._stop_writer = False; engine._write_queue = queue.Queue()
                    engine._writer_thread = threading.Thread(target=engine._writer_loop, daemon=True)
                    engine._writer_thread.start()

                    total = len(engine.dorks); chunk = engine.chunk_size; last_update = [0]

                    def update_status():
                        while state.get('running'):
                            time.sleep(3)
                            if not state.get('running'): break
                            d = engine.dorks_done
                            if d == last_update[0]: continue
                            last_update[0] = d
                            res = len(engine.results); alive = engine.get_alive_proxies()
                            eta = engine.get_eta()
                            m, sd = divmod(int(eta), 60); h, mm = divmod(m, 60); dpm = engine.get_dpm()
                            try:
                                txt = pe(f"▶️ <b>Parsing...</b>\n\n"
                                         f"🧠 Progress: <b>{d}/{total}</b>\n"
                                         f"🔗 URLs: <b>{fmt(res)}</b>\n"
                                         f"⏰ ETA: <b>{h:02d}:{mm:02d}:{sd:02d}</b>\n"
                                         f"⚡ Speed: <b>{dpm:.0f} d/m</b>\n"
                                         f"🛰 Proxies: <b>{alive}</b>")
                                _safe_edit(event.chat_id, event.message_id, txt,
                                    buttons=[[Button.inline("🛑 STOP", b"parse_stop")]])
                            except Exception as ex:
                                print(f"[update_status] Error: {ex}")

                    threading.Thread(target=update_status, daemon=True).start()
                    import gc
                    for cs in range(0, total, chunk):
                        if not state.get('running'): break
                        ce = min(cs + chunk, total); cdorks = engine.dorks[cs:ce]
                        executor = ThreadPoolExecutor(max_workers=engine.threads)
                        futs = {executor.submit(engine._search_dork, d): d for d in cdorks}
                        for f in as_completed(futs):
                            try:
                                f.result()
                            except Exception as ferr:
                                print(f"[parser] dork error: {ferr}")
                            if not state.get('running'):
                                for t in futs: t.cancel(); break
                        executor.shutdown(wait=True)
                        if cs > 0 and cs % (chunk * 3) == 0: gc.collect()

                    engine.running = False; engine._stop_writer = True; engine._write_queue.put(None)
                    if engine._writer_thread and engine._writer_thread.is_alive():
                        engine._writer_thread.join(timeout=5)
                    del state['running']
                    res = len(engine.results)
                    _safe_send(uid, pe(f"✅ <b>COMPLETE!</b>\n🔗 <b>{fmt(res)}</b> URLs.\n/results to download."))
                except Exception as e:
                    import traceback, sys; print(f"[PARSER] CRASH: {e}"); sys.stdout.flush(); traceback.print_exc(); sys.stdout.flush()
                    try: _safe_send(uid, pe(f"❌ <b>Parser error:</b> {e}"))
                    except: pass

            threading.Thread(target=run_parser, daemon=True).start()

        elif data == "parse_stop":
            state['running'] = False; engine.stop()
            await event.answer(pe("🛑 Stopped!"))
            await event.edit(pe(f"🛑 <b>STOPPED!</b>\n🔗 {fmt(len(engine.results))} URLs."),
                             buttons=main_buttons(), parse_mode='html')

        # ── RESULTS ──

        elif data == "results_download":
            fname = f"{engine.output_file}{engine.output_ext}"
            if os.path.exists(fname):
                await bot.send_file(uid, fname, caption=pe("📥 Results"))
                await event.answer(pe("✅ File sent!"))
            else:
                await event.answer(pe("❌ No file!"))

        elif data == "results_clear":
            fname = f"{engine.output_file}{engine.output_ext}"
            if os.path.exists(fname): os.remove(fname)
            engine.results = set(); engine.filtered = set()
            await event.edit(pe("🗑 <b>Cleared!</b>"), buttons=main_buttons(), parse_mode='html')

    except Exception as e:
        try: await event.answer(f"Error: {str(e)[:50]}")
        except: pass

# ==================== MESSAGE HANDLERS ====================

@bot.on(events.NewMessage(func=lambda e: e.file and not e.text))
async def handle_file(event):
    uid = event.sender_id; state = get_state(uid); engine = get_engine(uid)
    waiting = state.get('waiting_for', '')
    if waiting not in ('dorks', 'proxy_file'):
        await event.reply(pe("ℹ️ Use menu to upload."), buttons=main_buttons(), parse_mode='html'); return
    try:
        path = await event.download_media()
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        os.remove(path)
        if waiting == 'dorks':
            engine.dorks = [l.strip() for l in content.split('\n') if l.strip()]
            txt = pe(f"✅ <b>{fmt(len(engine.dorks))}</b> dorks loaded!")
        else:
            engine.raw_proxies = [l.strip() for l in content.split('\n') if l.strip() and ':' in l]
            engine.dead_proxies = set(); engine.proxies_from_file = True
            txt = pe(f"✅ <b>{fmt(len(engine.raw_proxies))}</b> proxies loaded!")
        state.pop('waiting_for', None)
        await event.reply(txt, buttons=main_buttons(), parse_mode='html')
    except Exception as e:
        await event.reply(pe(f"❌ Error: {e}"))

@bot.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))
async def handle_text(event):
    uid = event.sender_id; state = get_state(uid); engine = get_engine(uid)
    text = event.text.strip(); waiting = state.get('waiting_for', '')
    # Auto-redeem if the message looks like a license key
    if re.match(r'(?i)^DPV1-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}$', text):
        await _do_redeem(event, text); return
    if not waiting:
        await event.reply(pe("🤖 Use menu:"), buttons=main_buttons(uid), parse_mode='html'); return
    try:
        if waiting == 'dorks':
            engine.dorks = [l.strip() for l in text.split('\n') if l.strip()]
            state.pop('waiting_for', None)
            await event.reply(pe(f"✅ <b>{fmt(len(engine.dorks))}</b> dorks loaded!"), buttons=main_buttons(), parse_mode='html')
        elif waiting == 'pages':
            v = int(text)
            if 1 <= v <= 10: engine.pages_per_dork = v; state.pop('waiting_for', None)
            else: await event.reply(pe("❌ Enter 1-10.")); return
            await event.reply(pe(f"✅ Pages: <b>{v}</b>"), buttons=settings_buttons(), parse_mode='html')
        elif waiting == 'threads':
            v = int(text)
            if 10 <= v <= 300: engine.threads = v; state.pop('waiting_for', None)
            else: await event.reply(pe("❌ Enter 10-300.")); return
            await event.reply(pe(f"✅ Threads: <b>{v}</b>"), buttons=settings_buttons(), parse_mode='html')
        elif waiting == 'output':
            ext = text if text.startswith('.') else f".{text}"; engine.output_ext = ext
            state.pop('waiting_for', None)
            await event.reply(pe(f"✅ Output: <b>{ext}</b>"), buttons=settings_buttons(), parse_mode='html')
        elif waiting == 'proxy_file':
            engine.raw_proxies = [l.strip() for l in text.split('\n') if l.strip() and ':' in l]
            engine.dead_proxies = set(); engine.proxies_from_file = True
            state.pop('waiting_for', None)
            await event.reply(pe(f"✅ <b>{fmt(len(engine.raw_proxies))}</b> proxies!"), buttons=proxy_buttons(), parse_mode='html')
        else: state.pop('waiting_for', None)
    except ValueError:
        await event.reply(pe("❌ Invalid number."))

# ==================== QUICK COMMANDS ====================

@bot.on(events.NewMessage(pattern='/settings'))
async def cmd_settings(event):
    engine = get_engine(event.sender_id)
    txt = pe(f"⚙️ <b>Settings</b>\n\n"
             f"🌐 Engine: <b>{engine.search_engine.upper()}</b>\n"
             f"📄 Pages/Dork: <b>{engine.pages_per_dork}</b>\n"
             f"⚡ Threads: <b>{engine.threads}</b>\n"
             f"🎯 Country: <b>{engine.country.upper()}</b>\n"
             f"🔋 Auto: <b>{'ON' if engine.auto_scrape else 'OFF'}</b>\n"
             f"🛰 Protocol: <b>{engine.proxy_protocol.upper()}</b>")
    await event.reply(txt, buttons=settings_buttons(), parse_mode='html')

@bot.on(events.NewMessage(pattern='/proxies'))
async def cmd_proxies(event):
    engine = get_engine(event.sender_id)
    alive = engine.get_alive_proxies(); total = len(engine.raw_proxies)
    txt = pe(f"🌐 <b>Proxy Manager</b>\n🛰 Protocol: <b>{engine.proxy_protocol.upper()}</b>\n"
             f"🎯 Country: <b>{engine.country.upper()}</b>\n"
             f"📊 Proxies: <b>{alive} alive / {total} total</b>")
    await event.reply(txt, buttons=proxy_buttons(), parse_mode='html')

@bot.on(events.NewMessage(pattern='/results'))
async def cmd_results(event):
    engine = get_engine(event.sender_id)
    fname = f"{engine.output_file}{engine.output_ext}"
    if os.path.exists(fname):
        await bot.send_file(event.chat_id, fname, caption=pe("📥 Results"))
    else:
        await event.reply(pe("❌ No results yet."))

@bot.on(events.NewMessage(pattern='/status'))
async def cmd_status(event):
    uid = event.sender_id; engine = get_engine(uid); state = get_state(uid)
    if state.get('running'):
        d, t = engine.dorks_done, len(engine.dorks); r = len(engine.results)
        dpm = engine.get_dpm(); eta = engine.get_eta()
        m, s = divmod(int(eta), 60); h, mm = divmod(m, 60)
        txt = pe(f"▶️ <b>RUNNING</b>\n🧠 {d}/{t} | 🔗 {fmt(r)} URLs | ⚡ {dpm:.0f} d/m | ETA: {h:02d}:{mm:02d}:{s:02d}")
    else:
        txt = pe(f"🛑 <b>IDLE</b>\n🧠 {fmt(len(engine.dorks))} dorks | 🔗 {fmt(len(engine.results))} URLs")
    await event.reply(txt, parse_mode='html')

@bot.on(events.NewMessage(pattern='/stop'))
async def cmd_stop(event):
    uid = event.sender_id; get_state(uid)['running'] = False; get_engine(uid).stop()
    await event.reply(pe("🛑 <b>Parser stopped!</b>"), parse_mode='html')

# ==================== START ====================

if __name__ == "__main__":
    print(f"🚀 DevParser v1 Bot (Telethon Edition)")
    print(f"🤖 Token: {'SET' if BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else 'NOT SET'}")
    print(f"💎 Premium Emojis: {len(PE)} IDs mapped (Telethon <tg-emoji> mode)")
    print(f"👑 Admins: {ADMIN_IDS}")
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("=" * 50)
        print("SETUP:")
        print("1. Create bot at @BotFather -> get token")
        print("2. Set BOT_TOKEN in tg_bot.py")
        print("3. Get API_ID & API_HASH from https://my.telegram.org/apps")
        print("4. Bot owner MUST have Telegram Premium")
        print("5. pip install telethon aiohttp aiofiles")
        print("6. python tg_bot.py")
        print("=" * 50)
        sys.exit(0)
    print("Bot polling started...")
    bot.run_until_disconnected()
