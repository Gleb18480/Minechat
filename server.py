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
BOT_NAME = "Игровой Бот"
MAIN_ID = "main_channel"

USERS, CHATS, MESSAGES, DOCUMENTS, COUNTER, BANNED, MUTED, STICKERS, VERIFY_REQ, UNREAD, ACTIVE, STORIES = {}, {}, {}, {}, [0], [], {}, {}, {}, {}, {}, {}
GAME_ROOMS = {}

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
        "Носов Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3", "creator": True, "verified": True, "pinned": [], "coins": 5000},
        "Носова Наталья": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63", "pinned": [], "coins": 1000},
        "Носов Даниил": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800", "pinned": [], "coins": 1000},
        "Носов Виталий": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50", "pinned": [], "coins": 1000},
        BOT_NAME: {"password": "bot", "color": "#ff9800", "bot": True, "verified": True, "pinned": [], "coins": 0},
    })
    CHATS.clear(); MESSAGES.clear()
    family_members = ["Носова Наталья", "Носов Даниил", "Носов Виталий"]
    for member in family_members:
        cid = private_id("Носов Глеб", member)
        CHATS[cid] = {"type": "private", "name": "", "members": ["Носов Глеб", member]}
        MESSAGES[cid] = [{"id": "m_fam", "from": member, "type": "text", "text": "Привет!", "time": datetime.now().strftime("%H:%M")}]
        USERS["Носов Глеб"]["pinned"].append(cid)
    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat Общий", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True}
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "Добро пожаловать! 🎉", "time": datetime.now().strftime("%H:%M")}]
    save_data()

if not load_data(): init_default()

def normalize_name(raw): return " ".join(w.capitalize() for w in raw.strip().split())

def check_ttt_winner(b):
    lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
    for line in lines:
        if b[line[0]] and b[line[0]] == b[line[1]] == b[line[2]]: return b[line[0]]
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

            if a == "login":
                name = normalize_name(m.get("username", ""))
                p = hashlib.md5(m["password"].encode()).hexdigest()
                if name in USERS and USERS[name]["password"] == p:
                    u = name; ACTIVE[u] = websocket
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u, "users": list(USERS.keys()),
                        "chats": [{"id": cid, **ch} for cid, ch in CHATS.items() if u in ch["members"]],
                        "verified_users": [n for n, d in USERS.items() if d.get("verified")],
                        "pinned": USERS[u].get("pinned", []), "coins": {n: d.get("coins", 0) for n, d in USERS.items()}
                    }))
                else: await websocket.send_text(json.dumps({"action": "login_fail"}))
                continue

            if not u: continue

            # === ИГРЫ (ОТПРАВКА ПРИГЛАШЕНИЯ В КОНКРЕТНЫЙ ЧАТ) ===
            if a == "create_room":
                bet = int(m.get("bet", 0))
                g_type = m.get("game")
                cid = m.get("chat_id") # Берем ID чата, откуда создали игру
                
                if USERS[u].get("coins", 0) < bet: 
                    await websocket.send_text(json.dumps({"action": "error", "text": "Мало монет!"})); continue
                
                room_id = new_id("room_")
                USERS[u]["coins"] -= bet
                save_data()
                
                GAME_ROOMS[room_id] = {"game": g_type, "players": [u], "turn": u, "bet": bet, "state": "waiting", "board": [""]*9}
                
                # Отправляем приглашение ТОЛЬКО в этот чат
                invite_text = f"Игра: {g_type.upper()}. Ставка: {bet}🪙. Ждем второго игрока!"
                msg = {"id": new_id("m"), "from": BOT_NAME, "type": "game_invite", "text": invite_text, "data": room_id, "time": datetime.now().strftime("%H:%M")}
                
                if cid in CHATS:
                    MESSAGES[cid].append(msg); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                            except: pass
                
                await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))

            elif a == "join_room":
                room_id = m.get("room_id")
                cid = m.get("chat_id")
                if room_id in GAME_ROOMS and GAME_ROOMS[room_id]["state"] == "waiting":
                    room = GAME_ROOMS[room_id]
                    if u != room["players"][0]:
                        if USERS[u].get("coins", 0) < room["bet"]:
                            await websocket.send_text(json.dumps({"action": "error", "text": "Мало монет!"})); continue
                        
                        USERS[u]["coins"] -= room["bet"]
                        save_data()
                        
                        room["players"].append(u); room["state"] = "playing"
                        if room["game"] == "tictactoe": room["board"] = [""]*9; room["turn"] = room["players"][0]
                        elif room["game"] == "cities": room["board"] = []; room["turn"] = room["players"][0]
                        elif room["game"] == "football": room["board"] = {"p1_choice": "", "step": "shoot"}; room["turn"] = room["players"][0]
                        
                        for p in room["players"]:
                            if p in ACTIVE:
                                await ACTIVE[p].send_text(json.dumps({"action": "game_started", "room_id": room_id, "game": room["game"], "board": room["board"], "turn": room["turn"], "players": room["players"]}))
                        await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))
                else:
                    await websocket.send_text(json.dumps({"action": "error", "text": "Комната занята!"}))

            elif a == "game_move":
                room_id = m.get("room_id")
                if room_id in GAME_ROOMS:
                    room = GAME_ROOMS[room_id]
                    if room["state"] == "playing" and u == room["turn"]:
                        if room["game"] == "tictactoe":
                            idx = int(m.get("move"))
                            sym = "X" if u == room["players"][0] else "O"
                            if room["board"][idx] == "":
                                room["board"][idx] = sym
                                winner = check_ttt_winner(room["board"])
                                if winner or "" not in room["board"]:
                                    winner_user = room["players"][0] if winner == "X" else (room["players"][1] if winner == "O" else "draw")
                                    if winner_user != "draw": USERS[winner_user]["coins"] += room["bet"] * 2
                                    else:
                                        for p in room["players"]: USERS[p]["coins"] += room["bet"]
                                    save_data()
                                    for p in room["players"]:
                                        if p in ACTIVE:
                                            await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": winner_user, "board": room["board"], "coins": USERS[p]["coins"]}))
                                    del GAME_ROOMS[room_id]
                                else:
                                    room["turn"] = room["players"][1] if room["turn"] == room["players"][0] else room["players"][0]
                                    for p in room["players"]:
                                        if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_update", "board": room["board"], "turn": room["turn"]}))
                        
                        elif room["game"] == "cities":
                            word = m.get("move").strip().lower()
                            if len(word) > 1:
                                room["board"].append({"user": u, "word": word})
                                room["turn"] = room["players"][1] if room["turn"] == room["players"][0] else room["players"][0]
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_update", "board": room["board"], "turn": room["turn"]}))

                        elif room["game"] == "football":
                            step = room["board"].get("step")
                            move = m.get("move")
                            if step == "shoot" and u == room["players"][0]:
                                room["board"]["p1_choice"] = move; room["board"]["step"] = "save"; room["turn"] = room["players"][1]
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_update", "board": room["board"], "turn": room["turn"]}))
                            elif step == "save" and u == room["players"][1]:
                                p1_c = room["board"]["p1_choice"]
                                goal = (p1_c != move)
                                if goal: USERS[room["players"][0]]["coins"] += room["bet"] * 2
                                else: USERS[room["players"][1]]["coins"] += room["bet"] * 2
                                save_data()
                                res = "ГОЛ! Победил " + room["players"][0] if goal else "СЕЙВ! Победил " + room["players"][1]
                                for p in room["players"]:
                                    if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": res, "board": [], "coins": USERS[p]["coins"]}))
                                del GAME_ROOMS[room_id]

            # === ПРОЧЕЕ ===
            elif a == "message":
                cid = m["chat_id"]
                if cid in CHATS and u in CHATS[cid]["members"]:
                    msg = {"id": new_id("m"), "from": u, "type": "text", "text": m.get("text", ""), "time": datetime.now().strftime("%H:%M")}
                    MESSAGES[cid].append(msg); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE and member != u:
                            try: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                            except: pass
            elif a == "open_chat":
                cid = m.get("chat_id")
                if cid in CHATS and u in CHATS[cid]["members"]:
                    await websocket.send_text(json.dumps({"action": "chat_opened", "chat_id": cid, "chat": CHATS[cid], "messages": MESSAGES.get(cid, [])}))

    except WebSocketDisconnect:
        if u: ACTIVE.pop(u, None)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 11460))
    uvicorn.run(app, host="0.0.0.0", port=port)
