# -*- coding: utf-8 -*-
"""
Bot License System (Telegram-ID based)
- Admin generates keys with an expiry (in days).
- Users redeem a key -> it binds to their Telegram user ID.
- No HWID (that is only for the desktop exe). This is separate from key_system.py.
"""
import os, json, time, secrets, threading

# Admin(s) allowed to generate keys
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "8669173066").split(",") if x.strip().isdigit()}

# Persistent data file (set BOT_DATA_DIR on Railway to a mounted volume for persistence)
_DATA_DIR = os.environ.get("BOT_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
_DATA_FILE = os.path.join(_DATA_DIR, "bot_licenses.json")

_lock = threading.RLock()


def _load():
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"keys": {}, "users": {}}


def _save(data):
    tmp = _DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _DATA_FILE)


def is_admin(user_id) -> bool:
    try:
        return int(user_id) in ADMIN_IDS
    except Exception:
        return False


def _make_key() -> str:
    raw = secrets.token_hex(6).upper()  # 12 hex chars
    return "DPV1-" + "-".join(raw[i:i + 4] for i in range(0, 12, 4))


def generate_key(days: int = 30, note: str = "") -> str:
    """Create a new unredeemed key valid for `days` after it is redeemed. days<=0 => lifetime."""
    with _lock:
        data = _load()
        key = _make_key()
        while key in data["keys"]:
            key = _make_key()
        data["keys"][key] = {
            "days": int(days),
            "created": int(time.time()),
            "note": note,
            "redeemed_by": None,
            "redeemed_at": None,
        }
        _save(data)
        return key


def redeem_key(key: str, user_id, name: str = "", username: str = "") -> dict:
    """Bind a key to a Telegram user. Returns {ok, message, expiry}."""
    key = (key or "").strip().upper()
    with _lock:
        data = _load()
        info = data["keys"].get(key)
        if not info:
            return {"ok": False, "message": "Invalid key. Check and try again."}
        if info.get("suspended"):
            return {"ok": False, "message": "This key is suspended. Contact @devtronex."}
        if info.get("redeemed_by") not in (None, str(user_id), int(user_id)):
            return {"ok": False, "message": "This key is already used by another user."}

        now = int(time.time())
        days = int(info.get("days", 0))
        expiry = 0 if days <= 0 else now + days * 86400

        info["redeemed_by"] = str(user_id)
        info["redeemed_at"] = now
        data["users"][str(user_id)] = {
            "expiry": expiry,
            "name": name,
            "username": username,
            "key": key,
            "activated": now,
            "status": "active",
        }
        _save(data)
        return {"ok": True, "message": "License activated!", "expiry": expiry}


def get_license(user_id) -> dict:
    """Return current license status for a user."""
    with _lock:
        data = _load()
        u = data["users"].get(str(user_id))
    if is_admin(user_id):
        return {"valid": True, "admin": True, "expiry": 0, "lifetime": True,
                "name": (u or {}).get("name", ""), "username": (u or {}).get("username", ""),
                "key": (u or {}).get("key", "ADMIN")}
    if not u:
        return {"valid": False, "message": "No license. Get a free key from @devtronex."}
    if u.get("status") == "suspended":
        return {"valid": False, "message": "Your license is SUSPENDED. Contact @devtronex.",
                "suspended": True, "expiry": u.get("expiry", 0), "name": u.get("name", ""),
                "username": u.get("username", ""), "key": u.get("key", "")}
    expiry = u.get("expiry", 0)
    if expiry and time.time() > expiry:
        return {"valid": False, "message": "License expired. Get a new key from @devtronex.",
                "expiry": expiry, "name": u.get("name", ""), "username": u.get("username", ""),
                "key": u.get("key", "")}
    days_left = 0 if not expiry else max(0, int((expiry - time.time()) // 86400))
    return {"valid": True, "admin": False, "expiry": expiry, "lifetime": expiry == 0,
            "days_left": days_left, "name": u.get("name", ""), "username": u.get("username", ""),
            "key": u.get("key", ""), "activated": u.get("activated", 0)}


def list_users() -> list:
    """All users that hold a key (no-key users are never stored). Newest first."""
    with _lock:
        data = _load()
    out = []
    for uid, u in data["users"].items():
        expiry = u.get("expiry", 0)
        if u.get("status") == "suspended":
            status = "suspended"
        elif expiry and time.time() > expiry:
            status = "expired"
        else:
            status = "active"
        out.append({
            "user_id": uid,
            "username": u.get("username", ""),
            "name": u.get("name", ""),
            "key": u.get("key", ""),
            "expiry": expiry,
            "status": status,
        })
    return out[::-1]  # newest first (dict keeps insertion/redeem order)


def suspend_user(user_id) -> dict:
    """Suspend a user's license and their key. (Punishment: expiry does NOT change,
    the suspended days are lost and the timer keeps running.)"""
    with _lock:
        data = _load()
        u = data["users"].get(str(user_id))
        if not u:
            return {"ok": False, "message": "User not found."}
        u["status"] = "suspended"
        k = data["keys"].get(u.get("key", ""))
        if k:
            k["suspended"] = True
        _save(data)
        return {"ok": True, "message": "User suspended.", "key": u.get("key", "")}


def unsuspend_user(user_id) -> dict:
    """Re-activate a suspended user + key. Expiry is unchanged — the days spent
    suspended are NOT given back (suspension is a punishment)."""
    with _lock:
        data = _load()
        u = data["users"].get(str(user_id))
        if not u:
            return {"ok": False, "message": "User not found."}
        u["status"] = "active"
        k = data["keys"].get(u.get("key", ""))
        if k:
            k["suspended"] = False
        _save(data)
        return {"ok": True, "message": "User re-activated (expiry unchanged).", "key": u.get("key", "")}


def delete_user(user_id) -> dict:
    """Permanently delete a user AND their key (key cannot be reused)."""
    with _lock:
        data = _load()
        u = data["users"].pop(str(user_id), None)
        if not u:
            return {"ok": False, "message": "User not found."}
        data["keys"].pop(u.get("key", ""), None)  # remove key permanently
        _save(data)
        return {"ok": True, "message": "User & key permanently deleted.", "key": u.get("key", "")}


def list_keys() -> list:
    """Admin helper: all keys with status."""
    with _lock:
        data = _load()
    out = []
    for k, v in data["keys"].items():
        out.append({"key": k, "days": v.get("days"), "redeemed_by": v.get("redeemed_by")})
    return out
