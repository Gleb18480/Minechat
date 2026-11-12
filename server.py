# -*- coding: utf-8 -*-
import os, json, hashlib, time, random
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "minechat_data.json")
INDEX_FILE = os.path.join(BASE, "index.html")
BOT_NAME = "Minechat Бот"
MAIN_ID = "main_channel"

# ПРОМОКОДЫ
PROMO_CODES = {
    "MINE2025": 500,
    "NEWYEAR": 1000,
    "KIBERONE": 2000
}

USERS, CHATS, MESSAGES, DOCUMENTS, COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD, ACTIVE = {}, {}, {}, {}, [0], [], {}, {}, {}, {}, {}

def new_id(p="c"):
    COUNTER[0] += 1
    return p + str(COUNTER[0])

def private_id(a, b): 
    return "p_" + "_".join(sorted([a, b]))

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": USERS, "chats": CHATS, "messages": MESSAGES, "documents": DOCUMENTS, "counter": COUNTER[0], "banned": BANNED, "muted": MUTED, "stickers": STICKERS, "unread": UNREAD}, f, ensure_ascii=False)
    except Exception as e: print("Save error:", e)

def load_data():
    if not os.path.exists(DATA_FILE): return False
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        USERS.clear(); USERS.update(data.get("users", {}))
        CHATS.clear(); CHATS.update(data.get("chats", {}))
        MESSAGES.clear(); MESSAGES.update(data.get("messages", {}))
        DOCUMENTS.clear(); DOCUMENTS.update(data.get("documents", {}))
        COUNTER[0] = data.get("counter", 0)
        BANNED.clear(); BANNED.extend(data.get("banned", []))
        MUTED.clear(); MUTED.update(data.get("muted", {}))
        STICKERS.clear(); STICKERS.update(data.get("stickers", {}))
        UNREAD.clear(); UNREAD.update(data.get("unread", {}))
        return True
    except Exception as e: return False

def init_default():
    USERS.clear()
    USERS.update({
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True, "avatar": "", "status": "С наступающим!", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 5000, "ny_bonus": False, "used_promos": []},
        "Носова Наталья": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        "Носов Даниил": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        "Носов Виталий": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        "Александр (kiberone)": {"password": hashlib.md5("k1b4r076§¶".encode()).hexdigest(), "color": "#f44336", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        BOT_NAME: {"password": "bot", "color": "#9c27b0", "avatar": "", "bot": True, "verified": True, "status": "🎅 Эльф", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 0, "ny_bonus": True, "used_promos": []},
    })
    CHATS.clear()
    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat (Russia) News", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True, "official": True, "avatar": "", "desc": "Официальный канал", "admins": {"Носов Глеб": "Владелец"}, "banned": [], "pinned": ""}
    MESSAGES.clear()
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "🎄 С Наступающим Новым Годом! 🎄", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
    for uname in list(USERS.keys()):
        if uname == BOT_NAME: continue
        cid_bot = private_id(uname, BOT_NAME)
        CHATS[cid_bot] = {"type": "private", "name": "", "members": [uname, BOT_NAME], "owner": "", "banned": []}
        MESSAGES[cid_bot] = [{"id": "m_bot_hello_" + uname, "from": BOT_NAME, "type": "text", "text": "Привет! /help", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
    save_data()

if not load_data(): init_default()

def ensure_private(a, b):
    cid = private_id(a, b)
    if cid not in CHATS:
        CHATS[cid] = {"type": "private", "name": "", "members": [a, b], "owner": "", "banned": []}
        MESSAGES[cid] = []
        save_data()
    return cid

def user_chats(u): return [{"id": cid, **ch} for cid, ch in CHATS.items() if u in ch["members"]]
def normalize_name(raw): return " ".join(w.capitalize() for w in raw.strip().split())

def name_exists(name):
    n = name.lower()
    return any(existing.lower() == n for existing in USERS.keys()) or any(banned.lower() == n for banned in BANNED)

def is_muted(u):
    if u not in MUTED: return False
    if MUTED[u] == "forever": return True
    if time.time() > MUTED[u]:
        del MUTED[u]; save_data(); return False
    return True

def is_chat_admin(cid, u):
    if cid not in CHATS: return False
    ch = CHATS[cid]
    return USERS.get(u, {}).get("creator") or ch.get("owner") == u or u in ch.get("admins", {})

def bump_unread(cid, sender):
    for member in CHATS[cid]["members"]:
        if member in (sender, BOT_NAME): continue
        UNREAD.setdefault(member, {})
        UNREAD[member][cid] = UNREAD[member].get(cid, 0) + 1

def clear_unread(u, cid):
    if u in UNREAD and cid in UNREAD[u]:
        del UNREAD[u][cid]; save_data()

def bot_reply(user, text):
    cid = private_id(user, BOT_NAME)
    cmd = text.strip(); low = cmd.lower(); reply = ""
    if low.startswith("/start") or low.startswith("/help"): reply = "🎅 С Новым Годом! /newpack Имя — пак\n/addsticker — фото\n/packs — паки\n/usepack N — выбрать"
    elif low.startswith("/newpack"):
        name = cmd[8:].strip()
        if not name: reply = "❌ /newpack Кошки"
        elif name in STICKERS: reply = "❌ Уже есть"
        else:
            STICKERS[name] = {"owner": user, "stickers": []}
            USERS[user]["active_pack"] = name
            save_data(); reply = "✅ Пак «" + name + "» создан."
    elif low.startswith("/usepack"):
        try:
            n = int(cmd[8:].strip())
            my_packs = [p for p in STICKERS if STICKERS[p]["owner"] == user]
            if 1 <= n <= len(my_packs):
                USERS[user]["active_pack"] = my_packs[n-1]; save_data(); reply = "✅ Активный: «" + my_packs[n-1] + "»"
            else: reply = "❌ Нет такого номера"
        except: reply = "❌ /usepack 1"
    elif low.startswith("/packs"):
        my_packs = [p for p in STICKERS if STICKERS[p]["owner"] == user]
        if not my_packs: reply = "Нет паков. /newpack Имя"
        else: reply = "📦 Твои паки:\n" + "\n".join(f"{i}. {p} ({len(STICKERS[p]['stickers'])})" for i, p in enumerate(my_packs, 1))
    elif low.startswith("/addsticker"):
        active = USERS.get(user, {}).get("active_pack")
        if not active: reply = "❌ Сначала /newpack"
        else: USERS[user]["await_sticker"] = True; save_data(); reply = "📷 Пришли фото"
    elif low == "/_sticker_saved": reply = "✅ Стикер добавлен!"
    else: reply = "🎅 /help"
    
    msg = {"id": new_id("m"), "from": BOT_NAME, "type": "text", "text": reply, "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
    MESSAGES[cid].append(msg); save_data()
    return cid, msg

async def send_bot(user, text):
    cid, msg = bot_reply(user, text)
    if user in ACTIVE:
        try: await ACTIVE[user].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
        except: pass

@app.get("/")
def root():
    with open(INDEX_FILE, "r", encoding="utf-8") as f: return HTMLResponse(f.read())

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    u = None
    try:
        while True:
            raw = await websocket.receive_text()
            m = json.loads(raw); a = m.get("action")

            if a == "register":
                name = normalize_name(m.get("username", ""))
                if name_exists(name): await websocket.send_text(json.dumps({"action": "register_fail", "reason": "Имя занято"}))
                else:
                    USERS[name] = {"password": hashlib.md5(m["password"].encode()).hexdigest(), "color": "#9c27b0", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []}
                    if MAIN_ID in CHATS: CHATS[MAIN_ID]["members"].append(name)
                    cid_bot = private_id(name, BOT_NAME)
                    if cid_bot not in CHATS:
                        CHATS[cid_bot] = {"type": "private", "name": "", "members": [name, BOT_NAME], "owner": "", "banned": []}
                        MESSAGES[cid_bot] = [{"id": "m_bot_hello_" + name, "from": BOT_NAME, "type": "text", "text": "Привет! /help", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
                    save_data()
                    await websocket.send_text(json.dumps({"action": "register_ok"}))
                    await broadcast_online()
                continue

            if a == "login":
                name = normalize_name(m.get("username", ""))
                real_name = next((existing for existing in USERS.keys() if existing.lower() == name.lower()), None)
                p = hashlib.md5(m["password"].encode()).hexdigest()
                if real_name and real_name in BANNED: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "🚫 Забанен"}))
                elif real_name and USERS[real_name]["password"] == p:
                    u = real_name; ACTIVE[u] = websocket; USERS[u]["last_seen"] = time.time(); save_data()
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u, "color": USERS[u]["color"], "users": list(USERS.keys()), "chats": user_chats(u),
                        "creator": USERS[u].get("creator", False), "verified_users": [n for n, d in USERS.items() if d.get("verified")],
                        "avatars": {n: d.get("avatar", "") for n, d in USERS.items()}, "statuses": {n: d.get("status", "") for n, d in USERS.items()},
                        "last_seen": {n: d.get("last_seen", 0) for n, d in USERS.items()}, "ages": {n: d.get("age", 0) for n, d in USERS.items()},
                        "age_groups": {n: d.get("age_group", "") for n, d in USERS.items()}, "phones": {n: d.get("phone", "") for n, d in USERS.items()},
                        "emails": {n: d.get("email", "") for n, d in USERS.items()}, "devices": {n: d.get("device", {}) for n, d in USERS.items()},
                        "banned": BANNED, "muted": MUTED, "my_muted": is_muted(u), "coins": {n: d.get("coins", 0) for n, d in USERS.items()},
                        "ny_bonus": USERS[u].get("ny_bonus", False),
                        "stickers": {p: {"owner": STICKERS[p]["owner"], "count": len(STICKERS[p]["stickers"])} for p in STICKERS},
                        "verify_req": VERIFY_REQ, "unread": UNREAD.get(u, {})
                    }))
                    await broadcast_online()
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            # --- НОВОГОДНИЙ БОНУС И ПРОМОКОДЫ ---
            if a == "claim_ny_bonus":
                if not USERS[u].get("ny_bonus", False):
                    USERS[u]["coins"] += 1000
                    USERS[u]["ny_bonus"] = True
                    save_data()
                    await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "🎉 Вы получили 1000 монет на Новогодние подарки!"}))
                else:
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "Вы уже забирали новогодний бонус!"}))

            elif a == "activate_promo":
                code = m.get("code", "").strip().upper()
                if code in PROMO_CODES:
                    if code in USERS[u].get("used_promos", []):
                        await websocket.send_text(json.dumps({"action": "error_msg", "text": "Вы уже использовали этот промокод!"}))
                    else:
                        USERS[u].setdefault("used_promos", []).append(code)
                        USERS[u]["coins"] += PROMO_CODES[code]
                        save_data()
                        await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))
                        await websocket.send_text(json.dumps({"action": "error_msg", "text": f"✅ Промокод активирован! Вы получили {PROMO_CODES[code]} монет!"}))
                else:
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "❌ Неверный промокод!"}))

            elif a == "set_device":
                USERS[u]["device"] = m.get("device", {}); save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "device_update", "username": u, "device": USERS[u]["device"]}))
                    except: pass
            elif a == "set_email":
                USERS[u]["email"] = (m.get("email", "") or "").strip()[:50]; save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "email_update", "username": u, "email": USERS[u]["email"]}))
                    except: pass
            elif a == "set_phone":
                USERS[u]["phone"] = (m.get("phone", "") or "").strip()[:30]; save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "phone_update", "username": u, "phone": USERS[u]["phone"]}))
                    except: pass
            elif a == "set_age_group":
                try: age = int(m.get("age", 0))
                except: age = 0
                group = m.get("group", "")
                USERS[u]["age"] = age; USERS[u]["age_group"] = group; save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "age_update", "username": u, "age": age, "age_group": group}))
                    except: pass
            elif a == "set_status":
                USERS[u]["status"] = (m.get("status", "") or "").strip()[:100]; save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "status_update", "username": u, "status": USERS[u]["status"]}))
                    except: pass
            elif a == "clear_history":
                cid = m.get("chat_id", "")
                if cid in CHATS and (is_chat_admin(cid, u) or CHATS[cid]["type"] == "private"):
                    MESSAGES[cid] = []; save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "history_cleared", "chat_id": cid}))
                            except: pass
            elif a == "create_poll":
                cid = m.get("chat_id", ""); question = (m.get("question", "") or "").strip(); options = m.get("options", [])
                if cid in CHATS and question and len(options) >= 2:
                    msg = {"id": new_id("m"), "from": u, "type": "poll", "text": question, "data": "", "mime": "", "fname": "", "options": options, "votes": {}, "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
                    MESSAGES[cid].append(msg); save_data(); bump_unread(cid, u)
                    for member in CHATS[cid]["members"]:
                        if member == BOT_NAME: continue
                        if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
            elif a == "vote":
                cid, mid = m.get("chat_id"), m.get("msg_id"); idx = m.get("option", -1)
                for msg in MESSAGES.get(cid, []):
                    if msg["id"] == mid and msg["type"] == "poll":
                        votes = msg.setdefault("votes", {})
                        for k in list(votes.keys()):
                            if u in votes[k]: votes[k].remove(u)
                        votes.setdefault(str(idx), []).append(u); save_data()
                        for member in CHATS[cid]["members"]:
                            if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "poll_update", "chat_id": cid, "msg_id": mid, "votes": votes}))
                        break
            elif a == "get_sticker_pack":
                pname = m.get("pack", "")
                if pname in STICKERS: await websocket.send_text(json.dumps({"action": "sticker_pack_data", "pack": pname, "stickers": STICKERS[pname]["stickers"]}))
            elif a == "request_verify":
                VERIFY_REQ[u] = {"from": u, "status": "pending"}; save_data()
                admin = "Носов Глеб"
                if admin in ACTIVE:
                    try: await ACTIVE[admin].send_text(json.dumps({"action": "incoming_verify_call", "from": u}))
                    except: pass
                await websocket.send_text(json.dumps({"action": "verify_sent"}))
            elif a == "verify_answer" and USERS.get(u, {}).get("creator"):
                target = m.get("target", ""); ok = m.get("ok", False)
                if target in USERS:
                    if ok:
                        USERS[target]["verified"] = True; save_data()
                        if target in ACTIVE:
                            try: await ACTIVE[target].send_text(json.dumps({"action": "you_verified"}))
                            except: pass
                    VERIFY_REQ.pop(target, None)
                    for w in ACTIVE.values():
                        try: await w.send_text(json.dumps({"action": "verify_update", "verified_users": [n for n, d in USERS.items() if d.get("verified")], "verify_req": VERIFY_REQ}))
                        except: pass
            elif a in ("ban", "unban", "mute", "unmute") and USERS.get(u, {}).get("creator"):
                target = m.get("target", "")
                if target not in USERS or USERS[target].get("creator"): continue
                if a == "ban":
                    if target not in BANNED: BANNED.append(target)
                    if target in ACTIVE:
                        try: await ACTIVE[target].send_text(json.dumps({"action": "you_banned"}))
                        except: pass
                elif a == "unban":
                    if target in BANNED: BANNED.remove(target)
                elif a == "mute":
                    dur = m.get("duration", "5m")
                    if dur == "forever": MUTED[target] = "forever"
                    else: MUTED[target] = time.time() + {"5m": 300, "1h": 3600, "1d": 86400}.get(dur, 300)
                    if target in ACTIVE:
                        try: await ACTIVE[target].send_text(json.dumps({"action": "you_muted", "duration": dur}))
                        except: pass
                elif a == "unmute": MUTED.pop(target, None)
                save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "admin_update", "banned": BANNED, "muted": MUTED}))
                    except: pass
            elif a == "set_avatar":
                USERS[u]["avatar"] = m.get("avatar", ""); save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "avatar_update", "username": u, "avatar": USERS[u]["avatar"]}))
                    except: pass
            elif a == "set_chat_avatar":
                cid = m.get("chat_id", "")
                if cid in CHATS and is_chat_admin(cid, u):
                    CHATS[cid]["avatar"] = m.get("avatar", ""); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "chat_update", "chat_id": cid, "chat": CHATS[cid]}))
                            except: pass
            elif a == "rename_chat":
                cid = m.get("chat_id", ""); new_name = (m.get("name", "") or "").strip()
                if cid in CHATS and new_name and is_chat_admin(cid, u):
                    CHATS[cid]["name"] = new_name; save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "chat_update", "chat_id": cid, "chat": CHATS[cid]}))
                            except: pass
            elif a == "set_chat_desc":
                cid = m.get("chat_id", ""); desc = (m.get("desc", "") or "").strip()
                if cid in CHATS and is_chat_admin(cid, u):
                    CHATS[cid]["desc"] = desc; save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "chat_update", "chat_id": cid, "chat": CHATS[cid]}))
                            except: pass
            elif a == "add_member":
                cid = m.get("chat_id", ""); target = m.get("target", "")
                if cid in CHATS and target in USERS and is_chat_admin(cid, u) and target not in CHATS[cid]["members"]:
                    CHATS[cid]["members"].append(target)
                    if "banned" in CHATS[cid] and target in CHATS[cid]["banned"]: CHATS[cid]["banned"].remove(target)
                    save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "chat_update", "chat_id": cid, "chat": CHATS[cid]}))
                            except: pass
            elif a == "kick":
                cid = m.get("chat_id", ""); target = m.get("target", "")
                if cid in CHATS and is_chat_admin(cid, u) and target != u and target in CHATS[cid]["members"]:
                    CHATS[cid]["members"].remove(target); save_data()
                    if target in ACTIVE:
                        try: await ACTIVE[target].send_text(json.dumps({"action": "you_kicked", "chat_id": cid}))
                        except: pass
            elif a == "pin_message":
                cid = m.get("chat_id", ""); mid = m.get("msg_id", "")
                if cid in CHATS and is_chat_admin(cid, u):
                    CHATS[cid]["pinned"] = mid; save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "chat_update", "chat_id": cid, "chat": CHATS[cid]}))
                            except: pass

            elif a == "mark_read":
                cid = m.get("chat_id")
                if cid in CHATS:
                    changed = False
                    for msg in MESSAGES.get(cid, []):
                        if u not in msg.get("read_by", []) and msg["from"] != u:
                            msg.setdefault("read_by", []).append(u); changed = True
                    if changed:
                        save_data()
                        for member in CHATS[cid]["members"]:
                            if member in ACTIVE and member != u:
                                try: await ACTIVE[member].send_text(json.dumps({"action": "messages_read", "chat_id": cid, "reader": u}))
                                except: pass
            elif a == "get_doc":
                doc_id = m.get("doc_id")
                if doc_id in DOCUMENTS:
                    await websocket.send_text(json.dumps({"action": "doc_data", "doc_id": doc_id, "title": DOCUMENTS[doc_id]["title"], "text": DOCUMENTS[doc_id]["text"]}))
            elif a == "save_doc":
                doc_id, title, text = m.get("doc_id"), m.get("title"), m.get("text")
                if doc_id not in DOCUMENTS: DOCUMENTS[doc_id] = {"title": title, "text": text}
                else: DOCUMENTS[doc_id]["text"] = text; DOCUMENTS[doc_id]["title"] = title
                save_data()
                for cid, msgs in MESSAGES.items():
                    for msg in msgs:
                        if msg["id"] == doc_id:
                            msg["text"] = title
                            for member in CHATS[cid]["members"]:
                                if member in ACTIVE:
                                    try: await ACTIVE[member].send_text(json.dumps({"action": "msg_edited", "chat_id": cid, "msg_id": msg["id"], "text": title}))
                                    except: pass

            elif a == "open_private":
                other = m["with"]; cid = ensure_private(u, other); clear_unread(u, cid)
                await websocket.send_text(json.dumps({"action": "chat_opened", "chat_id": cid, "chat": CHATS[cid], "messages": MESSAGES.get(cid, []), "unread": UNREAD.get(u, {})}))
            elif a == "create_chat":
                cid = new_id("c")
                CHATS[cid] = {"type": m["type"], "name": m["name"], "members": [u] + m.get("members", []), "owner": u, "verified": False, "avatar": "", "desc": "", "admins": {u: "Владелец"}, "banned": [], "pinned": ""}
                MESSAGES[cid] = []; save_data()
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "chat_created", "chat_id": cid, "chat": CHATS[cid]}))
            elif a == "open_chat":
                cid = m["chat_id"]
                if cid in CHATS and u in CHATS[cid]["members"]:
                    clear_unread(u, cid)
                    await websocket.send_text(json.dumps({"action": "chat_opened", "chat_id": cid, "chat": CHATS[cid], "messages": MESSAGES.get(cid, []), "unread": UNREAD.get(u, {})}))
            elif a == "message":
                cid = m["chat_id"]
                if cid not in CHATS or u not in CHATS[cid]["members"] or u in CHATS[cid].get("banned", []): continue

                is_bot_chat = (BOT_NAME in CHATS[cid]["members"])
                if is_bot_chat and u != BOT_NAME:
                    mtype = m.get("type", "text")
                    if USERS.get(u, {}).get("await_sticker") and mtype in ("image", "sticker"):
                        active = USERS[u].get("active_pack")
                        if active and active in STICKERS:
                            STICKERS[active]["stickers"].append(m.get("data", "")); USERS[u]["await_sticker"] = False; save_data()
                            echo = {"id": new_id("m"), "from": u, "type": "image", "text": "", "data": m.get("data", ""), "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
                            MESSAGES[cid].append(echo); save_data()
                            if u in ACTIVE:
                                try: await ACTIVE[u].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": echo}))
                                except: pass
                            await send_bot(u, "/_sticker_saved")
                            for w in ACTIVE.values():
                                try: await w.send_text(json.dumps({"action": "stickers_update", "stickers": {p: {"owner": STICKERS[p]["owner"], "count": len(STICKERS[p]["stickers"])} for p in STICKERS}}))
                                except: pass
                            continue
                    if mtype == "text":
                        msg = {"id": new_id("m"), "from": u, "type": "text", "text": m.get("text", ""), "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
                        MESSAGES[cid].append(msg); save_data()
                        if u in ACTIVE:
                            try: await ACTIVE[u].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                            except: pass
                        await send_bot(u, m.get("text", ""))
                        continue

                if CHATS[cid]["type"] == "channel" and not is_chat_admin(cid, u): continue
                if is_muted(u):
                    await websocket.send_text(json.dumps({"action": "mute_warning"}))
                    continue
                msg = {"id": new_id("m"), "from": u, "type": m.get("type", "text"), "text": m.get("text", ""), "data": m.get("data", ""), "mime": m.get("mime", ""), "fname": m.get("fname", ""), "reply_to": m.get("reply_to", ""), "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
                MESSAGES[cid].append(msg); save_data(); bump_unread(cid, u)
                if m.get("type") == "doc":
                    DOCUMENTS[msg["id"]] = {"title": m.get("text", "Документ"), "text": ""}
                    save_data()
                for member in CHATS[cid]["members"]:
                    if member == BOT_NAME: continue
                    if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE and member != u:
                        try: await ACTIVE[member].send_text(json.dumps({"action": "unread_update", "unread": UNREAD.get(member, {})}))
                        except: pass
            elif a == "react":
                cid, mid, emoji = m["chat_id"], m["msg_id"], m["emoji"]
                for msg in MESSAGES.get(cid, []):
                    if msg["id"] == mid:
                        users = msg.setdefault("reactions", {}).get(emoji, [])
                        if u in users: users.remove(u)
                        else: users.append(u)
                        msg["reactions"][emoji] = users; save_data()
                        for member in CHATS[cid]["members"]:
                            if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "reaction_update", "chat_id": cid, "msg_id": mid, "reactions": msg["reactions"]}))
                        break
            elif a == "delete":
                cid, mid = m["chat_id"], m["msg_id"]
                MESSAGES[cid] = [x for x in MESSAGES.get(cid, []) if x["id"] != mid]; save_data()
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "msg_deleted", "chat_id": cid, "msg_id": mid}))
            elif a == "edit":
                cid, mid, new_text = m["chat_id"], m["msg_id"], m["text"]
                for msg in MESSAGES.get(cid, []):
                    if msg["id"] == mid and (msg["from"] == u or is_chat_admin(cid, u)):
                        msg["text"] = new_text; msg["edited"] = True; break
                save_data()
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "msg_edited", "chat_id": cid, "msg_id": mid, "text": new_text}))
            elif a in ("call_offer", "call_answer", "call_decline", "call_end", "webrtc"):
                to = m["to"]
                if USERS.get(to, {}).get("bot"):
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "Ботам звонить нельзя!"}))
                    continue
                if to in ACTIVE:
                    await ACTIVE[to].send_text(json.dumps({"action": {"call_offer": "incoming_call", "call_answer": "call_accepted", "call_decline": "call_declined", "call_end": "call_ended", "webrtc": "webrtc"}[a], "from": u, "data": m.get("data")}))

            # ПОДАРКИ
            elif a == "send_gift":
                cid = m["chat_id"]; cost = int(m.get("cost", 0))
                if USERS[u].get("coins", 0) >= cost:
                    USERS[u]["coins"] -= cost
                    receiver = [x for x in CHATS[cid]["members"] if x != u][0]
                    if receiver in USERS: USERS[receiver]["coins"] = USERS[receiver].get("coins", 0) + (cost // 2)
                    save_data()
                    msg = {"id": new_id("m"), "from": u, "type": "gift", "text": m.get("name"), "data": m.get("icon"), "time": datetime.now().strftime("%H:%M")}
                    MESSAGES[cid].append(msg); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                            except: pass
                    await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))
                    if receiver in ACTIVE:
                        try: await ACTIVE[receiver].send_text(json.dumps({"action": "balance_update", "coins": USERS[receiver]["coins"]}))
                        except: pass
                else: await websocket.send_text(json.dumps({"action": "error_msg", "text": "Недостаточно монет!"}))

    except WebSocketDisconnect:
        if u:
            USERS[u]["last_seen"] = time.time(); ACTIVE.pop(u, None); save_data()
        await broadcast_online()

async def broadcast_online():
    online = list(ACTIVE.keys())
    last_seen = {n: d.get("last_seen", 0) for n, d in USERS.items()}
    for w in ACTIVE.values():
        try: await w.send_text(json.dumps({"action": "online", "users": online, "last_seen": last_seen}))
        except: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)
