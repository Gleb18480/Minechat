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
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True, "avatar": "", "status": "На связи", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 5000},
        "Носова Наталья": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000},
        "Носов Даниил": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000},
        "Носов Виталий": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50", "avatar": "", "status": "", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000},
        BOT_NAME: {"password": "bot", "color": "#9c27b0", "avatar": "", "bot": True, "verified": True, "status": "🤖 Я бот", "last_seen": 0, "phone": "", "email": "", "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 0},
    })
    
    CHATS.clear(); MESSAGES.clear()

    family_members = ["Носова Наталья", "Носов Даниил", "Носов Виталий"]
    for member in family_members:
        cid = private_id("Носов Глеб", member)
        CHATS[cid] = {"type": "private", "name": "", "members": ["Носов Глеб", member], "owner": "", "banned": []}
        MESSAGES[cid] = [{"id": "m_fam_" + member, "from": member, "type": "text", "text": "Привет!", "data": "", "time": datetime.now().strftime("%H:%M")}]
        USERS["Носов Глеб"]["pinned"].append(cid)

    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat (Russia) News", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True, "official": True, "avatar": "", "desc": "Официальный канал", "admins": {"Носов Глеб": "Владелец"}, "banned": [], "pinned": ""}
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "Добро пожаловать в Игровой центр! 🎉", "data": "", "time": datetime.now().strftime("%H:%M")}]
    save_data()

if not load_data(): init_default()

def normalize_name(raw): return " ".join(w.capitalize() for w in raw.strip().split())

def run_bot_code(code, text):
    try:
        safe_globals = {"__builtins__": {"len": len, "str": str, "int": int, "float": float, "range": range, "list": list, "dict": dict}}
        local_vars = {}
        exec(code, safe_globals, local_vars)
        if "handle_message" in local_vars: return str(local_vars["handle_message"](text))
        return "Ошибка: в коде нет функции handle_message(text)"
    except Exception as e: return f"Ошибка бота: {str(e)}"

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
                    USERS[name] = {"password": hashlib.md5(m["password"].encode()).hexdigest(), "color": "#2AABEE", "avatar": "", "status": "", "last_seen": 0, "phone": m.get("phone",""), "email": m.get("email",""), "age": 0, "age_group": "", "device": {}, "pinned": [], "coins": 1000}
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
                        "coins": {n: d.get("coins", 0) for n, d in USERS.items()},
                        "pinned": USERS[u].get("pinned", []),
                        "my_bots": my_bots_list,
                        "stories": STORIES
                    }))
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            # --- ИГРЫ ---
            if a == "play_game":
                game = m.get("game")
                bet = int(m.get("bet", 0))
                
                if USERS[u].get("coins", 0) < bet or bet <= 0:
                    await websocket.send_text(json.dumps({"action": "error_msg", "text": "Недостаточно монет для ставки!"}))
                    continue
                
                # Списываем ставку
                USERS[u]["coins"] -= bet
                win = False
                result_text = ""
                data = {}

                if game == "dice":
                    roll = random.randint(1, 6)
                    win = roll >= 4
                    result_text = f"Выпало {roll}."
                    data = {"roll": roll}
                elif game == "coin":
                    side = random.choice(["Орел", "Решка"])
                    user_side = m.get("choice", "Орел")
                    win = (side == user_side)
                    result_text = f"Выпало: {side}."
                    data = {"side": side}
                elif game == "slots":
                    symbols = ["🍒", "🍋", "🍇", "🔔", "💎", "7️⃣"]
                    res = [random.choice(symbols) for _ in range(3)]
                    win = (res[0] == res[1] == res[2])
                    result_text = f"Слоты: {' '.join(res)}"
                    data = {"res": res}
                elif game == "darts":
                    score = random.randint(0, 60)
                    win = score >= 40
                    result_text = f"Вы набрали {score} очков."
                    data = {"score": score}
                elif game == "roulette":
                    chamber = random.randint(1, 6)
                    win = chamber != 1
                    result_text = "БУМ! 💥 Вы проиграли." if not win else "Щелчок... Вы выжили! 😅"
                elif game == "bj":
                    player_sum = random.randint(14, 22)
                    dealer_sum = random.randint(15, 23)
                    win = player_sum <= 21 and (dealer_sum > 21 or player_sum > dealer_sum)
                    result_text = f"Вы: {player_sum}, Дилер: {dealer_sum}"
                    data = {"p": player_sum, "d": dealer_sum}
                elif game == "race":
                    user_speed = random.randint(50, 100)
                    bot_speed = random.randint(50, 100)
                    win = user_speed > bot_speed
                    result_text = f"Вы: {user_speed} км/ч, Бот: {bot_speed} км/ч"
                elif game == "mines":
                    is_mine = random.random() < 0.3
                    win = not is_mine
                    result_text = "💥 МИНА! Вы проиграли." if is_mine else "Безопасно! Вы нашли выход."
                elif game == "rps":
                    user_choice = m.get("choice")
                    bot_choice = random.choice(["rock", "paper", "scissors"])
                    names = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
                    if user_choice == bot_choice: result_text = f"Ничья! {names[user_choice]} vs {names[bot_choice]}"; USERS[u]["coins"] += bet # Возврат ставки
                    elif (user_choice=="rock" and bot_choice=="scissors") or (user_choice=="paper" and bot_choice=="rock") or (user_choice=="scissors" and bot_choice=="paper"):
                        win = True; result_text = f"Вы победили! {names[user_choice]} бьет {names[bot_choice]}"
                    else: result_text = f"Вы проиграли! {names[bot_choice]} бьет {names[user_choice]}"
                elif game == "wheel":
                    wheel = [0, 2, 0, 3, 0, 1, 0, 5] # x5 - джекпот
                    mult = random.choice(wheel)
                    win = mult > 0
                    result_text = f"Множитель: x{mult}"
                    bet = bet * mult if mult > 0 else bet # Пересчитываем выигрыш

                if win:
                    USERS[u]["coins"] += bet * 2
                save_data()
                
                await websocket.send_text(json.dumps({
                    "action": "game_result", "game": game, "win": win, 
                    "text": result_text, "coins": USERS[u]["coins"], "bet": bet, "data": data
                }))

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

            # --- ОСТАЛЬНОЕ (сообщения, чаты, звонки) ---
            elif a == "message":
                cid = m["chat_id"]
                if cid in CHATS and u in CHATS[cid]["members"]:
                    msg = {"id": new_id("m"), "from": u, "type": m.get("type", "text"), "text": m.get("text", ""), "data": m.get("data", ""), "time": datetime.now().strftime("%H:%M")}
                    MESSAGES[cid].append(msg); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE and member != u:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                            except: pass
                            
            elif a in ("call_offer", "call_answer", "call_decline", "call_end", "webrtc"):
                to = m["to"]
                if to in ACTIVE:
                    action_map = {"call_offer": "incoming_call", "call_answer": "call_accepted", "call_decline": "call_declined", "call_end": "call_ended", "webrtc": "webrtc"}
                    await ACTIVE[to].send_text(json.dumps({"action": action_map[a], "from": u, "data": m.get("data")}))
            
            # (Обработчики профиля, ботов, закреплений оставляем без изменений)
            elif a == "set_phone":
                USERS[u]["phone"] = m.get("phone", ""); save_data()
                await websocket.send_text(json.dumps({"action": "phone_update", "username": u, "phone": USERS[u]["phone"]}))
            elif a == "set_avatar":
                USERS[u]["avatar"] = m.get("avatar", ""); save_data()
                await websocket.send_text(json.dumps({"action": "avatar_update", "username": u, "avatar": USERS[u]["avatar"]}))
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
            elif a == "search_users":
                query = m.get("query", "").lower()
                await websocket.send_text(json.dumps({"action": "search_results", "results": [name for name in USERS.keys() if query in name.lower() and name != u]}))
            
    except WebSocketDisconnect:
        if u: ACTIVE.pop(u, None)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)
