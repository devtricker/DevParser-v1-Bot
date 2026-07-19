# -*- coding: utf-8 -*-
"""
DevParser v1 - Telegram Bot (Telethon Edition)
Uses Telethon MTProto for native premium animated emoji support via <tg-emoji> tags
Bot owner MUST have Telegram Premium
"""
import os, sys, time, re, random, threading, queue, asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityCustomEmoji
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bot_engine import DorkEngine, COUNTRY_CODES
from bot_keys import (is_admin, generate_key, redeem_key, get_license, list_keys, ADMIN_IDS,
                      list_users, suspend_user, unsuspend_user, delete_user)
from kw_engine import clean_keywords, KWScraper, LANGUAGES as KW_LANGUAGES, COUNTRIES as KW_COUNTRIES
from vuln_engine import VulnScanner, dump_database

CONTACT = "@devtronex"

# ==================== CONFIG ====================
API_ID = int(os.environ.get("API_ID", "21124241"))          # Get from https://my.telegram.org/apps
API_HASH = os.environ.get("API_HASH", 'b7ddce3d3683f54be788fddae73fa468')
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8869647573:AAEBQfRqJaQv0Sdes_IgRlUQwqsivDb6HFk")
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

# ==================== DORK GENERATOR SESSION ====================
DEFAULT_KEYWORDS = [
    "shopping", "checkout", "cart", "payment", "shop", "store", "buy", "purchase", "order", 
    "account", "billing", "invoice", "delivery", "shipping", "discount", "deals", "coupon", 
    "sale", "products", "catalog", "categories", "brand", "login", "register", "signup", 
    "profile", "member", "subscription", "dashboard", "tracking", "rewards", "loyalty", 
    "offer", "item", "items", "gift", "donate", "donation", "voucher", "wallet", "credit", 
    "debit", "receipt", "refund", "registration", "renew", "signin",
    "credit-card", "shopping-cart", "add-to-cart", "buy-now", "place-order", 
    "payment-gateway", "order-history", "track-order"
]
DEFAULT_EXTENSIONS = [".php?", ".asp?", ".aspx?", ".jsp?", ".cfm?", ".html?", ".htm?"]
DEFAULT_PARAMETERS = [
    "id=", "page=", "cat=", "pid=", "cid=", "ref=", "type=", "view=", "mode=", "action=", 
    "lang=", "p=", "detail=", "show=", "list=", "search=", "q=", "s=", "sort=", "filter=", 
    "status=", "key=", "code=", "token="
]
DEFAULT_DOMAINS = [
    ".com", ".net", ".org", ".co.in", ".co.uk", ".shop", ".online", ".store", 
    ".edu", ".gov", ".in", ".us", ".uk", ".pk", ".ae"
]

import json

class DorkSession:
    def __init__(self, uid):
        self.uid = uid
        self.keywords = list(DEFAULT_KEYWORDS)
        self.extensions = list(DEFAULT_EXTENSIONS)
        self.parameters = list(DEFAULT_PARAMETERS)
        self.domain_targeting = False
        self.target_domains = [".com"] 
        self.custom_domains = []
        self.custom_formats = []
        self.multi_op = False
        self.format = "url:"
        self.load()
    def load(self):
        try:
            with open(f"dork_session_{self.uid}.json", "r") as f:
                d = json.load(f)
            self.keywords = d.get("kw", self.keywords); self.extensions = d.get("ext", self.extensions); self.parameters = d.get("param", self.parameters)
            self.domain_targeting = d.get("dom_t", self.domain_targeting); self.target_domains = d.get("tdom", self.target_domains)
            self.custom_domains = d.get("cdom", self.custom_domains); self.custom_formats = d.get("cfmt", self.custom_formats)
            self.multi_op = d.get("mop", self.multi_op); self.format = d.get("fmt", self.format)
        except: pass
    def save(self):
        try:
            with open(f"dork_session_{self.uid}.json", "w") as f:
                json.dump({"kw": self.keywords, "ext": self.extensions, "param": self.parameters, "dom_t": self.domain_targeting, "tdom": self.target_domains, "cdom": self.custom_domains, "cfmt": self.custom_formats, "mop": self.multi_op, "fmt": self.format}, f)
        except: pass

def get_dork_session(uid):
    st = get_state(uid)
    if 'dork_session' not in st:
        st['dork_session'] = DorkSession(uid)
    return st['dork_session']

# ==================== KW CLEANER / SCRAPER SESSION ====================
class KWCleanerSession:
    def __init__(self):
        self.split_1word = True
        self.split_2word = True
        self.remove_dupes = True
        self.remove_nums = True
        self.remove_short = True
        self.ai_filter = True
        self.min_len = 3
        self.cleaned_data = []
    def toggle(self, attr):
        setattr(self, attr, not getattr(self, attr))
        return getattr(self, attr)

class KWScraperSession:
    def __init__(self):
        self.seeds = ["shopping", "checkout", "payment"]
        self.lang_name = "English"
        self.lang_code = "en"
        self.country_name = "United States"
        self.country_code = "us"
        self.depth = 1
        self.scraper = None
        self.scrape_running = False
        self.scraped_keywords = set()

def get_kw_cleaner(uid):
    st = get_state(uid)
    if 'kw_cleaner' not in st:
        st['kw_cleaner'] = KWCleanerSession()
    return st['kw_cleaner']

def get_kw_scraper(uid):
    st = get_state(uid)
    if 'kw_scraper' not in st:
        st['kw_scraper'] = KWScraperSession()
    return st['kw_scraper']

# ==================== VULN SCANNER SESSION ====================
class VulnSession:
    def __init__(self):
        self.threads = 50
        self.proxy = None
        self.scanner = None
        self.scanning = False
        self.vuln_urls = []  # URLs to scan
        self.results = {}

def get_vuln_session(uid):
    st = get_state(uid)
    if 'vuln_session' not in st:
        st['vuln_session'] = VulnSession()
    return st['vuln_session']

# ==================== DB DUMP SESSION ====================
class DumpSession:
    def __init__(self):
        self.urls = []  # List of (url, param) tuples from vuln results
        self.dumping = False
        self.results = {}  # {url: dump_data}

def get_dump_session(uid):
    st = get_state(uid)
    if 'dump_session' not in st:
        st['dump_session'] = DumpSession()
    return st['dump_session']

# ==================== KEY GEN SESSION ====================
class KeyGenSession:
    def __init__(self):
        self.days = 0
        self.hours = 0
        self.mins = 0
        self.qty = 1
        self.step = "type"  # type, amount, confirm

def get_keygen(uid):
    st = get_state(uid)
    if 'keygen' not in st:
        st['keygen'] = KeyGenSession()
    return st['keygen']

def must_license(uid):
    """Return True if licensed, False if not. Use in handlers."""
    return get_license(uid).get("valid")

async def reject_unlicensed(event, uid):
    await event.answer(pe("🔒 License required!"))
    await event.edit(pe(f"🔒 <b>License Required!</b>\n\n<b>🔑 GET LICENSE FROM {CONTACT}</b>"),
                     buttons=main_buttons(uid), parse_mode='html')

def build_keygen_type():
    return [
        [Button.inline("📅 Days", b"kg_type_d"), Button.inline("⏰ Hours", b"kg_type_h")],
        [Button.inline("⏱ Minutes", b"kg_type_m")],
        [Button.inline("🔙 Cancel", b"menu_home")],
    ]

def build_keygen_amount(kg):
    unit = {"d": "Days", "h": "Hours", "m": "Minutes"}
    u = kg.step.split("_")[1] if "_" in kg.step else "d"
    label = unit.get(u, "Days")
    presets = {"d": [1, 3, 7, 15, 30, 60, 90, 365], 
               "h": [1, 3, 6, 12, 24, 48, 72],
               "m": [5, 10, 15, 30, 45, 60, 120, 180]}
    btns = []
    vals = presets.get(u, presets["d"])
    row = []
    for v in vals:
        row.append(Button.inline(f"{v} {label}", f"kg_amt_{u}_{v}".encode()))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([Button.inline("0 = Lifetime", f"kg_amt_{u}_0".encode()), 
                 Button.inline("✏️ Custom", f"kg_custom_{u}".encode())])
    btns.append([Button.inline("🔙 Back", b"admin_genkey")])
    return btns

def build_keygen_qty(kg):
    btns = []
    row = []
    for q in [1, 3, 5, 10, 15, 20]:
        row.append(Button.inline(f"x{q}", f"kg_qty_{q}".encode()))
        if len(row) == 3: btns.append(row); row = []
    if row: btns.append(row)
    btns.append([Button.inline("✏️ Custom", b"kg_custom_qty")])
    btns.append([Button.inline("🔙 Back", f"kg_type_{kg.get_type()}".encode())])
    return btns

def build_keygen_confirm(kg):
    dur = kg.format_duration()
    return [
        [Button.inline(f"✅ Generate {kg.qty} key(s) - {dur}", b"kg_do")],
        [Button.inline("🔄 Change Duration", f"kg_type_{kg.get_type()}".encode()),
         Button.inline("🔄 Change Qty", "kg_change_qty")],
        [Button.inline("🔙 Cancel", b"admin_genkey")],
    ]

def get_type_char(kg):
    if kg.days > 0: return "d"
    if kg.hours > 0: return "h"
    if kg.mins > 0: return "m"
    return "d"

# Add format_duration and get_type methods
KeyGenSession.format_duration = lambda self: (
    f"{self.days}d {self.hours}h {self.mins}m" if (self.days and self.hours) or (self.days and self.mins) or (self.hours and self.mins)
    else f"{self.days} Days" if self.days > 0
    else f"{self.hours} Hours" if self.hours > 0
    else f"{self.mins} Minutes" if self.mins > 0
    else "LIFETIME"
)

KeyGenSession.get_type = lambda self: (
    "d" if self.days > 0 else "h" if self.hours > 0 else "m" if self.mins > 0 else "d"
)

# ==================== KEYBOARD BUILDERS ====================

def main_buttons(uid=None):
    btns = [
        [Button.inline("▶️ Start Parsing", b"menu_start_parse"),
         Button.inline("📤 Upload Dorks", b"menu_upload_dorks")],
        [Button.inline("🧠 Gen Dorks", b"menu_dork_gen"),
         Button.inline("🧹 KW Cleaner", b"menu_kw_cleaner")],
        [Button.inline("🔍 KW Scraper", b"menu_kw_scraper"),
         Button.inline("🛡 Vuln Scanner", b"menu_vuln")],
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

def build_dump_dash(ds):
    sc = ds.dumping
    return [
        [Button.inline(f"📥 Load Vuln URLs ({len(ds.urls)})", b"dump_load")],
        [Button.inline("▶️ START DUMP" if not sc else "⏹ STOP DUMP", b"dump_start" if not sc else b"dump_stop")],
        [Button.inline("📤 Download Dump", b"dump_download"),
         Button.inline("📊 Status", b"dump_status")],
        [Button.inline("🔙 Back", b"menu_home")],
    ]

def build_dork_dash():
    return [
        [Button.inline("🔑 Keywords", b"dork_edit_kw"), Button.inline("📁 Extensions", b"dork_edit_ext")],
        [Button.inline("⚙️ Parameters", b"dork_edit_param"), Button.inline("🔗 Format", b"dork_edit_fmt")],
        [Button.inline("🌐 Domain Target", b"dork_edit_dom"), Button.inline("🔀 Multi-Op", b"dork_toggle_mop")],
        [Button.inline("🚀 GENERATE DORKS", b"dork_generate")],
        [Button.inline("🔙 Main Menu", b"menu_home")]
    ]

def build_dork_list(t):
    return [
        [Button.inline("👀 View Current (File)", f"dork_view_{t}".encode()), Button.inline("🗑 Clear All", f"dork_clear_{t}".encode())],
        [Button.inline("📤 Upload TXT", f"dork_upload_{t}".encode()), Button.inline("🔄 Reset Default", f"dork_reset_{t}".encode())],
        [Button.inline("📥 Load from KW Cleaner", b"dork_load_cleaner"), Button.inline("🔍 Load from Scraper", b"dork_load_scraper")],
        [Button.inline("🔙 Back to Dashboard", b"menu_dork_gen")]
    ]

def build_dork_dom(session, page=0):
    kb = []
    st = "🟢 ON" if session.domain_targeting else "🔴 OFF"
    kb.append([Button.inline(f"Domain Targeting: {st}", b"dork_toggle_dom")])
    row = []
    for d in DEFAULT_DOMAINS:
        mark = "✅" if d in session.target_domains else "❌"
        row.append(Button.inline(f"{mark} {d}", f"dork_tdom_{d}".encode()))
        if len(row) == 3: kb.append(row); row = []
    if row: kb.append(row)
    
    if session.custom_domains:
        kb.append([Button.inline("--- Custom Domains ---", b"noop")])
        start = page * 9
        chunk = session.custom_domains[start:start+9]
        row = []
        for d in chunk:
            mark = "✅" if d in session.target_domains else "❌"
            row.append(Button.inline(f"{mark} {d}", f"dork_tdom_{d}".encode()))
            if len(row) == 3: kb.append(row); row = []
        if row: kb.append(row)
        nav = []
        if page > 0: nav.append(Button.inline("◀ Prev", f"dork_dompage_{page-1}".encode()))
        if start + 9 < len(session.custom_domains): nav.append(Button.inline("Next ▶", f"dork_dompage_{page+1}".encode()))
        if nav: kb.append(nav)
        
    kb.append([Button.inline("➕ Add Custom Domain", b"dork_add_cdom"), Button.inline("🗑 Clear Custom", b"dork_clear_cdom")])
    kb.append([Button.inline("🔙 Back to Dashboard", b"menu_dork_gen")])
    return kb

def build_dork_fmt(session):
    formats = [
        ("inurl:", "inurl:"), 
        ("intitle:", "intitle:"), 
        ("intext:", "intext:"), 
        ("url: (recommend for yahojp)", "url:")
    ]
    kb = []
    for label, val in formats:
        mark = "✅" if session.format == val else "🔗"
        kb.append([Button.inline(f"{mark} {label}", f"dork_fmt_{val}".encode())])
    for c in session.custom_formats:
        mark = "✅" if session.format == c else "🔗"
        kb.append([Button.inline(f"{mark} {c}", f"dork_fmt_{c}".encode())])
    kb.append([Button.inline("➕ Add Custom Format", b"dork_add_fmt"), Button.inline("🗑 Clear Custom", b"dork_clear_fmt")])
    kb.append([Button.inline("🔙 Back", b"menu_dork_gen")])
    return kb

def build_kw_cleaner(cs):
    """Build KW Cleaner dashboard with toggle options"""
    def mk(val, label):
        return f"{'✅' if val else '❌'} {label}"
    return [
        [Button.inline(mk(cs.split_1word, "Split to 1-word"), b"kwc_split1"),
         Button.inline(mk(cs.split_2word, "Split to 2-word"), b"kwc_split2")],
        [Button.inline(mk(cs.remove_dupes, "Remove Duplicates"), b"kwc_dupes"),
         Button.inline(mk(cs.remove_nums, "Remove Numbers"), b"kwc_nums")],
        [Button.inline(mk(cs.remove_short, f"Remove Short (< {cs.min_len})"), b"kwc_short"),
         Button.inline(mk(cs.ai_filter, "AI Validate (Shopping)"), b"kwc_ai")],
        [Button.inline(f"🔢 Min Length: {cs.min_len}", b"kwc_minlen"),
         Button.inline("📥 Load Keywords", b"kwc_load")],
        [Button.inline("⚡ PROCESS NOW", b"kwc_process")],
        [Button.inline("📤 Download Cleaned", b"kwc_download"),
         Button.inline("🧠 Send to Dork Gen", b"kwc_send_dorkgen")],
        [Button.inline("🗑 Clear", b"kwc_clear"),
         Button.inline("🔙 Back", b"menu_home")],
    ]

def build_kw_scraper(ss):
    """Build KW Scraper dashboard"""
    running = ss.scrape_running
    return [
        [Button.inline(f"🌍 Lang: {ss.lang_name}", b"kws_lang"),
         Button.inline(f"📍 Country: {ss.country_name}", b"kws_country")],
        [Button.inline(f"📏 Depth: {ss.depth}", b"kws_depth"),
         Button.inline("✏️ Edit Seeds", b"kws_seeds")],
        [Button.inline("▶️ START SCRAPING", b"kws_start") if not running else
         Button.inline("⏹ STOP SCRAPING", b"kws_stop")],
        [Button.inline(f"📊 Kw: {len(ss.scraped_keywords)}", b"noop")],
        [Button.inline("📤 Download Results", b"kws_download"),
         Button.inline("📋 Copy All", b"kws_copy")],
        [Button.inline("🧹 Send to Cleaner", b"kws_send_cleaner"),
         Button.inline("🧠 Send to Dork Gen", b"kws_send_dorkgen")],
        [Button.inline("🗑 Clear", b"kws_clear"),
         Button.inline("🔙 Back", b"menu_home")],
    ]

def build_kw_lang_page(ss, page=0):
    per = 8
    start = page * per
    chunk = KW_LANGUAGES[start:start+per]
    btns = []
    row = []
    for name, code in chunk:
        mark = "✅" if ss.lang_code == code else ""
        row.append(Button.inline(f"{mark} {name}".strip(), f"kws_lang_{code}".encode()))
        if len(row) == 2: btns.append(row); row = []
    if row: btns.append(row)
    nav = []
    if page > 0: nav.append(Button.inline("◀ Prev", f"kws_langpage_{page-1}".encode()))
    if start + per < len(KW_LANGUAGES): nav.append(Button.inline("Next ▶", f"kws_langpage_{page+1}".encode()))
    if nav: btns.append(nav)
    btns.append([Button.inline("🔙 Back", b"menu_kw_scraper")])
    return btns

def build_vuln_dash(vs):
    sc = vs.scanning
    th = f"⚡ Threads: {vs.threads}" if not sc else f"🔍 Scanning..."
    return [
        [Button.inline(f"📥 Load URLs ({len(vs.vuln_urls)})", b"vuln_load"),
         Button.inline(th, b"vuln_threads")],
        [Button.inline(f"🛰 Proxy: {'ON' if vs.proxy else 'OFF'}", b"vuln_proxy"),
         Button.inline("📊 Results", b"vuln_results")],
        [Button.inline("▶️ START SCAN", b"vuln_start") if not sc else
         Button.inline("⏹ STOP SCAN", b"vuln_stop")],
        [Button.inline("📤 Download Report", b"vuln_report"),
         Button.inline("👀 Live Results", b"vuln_see")],
        [Button.inline("🔙 Back", b"menu_home")],
    ]

def build_kw_country_page(ss, page=0):
    per = 8
    start = page * per
    chunk = KW_COUNTRIES[start:start+per]
    btns = []
    row = []
    for name, code in chunk:
        mark = "✅" if ss.country_code == code else ""
        row.append(Button.inline(f"{mark} {name}".strip(), f"kws_cty_{code}".encode()))
        if len(row) == 2: btns.append(row); row = []
    if row: btns.append(row)
    nav = []
    if page > 0: nav.append(Button.inline("◀ Prev", f"kws_ctypage_{page-1}".encode()))
    if start + per < len(KW_COUNTRIES): nav.append(Button.inline("Next ▶", f"kws_ctypage_{page+1}".encode()))
    if nav: btns.append(nav)
    btns.append([Button.inline("🔙 Back", b"menu_kw_scraper")])
    return btns


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
        "✅ <b>Licensed</b>" if lic.get("valid") else "🔒 <b>No license</b> — get a key")
    txt = pe(f"🚀 <b>DevParser v2</b> 🚀\n\n"
             f"Welcome, <b>{event.sender.first_name}</b>!\n"
             f"I convert Google Dorks into targeted URLs.\n\n"
             f"⚡ <b>Features:</b>\n"
             f"🌐 6 Search Engines\n"
             f"🛰 Auto Proxy Scrape + Country\n"
             f"🧠 Built-in Dork Generator\n"
             f"🧹 Keyword Cleaner + Scraper\n"
             f"🛡 SQLi/XSS/LFI Vuln Scanner\n"
             f"⚙️ Smart Filters + Dedup\n"
             f"📄 Export results as file\n\n"
             f"🔑 Status: {lic_line}\n\n"
             f"<b>🔑 GET YOUR LICENSE KEY FROM {CONTACT}</b>\n"
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
    return pe(f"❓ <b>DevParser v2 — Help</b>\n\n"
              f"<b>Quick Start:</b>\n"
              f"1️⃣ Get a license key from {CONTACT}, then send it here (or /redeem KEY)\n"
              f"2️⃣ 🧠 Gen Dorks → create custom dork queries\n"
              f"3️⃣ 🧹 KW Cleaner → clean keywords, 🔍 KW Scraper → scrape from Google\n"
              f"4️⃣ 📤 Upload dork file (one dork per line)\n"
              f"5️⃣ ▶️ Start Parsing → live progress → 📊 Download results\n"
              f"6️⃣ 🛡 Vuln Scanner → scan results for SQLi/XSS/LFI\n\n"
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
              f"💬 Contact {CONTACT}")

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
    body += f"\n💬 Get a key / support: {CONTACT}"
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
    return pe(f"ℹ️ <b>DevParser v2 — Info</b>\n\n"
              f"🤖 <b>Bot:</b> Google Dork → URL parser\n"
              f"🌐 6 engines • 🛰 auto proxy • ⚙️ smart filters\n"
              f"🧠 Dork Gen • 🧹 KW Cleaner • 🔍 KW Scraper\n"
              f"🛡 SQLi/XSS/LFI Vuln Scanner\n\n"
              f"👤 <b>Your account:</b>\n"
              f"Name: <b>{sender.first_name or '—'}</b>\n"
              f"Username: <b>{('@'+sender.username) if getattr(sender,'username',None) else '—'}</b>\n"
              f"License: <b>{status}</b>\n\n"
              f"<b>🔑 GET LICENSE KEY FROM {CONTACT}</b>\n\n"
              f"💬 Message {CONTACT}")

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
        used = f"used by {k['redeemed_by']}" if k['redeemed_by'] else "unredeemed"
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
            if not must_license(uid): return await reject_unlicensed(event, uid)
            alive = engine.get_alive_proxies()
            total = len(engine.raw_proxies)
            txt = pe(f"🌐 <b>Proxy Manager</b>\n\n"
                     f"🛰 Protocol: <b>{engine.proxy_protocol.upper()}</b>\n"
                     f"🎯 Country: <b>{engine.country.upper()}</b>\n"
                     f"🔋 Auto: <b>{'ON' if engine.auto_scrape else 'OFF'}</b>\n"
                     f"📊 Proxies: <b>{alive} alive / {total} total</b>")
            await event.edit(txt, buttons=proxy_buttons(), parse_mode='html')

        elif data == "menu_settings":
            if not must_license(uid): return await reject_unlicensed(event, uid)
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
            if not must_license(uid): return await reject_unlicensed(event, uid)
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
            kg = get_keygen(uid)
            kg.step = "type"; kg.days = 0; kg.hours = 0; kg.mins = 0; kg.qty = 1
            await event.edit(pe("🛠 <b>Generate License Keys</b>\n\nSelect duration type:"),
                             buttons=build_keygen_type(), parse_mode='html')

        elif data.startswith("kg_type_"):
            kg = get_keygen(uid)
            t = data[8:]
            if t == "d":
                kg.step = "amount_d"
            elif t == "h":
                kg.step = "amount_h"
            elif t == "m":
                kg.step = "amount_m"
            kg.days = 0; kg.hours = 0; kg.mins = 0
            tname = {"d": "Days", "h": "Hours", "m": "Minutes"}[t]
            await event.edit(pe(f"🛠 <b>Select Duration</b>\n\nType: {tname}"),
                             buttons=build_keygen_amount(kg), parse_mode='html')

        elif data.startswith("kg_amt_"):
            kg = get_keygen(uid)
            parts = data[7:].split("_")
            unit = parts[0]; val = int(parts[1])
            if unit == "d": kg.days = val
            elif unit == "h": kg.hours = val
            elif unit == "m": kg.mins = val
            kg.step = "qty"
            dur = kg.format_duration()
            await event.edit(pe(f"🛠 Duration: <b>{dur}</b>\n\nSelect quantity:"),
                             buttons=build_keygen_qty(kg), parse_mode='html')

        elif data.startswith("kg_custom_"):
            kg = get_keygen(uid)
            unit = data[10:]  # "d", "h", "m", or "qty"
            if unit == "qty":
                state['waiting_for'] = 'kg_custom_qty'
                await event.edit(pe("🔢 <b>Custom Quantity</b>\n\nSend a number (1-50):"),
                                 buttons=[[Button.inline("🔙 Back", "kg_change_qty")]], parse_mode='html')
            else:
                state['waiting_for'] = f'kg_custom_{unit}'
                unit_name = {"d": "Days", "h": "Hours", "m": "Minutes"}[unit]
                await event.edit(pe(f"✏️ <b>Custom {unit_name}</b>\n\nSend a number:"),
                                 buttons=[[Button.inline("🔙 Back", f"kg_type_{unit}".encode())]], parse_mode='html')

        elif data.startswith("kg_qty_"):
            kg = get_keygen(uid)
            kg.qty = int(data[7:])
            dur = kg.format_duration()
            await event.edit(pe(f"🛠 <b>Confirm</b>\n\n"
                                f"⏰ Duration: <b>{dur}</b>\n"
                                f"🔢 Quantity: <b>{kg.qty}</b> key(s)"),
                             buttons=build_keygen_confirm(kg), parse_mode='html')

        elif data == "kg_change_qty":
            kg = get_keygen(uid)
            await event.edit(pe(f"🛠 Duration: <b>{kg.format_duration()}</b>\n\nSelect quantity:"),
                             buttons=build_keygen_qty(kg), parse_mode='html')

        elif data == "kg_do":
            kg = get_keygen(uid)
            if not is_admin(uid):
                await event.answer(pe("🔒 Admin only")); return
            dur = kg.format_duration()
            keys_generated = []
            for _ in range(min(kg.qty, 20)):
                k = generate_key(days=kg.days, hours=kg.hours, minutes=kg.mins)
                keys_generated.append(k)
            await event.answer(pe(f"✅ {len(keys_generated)} key(s) generated!"))
            txt = pe(f"🛠 <b>Keys Generated</b>\n\n"
                     f"⏰ Duration: <b>{dur}</b>\n"
                     f"🔢 Qty: <b>{len(keys_generated)}</b>\n\n")
            for i, k in enumerate(keys_generated[:20]):
                txt += f"<code>{k}</code>\n"
            await event.reply(txt, parse_mode='html')
            # Reset
            kg.days = 0; kg.hours = 0; kg.mins = 0; kg.qty = 1; kg.step = "type"
            await event.edit(pe("🛠 <b>Generate More Keys?</b>"),
                             buttons=build_keygen_type(), parse_mode='html')

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

        # ── DORK GENERATOR ──
        elif data == "menu_dork_gen":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            session = get_dork_session(uid)
            get_state(uid).pop('waiting_for', None)
            txt = pe(
                "🧠 <b>XDumpGO Dork Generator (Pro)</b>\n\n"
                f"🔑 <b>Keywords:</b> {len(session.keywords)}\n"
                f"📁 <b>Extensions:</b> {len(session.extensions)}\n"
                f"⚙️ <b>Parameters:</b> {len(session.parameters)}\n"
                f"🌐 <b>Domains:</b> {'ON' if session.domain_targeting else 'OFF'} ({len(session.target_domains)+len(session.custom_domains)} selected)\n"
                f"🔗 <b>Format:</b> <code>{session.format}</code>\n"
                f"🔀 <b>Multi-Op:</b> {'ON' if session.multi_op else 'OFF'} <i>(generates intitle+intext variations)</i>\n\n"
                "👇 Configure your settings & GENERATE:"
            )
            await event.edit(txt, buttons=build_dork_dash(), parse_mode='html')
            
        elif data.startswith("dork_edit_"):
            t = data.split("_")[2]
            get_state(uid)['waiting_for'] = f"dork_{t}"
            names = {"kw": "Keywords", "ext": "Extensions", "param": "Parameters"}
            if t in names:
                session = get_dork_session(uid)
                cnt = len(getattr(session, {"kw":"keywords", "ext":"extensions", "param":"parameters"}[t]))
                txt = pe(
                    f"⚙️ <b>Edit {names[t]}</b>\n\n"
                    f"Currently loaded: <b>{cnt}</b>\n\n"
                    f"✏️ <b>To ADD items:</b> Send them now as a comma-separated list.\n"
                    f"Example: <code>item1, item2, item3</code>"
                )
                await event.edit(txt, buttons=build_dork_list(t), parse_mode='html')
            elif t == "fmt":
                session = get_dork_session(uid)
                await event.edit(pe("🔗 <b>Select Format Base:</b>\n\nChoose the primary operator to use."), buttons=build_dork_fmt(session), parse_mode='html')
            elif t == "dom":
                session = get_dork_session(uid)
                await event.edit(pe("🌐 <b>Domain Targeting</b>\n\nEnable/Disable targeting and select domains below."), buttons=build_dork_dom(session), parse_mode='html')
                
        elif data.startswith("dork_view_"):
            t = data.split("_")[2]
            session = get_dork_session(uid)
            attr = {"kw":"keywords", "ext":"extensions", "param":"parameters"}[t]
            names = {"kw": "Keywords", "ext": "Extensions", "param": "Parameters"}
            items = getattr(session, attr)
            if not items:
                await event.answer(pe(f"No {names[t]} loaded."))
            else:
                with open(f"current_{t}.txt", "w", encoding="utf-8") as f:
                    f.write("\n".join(items))
                await bot.send_file(uid, f"current_{t}.txt", caption=pe(f"📁 <b>Current {names[t]}</b> ({len(items)})"), parse_mode='html')
                os.remove(f"current_{t}.txt")
            
        elif data.startswith("dork_upload_"):
            t = data.split("_")[2]
            get_state(uid)['waiting_for'] = f"dorkfile_{t}"
            names = {"kw": "Keywords", "ext": "Extensions", "param": "Parameters"}
            await event.edit(pe(f"📤 <b>Upload TXT File for {names[t]}</b>\n\nSend a `.txt` file with one item per line."), buttons=[[Button.inline("🔙 Cancel", f"dork_edit_{t}".encode())]], parse_mode='html')
            
        elif data.startswith("dork_clear_"):
            t = data.split("_")[2]
            session = get_dork_session(uid)
            if t == "cdom":
                session.custom_domains.clear(); session.save()
                await event.answer(pe("🗑 Custom domains cleared!"))
                await event.edit(pe("🌐 <b>Domain Targeting</b>\n\nEnable/Disable targeting and select domains below."), buttons=build_dork_dom(session), parse_mode='html')
            elif t == "fmt":
                session.custom_formats.clear(); session.save()
                await event.answer(pe("🗑 Custom formats cleared!"))
                await event.edit(pe("🔗 <b>Select Format Base:</b>\n\nChoose the primary operator to use."), buttons=build_dork_fmt(session), parse_mode='html')
            else:
                attr = {"kw":"keywords", "ext":"extensions", "param":"parameters"}[t]
                setattr(session, attr, []); session.save()
                await event.answer(pe("🗑 Cleared!"))
                await event.edit(pe("✅ <b>Cleared!</b>"), buttons=build_dork_list(t), parse_mode='html')
                
        elif data.startswith("dork_reset_"):
            t = data.split("_")[2]
            session = get_dork_session(uid)
            attr = {"kw":"keywords", "ext":"extensions", "param":"parameters"}[t]
            defs = {"kw":DEFAULT_KEYWORDS, "ext":DEFAULT_EXTENSIONS, "param":DEFAULT_PARAMETERS}[t]
            setattr(session, attr, list(defs)); session.save()
            await event.answer(pe("🔄 Reset to default!"))
            await event.edit(pe("✅ <b>Reset to default!</b>"), buttons=build_dork_list(t), parse_mode='html')
            
        elif data.startswith("dork_fmt_"):
            session = get_dork_session(uid)
            session.format = data[9:]
            session.save()
            await event.answer(pe(f"Format set to {session.format}"))
            txt = pe("🧠 <b>XDumpGO Dork Generator (Pro)</b>\n\n"
                f"🔑 <b>Keywords:</b> {len(session.keywords)}\n"
                f"📁 <b>Extensions:</b> {len(session.extensions)}\n"
                f"⚙️ <b>Parameters:</b> {len(session.parameters)}\n"
                f"🌐 <b>Domains:</b> {'ON' if session.domain_targeting else 'OFF'} ({len(session.target_domains)+len(session.custom_domains)} selected)\n"
                f"🔗 <b>Format:</b> <code>{session.format}</code>\n"
                f"🔀 <b>Multi-Op:</b> {'ON' if session.multi_op else 'OFF'} <i>(generates intitle+intext variations)</i>\n\n"
                "👇 Configure your settings & GENERATE:")
            await event.edit(txt, buttons=build_dork_dash(), parse_mode='html')
            
        elif data == "dork_toggle_mop":
            session = get_dork_session(uid)
            session.multi_op = not session.multi_op
            session.save()
            await event.answer(pe(f"Multi-Op: {'ON' if session.multi_op else 'OFF'}"))
            txt = pe("🧠 <b>XDumpGO Dork Generator (Pro)</b>\n\n"
                f"🔑 <b>Keywords:</b> {len(session.keywords)}\n"
                f"📁 <b>Extensions:</b> {len(session.extensions)}\n"
                f"⚙️ <b>Parameters:</b> {len(session.parameters)}\n"
                f"🌐 <b>Domains:</b> {'ON' if session.domain_targeting else 'OFF'} ({len(session.target_domains)+len(session.custom_domains)} selected)\n"
                f"🔗 <b>Format:</b> <code>{session.format}</code>\n"
                f"🔀 <b>Multi-Op:</b> {'ON' if session.multi_op else 'OFF'} <i>(generates intitle+intext variations)</i>\n\n"
                "👇 Configure your settings & GENERATE:")
            await event.edit(txt, buttons=build_dork_dash(), parse_mode='html')
            
        elif data == "dork_toggle_dom":
            session = get_dork_session(uid)
            session.domain_targeting = not session.domain_targeting
            session.save()
            await event.edit(pe("🌐 <b>Domain Targeting</b>\n\nEnable/Disable targeting and select domains below."), buttons=build_dork_dom(session), parse_mode='html')
            
        elif data.startswith("dork_tdom_"):
            session = get_dork_session(uid)
            dom = data[10:]
            if dom in session.target_domains: session.target_domains.remove(dom)
            else: session.target_domains.append(dom)
            session.save()
            await event.edit(pe("🌐 <b>Domain Targeting</b>\n\nEnable/Disable targeting and select domains below."), buttons=build_dork_dom(session), parse_mode='html')
            
        elif data.startswith("dork_dompage_"):
            page = int(data[13:])
            session = get_dork_session(uid)
            await event.edit(pe("🌐 <b>Domain Targeting</b>\n\nEnable/Disable targeting and select domains below."), buttons=build_dork_dom(session, page=page), parse_mode='html')
            
        elif data == "dork_add_cdom":
            get_state(uid)['waiting_for'] = "dork_cdom"
            await event.edit(pe("➕ <b>Add Custom Domains</b>\n\nSend custom domains comma-separated.\nExample: <code>.xyz, .pk, .ru</code>"), buttons=[[Button.inline("🔙 Back", b"dork_edit_dom")]], parse_mode='html')
            
        elif data == "dork_add_fmt":
            get_state(uid)['waiting_for'] = "dork_cfmt"
            await event.edit(pe("➕ <b>Add Custom Format</b>\n\nSend the custom format string (e.g., <code>site:</code> or <code>filetype:</code>)."), buttons=[[Button.inline("🔙 Back", b"dork_edit_fmt")]], parse_mode='html')

        elif data == "dork_load_cleaner":
            cs = get_kw_cleaner(uid); session = get_dork_session(uid)
            if not cs.cleaned_data:
                await event.answer(pe("❌ No cleaned data in KW Cleaner!")); return
            session.keywords = list(dict.fromkeys(cs.cleaned_data))
            session.save()
            await event.answer(pe(f"✅ Loaded {len(session.keywords)} from KW Cleaner!"))
            txt = pe("🧠 <b>XDumpGO Dork Generator (Pro)</b>\n\n"
                f"🔑 <b>Keywords:</b> {len(session.keywords)}\n"
                f"📁 <b>Extensions:</b> {len(session.extensions)}\n"
                f"⚙️ <b>Parameters:</b> {len(session.parameters)}\n"
                f"🌐 <b>Domains:</b> {'ON' if session.domain_targeting else 'OFF'}\n"
                f"🔗 <b>Format:</b> <code>{session.format}</code>\n"
                f"🔀 <b>Multi-Op:</b> {'ON' if session.multi_op else 'OFF'}\n\n"
                "👇 Configure & GENERATE:")
            await event.edit(txt, buttons=build_dork_dash(), parse_mode='html')

        elif data == "dork_load_scraper":
            ss = get_kw_scraper(uid); session = get_dork_session(uid)
            if not ss.scraped_keywords:
                await event.answer(pe("❌ No data in KW Scraper!")); return
            session.keywords = list(dict.fromkeys(ss.scraped_keywords))
            session.save()
            await event.answer(pe(f"✅ Loaded {len(session.keywords)} from Scraper!"))
            txt = pe("🧠 <b>XDumpGO Dork Generator (Pro)</b>\n\n"
                f"🔑 <b>Keywords:</b> {len(session.keywords)}\n"
                f"📁 <b>Extensions:</b> {len(session.extensions)}\n"
                f"⚙️ <b>Parameters:</b> {len(session.parameters)}\n"
                f"🌐 <b>Domains:</b> {'ON' if session.domain_targeting else 'OFF'}\n"
                f"🔗 <b>Format:</b> <code>{session.format}</code>\n"
                f"🔀 <b>Multi-Op:</b> {'ON' if session.multi_op else 'OFF'}\n\n"
                "👇 Configure & GENERATE:")
            await event.edit(txt, buttons=build_dork_dash(), parse_mode='html')
            
        elif data == "dork_generate":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            session = get_dork_session(uid)
            if not session.keywords:
                return await event.answer(pe("❌ Error: Keywords empty!"))
            
            await event.answer(pe("⏳ Generating..."))
            status_msg = await bot.send_message(event.chat_id, pe("⏳ **XDumpGO Engine is Generating Dorks...**"), parse_mode='html')
            
            all_dorks = set()
            fmt_op = session.format
            for kw in session.keywords:
                base_set = set()
                if session.extensions and session.parameters:
                    for ext in session.extensions:
                        for param in session.parameters:
                            base_set.add(f"{fmt_op}{kw}{ext}{param}")
                elif session.extensions:
                    for ext in session.extensions:
                        base_set.add(f"{fmt_op}{kw}{ext}")
                elif session.parameters:
                    for param in session.parameters:
                        base_set.add(f"{fmt_op}{kw}{param}")
                else:
                    base_set.add(f"{fmt_op}{kw}")
                    
                if session.multi_op:
                    multi_set = set()
                    for b in base_set:
                        multi_set.add(f"intitle:{kw} {b}")
                        multi_set.add(f"intext:{kw} {b}")
                    base_set.update(multi_set)
                    
                if session.domain_targeting:
                    active_doms = session.target_domains + session.custom_domains
                    if active_doms:
                        dom_set = set()
                        for b in base_set:
                            for d in active_doms:
                                dom_set.add(f"site:{d} {b}")
                        base_set = dom_set
                        
                all_dorks.update(base_set)
                
            if not all_dorks:
                await status_msg.edit(pe("❌ No dorks could be generated."), buttons=[[Button.inline("🔙 Back", b"menu_dork_gen")]], parse_mode='html')
                return
                
            dorks_list = list(all_dorks)
            random.shuffle(dorks_list)
            
            import io
            file_content = "\n".join(dorks_list).encode('utf-8')
            doc = io.BytesIO(file_content)
            doc.name = f"XDumpGO_Dorks_{len(dorks_list)}.txt"
            
            await bot.send_file(
                event.chat_id,
                file=doc,
                caption=pe(f"✅ <b>XDumpGO Dorks Generated!</b>\n\n"
                           f"📊 <b>Total Dorks:</b> <code>{len(dorks_list)}</code>\n"
                           f"⚙️ <b>Multi-Op:</b> {'ON' if session.multi_op else 'OFF'}\n"
                           f"🌐 <b>Domains Targeted:</b> {'ON' if session.domain_targeting else 'OFF'}\n"
                           f"👨‍💻 <b>Generated by:</b> {CONTACT}"),
                parse_mode='html'
            )
            await status_msg.delete()
            # Auto load into engine
            engine = get_engine(uid)
            engine.dorks = dorks_list
            await bot.send_message(
                event.chat_id, 
                pe(f"💡 <b>Tip:</b> Generated dorks have been automatically loaded into the parser! You can click ▶️ Start Parsing directly."),
                buttons=[[Button.inline("🔙 Back to Main Menu", b"menu_home")]],
                parse_mode='html'
            )

        # ── KW CLEANER ──
        elif data == "menu_kw_cleaner":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            cs = get_kw_cleaner(uid)
            get_state(uid).pop('waiting_for', None)
            txt = pe(
                "🧹 <b>XDumpGO KW Cleaner</b>\n\n"
                "Paste or upload keywords, configure filters, and process.\n"
                f"📥 Cleaned: <b>{len(cs.cleaned_data)}</b> keywords ready\n\n"
                "Toggle options below:"
            )
            await event.edit(txt, buttons=build_kw_cleaner(cs), parse_mode='html')

        elif data == "kwc_split1":
            cs = get_kw_cleaner(uid); cs.split_1word = not cs.split_1word
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_split2":
            cs = get_kw_cleaner(uid); cs.split_2word = not cs.split_2word
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_dupes":
            cs = get_kw_cleaner(uid); cs.remove_dupes = not cs.remove_dupes
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_nums":
            cs = get_kw_cleaner(uid); cs.remove_nums = not cs.remove_nums
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_short":
            cs = get_kw_cleaner(uid); cs.remove_short = not cs.remove_short
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_ai":
            cs = get_kw_cleaner(uid); cs.ai_filter = not cs.ai_filter
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_minlen":
            state['waiting_for'] = 'kwc_minlen'
            cs = get_kw_cleaner(uid)
            await event.edit(pe(f"🔢 <b>Min Length</b>\nCurrent: <b>{cs.min_len}</b>\nSend 2-10:"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_kw_cleaner")]], parse_mode='html')
        elif data == "kwc_load":
            state['waiting_for'] = 'kwc_input'
            await event.edit(pe("📥 <b>Load Keywords</b>\n\nSend/paste your keywords (one per line) or upload a .txt file."),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_kw_cleaner")]], parse_mode='html')
        elif data == "kwc_process":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            cs = get_kw_cleaner(uid)
            if 'kwc_input' not in state:
                await event.answer(pe("❌ No input! Load keywords first.")); return
            raw = state.pop('kwc_input', '')
            if not raw.strip():
                await event.answer(pe("❌ Empty input!")); return
            result, stats = clean_keywords(raw,
                split_1=cs.split_1word, split_2=cs.split_2word,
                rm_dupes=cs.remove_dupes, rm_nums=cs.remove_nums,
                rm_short=cs.remove_short, min_len=cs.min_len, ai_filter=cs.ai_filter)
            cs.cleaned_data = result
            txt = pe(
                f"⚡ <b>Processing Complete!</b>\n\n"
                f"📊 <b>Stats:</b>\n"
                f"📥 Input Lines: <b>{stats['original']}</b>\n"
                f"📤 After Split: <b>{stats['after_split']}</b>\n"
                f"🗑 Dupes Removed: <b>{stats['after_split'] - stats['after_dedupe']}</b>\n"
                f"🔢 Num Filtered: <b>{stats['after_dedupe'] - stats['after_num_filter']}</b>\n"
                f"📏 Short Filtered: <b>{stats['after_num_filter'] - stats['after_short_filter']}</b>\n"
                f"🤖 AI Removed: <b>{stats['removed_by_ai']}</b>\n"
                f"✅ <b>Final: {stats['final']} keywords</b>"
            )
            await event.edit(txt, buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kwc_download":
            cs = get_kw_cleaner(uid)
            if not cs.cleaned_data:
                await event.answer(pe("❌ No cleaned data!")); return
            import io
            f = io.BytesIO("\n".join(cs.cleaned_data).encode('utf-8'))
            f.name = f"XDumpGO_Clean_{len(cs.cleaned_data)}.txt"
            await bot.send_file(uid, f, caption=pe(f"🧹 Cleaned: {len(cs.cleaned_data)} keywords"))
        elif data == "kwc_send_dorkgen":
            cs = get_kw_cleaner(uid); session = get_dork_session(uid)
            if not cs.cleaned_data:
                await event.answer(pe("❌ No cleaned data!")); return
            session.keywords = list(dict.fromkeys(cs.cleaned_data))
            session.save()
            await event.answer(pe(f"✅ Sent {len(session.keywords)} keywords to Dork Gen!"))
            await event.edit(pe("🧠 <b>XDumpGO Dork Generator</b> — Keywords loaded from Cleaner"), buttons=build_dork_dash(), parse_mode='html')
        elif data == "kwc_clear":
            cs = get_kw_cleaner(uid); cs.cleaned_data = []
            state.pop('kwc_input', None)
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b> — Cleared"), buttons=build_kw_cleaner(cs), parse_mode='html')

        # ── KW SCRAPER ──
        elif data == "menu_kw_scraper":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            ss = get_kw_scraper(uid)
            get_state(uid).pop('waiting_for', None)
            txt = pe(
                f"🔍 <b>XDumpGO KW Scraper</b>\n\n"
                f"🌍 Language: <b>{ss.lang_name}</b>\n"
                f"📍 Country: <b>{ss.country_name}</b>\n"
                f"📏 Depth: <b>{ss.depth}</b>\n"
                f"🌱 Seeds: <code>{', '.join(ss.seeds[:5])}{'...' if len(ss.seeds) > 5 else ''}</code>\n"
                f"📊 Scraped: <b>{len(ss.scraped_keywords)}</b> keywords\n"
                f"⏳ Status: <b>{'RUNNING' if ss.scrape_running else 'IDLE'}</b>"
            )
            await event.edit(txt, buttons=build_kw_scraper(ss), parse_mode='html')

        elif data == "kws_seeds":
            state['waiting_for'] = 'kws_seeds'
            await event.edit(pe("✏️ <b>Edit Seed Keywords</b>\n\nSend comma-separated seeds.\nExample: <code>shopping, checkout, payment</code>"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_kw_scraper")]], parse_mode='html')
        elif data == "kws_depth":
            state['waiting_for'] = 'kws_depth'
            ss = get_kw_scraper(uid)
            await event.edit(pe(f"📏 <b>Scrape Depth</b>\nCurrent: <b>{ss.depth}</b>\nSend 1-3 (higher = more keywords but slower):"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_kw_scraper")]], parse_mode='html')
        elif data == "kws_lang":
            ss = get_kw_scraper(uid)
            await event.edit(pe(f"🌍 <b>Select Language</b>\nCurrent: <b>{ss.lang_name}</b>"),
                             buttons=build_kw_lang_page(ss), parse_mode='html')
        elif data == "kws_country":
            ss = get_kw_scraper(uid)
            await event.edit(pe(f"📍 <b>Select Country</b>\nCurrent: <b>{ss.country_name}</b>"),
                             buttons=build_kw_country_page(ss), parse_mode='html')
        elif data.startswith("kws_langpage_"):
            page = int(data[12:]); ss = get_kw_scraper(uid)
            await event.edit(pe(f"🌍 <b>Select Language</b>"), buttons=build_kw_lang_page(ss, page), parse_mode='html')
        elif data.startswith("kws_ctypage_"):
            page = int(data[12:]); ss = get_kw_scraper(uid)
            await event.edit(pe(f"📍 <b>Select Country</b>"), buttons=build_kw_country_page(ss, page), parse_mode='html')
        elif data.startswith("kws_lang_"):
            code = data[9:]; ss = get_kw_scraper(uid)
            for n, c in KW_LANGUAGES:
                if c == code: ss.lang_name = n; ss.lang_code = c; break
            await event.answer(pe(f"✅ Lang: {ss.lang_name}"))
            await event.edit(pe(f"🌍 Lang set to <b>{ss.lang_name}</b>"), buttons=build_kw_lang_page(ss), parse_mode='html')
        elif data.startswith("kws_cty_"):
            code = data[8:]; ss = get_kw_scraper(uid)
            for n, c in KW_COUNTRIES:
                if c == code: ss.country_name = n; ss.country_code = c; break
            await event.answer(pe(f"✅ Country: {ss.country_name}"))
            await event.edit(pe(f"📍 Country set to <b>{ss.country_name}</b>"), buttons=build_kw_country_page(ss), parse_mode='html')
        elif data == "kws_start":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            ss = get_kw_scraper(uid)
            if not ss.seeds:
                await event.answer(pe("❌ No seeds!")); return
            if ss.scrape_running:
                await event.answer(pe("Already running!")); return
            ss.scrape_running = True
            ss.scraped_keywords.clear()
            ss.scraper = KWScraper(list(ss.seeds), ss.lang_code, ss.country_code, ss.depth)
            ss.scraper.start()
            await event.answer(pe("🚀 Scraping started!"))
            await event.edit(pe("🔍 <b>Scraping...</b>\n🌱 From: <code>" + ", ".join(ss.seeds[:3]) + "</code>"),
                             buttons=build_kw_scraper(ss), parse_mode='html')
            # Background UI updater
            def _kws_updater():
                last_c = -1
                while ss.scrape_running and (ss.scraper and ss.scraper.running):
                    time.sleep(2)
                    c = len(ss.scraped_keywords)
                    if c != last_c:
                        last_c = c
                        ss.scraped_keywords = ss.scraper.results
                        _safe_edit(event.chat_id, event.message_id,
                            pe(f"🔍 <b>Scraping...</b>\n📊 Kw: <b>{c}</b> | ❌ Errs: {ss.scraper.errors}\n⏱ {int(time.time()-ss.scraper.start_time)}s"),
                            buttons=build_kw_scraper(ss))
                ss.scraped_keywords = ss.scraper.results if ss.scraper else ss.scraped_keywords
                ss.scrape_running = False
                _safe_edit(event.chat_id, event.message_id,
                    pe(f"✅ <b>Scraping Complete!</b>\n📊 Total: <b>{len(ss.scraped_keywords)}</b> keywords"),
                    buttons=build_kw_scraper(ss))
            threading.Thread(target=_kws_updater, daemon=True).start()
        elif data == "kws_stop":
            ss = get_kw_scraper(uid)
            if ss.scraper: ss.scraper.stop()
            ss.scrape_running = False
            await event.answer(pe("⏹ Stopped!"))
            await event.edit(pe(f"⏹ <b>Stopped!</b>\n📊 Total: <b>{len(ss.scraped_keywords)}</b>"),
                             buttons=build_kw_scraper(ss), parse_mode='html')
        elif data == "kws_download":
            ss = get_kw_scraper(uid)
            if not ss.scraped_keywords:
                await event.answer(pe("❌ No data!")); return
            import io
            kw_list = sorted(ss.scraped_keywords)
            f = io.BytesIO("\n".join(kw_list).encode('utf-8'))
            f.name = f"XDumpGO_Scraped_{len(kw_list)}.txt"
            await bot.send_file(uid, f, caption=pe(f"🔍 Scraped: {len(kw_list)} keywords"))
        elif data == "kws_copy":
            ss = get_kw_scraper(uid)
            if not ss.scraped_keywords:
                await event.answer(pe("❌ No data!")); return
            kw_list = sorted(ss.scraped_keywords)
            import io
            f = io.BytesIO("\n".join(kw_list).encode('utf-8'))
            f.name = f"XDumpGO_Scraped_{len(kw_list)}.txt"
            await bot.send_file(uid, f, caption=pe(f"🔍 Scraped: {len(kw_list)} keywords"))
            await event.answer(pe("📋 File sent!"))
        elif data == "kws_send_cleaner":
            ss = get_kw_scraper(uid); cs = get_kw_cleaner(uid)
            if not ss.scraped_keywords:
                await event.answer(pe("❌ No data!")); return
            state['kwc_input'] = "\n".join(sorted(ss.scraped_keywords))
            await event.answer(pe(f"✅ Sent {len(ss.scraped_keywords)} to Cleaner!"))
            await event.edit(pe("🧹 <b>XDumpGO KW Cleaner</b> — Ready to process"), buttons=build_kw_cleaner(cs), parse_mode='html')
        elif data == "kws_send_dorkgen":
            ss = get_kw_scraper(uid); session = get_dork_session(uid)
            if not ss.scraped_keywords:
                await event.answer(pe("❌ No data!")); return
            session.keywords = list(dict.fromkeys(ss.scraped_keywords))
            session.save()
            await event.answer(pe(f"✅ Sent {len(session.keywords)} keywords to Dork Gen!"))
            await event.edit(pe("🧠 <b>XDumpGO Dork Generator</b> — Keywords loaded from Scraper"), buttons=build_dork_dash(), parse_mode='html')
        elif data == "kws_clear":
            ss = get_kw_scraper(uid); ss.scraped_keywords.clear()
            if ss.scraper: ss.scraper.stop()
            ss.scrape_running = False
            await event.edit(pe("🔍 <b>XDumpGO KW Scraper</b> — Cleared"), buttons=build_kw_scraper(ss), parse_mode='html')

        # ── VULN SCANNER ──
        elif data == "menu_vuln":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            vs = get_vuln_session(uid)
            get_state(uid).pop('waiting_for', None)
            txt = pe(
                "🛡 <b>XDumpGO Vuln Scanner</b>\n\n"
                f"📥 URLs Loaded: <b>{len(vs.vuln_urls)}</b>\n"
                f"⚡ Threads: <b>{vs.threads}</b>\n"
                f"🛰 Proxy: <b>{'ON' if vs.proxy else 'OFF'}</b>\n"
                f"🔗 Total Findings: <b>{sum(len(v) for v in vs.results.values()) if vs.results else 0}</b>\n\n"
                "Scans for: 💉 SQLi | 🖥 XSS | 📁 LFI | 🔀 Open Redirect"
            )
            await event.edit(txt, buttons=build_vuln_dash(vs), parse_mode='html')

        elif data == "vuln_load":
            # Load from parser results or upload
            engine = get_engine(uid)
            res_count = len(engine.results)
            btns = [
                [Button.inline(f"📥 Load from Results ({res_count} URLs)", b"vuln_load_results")],
                [Button.inline("📤 Upload URL File", b"vuln_load_file")],
                [Button.inline("✏️ Paste URLs", b"vuln_load_paste")],
                [Button.inline("🔙 Cancel", b"menu_vuln")],
            ]
            await event.edit(pe(f"📥 <b>Load URLs</b>\n\nChoose source:"), buttons=btns, parse_mode='html')

        elif data == "vuln_load_results":
            engine = get_engine(uid)
            if not engine.results:
                await event.answer(pe("❌ No parser results!")); return
            vs = get_vuln_session(uid)
            vs.vuln_urls = list(engine.results)
            await event.answer(pe(f"✅ Loaded {len(vs.vuln_urls)} URLs!"))
            await event.edit(pe(f"🛡 <b>XDumpGO Vuln Scanner</b>\n📥 <b>{len(vs.vuln_urls)}</b> URLs ready"), buttons=build_vuln_dash(vs), parse_mode='html')

        elif data == "vuln_load_file":
            state['waiting_for'] = 'vuln_file'
            await event.edit(pe("📤 <b>Upload URL File</b>\nSend .txt file (one URL per line)."),
                             buttons=[[Button.inline("🔙 Cancel", b"vuln_load")]], parse_mode='html')

        elif data == "vuln_load_paste":
            state['waiting_for'] = 'vuln_paste'
            await event.edit(pe("✏️ <b>Paste URLs</b>\nSend URLs one per line."),
                             buttons=[[Button.inline("🔙 Cancel", b"vuln_load")]], parse_mode='html')

        elif data == "vuln_threads":
            state['waiting_for'] = 'vuln_threads'
            vs = get_vuln_session(uid)
            await event.edit(pe(f"⚡ <b>Threads</b>\nCurrent: <b>{vs.threads}</b>\nSend 10-100:"),
                             buttons=[[Button.inline("🔙 Cancel", b"menu_vuln")]], parse_mode='html')

        elif data == "vuln_proxy":
            vs = get_vuln_session(uid)
            vs.proxy = None if vs.proxy else "auto"  # Will use engine proxies
            await event.edit(pe(f"🛰 Proxy: <b>{'ON' if vs.proxy else 'OFF'}</b>"), buttons=build_vuln_dash(vs), parse_mode='html')

        elif data == "vuln_start":
            if not must_license(uid): return await reject_unlicensed(event, uid)
            vs = get_vuln_session(uid)
            if not vs.vuln_urls:
                await event.answer(pe("❌ No URLs loaded!")); return
            if vs.scanning:
                await event.answer(pe("Already scanning!")); return
            
            vs.scanning = True
            vs.results = {"SQLi": [], "XSS": [], "LFI": [], "Open Redirect": []}
            
            proxy = None
            if vs.proxy:
                engine = get_engine(uid)
                alive = engine.get_alive_proxies()
                if alive > 0:
                    proxy = engine.get_next_proxy()
            
            scanner = VulnScanner(threads=vs.threads, proxy=proxy)
            vs.scanner = scanner
            
            await event.answer(pe("🚀 Scan started!"))
            await event.edit(pe("🛡 <b>Scanning...</b>\n📥 <b>0/{} </b>| 🔗 <b>0</b> found".format(len(vs.vuln_urls))),
                             buttons=build_vuln_dash(vs), parse_mode='html')
            
            def run():
                def prog_cb(s, t, r):
                    _safe_edit(event.chat_id, event.message_id,
                        pe(f"🛡 <b>Scanning...</b>\n📥 <b>{s}/{t}</b> | 🔗 <b>{r}</b> found"),
                        buttons=build_vuln_dash(vs))
                
                scanner.scan_urls(vs.vuln_urls, progress_callback=prog_cb)
                vs.results = scanner.results
                vs.scanning = False
                total = sum(len(v) for v in vs.results.values())
                time.sleep(1)  # Wait for _safe_edit throttle
                _safe_edit(event.chat_id, event.message_id,
                    pe(f"✅ <b>Scan Complete!</b>\n📥 {scanner.scanned} scanned | 🔗 <b>{total}</b> vulnerabilities"),
                    buttons=build_vuln_dash(vs))
            
            threading.Thread(target=run, daemon=True).start()

        elif data == "vuln_stop":
            vs = get_vuln_session(uid)
            if vs.scanner: vs.scanner.stop()
            vs.scanning = False
            await event.answer(pe("⏹ Stopped!"))
            total = sum(len(v) for v in vs.results.values()) if vs.results else 0
            await event.edit(pe(f"⏹ <b>Stopped!</b>\n🔗 <b>{total}</b> found"), buttons=build_vuln_dash(vs), parse_mode='html')

        elif data == "vuln_results":
            vs = get_vuln_session(uid)
            if not vs.results or sum(len(v) for v in vs.results.values()) == 0:
                await event.answer(pe("📭 No results yet!")); return
            lines = []
            icons = {"SQLi": "💉", "XSS": "🖥", "LFI": "📁", "Open Redirect": "🔀"}
            for vt in ["SQLi", "XSS", "LFI", "Open Redirect"]:
                items = vs.results.get(vt, [])
                if items:
                    lines.append(f"\n{icons[vt]} <b>{vt}: {len(items)}</b>")
                    for url, ev in items[:5]:
                        lines.append(f"  • <code>{url[:60]}...</code>")
                    if len(items) > 5: lines.append(f"  ... +{len(items)-5} more")
            await event.edit(pe("🛡 <b>Scan Results</b>\n" + "\n".join(lines)[:3500]),
                             buttons=build_vuln_dash(vs), parse_mode='html')

        elif data == "vuln_see":
            vs = get_vuln_session(uid)
            if not vs.results or sum(len(v) for v in vs.results.values()) == 0:
                await event.answer(pe("📭 No results!")); return
            
            # Build text file
            report = []
            icons = {"SQLi": "SQLi", "XSS": "XSS", "LFI": "LFI", "Open Redirect": "Redirect"}
            for vt in ["SQLi", "XSS", "LFI", "Open Redirect"]:
                items = vs.results.get(vt, [])
                for url, ev in items:
                    report.append(f"[{icons[vt]}] {url}")
            if not report:
                await event.answer(pe("📭 No vulnerabilities found!")); return
            
            import io
            f = io.BytesIO("\n".join(report).encode('utf-8'))
            f.name = f"VulnScan_{sum(len(v) for v in vs.results.values())}.txt"
            await bot.send_file(uid, f, caption=pe(f"🛡 {sum(len(v) for v in vs.results.values())} vulnerabilities found"))
            await event.answer(pe("📤 Sent!"))

        elif data == "vuln_report":
            vs = get_vuln_session(uid)
            if not vs.results or sum(len(v) for v in vs.results.values()) == 0:
                await event.answer(pe("📭 No results!")); return
            
            report = vs.scanner.generate_report() if vs.scanner else "Report not available"
            import io
            f = io.BytesIO(report.encode('utf-8'))
            total = sum(len(v) for v in vs.results.values())
            f.name = f"VulnReport_{total}.txt"
            await bot.send_file(uid, f, caption=pe(f"🛡 Full Report: {total} vulnerabilities"))
            await event.answer(pe("📤 Report sent!"))

        # ── DB DUMP ──
        elif data == "menu_dump":
            ds = get_dump_session(uid)
            txt = pe(
                "🛢 <b>XDumpGO DB Dump</b>\n\n"
                "Auto-dumps database from confirmed SQLi URLs.\n"
                f"📥 URLs Loaded: <b>{len(ds.urls)}</b>\n\n"
                "1. Load from Vuln Scanner results\n"
                "2. START DUMP to extract DB info"
            )
            await event.edit(txt, buttons=build_dump_dash(ds), parse_mode='html')

        elif data == "dump_load":
            vs = get_vuln_session(uid)
            ds = get_dump_session(uid)
            
            # Direct extract: just grab the first query param from each SQLi URL
            from urllib.parse import urlparse, parse_qs
            sqli_parsed = []
            seen = set()
            for vuln_type, items in vs.results.items():
                if vuln_type == "SQLi":
                    for url, ev in items:
                        if url in seen: continue
                        seen.add(url)
                        try:
                            p = urlparse(url)
                            qs = parse_qs(p.query)
                            if qs:
                                first_param = list(qs.keys())[0]
                                sqli_parsed.append((url, first_param))
                        except: pass
            
            btns = []
            if sqli_parsed:
                # "Load All" button
                btns.append([Button.inline(f"📥 Load ALL ({len(sqli_parsed)} URLs)", b"dump_load_all")])
                btns.append([Button.inline("📋 Select Individual", b"dump_load_select")])
            else:
                await event.answer(pe("❌ No SQLi URLs in Vuln Scanner!"))
            
            btns.append([Button.inline("📤 Paste Vuln URL", b"dump_paste")])
            btns.append([Button.inline("🔙 Cancel", b"menu_dump")])
            await event.edit(pe(f"📥 <b>Load Vulnerable URLs</b>\n\nSQLi URLs in Scanner: <b>{len(sqli_parsed)}</b>"),
                             buttons=btns, parse_mode='html')

        elif data == "dump_load_all":
            vs = get_vuln_session(uid); ds = get_dump_session(uid)
            from urllib.parse import urlparse, parse_qs
            sqli_parsed = []
            seen = set()
            for vuln_type, items in vs.results.items():
                if vuln_type == "SQLi":
                    for url, ev in items:
                        if url in seen: continue
                        seen.add(url)
                        try:
                            p = urlparse(url)
                            qs = parse_qs(p.query)
                            if qs:
                                sqli_parsed.append((url, list(qs.keys())[0]))
                        except: pass
            ds.urls = sqli_parsed  # All URLs, no limit
            await event.answer(pe(f"✅ Loaded {len(ds.urls)} URLs!"))
            await event.edit(pe(f"🛢 <b>DB Dump</b>\n📥 {len(ds.urls)} URLs loaded"), buttons=build_dump_dash(ds), parse_mode='html')

        elif data == "dump_load_select":
            vs = get_vuln_session(uid)
            from urllib.parse import urlparse, parse_qs
            sqli_parsed = []
            seen = set()
            for vuln_type, items in vs.results.items():
                if vuln_type == "SQLi":
                    for url, ev in items:
                        if url in seen: continue
                        seen.add(url)
                        try:
                            p = urlparse(url)
                            qs = parse_qs(p.query)
                            if qs:
                                sqli_parsed.append((url, list(qs.keys())[0]))
                        except: pass
            
            btns = []
            for i, (url, param) in enumerate(sqli_parsed[:20]):
                # Short URL for button
                short = url.replace("https://", "").replace("http://", "")[:35]
                btns.append([Button.inline(f"{short}... [{param}]", f"dump_add_{i}".encode())])
            
            btns.append([Button.inline("🔙 Back", b"dump_load")])
            await event.edit(pe(f"📋 <b>Select URLs to Dump</b> ({len(sqli_parsed)} available)"),
                             buttons=btns, parse_mode='html')

        elif data.startswith("dump_add_"):
            idx = int(data[9:])
            vs = get_vuln_session(uid)
            from urllib.parse import urlparse, parse_qs
            sqli_list = []
            seen = set()
            for vuln_type, items in vs.results.items():
                if vuln_type == "SQLi":
                    for url, ev in items:
                        if url in seen: continue
                        seen.add(url)
                        try:
                            p = urlparse(url)
                            qs = parse_qs(p.query)
                            if qs:
                                sqli_list.append((url, list(qs.keys())[0]))
                        except: pass
            if idx < len(sqli_list):
                ds = get_dump_session(uid)
                ds.urls.append(sqli_list[idx])
                await event.answer(pe(f"✅ Added [{sqli_list[idx][1]}]"))
                await event.edit(pe(f"🛢 <b>DB Dump</b>\n📥 {len(ds.urls)} URLs loaded"), buttons=build_dump_dash(ds), parse_mode='html')
            else:
                await event.answer(pe("❌ Invalid selection"))

        elif data == "dump_paste":
            state['waiting_for'] = 'dump_paste'
            await event.edit(pe("✏️ <b>Paste Vulnerable URL</b>\n\nFormat: <code>URL | parameter</code>\nExample:\n<code>http://site.com/page?id=1 | id</code>"),
                             buttons=[[Button.inline("🔙 Cancel", b"dump_load")]], parse_mode='html')

        elif data == "dump_start":
            ds = get_dump_session(uid)
            if not ds.urls:
                await event.answer(pe("❌ No URLs loaded!")); return
            if ds.dumping:
                await event.answer(pe("Already dumping!")); return
            
            ds.dumping = True
            ds.results = {}
            
            await event.answer(pe("🛢 Dumping started!"))
            
            def run_dump():
                for url, param in ds.urls[:5]:  # Max 5 URLs
                    if not ds.dumping: break
                    _safe_edit(event.chat_id, event.message_id,
                        pe(f"🛢 <b>Dumping...</b>\n🔗 {url[:50]}...\n🔍 Finding columns..."),
                        buttons=build_dump_dash(ds))
                    
                    def prog_cb(step, msg):
                        if not ds.dumping: return
                        _safe_edit(event.chat_id, event.message_id,
                            pe(f"🛢 <b>Dumping...</b>\n🔗 {url[:50]}...\n{msg}"),
                            buttons=build_dump_dash(ds))
                    
                    result = dump_database(url, param, callback=prog_cb)
                    ds.results[url] = result
                    
                    if not ds.dumping: break
                    time.sleep(1)
                
                ds.dumping = False
                
                # Generate combined dump file
                combined = []
                for url, res in ds.results.items():
                    if "dump_text" in res:
                        combined.append(res["dump_text"])
                        combined.append("\n")
                
                if combined:
                    import io
                    f = io.BytesIO("\n".join(combined).encode('utf-8'))
                    f.name = "XDumpGO_DB_Dump.txt"
                    async def send():
                        await bot.send_file(uid, f, caption=pe(f"🛢 DB Dump Complete! {len(ds.results)} URLs"))
                    # Schedule send
                    loop = asyncio.get_event_loop()
                    loop.create_task(send())
                
                _safe_edit(event.chat_id, event.message_id,
                    pe(f"✅ <b>Dump Complete!</b>\n🛢 {len(ds.results)} URLs processed"),
                    buttons=build_dump_dash(ds))
            
            threading.Thread(target=run_dump, daemon=True).start()
            await event.edit(pe("🛢 <b>Dumping started...</b>"), buttons=build_dump_dash(ds), parse_mode='html')

        elif data == "dump_stop":
            ds = get_dump_session(uid)
            ds.dumping = False
            await event.answer(pe("⏹ Stopped!"))
            await event.edit(pe(f"⏹ <b>Stopped!</b>\n🛢 {len(ds.results)} URLs processed"), buttons=build_dump_dash(ds), parse_mode='html')

        elif data == "dump_download":
            ds = get_dump_session(uid)
            if not ds.results:
                await event.answer(pe("❌ No dumps!")); return
            
            combined = []
            for url, res in ds.results.items():
                if "dump_text" in res:
                    combined.append(res["dump_text"])
                    combined.append("\n")
            
            if combined:
                import io
                f = io.BytesIO("\n".join(combined).encode('utf-8'))
                f.name = "XDumpGO_DB_Dump.txt"
                await bot.send_file(uid, f, caption=pe(f"🛢 DB Dump: {len(ds.results)} URLs"))
                await event.answer(pe("📤 Sent!"))

        elif data == "dump_status":
            ds = get_dump_session(uid)
            if ds.dumping:
                await event.answer(pe("🛢 Still dumping..."))
            else:
                total_rows = sum(r.get("rows_dumped", 0) for r in ds.results.values())
                await event.answer(pe(f"📊 {len(ds.results)} URLs | {total_rows} rows dumped"))

        # ── PROXY ──

        elif data == "proxy_scrape":
            if not must_license(uid): return await reject_unlicensed(event, uid)
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
                                     f"<b>🔑 GET LICENSE FROM {CONTACT}</b>"),
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
                buttons=[[Button.inline("🛑 STOP", b"parse_stop"), Button.inline("👀 See Result", b"parse_see_result")]], parse_mode='html'
            )

            def run_parser():
                try:
                    if engine.get_alive_proxies() == 0 and engine.proxy_protocol != "none":
                        _safe_edit(event.chat_id, event.message_id,
                            pe("🛰 <b>No proxies! Auto-scraping...</b>"),
                            buttons=[[Button.inline("🛑 STOP", b"parse_stop"), Button.inline("👀 See Result", b"parse_see_result")]])
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

                    last_text = [""]
                    def update_status():
                        while state.get('running'):
                            time.sleep(5) # Increase sleep to 5s to prevent FloodWait limits
                            if not state.get('running'): break
                            
                            d = engine.dorks_done
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
                                if txt == last_text[0]: continue
                                last_text[0] = txt
                                _safe_edit(event.chat_id, event.message_id, txt,
                                    buttons=[[Button.inline("🛑 STOP", b"parse_stop"), Button.inline("👀 See Result", b"parse_see_result")]])
                            except Exception as ex:
                                if "Flood" in str(ex):
                                    time.sleep(10) # Wait out flood limit
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
                                for t in futs: t.cancel()
                                break
                        executor.shutdown(wait=False)
                        if not state.get('running'): break
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

        elif data == "parse_see_result":
            if not state.get('running'):
                await event.answer(pe("❌ Parser not running!")); return
            res = list(engine.results)
            if not res:
                await event.answer(pe("📭 No URLs extracted yet!")); return
            # Delete all previous temp files for this user
            prev = state.get('_last_see_result_file')
            if prev and os.path.exists(prev):
                try: os.remove(prev)
                except Exception as ex: print(f"[see_result] remove prev: {ex}")
            # Create new temp file with unique name (counter-based)
            counter = state.get('_see_result_counter', 0) + 1
            state['_see_result_counter'] = counter
            fname = os.path.abspath(f"temp_see_result_{uid}_{counter}.txt")
            with open(fname, 'w', encoding='utf-8') as f:
                f.write('\n'.join(res))
            state['_last_see_result_file'] = fname
            # Send file
            await bot.send_file(
                uid, fname,
                caption=pe(f"👀 <b>Live Results</b>\n\n"
                           f"🔗 <b>{fmt(len(res))}</b> URLs extracted so far\n"
                           f"Click 👀 See Result again for updated results."),
                parse_mode='html'
            )
            await event.answer(pe(f"📤 Sent! {fmt(len(res))} URLs"))
            # Schedule deletion after 60s
            def _del(path):
                time.sleep(60)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"[see_result] deleted: {path}")
                except Exception as ex:
                    print(f"[see_result] del error: {ex}")
            t = threading.Thread(target=_del, args=(fname,), daemon=True)
            t.start()

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
    if waiting not in ('dorks', 'proxy_file') and not waiting.startswith('dorkfile_') and waiting != 'kwc_input' and waiting != 'vuln_file':
        await event.reply(pe("ℹ️ Use menu to upload."), buttons=main_buttons(), parse_mode='html'); return
    try:
        path = await event.download_media()
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        os.remove(path)
        if waiting == 'dorks':
            engine.dorks = [l.strip() for l in content.split('\n') if l.strip()]
            txt = pe(f"✅ <b>{fmt(len(engine.dorks))}</b> dorks loaded!")
            state.pop('waiting_for', None)
            await event.reply(txt, buttons=main_buttons(), parse_mode='html')
        elif waiting == 'proxy_file':
            engine.raw_proxies = [l.strip() for l in content.split('\n') if l.strip() and ':' in l]
            engine.dead_proxies = set(); engine.proxies_from_file = True
            txt = pe(f"✅ <b>{fmt(len(engine.raw_proxies))}</b> proxies loaded!")
            state.pop('waiting_for', None)
            await event.reply(txt, buttons=main_buttons(), parse_mode='html')
        elif waiting.startswith('dorkfile_'):
            t = waiting.split("_")[1]
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            if not lines: return await event.reply(pe("❌ File is empty."))
            session = get_dork_session(uid)
            attr = {"kw":"keywords", "ext":"extensions", "param":"parameters"}[t]
            getattr(session, attr).extend(lines)
            session.save()
            state.pop('waiting_for', None)
            btn = [Button.inline("🔙 Back to Edit", f"dork_edit_{t}".encode())]
            await event.reply(pe(f"✅ Loaded <b>{len(lines)}</b> items from file!"), buttons=[btn], parse_mode='html')
        elif waiting == 'kwc_input':
            state['kwc_input'] = content; state.pop('waiting_for', None)
            cs = get_kw_cleaner(uid)
            await event.reply(pe(f"✅ <b>{content.count(chr(10))+1}</b> lines loaded from file!\nClick ⚡ PROCESS NOW to clean."),
                             buttons=[Button.inline("⚡ Process Now", b"kwc_process"),
                                      Button.inline("🔙 Back", b"menu_kw_cleaner")], parse_mode='html')
        elif waiting == 'vuln_file':
            urls = [u.strip() for u in content.split('\n') if u.strip().startswith('http')]
            if not urls: return await event.reply(pe("❌ No valid URLs in file!"))
            vs = get_vuln_session(uid)
            vs.vuln_urls = urls; state.pop('waiting_for', None)
            await event.reply(pe(f"✅ <b>{len(urls)}</b> URLs loaded from file!"), buttons=build_vuln_dash(vs), parse_mode='html')
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
        elif waiting.startswith('dork_'):
            t = waiting.split("_")[1]
            parts = [x.strip() for x in text.split(",") if x.strip()]
            if not parts: return await event.reply(pe("❌ Invalid input."))
            session = get_dork_session(uid)
            if t == "kw": session.keywords.extend(parts)
            elif t == "ext": session.extensions.extend(parts)
            elif t == "param": session.parameters.extend(parts)
            elif t == "cdom": session.custom_domains.extend(parts)
            elif t == "cfmt": session.custom_formats.extend(parts)
            session.save()
            state.pop('waiting_for', None)
            if t == "cdom":
                btn = [Button.inline("🔙 Back to Domains", b"dork_edit_dom")]
            elif t == "cfmt":
                btn = [Button.inline("🔙 Back to Formats", b"dork_edit_fmt")]
            else:
                btn = [Button.inline("🔙 Back to Edit", f"dork_edit_{t}".encode())]
            await event.reply(pe(f"✅ Added {len(parts)} items!"), buttons=[btn], parse_mode='html')
        elif waiting == 'kwc_input':
            state['kwc_input'] = text; state.pop('waiting_for', None)
            cs = get_kw_cleaner(uid)
            await event.reply(pe(f"✅ <b>{text.count(chr(10))+1}</b> lines loaded!\nClick ⚡ PROCESS NOW to clean."),
                             buttons=[Button.inline("⚡ Process Now", b"kwc_process"),
                                      Button.inline("🔙 Back", b"menu_kw_cleaner")], parse_mode='html')
        elif waiting == 'kwc_minlen':
            try:
                v = int(text)
                if not (2 <= v <= 10): raise ValueError
                cs = get_kw_cleaner(uid); cs.min_len = v
                state.pop('waiting_for', None)
                await event.reply(pe(f"✅ Min Length: <b>{v}</b>"), buttons=build_kw_cleaner(cs), parse_mode='html')
            except: await event.reply(pe("❌ Send 2-10."))
        elif waiting == 'kws_seeds':
            seeds = [s.strip().lower() for s in text.split(",") if s.strip()]
            if not seeds: return await event.reply(pe("❌ Invalid input."))
            ss = get_kw_scraper(uid); ss.seeds = seeds
            state.pop('waiting_for', None)
            await event.reply(pe(f"✅ Seeds: <b>{len(seeds)}</b>"), buttons=build_kw_scraper(ss), parse_mode='html')
        elif waiting == 'kws_depth':
            try:
                v = int(text)
                if not (1 <= v <= 3): raise ValueError
                ss = get_kw_scraper(uid); ss.depth = v
                state.pop('waiting_for', None)
                await event.reply(pe(f"✅ Depth: <b>{v}</b>"), buttons=build_kw_scraper(ss), parse_mode='html')
            except: await event.reply(pe("❌ Send 1-3."))
        elif waiting == 'vuln_paste':
            urls = [u.strip() for u in text.split('\n') if u.strip().startswith('http')]
            if not urls: return await event.reply(pe("❌ No valid URLs found!"))
            vs = get_vuln_session(uid)
            vs.vuln_urls = urls; state.pop('waiting_for', None)
            await event.reply(pe(f"✅ <b>{len(urls)}</b> URLs loaded!"), buttons=build_vuln_dash(vs), parse_mode='html')
        elif waiting == 'vuln_threads':
            try:
                v = int(text)
                if not (10 <= v <= 100): raise ValueError
                vs = get_vuln_session(uid); vs.threads = v
                state.pop('waiting_for', None)
                await event.reply(pe(f"✅ Threads: <b>{v}</b>"), buttons=build_vuln_dash(vs), parse_mode='html')
            except: await event.reply(pe("❌ Send 10-100."))
        elif waiting == 'dump_paste':
            parts = text.split("|")
            if len(parts) >= 2:
                url = parts[0].strip()
                param = parts[1].strip()
                if url.startswith("http") and param:
                    ds = get_dump_session(uid)
                    ds.urls.append((url, param))
                    state.pop('waiting_for', None)
                    await event.reply(pe(f"✅ Added: <code>{url[:40]}...</code> [{param}]"), 
                                     buttons=build_dump_dash(ds), parse_mode='html')
                    return
            await event.reply(pe("❌ Format: URL | param"))
        elif waiting.startswith('kg_custom_'):
            try:
                v = int(text)
                unit = waiting.split("_")[2]
                kg = get_keygen(uid)
                if unit == "qty":
                    if not (1 <= v <= 50): raise ValueError
                    kg.qty = v
                    state.pop('waiting_for', None)
                    dur = kg.format_duration()
                    await event.reply(pe(f"✅ Qty: <b>{v}</b> | Duration: <b>{dur}</b>"), 
                                     buttons=build_keygen_confirm(kg), parse_mode='html')
                else:
                    if not (1 <= v <= 10000): raise ValueError
                    if unit == "d": kg.days = v
                    elif unit == "h": kg.hours = v
                    elif unit == "m": kg.mins = v
                    kg.step = "qty"
                    state.pop('waiting_for', None)
                    dur = kg.format_duration()
                    await event.reply(pe(f"✅ Duration: <b>{dur}</b>\n\nSelect quantity:"),
                                     buttons=build_keygen_qty(kg), parse_mode='html')
            except: await event.reply(pe("❌ Invalid number."))
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
    if os.path.exists(fname) and os.path.getsize(fname) > 0:
        await bot.send_file(event.chat_id, fname, caption=pe("📥 Results"), force_document=True)
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
    print(f"🚀 DevParser v2 Bot (Telethon Edition)")
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
