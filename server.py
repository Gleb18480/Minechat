# -*- coding: utf-8 -*-
import os, json, hashlib, time
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

USERS, CHATS, MESSAGES, DOCUMENTS, COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD, ACTIVE = {}, {}, {}, {}, [0], [], {}, {}, {}, {}, {}
PREMIUM_REQS = {} # {username: {"tier": "premium"|"vip", "duration": "1m"|"1y"}}

def new_id(p="c"):
    COUNTER[0] += 1
    return p + str(COUNTER[0])

def private_id(a, b): 
    return "p_" + "_".join(sorted([a, b]))

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": USERS, "chats": CHATS, "messages": MESSAGES, "documents": DOCUMENTS, "counter": COUNTER[0], "banned": BANNED, "muted": MUTED, "stickers": STICKERS, "unread": UNREAD, "premium_reqs": PREMIUM_REQS}, f, ensure_ascii=False)
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
        PREMIUM_REQS.clear(); PREMIUM_REQS.update(data.get("premium_reqs", {}))
        return True
    except Exception as e: return False

def init_default():
    USERS.clear()
    USERS.update({
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True, "tier": "vip", "tier_until": 9999999999, "custom_emoji": "👑", "custom_color": "#FFD700", "avatar": "", "status": "На связи", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}},
        "Носова Наталья": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}},
        "Носов Даниил": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}},
        "Носов Виталий": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}},
        "Александр (kiberone)": {"password": hashlib.md5("k1b4r076§¶".encode()).hexdigest(), "color": "#f44336", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}},
        BOT_NAME: {"password": "bot", "color": "#9c27b0", "avatar": "", "bot": True, "verified": True, "status": "🤖 Я бот", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}},
    })
    CHATS.clear()
    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat (Russia) News", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True, "official": True, "avatar": "", "desc": "Официальный канал", "admins": {"Носов Глеб": "Владелец"}, "banned": [], "pinned": ""}
    MESSAGES.clear()
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "Добро пожаловать! 🎉", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
    for uname in list(USERS.keys()):
        if uname == BOT_NAME: continue
        cid_bot = private_id(uname, BOT_NAME)
        CHATS[cid_bot] = {"type": "private", "name": "", "members": [uname, BOT_NAME], "owner": "", "banned": []}
        MESSAGES[cid_bot] = [{"id": "m_bot_hello_" + uname, "from": BOT_NAME, "type": "text", "text": "Привет! /help", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
    save_data()

if not load_data(): init_default()

def check_premium_expiration():
    now = time.time()
    changed = False
    for u, d in USERS.items():
        if d.get("tier") in ["premium", "vip"] and d.get("tier_until", 0) < now:
            d["tier"] = "free"
            d["custom_emoji"] = ""
            d["custom_color"] = ""
            changed = True
    if changed: save_data()

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

def run_bot_code(code, text):
    try:
        safe_globals = {"__builtins__": {"len": len, "str": str, "int": int, "float": float, "range": range, "list": list, "dict": dict}}
        local_vars = {}
        exec(code, safe_globals, local_vars)
        if "handle_message" in local_vars: return str(local_vars["handle_message"](text))
        return "Ошибка: в коде нет функции handle_message(text)"
    except Exception as e: return f"Ошибка бота: {str(e)}"

def bot_reply(user, text):
    cid = private_id(user, BOT_NAME)
    cmd = text.strip(); low = cmd.lower(); reply = ""
    if low.startswith("/start") or low.startswith("/help"): reply = "🤖 /newpack Имя — пак\n/addsticker — фото\n/packs — паки\n/usepack N — выбрать"
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
    else: reply = "🤖 /help"
    
    msg = {"id": new_id("m"), "from": BOT_NAME, "type": "text", "text": reply, "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
    MESSAGES[cid].append(msg); save_data()
    return cid, msg

async def send_bot(user, text):
    cid, msg = bot_reply(user, text)
    if user in ACTIVE:
        try: await ACTIVE[user].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
        except: pass

async def send_to_user(username, payload):
    if username in ACTIVE:
        for ws in ACTIVE[username]:
            try: await ws.send_text(json.dumps(payload))
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
                    USERS[name] = {"password": hashlib.md5(m["password"].encode()).hexdigest(), "color": "#9c27b0", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "tier": "free"}
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
                check_premium_expiration()
                name = normalize_name(m.get("username", ""))
                real_name = next((existing for existing in USERS.keys() if existing.lower() == name.lower()), None)
                p = hashlib.md5(m["password"].encode()).hexdigest()
                if real_name and real_name in BANNED: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "🚫 Забанен"}))
                elif real_name and USERS[real_name]["password"] == p:
                    u = real_name; ACTIVE.setdefault(u, []).append(websocket); USERS[u]["last_seen"] = time.time(); save_data()
                    
                    # Собираем инфу о подписках
                    tiers_info = {n: {"tier": d.get("tier", "free"), "emoji": d.get("custom_emoji", ""), "color": d.get("custom_color", "")} for n, d in USERS.items()}
                    
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u, "color": USERS[u]["color"], "users": list(USERS.keys()), "chats": user_chats(u),
                        "creator": USERS[u].get("creator", False), "verified_users": [n for n, d in USERS.items() if d.get("verified")],
                        "avatars": {n: d.get("avatar", "") for n, d in USERS.items()}, "statuses": {n: d.get("status", "") for n, d in USERS.items()},
                        "last_seen": {n: d.get("last_seen", 0) for n, d in USERS.items()}, "ages": {n: d.get("age", 0) for n, d in USERS.items()},
                        "age_groups": {n: d.get("age_group", "") for n, d in USERS.items()}, "phones": {n: d.get("phone", "") for n, d in USERS.items()},
                        "emails": {n: d.get("email", "") for n, d in USERS.items()}, "devices": {n: d.get("device", {}) for n, d in USERS.items()},
                        "banned": BANNED, "muted": MUTED, "my_muted": is_muted(u),
                        "tiers": tiers_info, # Отправляем стили
                        "premium_reqs": PREMIUM_REQS,
                        "stickers": {p: {"owner": STICKERS[p]["owner"], "count": len(STICKERS[p]["stickers"])} for p in STICKERS},
                        "verify_req": VERIFY_REQ, "unread": UNREAD.get(u, {})
                    }))
                    await broadcast_online()
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            # === PREMIUM / VIP ЛОГИКА ===
            if a == "request_premium":
                tier = m.get("tier", "premium")
                duration = m.get("duration", "1m")
                if USERS[u].get("tier") in ["premium", "vip"]:
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "У вас уже есть статус!"}))
                    continue
                PREMIUM_REQS[u] = {"tier": tier, "duration": duration}
                save_data()
                for admin_name, admin_data in USERS.items():
                    if admin_data.get("creator"):
                        await send_to_user(admin_name, {"action": "new_premium_req", "from": u, "tier": tier, "duration": duration})
                await websocket.send_text(json.dumps({"action": "error_msg", "text": "✅ Заявка отправлена! Ожидайте подтверждения."}))

            elif a == "approve_premium" and USERS.get(u, {}).get("creator"):
                target = m.get("target")
                tier = m.get("tier", "premium")
                duration = m.get("duration", "1m")
                if target in USERS:
                    days = 365 if duration == "1y" else 30
                    USERS[target]["tier"] = tier
                    USERS[target]["tier_until"] = time.time() + (days * 86400)
                    
                    if target in PREMIUM_REQS: del PREMIUM_REQS[target]
                    save_data()
                    
                    tiers_info = {n: {"tier": d.get("tier", "free"), "emoji": d.get("custom_emoji", ""), "color": d.get("custom_color", "")} for n, d in USERS.items()}
                    for w in ACTIVE.values():
                        for ws_conn in w:
                            try: await ws_conn.send_text(json.dumps({"action": "tier_update", "tiers": tiers_info, "premium_reqs": PREMIUM_REQS}))
                            except: pass
                    if target in ACTIVE:
                        await send_to_user(target, {"action": "error_msg", "text": f"🎉 Заявка одобрена! Теперь у вас статус {tier.upper()} на {days} дней."})
            
            # НАСТРОЙКА PREMIUM (Эмодзи и Цвет)
            elif a == "set_premium_features":
                if USERS[u].get("tier") in ["premium", "vip"]:
                    emoji = m.get("emoji", "")
                    color = m.get("color", "")
                    USERS[u]["custom_emoji"] = emoji
                    if USERS[u]["tier"] == "vip": # Цвет только для VIP
                        USERS[u]["custom_color"] = color
                    save_data()
                    
                    tiers_info = {n: {"tier": d.get("tier", "free"), "emoji": d.get("custom_emoji", ""), "color": d.get("custom_color", "")} for n, d in USERS.items()}
                    for w in ACTIVE.values():
                        for ws_conn in w:
                            try: await ws_conn.send_text(json.dumps({"action": "tier_update", "tiers": tiers_info}))
                            except: pass

            elif a == "set_device":
                USERS[u]["device"] = m.get("device", {}); save_data()
            elif a == "set_email": USERS[u]["email"] = (m.get("email", "") or "").strip()[:50]; save_data()
            elif a == "set_phone": USERS[u]["phone"] = (m.get("phone", "") or "").strip()[:30]; save_data()
            elif a == "set_age_group":
                try: age = int(m.get("age", 0))
                except: age = 0
                group = m.get("group", "")
                USERS[u]["age"] = age; USERS[u]["age_group"] = group; save_data()
            elif a == "set_status": USERS[u]["status"] = (m.get("status", "") or "").strip()[:100]; save_data()
            elif a == "set_avatar": USERS[u]["avatar"] = m.get("avatar", ""); save_data()
            
            elif a == "request_verify":
                VERIFY_REQ[u] = {"from": u, "status": "pending"}; save_data()
                admin = "Носов Глеб"
                if admin in ACTIVE:
                    try: await send_to_user(admin, {"action": "incoming_verify_call", "from": u})
                    except: pass
                await websocket.send_text(json.dumps({"action": "verify_sent"}))

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
                                await send_to_user(member, {"action": "messages_read", "chat_id": cid, "reader": u})
            elif a == "get_doc":
                doc_id = m.get("doc_id")
                if doc_id in DOCUMENTS:
                    await websocket.send_text(json.dumps({"action": "doc_data", "doc_id": doc_id, "title": DOCUMENTS[doc_id]["title"], "text": DOCUMENTS[doc_id]["text"]}))
            elif a == "save_doc":
                doc_id, title, text = m.get("doc_id"), m.get("title"), m.get("text")
                if doc_id not in DOCUMENTS: DOCUMENTS[doc_id] = {"title": title, "text": text}
                else: DOCUMENTS[doc_id]["text"] = text; DOCUMENTS[doc_id]["title"] = title
                save_data()

            elif a == "open_private":
                other = m["with"]; cid = ensure_private(u, other); clear_unread(u, cid)
                await websocket.send_text(json.dumps({"action": "chat_opened", "chat_id": cid, "chat": CHATS[cid], "messages": MESSAGES.get(cid, []), "unread": UNREAD.get(u, {})}))
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
                                try: await websocket.send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": echo}))
                                except: pass
                            await send_bot(u, "/_sticker_saved")
                            continue
                    if mtype == "text":
                        msg = {"id": new_id("m"), "from": u, "type": "text", "text": m.get("text", ""), "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}
                        MESSAGES[cid].append(msg); save_data()
                        if u in ACTIVE:
                            try: await websocket.send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
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
                    if member in ACTIVE: await send_to_user(member, {"action": "new_message", "chat_id": cid, "msg": msg})
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE and member != u:
                        try: await send_to_user(member, {"action": "unread_update", "unread": UNREAD.get(member, {})})
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
                            if member in ACTIVE: await send_to_user(member, {"action": "reaction_update", "chat_id": cid, "msg_id": mid, "reactions": msg["reactions"]})
                        break
            elif a == "delete":
                cid, mid = m["chat_id"], m["msg_id"]
                MESSAGES[cid] = [x for x in MESSAGES.get(cid, []) if x["id"] != mid]; save_data()
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE: await send_to_user(member, {"action": "msg_deleted", "chat_id": cid, "msg_id": mid})
            elif a == "edit":
                cid, mid, new_text = m["chat_id"], m["msg_id"], m["text"]
                for msg in MESSAGES.get(cid, []):
                    if msg["id"] == mid and (msg["from"] == u or is_chat_admin(cid, u)):
                        msg["text"] = new_text; msg["edited"] = True; break
                save_data()
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE: await send_to_user(member, {"action": "msg_edited", "chat_id": cid, "msg_id": mid, "text": new_text})
            elif a in ("call_offer", "call_answer", "call_decline", "call_end", "webrtc"):
                to = m["to"]
                if USERS.get(to, {}).get("bot"):
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "Ботам звонить нельзя!"}))
                    continue
                if to in ACTIVE:
                    await send_to_user(to, {"action": {"call_offer": "incoming_call", "call_answer": "call_accepted", "call_decline": "call_declined", "call_end": "call_ended", "webrtc": "webrtc"}[a], "from": u, "data": m.get("data")})

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
                            await send_to_user(member, {"action": "new_message", "chat_id": cid, "msg": msg})
                    await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))
                    if receiver in ACTIVE:
                        await send_to_user(receiver, {"action": "balance_update", "coins": USERS[receiver]["coins"]})
                else: await websocket.send_text(json.dumps({"action": "error_msg", "text": "Недостаточно монет!"}))

    except WebSocketDisconnect:
        if u:
            USERS[u]["last_seen"] = time.time()
            if u in ACTIVE and websocket in ACTIVE[u]: ACTIVE[u].remove(websocket)
            if u in ACTIVE and not ACTIVE[u]: del ACTIVE[u]
            save_data()
        await broadcast_online()

async def broadcast_online():
    online = list(ACTIVE.keys())
    last_seen = {n: d.get("last_seen", 0) for n, d in USERS.items()}
    for w in ACTIVE.values():
        for ws_conn in w:
            try: await ws_conn.send_text(json.dumps({"action": "online", "users": online, "last_seen": last_seen}))
            except: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)
