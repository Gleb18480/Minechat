# -*- coding: utf-8 -*-
import os, json, hashlib, time, random, asyncio
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

PROMO_CODES = {"MINE2025": 500, "NEWYEAR": 1000, "KIBERONE": 2000}

USERS, CHATS, MESSAGES, DOCUMENTS, COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD, ACTIVE = {}, {}, {}, {}, [0], [], {}, {}, {}, {}, {}
GAME_ROOMS = {}
CITIES_DB = ["Москва","Астрахань","Новгород","Рига","Анкара","Архангельск","Курск","Казань","Новосибирск","Кемерово","Омск","Киев","Волгоград","Дубай","Йошкар-Ола","Абакан","Нальчик","Калининград","Донецк","Краснодар","Ростов","Тула","Анапа","Алматы","Львов","Воронеж","Женева","Амстердам","Минск","Красноярск","Кишинев","Владивосток","Курган","Норильск","Киров","Винница","Ашхабад","Душанбе","Ереван","Нижний Новгород","Копенгаген","Нью-Йорк","Канберра","Аделаида","Алжир","Рим","Милан","Неаполь","Лондон","Лиссабон","Нарва","Афины","Никосия","Ялта","Алушта","Ярославль","Липецк"]

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
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True, "avatar": "", "status": "На связи", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 5000, "ny_bonus": False, "used_promos": []},
        "Носова Наталья": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        "Носов Даниил": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        "Носов Виталий": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        "Александр (kiberone)": {"password": hashlib.md5("k1b4r076§¶".encode()).hexdigest(), "color": "#f44336", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000, "ny_bonus": False, "used_promos": []},
        BOT_NAME: {"password": "bot", "color": "#9c27b0", "avatar": "", "bot": True, "verified": True, "status": "🤖 Я бот", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 0, "ny_bonus": True, "used_promos": []},
    })
    CHATS.clear()
    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat (Russia) News", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True, "official": True, "avatar": "", "desc": "Официальный канал", "admins": {"Носов Глеб": "Владелец"}, "banned": [], "pinned": ""}
    MESSAGES.clear()
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "🎄 С Наступающим Новым Годом! 🎄", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
    
    for m in ["Носова Наталья", "Носов Даниил", "Носов Виталий"]:
        cid = private_id("Носов Глеб", m)
        CHATS[cid] = {"type": "private", "name": "", "members": ["Носов Глеб", m], "owner": "", "banned": []}
        MESSAGES[cid] = [{"id": "m_fam", "from": m, "type": "text", "text": "Привет!", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]
        USERS["Носов Глеб"]["pinned"].append(cid)
        
    cid_alex = private_id("Носов Глеб", "Александр (kiberone)")
    CHATS[cid_alex] = {"type": "private", "name": "", "members": ["Носов Глеб", "Александр (kiberone)"], "owner": "", "banned": []}
    MESSAGES[cid_alex] = [{"id": "m_alex", "from": "Александр (kiberone)", "type": "text", "text": "Привет!", "data": "", "mime": "", "fname": "", "reply_to": "", "reactions": {}, "edited": False, "time": datetime.now().strftime("%H:%M"), "read_by": []}]

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

def check_ttt_winner(b):
    lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
    for l in lines:
        if b[l[0]] and b[l[0]] == b[l[1]] == b[l[2]]: return b[l[0]]
    return None

def init_checkers():
    b = [[0]*8 for _ in range(8)]
    for r in range(3):
        for c in range(8):
            if (r+c)%2 == 1: b[r][c] = 2
    for r in range(5, 8):
        for c in range(8):
            if (r+c)%2 == 1: b[r][c] = 1
    return b

def init_chess():
    b = [["" for _ in range(8)] for _ in range(8)]
    b[0] = ["r","n","b","q","k","b","n","r"]; b[1] = ["p"]*8; b[6] = ["P"]*8; b[7] = ["R","N","B","Q","K","B","N","R"]
    return b

def init_uno():
    colors = ["R", "G", "B", "Y"]
    deck = [c+n for c in colors for n in [str(i) for i in range(10)]]
    random.shuffle(deck)
    return {"deck": deck, "p1_hand": [deck.pop() for _ in range(5)], "p2_hand": [deck.pop() for _ in range(5)], "top": deck.pop()}

def check_no_pieces(b, side):
    for r in range(8):
        for c in range(8):
            if side == 'bot' and b[r][c] in [2, 4]: return False
            if side == 'player' and b[r][c] in [1, 3]: return False
    return True

def check_no_king(b, side):
    for r in range(8):
        for c in range(8):
            if side == 'bot' and b[r][c] == 'k': return False
            if side == 'player' and b[r][c] == 'K': return False
    return True

def get_bot_checkers_move(b):
    captures = []
    for r in range(8):
        for c in range(8):
            if b[r][c] in [2, 4]:
                for dr, dc in [(1,1), (1,-1), (-1,1), (-1,-1)]:
                    jr, jc = r+2*dr, c+2*dc
                    if 0 <= jr < 8 and 0 <= jc < 8:
                        if b[r+dr][c+dc] in [1, 3] and b[jr][jc] == 0:
                            captures.append({"from": [r,c], "to": [jr,jc]})
    if captures: return random.choice(captures)
    moves = []
    for r in range(8):
        for c in range(8):
            if b[r][c] in [2, 4]:
                for dr, dc in [(1,1), (1,-1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < 8 and 0 <= nc < 8 and b[nr][nc] == 0:
                        moves.append({"from": [r,c], "to": [nr,nc]})
    return random.choice(moves) if moves else None

def get_bot_chess_move(b):
    captures = []
    moves = []
    for r in range(8):
        for c in range(8):
            p = b[r][c]
            if p.islower():
                for dr, dc in [(1,0),(2,0),(1,1),(1,-1),(2,1),(2,-1),(0,1),(0,-1),(-1,1),(-1,-1),(-1,0),(-2,1),(-2,-1),(-2,0)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        t = b[nr][nc]
                        if t.isupper(): captures.append({"from": [r,c], "to": [nr,nc]})
                        elif t == "": moves.append({"from": [r,c], "to": [nr,nc]})
    if captures: return random.choice(captures)
    return random.choice(moves) if moves else None

def get_bot_city(b):
    if not b: return "Москва"
    last_word = b[-1]["word"].lower()
    last_char = last_word[-1]
    if last_char in ['ь', 'ы', 'й']: last_char = last_word[-2]
    used = [x["word"].lower() for x in b]
    for city in CITIES_DB:
        if city[0].lower() == last_char and city.lower() not in used:
            return city
    return None

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
                    my_bots_list = [{"name": b_name} for b_name, b_data in USERS.items() if b_data.get("bot") and b_data.get("owner") == u]
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
                        "verify_req": VERIFY_REQ, "unread": UNREAD.get(u, {}),
                        "my_bots": my_bots_list
                    }))
                    await broadcast_online()
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            # БОТЫ
            if a == "create_bot":
                bot_name = normalize_name(m.get("name", ""))
                code = m.get("code", "")
                if bot_name in USERS: await websocket.send_text(json.dumps({"action": "error", "message": "Имя занято"}))
                else:
                    USERS[bot_name] = {"password": "bot", "color": "#9c27b0", "bot": True, "owner": u, "code": code, "verified": False, "coins": 0}
                    save_data()
                    await websocket.send_text(json.dumps({"action": "bot_created", "bot": {"name": bot_name, "owner": u}}))
            elif a == "delete_bot":
                bot_name = m.get("name")
                if bot_name in USERS and USERS[bot_name].get("owner") == u:
                    del USERS[bot_name]; save_data()
                    await websocket.send_text(json.dumps({"action": "bot_deleted", "name": bot_name}))
            elif a == "get_my_bots":
                my_bots_list = [{"name": b_name} for b_name, b_data in USERS.items() if b_data.get("bot") and b_data.get("owner") == u]
                await websocket.send_text(json.dumps({"action": "bots_list", "bots": my_bots_list}))

            # НОВОГОДНИЙ БОНУС И ПРОМОКОДЫ
            elif a == "claim_ny_bonus":
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
            elif a == "request_verify":
                VERIFY_REQ[u] = {"from": u, "status": "pending"}; save_data()
                admin = "Носов Глеб"
                if admin in ACTIVE:
                    try: await ACTIVE[admin].send_text(json.dumps({"action": "incoming_verify_call", "from": u}))
                    except: pass
                await websocket.send_text(json.dumps({"action": "verify_sent"}))
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
            elif a == "delete":
                cid, mid = m["chat_id"], m["msg_id"]
                MESSAGES[cid] = [x for x in MESSAGES.get(cid, []) if x["id"] != mid]; save_data()
                for member in CHATS[cid]["members"]:
                    if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "msg_deleted", "chat_id": cid, "msg_id": mid}))
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

            # ИГРЫ
            elif a == "start_bot_game":
                g = m.get("game"); room_id = new_id("room_")
                board = init_checkers() if g == "checkers" else init_chess() if g == "chess" else init_uno() if g == "uno" else [""]*9 if g == "tictactoe" else []
                GAME_ROOMS[room_id] = {"game": g, "players": [u, "BOT"], "turn": u, "bet": 0, "state": "playing", "board": board}
                await websocket.send_text(json.dumps({"action": "game_started", "room_id": room_id, "game": g, "board": board, "turn": u, "players": [u, "BOT"]}))
                continue

            elif a == "create_room":
                target = m.get("target"); bet = int(m.get("bet", 0)); g = m.get("game")
                if USERS[u].get("coins", 0) < bet: continue
                room_id = new_id("room_"); USERS[u]["coins"] -= bet
                board = init_checkers() if g == "checkers" else init_chess() if g == "chess" else init_uno() if g == "uno" else [""]*9 if g == "tictactoe" else []
                GAME_ROOMS[room_id] = {"game": g, "players": [u], "turn": u, "bet": bet, "state": "waiting", "board": board}
                save_data()
                cid = private_id(u, target)
                msg = {"id": new_id("m"), "from": BOT_NAME, "type": "game_invite", "text": f"Игра: {g.upper()}. Ставка: {bet}🪙.", "data": room_id, "time": datetime.now().strftime("%H:%M")}
                if cid in CHATS:
                    MESSAGES[cid].append(msg); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))

            elif a == "join_room":
                room_id = m.get("room_id")
                if room_id in GAME_ROOMS and GAME_ROOMS[room_id]["state"] == "waiting":
                    room = GAME_ROOMS[room_id]
                    if u != room["players"][0]:
                        if USERS[u].get("coins", 0) < room["bet"]: continue
                        USERS[u]["coins"] -= room["bet"]; save_data()
                        room["players"].append(u); room["state"] = "playing"
                        for p in room["players"]:
                            if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_started", "room_id": room_id, "game": room["game"], "board": room["board"], "turn": room["turn"], "players": room["players"]}))
                        await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))

            elif a == "game_move":
                room_id = m.get("room_id")
                if room_id in GAME_ROOMS:
                    room = GAME_ROOMS[room_id]
                    if room["state"] == "playing" and u == room["turn"]:
                        valid = False; g = room["game"]; mv = m.get("move")
                        
                        if g == "tictactoe":
                            idx = int(mv); sym = "X" if u == room["players"][0] else "O"
                            if room["board"][idx] == "": room["board"][idx] = sym; valid = True
                        elif g == "cities":
                            room["board"].append({"user": u, "word": mv}); valid = True
                        elif g == "football":
                            if room["board"]["step"] == "shoot" and u == room["players"][0]:
                                room["board"]["p1_choice"] = mv; room["board"]["step"] = "save"; valid = True
                            elif room["board"]["step"] == "save" and u == room["players"][1]:
                                goal = (room["board"]["p1_choice"] != mv); wu = room["players"][0] if goal else room["players"][1]
                                USERS[wu]["coins"] += room["bet"] * 2; save_data()
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": "ГОЛ! " + wu if goal else "СЕЙВ! " + wu, "board": [], "coins": USERS[p]["coins"]}))
                                del GAME_ROOMS[room_id]; continue
                        elif g == "checkers":
                            fr, to = mv["from"], mv["to"]; p = room["board"][fr[0]][fr[1]]
                            if p != 0 and ((u == room["players"][0] and p in [1,3]) or (u == room["players"][1] and p in [2,4])):
                                dr, dc = to[0]-fr[0], to[1]-fr[1]
                                if abs(dr) == 1 and abs(dc) == 1 and room["board"][to[0]][to[1]] == 0:
                                    room["board"][to[0]][to[1]] = p; room["board"][fr[0]][fr[1]] = 0; valid = True
                                elif abs(dr) == 2 and abs(dc) == 2:
                                    mr, mc = (fr[0]+to[0])//2, (fr[1]+to[1])//2
                                    if room["board"][mr][mc] != 0 and ((room["board"][mr][mc] in [1,3] and p in [2,4]) or (room["board"][mr][mc] in [2,4] and p in [1,3])):
                                        room["board"][to[0]][to[1]] = p; room["board"][fr[0]][fr[1]] = 0; room["board"][mr][mc] = 0; valid = True
                        elif g == "chess":
                            fr, to = mv["from"], mv["to"]; p = room["board"][fr[0]][fr[1]]; t = room["board"][to[0]][to[1]]
                            if p != "" and ((u == room["players"][0] and p.isupper()) or (u == room["players"][1] and p.islower())):
                                pl = p.lower(); dr, dc = to[0]-fr[0], to[1]-fr[1]
                                if pl == 'p' and fr[1] == to[1] and t == "" and ((p.isupper() and dr==-1) or (p.islower() and dr==1)): valid = True
                                elif pl == 'r' and (fr[0]==to[0] or fr[1]==to[1]): valid = True
                                elif pl == 'n' and ((abs(dr)==2 and abs(dc)==1) or (abs(dr)==1 and abs(dc)==2)): valid = True
                                elif pl == 'b' and abs(dr)==abs(dc): valid = True
                                elif pl == 'q' and (fr[0]==to[0] or fr[1]==to[1] or abs(dr)==abs(dc)): valid = True
                                elif pl == 'k' and abs(dr)<=1 and abs(dc)<=1: valid = True
                                if valid: room["board"][to[0]][to[1]] = p; room["board"][fr[0]][fr[1]] = ""
                        elif g == "uno":
                            hand = room["board"]["p1_hand"] if u == room["players"][0] else room["board"]["p2_hand"]
                            top = room["board"]["top"]
                            if mv in hand and (mv[0] == top[0] or mv[1:] == top[1:]):
                                hand.remove(mv); room["board"]["top"] = mv
                                if room["board"]["deck"]: hand.append(room["board"]["deck"].pop())
                                valid = True

                        if valid:
                            if g == "tictactoe" and check_ttt_winner(room["board"]):
                                w = "X" if check_ttt_winner(room["board"]) == "X" else "O"; wu = room["players"][0] if w == "X" else room["players"][1]
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": wu, "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                del GAME_ROOMS[room_id]; continue
                            if g == "checkers" and check_no_pieces(room["board"], "bot"):
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": u, "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                del GAME_ROOMS[room_id]; continue
                            if g == "chess" and check_no_king(room["board"], "bot"):
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": u, "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                del GAME_ROOMS[room_id]; continue
                            
                            if "BOT" in room["players"]:
                                await asyncio.sleep(0.5)
                                if g == "tictactoe":
                                    for i in range(9):
                                        if room["board"][i] == "": room["board"][i] = "O"; break
                                elif g == "checkers":
                                    bmv = get_bot_checkers_move(room["board"])
                                    if bmv:
                                        fr, to = bmv["from"], bmv["to"]; p = room["board"][fr[0]][fr[1]]
                                        if abs(to[0]-fr[0]) == 2:
                                            mr, mc = (fr[0]+to[0])//2, (fr[1]+to[1])//2
                                            room["board"][mr][mc] = 0
                                        room["board"][to[0]][to[1]] = p; room["board"][fr[0]][fr[1]] = 0
                                elif g == "chess":
                                    bmv = get_bot_chess_move(room["board"])
                                    if bmv:
                                        fr, to = bmv["from"], bmv["to"]; p = room["board"][fr[0]][fr[1]]
                                        room["board"][to[0]][to[1]] = p; room["board"][fr[0]][fr[1]] = ""
                                elif g == "cities":
                                    bmv = get_bot_city(room["board"])
                                    if bmv: room["board"].append({"user": "BOT", "word": bmv})
                                elif g == "uno":
                                    hand = room["board"]["p2_hand"]; top = room["board"]["top"]
                                    for card in hand:
                                        if card[0] == top[0] or card[1:] == top[1:]:
                                            hand.remove(card); room["board"]["top"] = card; break
                                
                                if g == "tictactoe" and check_ttt_winner(room["board"]) == "O":
                                    for p in room["players"]:
                                        if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": "BOT", "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                    del GAME_ROOMS[room_id]; continue
                                if g == "checkers" and check_no_pieces(room["board"], "player"):
                                    for p in room["players"]:
                                        if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": "BOT", "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                    del GAME_ROOMS[room_id]; continue
                            else:
                                room["turn"] = room["players"][1] if room["turn"] == room["players"][0] else room["players"][0]
                            
                            for p in room["players"]:
                                if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_update", "board": room["board"], "turn": room["turn"]}))

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
