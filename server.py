# -*- coding: utf-8 -*-
import os, json, hashlib, time
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Пути к файлам
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "minechat_data.json")
INDEX_FILE = os.path.join(BASE, "index.html")

BOT_NAME = "Minechat Бот"
MAIN_ID = "main_channel"

# Хранилища данных
USERS, CHATS, MESSAGES, DOCUMENTS, STORIES = {}, {}, {}, {}, {}
COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD = [0], [], {}, {}, {}, {}
ACTIVE = {} # Активные WebSocket подключения

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "users": USERS, "chats": CHATS, "messages": MESSAGES,
                "documents": DOCUMENTS, "stories": STORIES, "counter": COUNTER[0],
                "banned": BANNED, "muted": MUTED, "stickers": STICKERS,
                "verify_req": VERIFY_REQ, "unread": UNREAD
            }, f, ensure_ascii=False)
    except Exception as e:
        print("Ошибка сохранения:", e)

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
    except Exception as e:
        print("Ошибка загрузки:", e)
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
            "bot": True, "verified": True, "status": "Я бот",
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
        "text": "Добро пожаловать в Minechat!", "data": "", "mime": "",
        "fname": "", "reply_to": "", "reactions": {}, "edited": False,
        "time": datetime.now().strftime("%H:%M"), "read_by": []
    }]
    save_data()

# Инициализация при старте
if not load_data():
    init_default()

def new_id(p="c"):
    COUNTER[0] += 1
    return p + str(COUNTER[0])

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
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    u = None
    try:
        while True:
            raw = await websocket.receive_text()
            m = json.loads(raw)
            a = m.get("action")

            # --- АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ---
            if a == "register":
                name = normalize_name(m.get("username", ""))
                password = m.get("password", "123")
                p = hashlib.md5(password.encode()).hexdigest()

                if name_exists(name):
                    # Если имя есть, пробуем войти
                    real_name = next((x for x in USERS.keys() if x.lower() == name.lower()), None)
                    if real_name and real_name in USERS and USERS[real_name]["password"] == p:
                        u = real_name
                        if u not in ACTIVE: ACTIVE[u] = []
                        ACTIVE[u].append(websocket)
                        USERS[u]["last_seen"] = time.time()
                        save_data()
                        
                        # Собираем данные для клиента
                        chats = [{"id": cid, **ch} for cid, ch in CHATS.items() if u in ch["members"]]
                        main_msgs = MESSAGES.get(MAIN_ID, [])
                        
                        await websocket.send_text(json.dumps({
                            "action": "login_ok", "username": u, "color": USERS[u]["color"],
                            "chats": chats, "messages": main_msgs,
                            "verified_users": [n for n, d in USERS.items() if d.get("verified")]
                        }))
                    else:
                        await websocket.send_text(json.dumps({"action": "register_fail", "reason": "Имя занято или неверный пароль"}))
                else:
                    # Регистрация нового
                    USERS[name] = {
                        "password": p, "color": "#9c27b0", "avatar": "", "status": "",
                        "last_seen": 0, "phone": m.get("phone", ""), "email": m.get("email", ""),
                        "age": 0, "age_group": "", "device": {}, "pinned": []
                    }
                    if MAIN_ID in CHATS:
                        CHATS[MAIN_ID]["members"].append(name)
                    save_data()
                    await websocket.send_text(json.dumps({"action": "register_ok"}))
                continue

            if not u:
                continue

            # --- ОТПРАВКА СООБЩЕНИЙ ---
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
                
                for member in CHATS[cid]["members"]:
                    if member != BOT_NAME:
                        await send_to_user(member, {"action": "new_message", "chat_id": cid, "msg": msg})
                        
            # --- СОЗДАНИЕ КАНАЛА ---
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
                    "action": "channel_created", "chat_id": new_cid, "chat": CHATS[new_cid]
                }))

            # --- ЗАПРОС ГАЛОЧКИ ---
            elif a == "request_verify":
                if u in VERIFY_REQ:
                    await websocket.send_text(json.dumps({"action": "error", "message": "Вы уже отправили запрос на верификацию."}))
                else:
                    VERIFY_REQ[u] = {"time": time.time()}
                    save_data()
                    # Уведомляем создателя
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)
