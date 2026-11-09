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

USERS, CHATS, MESSAGES, DOCUMENTS, COUNTER, BANNED, MUTED, VERIFY_REQ, UNREAD, ACTIVE, STORIES = {}, {}, {}, {}, [0], [], {}, {}, {}, {}, {}

def new_id(p="c"): COUNTER[0] += 1; return p + str(COUNTER[0])
def private_id(a, b): return "p_" + "_".join(sorted([a, b]))

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": USERS, "chats": CHATS, "messages": MESSAGES, "documents": DOCUMENTS, "counter": COUNTER[0], "banned": BANNED, "muted": MUTED, "unread": UNREAD, "stories": STORIES}, f, ensure_ascii=False)
    except Exception as e: print("Save error:", e)

def load_data():
    if not os.path.exists(DATA_FILE): return False
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        USERS.update(data.get("users", {})); CHATS.update(data.get("chats", {}))
        MESSAGES.update(data.get("messages", {})); DOCUMENTS.update(data.get("documents", {}))
        COUNTER[0] = data.get("counter", 0); BANNED.extend(data.get("banned", []))
        MUTED.update(data.get("muted", {})); UNREAD.update(data.get("unread", {}))
        STORIES.update(data.get("stories", {}))
        return True
    except: return False

def init_default():
    USERS.update({
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True},
        BOT_NAME: {"password": "bot", "color": "#9c27b0", "bot": True, "verified": True}
    })
    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat News", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True}
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "Добро пожаловать!", "time": datetime.now().strftime("%H:%M")}]
    save_data()

if not load_data(): init_default()

def normalize_name(raw): return " ".join(w.capitalize() for w in raw.strip().split())

def run_bot_code(code, text):
    try:
        # Безопасное выполнение Python
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
                    USERS[name] = {"password": hashlib.md5(m["password"].encode()).hexdigest(), "color": "#2AABEE", "pinned": [], "phone": m.get("phone",""), "email": m.get("email","")}
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
                    save_data()
                    
                    my_bots_list = [{"name": b_name} for b_name, b_data in USERS.items() if b_data.get("bot") and b_data.get("owner") == u]
                    
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u, "users": list(USERS.keys()),
                        "chats": [{"id": cid, **ch} for cid, ch in CHATS.items() if u in ch["members"]],
                        "creator": USERS[u].get("creator", False),
                        "verified_users": [n for n, d in USERS.items() if d.get("verified")],
                        "pinned": USERS[u].get("pinned", []),
                        "my_bots": my_bots_list,
                        "stories": STORIES
                    }))
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            if a == "create_bot":
                bot_name = normalize_name(m.get("name", ""))
                code = m.get("code", "")
                if bot_name in USERS:
                    await websocket.send_text(json.dumps({"action": "error", "message": "Бот с таким именем уже существует"}))
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
                CHATS[cid] = {"type": "channel", "name": m.get("name"), "members": [u], "owner": u, "verified": False}
                MESSAGES[cid] = []
                save_data()
                await websocket.send_text(json.dumps({"action": "channel_created", "chat_id": cid, "chat": CHATS[cid]}))
                
            elif a == "create_group":
                cid = new_id("gr_")
                CHATS[cid] = {"type": "group", "name": m.get("name"), "members": [u], "owner": u, "verified": False}
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
