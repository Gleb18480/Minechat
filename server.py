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
USERS, CHATS, MESSAGES, DOCUMENTS, STORIES, COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD = {}, {}, {}, {}, {}, [0], [], {}, {}, {}, {}
ACTIVE = {}

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "users": USERS, "chats": CHATS, "messages": MESSAGES,
                "documents": DOCUMENTS, "stories": STORIES, "counter": COUNTER[0],
                "banned": BANNED, "muted": MUTED, "stickers": STICKERS,
                "verify_req": VERIFY_REQ, "unread": UNREAD
            }, f, ensure_ascii=False)
    except Exception:
        pass

def load_data():
    if not os.path.exists(DATA_FILE): return False
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        USERS.update(data.get("users", {}))
        CHATS.update(data.get("chats", {}))
        MESSAGES.update(data.get("messages", {}))
        DOCUMENTS.update(data.get("documents", {}))
        STORIES.update(data.get("stories", {}))
        COUNTER[0] = data.get("counter", 0)
        BANNED.extend(data.get("banned", []))
        MUTED.update(data.get("muted", {}))
        STICKERS.update(data.get("stickers", {}))
        VERIFY_REQ.update(data.get("verify_req", {}))
        UNREAD.update(data.get("unread", {}))
        return True
    except Exception:
        return False

def init_default():
    USERS.clear()
    USERS.update({
        "Носов Глеб": {
            "password": hashlib.md5("310315".encode()).hexdigest(),
            "color": "#2196f3", "creator": True, "verified": True,
            "avatar": "", "status": "На связи", "last_seen": 0,
            "phone": "", "email": "", "age": 0, "age_group": "",
            "device": {}, "pinned": []
        },
        BOT_NAME: {
            "password": "bot", "color": "#9c27b0", "avatar": "",
            "bot": True, "verified": True, "status": " Я бот",
            "last_seen": 0, "phone": "", "email": "", "age": 0,
            "age_group": "", "device": {}, "pinned": []
        },
    })
    CHATS[MAIN_ID] = {
        "type": "channel", "name": "Minechat News",
        "members": list(USERS.keys()), "owner": "Носов Глеб",
        "verified": True, "official": True, "avatar": "",
        "desc": "Новости", "admins": {"Носов Глеб": "Владелец"},
        "banned": [], "pinned": ""
    }
    MESSAGES[MAIN_ID] = [{
        "id": "m_welcome", "from": "Носов Глеб", "type": "text",
        "text": "Добро пожаловать! ", "data": "", "mime": "",
        "fname": "", "reply_to": "", "reactions": {}, "edited": False,
        "time": datetime.now().strftime("%H:%M"), "read_by": []
    }]
    save_data()

if not load_data():
    init_default()

def new_id(p="c"):
    COUNTER[0] += 1
    return p + str(COUNTER[0])

def private_id(a, b):
    return "p_" + "_".join(sorted([a, b]))

def ensure_private(a, b):
    cid = private_id(a, b)
    if cid not in CHATS:
        CHATS[cid] = {"type": "private", "name": "", "members": [a, b], "owner": "", "banned": []}
        MESSAGES[cid] = []
        save_data()
    return cid

def normalize_name(raw):
    return " ".join(w.capitalize() for w in raw.strip().split())

def name_exists(name):
    n = name.lower()
    return any(existing.lower() == n for existing in USERS.keys()) or any(banned.lower() == n for banned in BANNED)

async def send_to_user(username, payload):
    if username in ACTIVE:
        for ws in ACTIVE[username]:
            try:
                await ws.send_text(json.dumps(payload))
            except:
                pass

@app.get("/")
def root():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    u = None
    try:
        while True:
            raw = await websocket.receive_text()
            m = json.loads(raw)
            a = m.get("action")

            if a == "register":
                name = normalize_name(m.get("username", ""))
                if name_exists(name):
                    await websocket.send_text(json.dumps({"action": "register_fail", "reason": "Имя занято"}))
                else:
                    USERS[name] = {
                        "password": hashlib.md5(m["password"].encode()).hexdigest(),
                        "color": "#9c27b0", "avatar": "", "status": "",
                        "last_seen": 0, "phone": m.get("phone", ""),
                        "email": m.get("email", ""), "age": 0,
                        "age_group": "", "device": {}, "pinned": []
                    }
                    if MAIN_ID in CHATS:
                        CHATS[MAIN_ID]["members"].append(name)
                    save_data()
                    await websocket.send_text(json.dumps({"action": "register_ok"}))
                continue

            if a == "login":
                name = normalize_name(m.get("username", ""))
                real_name = next((x for x in USERS.keys() if x.lower() == name.lower()), None)
                p = hashlib.md5(m["password"].encode()).hexdigest()
                if real_name and real_name in BANNED:
                    await websocket.send_text(json.dumps({"action": "login_fail", "reason": " Забанен"}))
                elif real_name and USERS[real_name]["password"] == p:
                    u = real_name
                    if u not in ACTIVE:
                        ACTIVE[u] = []
                    ACTIVE[u].append(websocket)
                    USERS[u]["last_seen"] = time.time()
                    save_data()
                    chats = [{"id": cid, **ch} for cid, ch in CHATS.items() if u in ch["members"]]
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u, "color": USERS[u]["color"],
                        "users": list(USERS.keys()), "chats": chats,
                        "creator": USERS[u].get("creator", False),
                        "verified_users": [n for n, d in USERS.items() if d.get("verified")],
                        "avatars": {n: d.get("avatar", "") for n, d in USERS.items()},
                        "statuses": {n: d.get("status", "") for n, d in USERS.items()},
                        "last_seen": {n: d.get("last_seen", 0) for n, d in USERS.items()},
                        "ages": {n: d.get("age", 0) for n, d in USERS.items()},
                        "age_groups": {n: d.get("age_group", "") for n, d in USERS.items()},
                        "phones": {n: d.get("phone", "") for n, d in USERS.items()},
                        "emails": {n: d.get("email", "") for n, d in USERS.items()},
                        "pinned": USERS[u].get("pinned", []),
                        "stickers": {p: {"owner": STICKERS[p]["owner"], "count": len(STICKERS[p]["stickers"])} for p in STICKERS},
                        "unread": UNREAD.get(u, {}), "stories": STORIES
                    }))
                    await broadcast_online()
                else:
                    await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u:
                continue

            if a == "message":
                cid = m["chat_id"]
                if cid not in CHATS or u not in CHATS[cid]["members"]:
                    continue
                msg = {
                    "id": new_id("m"), "from": u, "type": m.get("type", "text"),
                    "text": m.get("text", ""), "data": m.get("data", ""),
                    "mime": m.get("mime", ""), "fname": m.get("fname", ""),
                    "reply_to": m.get("reply_to", ""), "reactions": {},
                    "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []
                }
                MESSAGES[cid].append(msg)
                save_data()
                if m.get("type") == "doc":
                    DOCUMENTS[msg["id"]] = {"title": m.get("text", "Документ"), "text": ""}
                    save_data()
                for member in CHATS[cid]["members"]:
                    if member != BOT_NAME:
                        await send_to_user(member, {"action": "new_message", "chat_id": cid, "msg": msg})
            elif a == "set_pin":
                cid = m.get("chat_id")
                pinned = USERS[u].setdefault("pinned", [])
                if cid in pinned:
                    pinned.remove(cid)
                else:
                    pinned.append(cid)
                save_data()
                await websocket.send_text(json.dumps({"action": "pins_updated", "pinned": pinned}))
            elif a == "add_story":
                STORIES[u] = {"image": m.get("image", ""), "time": datetime.now().strftime("%H:%M")}
                save_data()
                for w in ACTIVE.values():
                    for sock in w:
                        try:
                            await sock.send_text(json.dumps({"action": "stories_updated", "stories": STORIES}))
                        except:
                            pass
            elif a == "search_users":
                q = m.get("query", "").lower()
                res = [name for name in USERS.keys() if q in name.lower() and name != u]
                await websocket.send_text(json.dumps({"action": "search_results", "results": res}))
            elif a == "open_chat":
                cid = m["chat_id"]
                if cid in CHATS and u in CHATS[cid]["members"]:
                    if u in UNREAD and cid in UNREAD[u]:
                        del UNREAD[u][cid]
                    await websocket.send_text(json.dumps({
                        "action": "chat_opened", "chat_id": cid,
                        "chat": CHATS[cid], "messages": MESSAGES.get(cid, []),
                        "unread": UNREAD.get(u, {})
                    }))
            elif a == "open_private":
                other = m["with"]
                cid = ensure_private(u, other)
                if u in UNREAD and cid in UNREAD[u]:
                    del UNREAD[u][cid]
                await websocket.send_text(json.dumps({
                    "action": "chat_opened", "chat_id": cid,
                    "chat": CHATS[cid], "messages": MESSAGES.get(cid, []),
                    "unread": UNREAD.get(u, {})
                }))
            elif a == "get_doc":
                doc_id = m.get("doc_id")
                if doc_id in DOCUMENTS:
                    await websocket.send_text(json.dumps({
                        "action": "doc_data", "doc_id": doc_id,
                        "title": DOCUMENTS[doc_id]["title"], "text": DOCUMENTS[doc_id]["text"]
                    }))
            elif a == "save_doc":
                doc_id, title, text = m.get("doc_id"), m.get("title"), m.get("text")
                if doc_id not in DOCUMENTS:
                    DOCUMENTS[doc_id] = {"title": title, "text": text}
                else:
                    DOCUMENTS[doc_id]["text"] = text
                    DOCUMENTS[doc_id]["title"] = title
                save_data()
                for cid, msgs in MESSAGES.items():
                    for msg in msgs:
                        if msg["id"] == doc_id:
                            msg["text"] = title
                for member in CHATS[cid]["members"]:
                    await send_to_user(member, {"action": "msg_edited", "chat_id": cid, "msg_id": msg["id"], "text": title})
            elif a == "forward":
                to_cid = m.get("to_chat")
                msg_data = m.get("msg")
                if to_cid in CHATS and u in CHATS[to_cid]["members"]:
                    msg_data["id"] = new_id("m")
                    msg_data["forwarded_from"] = msg_data["from"]
                    msg_data["from"] = u
                    msg_data["read_by"] = []
                    MESSAGES[to_cid].append(msg_data)
                    save_data()
                    for member in CHATS[to_cid]["members"]:
                        if member != BOT_NAME:
                            await send_to_user(member, {"action": "new_message", "chat_id": to_cid, "msg": msg_data})
            elif a in ("call_offer", "call_answer", "call_decline", "call_end", "webrtc"):
                to = m["to"]
                act = {
                    "call_offer": "incoming_call", "call_answer": "call_accepted",
                    "call_decline": "call_declined", "call_end": "call_ended",
                    "webrtc": "webrtc"
                }[a]
                await send_to_user(to, {"action": act, "from": u, "data": m.get("data")})

            # --- НОВЫЕ ОБРАБОТЧИКИ ---
            elif a == "create_channel":
                channel_name = m.get("name", "").strip()
                if not channel_name:
                    await websocket.send_text(json.dumps({"action": "error", "message": "Название канала не может быть пустым"}))
                    continue
                new_cid = new_id("ch_")
                CHATS[new_cid] = {
                    "type": "channel", "name": channel_name,
                    "members": [u], "owner": u, "verified": False,
                    "official": False, "avatar": "", "desc": "",
                    "admins": {u: "Владелец"}, "banned": [], "pinned": ""
                }
                MESSAGES[new_cid] = []
                save_data()
                await websocket.send_text(json.dumps({
                    "action": "channel_created", "chat_id": new_cid,
                    "chat": CHATS[new_cid]
                }))

            elif a == "request_verify":
                if u in VERIFY_REQ:
                    await websocket.send_text(json.dumps({"action": "error", "message": "Вы уже отправили запрос на верификацию. Ожидайте."}))
                else:
                    VERIFY_REQ[u] = {"time": time.time()}
                    save_data()
                    # Уведомляем владельца (создателя) о новом запросе
                    for admin_name, admin_data in USERS.items():
                        if admin_data.get("creator"):
                            await send_to_user(admin_name, {
                                "action": "new_verify_request",
                                "from": u,
                                "message": f"Пользователь {u} запрашивает галочку."
                            })
                    await websocket.send_text(json.dumps({"action": "verify_request_sent", "message": "Запрос на галочку отправлен!"}))

    except WebSocketDisconnect:
        if u and u in ACTIVE:
            if websocket in ACTIVE[u]:
                ACTIVE[u].remove(websocket)
            if not ACTIVE[u]:
                del ACTIVE[u]
            USERS[u]["last_seen"] = time.time()
            save_data()
            await broadcast_online()

async def broadcast_online():
    online = list(ACTIVE.keys())
    last_seen = {n: d.get("last_seen", 0) for n, d in USERS.items()}
    for sockets in ACTIVE.values():
        for w in sockets:
            try:
                await w.send_text(json.dumps({"action": "online", "users": online, "last_seen": last_seen}))
            except:
                pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)