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

USERS, CHATS, MESSAGES, DOCUMENTS, COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD, ACTIVE, STORIES = {}, {}, {}, {}, [0], [], {}, {}, {}, {}, {}, {}

def new_id(p="c"): COUNTER[0] += 1; return p + str(COUNTER[0])
def private_id(a, b): return "p_" + "_".join(sorted([a, b]))

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": USERS, "chats": CHATS, "messages": MESSAGES, "documents": DOCUMENTS, "counter": COUNTER[0], "banned": BANNED, "muted": MUTED, "stickers": STICKERS, "unread": UNREAD, "stories": STORIES}, f, ensure_ascii=False)
    except Exception as e: print("Save error:", e)

def load_data():
    if not os.path.exists(DATA_FILE): return False
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        USERS.clear(); USERS.update(data.get("users", {})); CHATS.clear(); CHATS.update(data.get("chats", {}))
        MESSAGES.clear(); MESSAGES.update(data.get("messages", {})); DOCUMENTS.clear(); DOCUMENTS.update(data.get("documents", {}))
        COUNTER[0] = data.get("counter", 0); BANNED.clear(); BANNED.extend(data.get("banned", []))
        MUTED.clear(); MUTED.update(data.get("muted", {})); STICKERS.clear(); STICKERS.update(data.get("stickers", {}))
        UNREAD.clear(); UNREAD.update(data.get("unread", {})); STORIES.clear(); STORIES.update(data.get("stories", {}))
        return True
    except: return False

def init_default():
    USERS.clear()
    USERS.update({
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True, "avatar": "", "status": "На связи", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": []},
        "Носова Наталья": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": []},
        "Носов Даниил": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": []},
        "Носов Виталий": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": []},
        BOT_NAME: {"password": "bot", "color": "#9c27b0", "avatar": "", "bot": True, "verified": True, "status": "🤖 Я бот", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": []},
    })
    
    CHATS.clear()
    MESSAGES.clear()

    family_members = ["Носова Наталья", "Носов Даниил", "Носов Виталий"]
    for member in family_members:
        cid = private_id("Носов Глеб", member)
        CHATS[cid] = {"type": "private", "name": "", "members": ["Носов Глеб", member], "owner": "", "banned": []}
        MESSAGES[cid] = [{"id": "m_fam_" + member, "from": member, "type": "text", "text": "Привет!", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
        USERS["Носов Глеб"]["pinned"].append(cid)

    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat (Russia) News", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True, "official": True, "avatar": "", "desc": "Официальный канал", "admins": {"Носов Глеб": "Владелец"}, "banned": [], "pinned": ""}
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "Добро пожаловать! 🎉", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
    
    cid_bot = private_id("Носов Глеб", BOT_NAME)
    CHATS[cid_bot] = {"type": "private", "name": "", "members": ["Носов Глеб", BOT_NAME], "owner": "", "banned": []}
    MESSAGES[cid_bot] = [{"id": "m_bot_hello", "from": BOT_NAME, "type": "text", "text": "Привет! /help", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]

    save_data()

if not load_data(): init_default()

def normalize_name(raw): return " ".join(w.capitalize() for w in raw.strip().split())

def run_bot_code(code, text):
    try:
        safe_globals = {"__builtins__": {"len": len, "str": str, "int": int, "float": float, "range": range, "list": list, "dict": dict}}
        local_vars = {}
        exec(code, safe_globals, local_vars)
        if "handle_message" in local_vars:
            return str(local_vars["handle_message"](text))
        return "Ошибка: в коде нет функции handle_message(text)"
    except Exception as e:
        return f"Ошибка бота: {str(e)}"

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
                if name in USERS: await websocket.send_text(json.dumps({"action": "register_fail", "reason": "Имя занято"}))
                else:
                    USERS[name] = {"password": hashlib.md5(m["password"].encode()).hexdigest(), "color": "#2AABEE", "avatar": "", "status": "", "last_seen": 0, "phone": m.get("phone",""), "email": m.get("email",""), "age": 0, "age_group": "", "device": {}, "pinned": []}
                    CHATS[MAIN_ID]["members"].append(name)
                    save_data()
                    await websocket.send_text(json.dumps({"action": "register_ok"}))
                continue

            if a == "login":
                name = normalize_name(m.get("username", ""))
                p = hashlib.md5(m["password"].encode()).hexdigest()
                if name in USERS and USERS[name]["password"] == p:
                    u = name
                    ACTIVE[u] = websocket
                    USERS[u]["last_seen"] = time.time()
                    save_data()
                    
                    my_bots_list = [{"name": b_name} for b_name, b_data in USERS.items() if b_data.get("bot") and b_data.get("owner") == u]
                    
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u, "users": list(USERS.keys()),
                        "chats": [{"id": cid, **ch} for cid, ch in CHATS.items() if u in ch["members"]],
                        "creator": USERS[u].get("creator", False),
                        "verified_users": [n for n, d in USERS.items() if d.get("verified")],
                        "avatars": {n: d.get("avatar", "") for n, d in USERS.items()},
                        "statuses": {n: d.get("status", "") for n, d in USERS.items()},
                        "last_seen": {n: d.get("last_seen", 0) for n, d in USERS.items()},
                        "ages": {n: d.get("age", 0) for n, d in USERS.items()},
                        "age_groups": {n: d.get("age_group", "") for n, d in USERS.items()},
                        "phones": {n: d.get("phone", "") for n, d in USERS.items()},
                        "emails": {n: d.get("email", "") for n, d in USERS.items()},
                        "devices": {n: d.get("device", {}) for n, d in USERS.items()},
                        "pinned": USERS[u].get("pinned", []),
                        "my_bots": my_bots_list,
                        "stories": STORIES
                    }))
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            # ВОССТАНОВЛЕННЫЕ ОБРАБОТЧИКИ ПРОФИЛЯ
            if a == "set_phone":
                USERS[u]["phone"] = (m.get("phone", "") or "").strip()[:30]; save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "phone_update", "username": u, "phone": USERS[u]["phone"]}))
                    except: pass
            elif a == "set_email":
                USERS[u]["email"] = (m.get("email", "") or "").strip()[:50]; save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "email_update", "username": u, "email": USERS[u]["email"]}))
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
            elif a == "set_avatar":
                USERS[u]["avatar"] = m.get("avatar", ""); save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "avatar_update", "username": u, "avatar": USERS[u]["avatar"]}))
                    except: pass
            
            # ОСТАЛЬНОЕ
            elif a == "create_bot":
                bot_name = normalize_name(m.get("name", ""))
                code = m.get("code", "")
                if bot_name in USERS: await websocket.send_text(json.dumps({"action": "error", "message": "Имя занято"}))
                else:
                    USERS[bot_name] = {"password": "bot", "color": "#9c27b0", "bot": True, "owner": u, "code": code, "verified": False}
                    save_data()
                    await websocket.send_text(json.dumps({"action": "bot_created", "bot": {"name": bot_name, "owner": u}}))

            elif a == "delete_bot":
                bot_name = m.get("name")
                if bot_name in USERS and USERS[bot_name].get("owner") == u:
                    del USERS[bot_name]
                    save_data()
                    await websocket.send_text(json.dumps({"action": "bot_deleted", "name": bot_name}))

            elif a == "get_my_bots":
                my_bots_list = [{"name": b_name} for b_name, b_data in USERS.items() if b_data.get("bot") and b_data.get("owner") == u]
                await websocket.send_text(json.dumps({"action": "bots_list", "bots": my_bots_list}))

            elif a == "create_channel":
                cid = new_id("ch_")
                CHATS[cid] = {"type": "channel", "name": m.get("name"), "members": [u], "owner": u, "verified": False, "admins": {u: "Владелец"}, "banned": [], "pinned": ""}
                MESSAGES[cid] = []
                save_data()
                await websocket.send_text(json.dumps({"action": "channel_created", "chat_id": cid, "chat": CHATS[cid]}))
                
            elif a == "create_group":
                cid = new_id("gr_")
                CHATS[cid] = {"type": "group", "name": m.get("name"), "members": [u], "owner": u, "verified": False, "admins": {u: "Владелец"}, "banned": [], "pinned": ""}
                MESSAGES[cid] = []
                save_data()
                await websocket.send_text(json.dumps({"action": "channel_created", "chat_id": cid, "chat": CHATS[cid]}))

            elif a == "add_story":
                STORIES[u] = {"image": m.get("image", ""), "time": datetime.now().strftime("%H:%M")}
                save_data()
                for w in ACTIVE.values():
                    try: await w.send_text(json.dumps({"action": "stories_updated", "stories": STORIES}))
                    except: pass

            elif a == "set_pin":
                cid = m.get("chat_id")
                if cid:
                    if "pinned" not in USERS[u]: USERS[u]["pinned"] = []
                    if cid in USERS[u]["pinned"]: USERS[u]["pinned"].remove(cid)
                    else: USERS[u]["pinned"].append(cid)
                    save_data()
                    await websocket.send_text(json.dumps({"action": "pins_updated", "pinned": USERS[u]["pinned"]}))

            elif a == "open_chat":
                cid = m.get("chat_id")
                if cid in CHATS and u in CHATS[cid]["members"]:
                    await websocket.send_text(json.dumps({"action": "chat_opened", "chat_id": cid, "chat": CHATS[cid], "messages": MESSAGES.get(cid, [])}))
            
            elif a == "open_private":
                cid = private_id(u, m["with"])
                if cid not in CHATS:
                    CHATS[cid] = {"type": "private", "members": [u, m["with"]]}
                    MESSAGES[cid] = []
                    save_data()
                await websocket.send_text(json.dumps({"action": "chat_opened", "chat_id": cid, "chat": CHATS[cid], "messages": MESSAGES.get(cid, [])}))

            elif a == "message":
                cid = m["chat_id"]
                if cid in CHATS and u in CHATS[cid]["members"]:
                    msg = {"id": new_id("m"), "from": u, "type": m.get("type", "text"), "text": m.get("text", ""), "data": m.get("data", ""), "time": datetime.now().strftime("%H:%M")}
                    MESSAGES[cid].append(msg)
                    save_data()
                    
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE and member != u:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                            except: pass
                    
                    for member in CHATS[cid]["members"]:
                        if member != u and USERS.get(member, {}).get("bot"):
                            bot_code = USERS[member].get("code", "")
                            if bot_code and msg["type"] == "text":
                                reply_text = run_bot_code(bot_code, msg["text"])
                                bot_msg = {"id": new_id("m"), "from": member, "type": "text", "text": reply_text, "data": "", "time": datetime.now().strftime("%H:%M")}
                                MESSAGES[cid].append(bot_msg)
                                save_data()
                                if u in ACTIVE:
                                    try: await ACTIVE[u].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": bot_msg}))
                                    except: pass

            elif a == "get_doc":
                doc_id = m.get("doc_id")
                if doc_id in DOCUMENTS:
                    await websocket.send_text(json.dumps({"action": "doc_data", "doc_id": doc_id, "title": DOCUMENTS[doc_id]["title"], "text": DOCUMENTS[doc_id]["text"]}))

            elif a == "save_doc":
                doc_id, title, text = m.get("doc_id"), m.get("title"), m.get("text")
                if doc_id not in DOCUMENTS: DOCUMENTS[doc_id] = {"title": title, "text": text}
                else: DOCUMENTS[doc_id]["text"] = text
                save_data()

            elif a == "search_users":
                query = m.get("query", "").lower()
                await websocket.send_text(json.dumps({"action": "search_results", "results": [name for name in USERS.keys() if query in name.lower() and name != u]}))

    except WebSocketDisconnect:
        if u: ACTIVE.pop(u, None)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)
