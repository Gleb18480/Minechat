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
        "Александр (kiberone)": {"password": hashlib.md5("k1b4r076§¶".encode()).hexdigest(), "color": "#f44336", "pinned": [], "coins": 1000},
        BOT_NAME: {"password": "bot", "color": "#ff9800", "bot": True, "verified": True, "pinned": [], "coins": 0},
    })
    CHATS.clear(); MESSAGES.clear()
    for m in ["Носова Наталья", "Носов Даниил", "Носов Виталий"]:
        cid = private_id("Носов Глеб", m)
        CHATS[cid] = {"type": "private", "name": "", "members": ["Носов Глеб", m]}
        MESSAGES[cid] = [{"id": "m_fam", "from": m, "type": "text", "text": "Привет!", "time": datetime.now().strftime("%H:%M")}]
        USERS["Носов Глеб"]["pinned"].append(cid)
    
    cid_alex = private_id("Носов Глеб", "Александр (kiberone)")
    CHATS[cid_alex] = {"type": "private", "name": "", "members": ["Носов Глеб", "Александр (kiberone)"]}
    MESSAGES[cid_alex] = [{"id": "m_alex", "from": "Александр (kiberone)", "type": "text", "text": "Привет, я в сети!", "time": datetime.now().strftime("%H:%M")}]

    CHATS[MAIN_ID] = {"type": "channel", "name": "Minechat Общий", "members": list(USERS.keys()), "owner": "Носов Глеб", "verified": True}
    MESSAGES[MAIN_ID] = [{"id": "m_welcome", "from": "Носов Глеб", "type": "text", "text": "Добро пожаловать! 🎉", "time": datetime.now().strftime("%H:%M")}]
    save_data()

if not load_data(): init_default()

def normalize_name(raw): return " ".join(w.capitalize() for w in raw.strip().split())

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

# --- ЛОГИКА БОТА ---
def get_bot_move(room):
    g = room["game"]
    b = room["board"]
    
    if g == "tictactoe":
        # Ищем победу для бота ('O')
        for i in range(9):
            if b[i] == "":
                b[i] = "O"
                if check_ttt_winner(b) == "O": return i
                b[i] = ""
        # Блокируем игрока ('X')
        for i in range(9):
            if b[i] == "":
                b[i] = "X"
                if check_ttt_winner(b) == "X": b[i] = ""; return i
                b[i] = ""
        # Центр
        if b[4] == "": return 4
        # Любая свободная
        empty = [i for i in range(9) if b[i] == ""]
        return random.choice(empty) if empty else None
        
    elif g == "checkers":
        # Просто ищем случайный валидный ход для бота (2 или 4)
        moves = []
        for r in range(8):
            for c in range(8):
                if b[r][c] in [2, 4]:
                    for dr, dc in [(1,1), (1,-1), (2,2), (2,-2)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < 8 and 0 <= nc < 8 and b[nr][nc] == 0:
                            moves.append({"from": [r,c], "to": [nr,nc]})
        return random.choice(moves) if moves else None
        
    elif g == "chess":
        # Случайный ход для пешки или коня бота
        moves = []
        for r in range(8):
            for c in range(8):
                if b[r][c].islower():
                    # Просто пробуем ходить на 1 клетку
                    for dr, dc in [(1,0), (1,1), (2,1)]:
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < 8 and 0 <= nc < 8 and (b[nr][nc] == "" or b[nr][nc].isupper()):
                            moves.append({"from": [r,c], "to": [nr,nc]})
        return random.choice(moves) if moves else None

    elif g == "uno":
        hand = room["board"]["p2_hand"] # Бот играет 2-м
        top = room["board"]["top"]
        for card in hand:
            if card[0] == top[0] or card[1:] == top[1:]:
                return card
        return None

    elif g == "cities":
        return random.choice(["Москва", "Питер", "Казань", "Сочи", "Омск"])
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
                else: await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
                continue

            if not u: continue

            # --- С БОТОМ ---
            if a == "start_bot_game":
                g = m.get("game")
                room_id = new_id("room_")
                board = []
                if g == "tictactoe": board = [""]*9
                elif g == "cities": board = []
                elif g == "checkers": board = init_checkers()
                elif g == "chess": board = init_chess()
                elif g == "uno": board = init_uno()
                
                GAME_ROOMS[room_id] = {"game": g, "players": [u, "BOT"], "turn": u, "bet": 0, "state": "playing", "board": board}
                await websocket.send_text(json.dumps({"action": "game_started", "room_id": room_id, "game": g, "board": board, "turn": u, "players": [u, "BOT"]}))
                continue

            # --- С ДРУГОМ ---
            elif a == "create_room":
                target = m.get("target")
                bet = int(m.get("bet", 0)); g = m.get("game")
                if USERS[u].get("coins", 0) < bet: continue
                
                room_id = new_id("room_")
                USERS[u]["coins"] -= bet
                board = []
                if g == "tictactoe": board = [""]*9
                elif g == "cities": board = []
                elif g == "football": board = {"step": "shoot", "p1_choice": ""}
                elif g == "checkers": board = init_checkers()
                elif g == "chess": board = init_chess()
                elif g == "uno": board = init_uno()
                
                GAME_ROOMS[room_id] = {"game": g, "players": [u], "turn": u, "bet": bet, "state": "waiting", "board": board}
                save_data()
                
                cid = private_id(u, target)
                msg = {"id": new_id("m"), "from": BOT_NAME, "type": "game_invite", "text": f"Игра: {g.upper()}. Ставка: {bet}🪙.", "data": room_id, "time": datetime.now().strftime("%H:%M")}
                if cid in CHATS:
                    MESSAGES[cid].append(msg); save_data()
                    for member in CHATS[cid]["members"]:
                        if member in ACTIVE: await ACTIVE[member].send_text(json.dumps({"action": "new_message", "chat_id": cid, "msg": msg}))
                await websocket.send_text(json.dumps({"action": "balance_update", "coins": USERS[u]["coins"]}))
                await websocket.send_text(json.dumps({"action": "error", "text": "Приглашение отправлено!"}))

            elif a == "join_room":
                room_id = m.get("room_id"); cid = m.get("chat_id")
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
                        valid = False
                        g = room["game"]; mv = m.get("move")
                        
                        # ХОД ИГРОКА
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
                                    if room["board"][mr][mc] != 0 and (room["board"][mr][mc] + p) in [3, 7]:
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
                            # ПРОВЕРКА НА ПОБЕДУ ИГРОКА
                            if g == "tictactoe":
                                if check_ttt_winner(room["board"]) or "" not in room["board"]:
                                    w = "X" if check_ttt_winner(room["board"]) == "X" else ("O" if check_ttt_winner(room["board"]) == "O" else "draw")
                                    wu = room["players"][0] if w == "X" else (room["players"][1] if w == "O" else "draw")
                                    if "BOT" not in room["players"] and wu != "draw": USERS[wu]["coins"] += room["bet"] * 2
                                    save_data()
                                    for p in room["players"]:
                                        if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": wu, "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                    del GAME_ROOMS[room_id]; continue
                            
                            # ХОД БОТА
                            if "BOT" in room["players"]:
                                time.sleep(0.5) # Задержка для реализма
                                bmv = get_bot_move(room)
                                if bmv is not None:
                                    if g == "tictactoe": room["board"][bmv] = "O"
                                    elif g == "checkers": 
                                        p = room["board"][bmv["from"][0]][bmv["from"][1]]
                                        room["board"][bmv["to"][0]][bmv["to"][1]] = p; room["board"][bmv["from"][0]][bmv["from"][1]] = 0
                                    elif g == "chess":
                                        p = room["board"][bmv["from"][0]][bmv["from"][1]]
                                        room["board"][bmv["to"][0]][bmv["to"][1]] = p; room["board"][bmv["from"][0]][bmv["from"][1]] = ""
                                    elif g == "uno":
                                        room["board"]["p2_hand"].remove(bmv); room["board"]["top"] = bmv
                                    elif g == "cities":
                                        room["board"].append({"user": "BOT", "word": bmv})
                                
                                # Проверка победы бота (для крестиков)
                                if g == "tictactoe" and check_ttt_winner(room["board"]) == "O":
                                    for p in room["players"]:
                                        if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_over", "winner": "BOT", "board": room["board"], "coins": USERS.get(p, 0)["coins"] if p in USERS else 0}))
                                    del GAME_ROOMS[room_id]; continue
                            else:
                                room["turn"] = room["players"][1] if room["turn"] == room["players"][0] else room["players"][0]
                            
                            for p in room["players"]:
                                if p in ACTIVE: await ACTIVE[p].send_text(json.dumps({"action": "game_update", "board": room["board"], "turn": room["turn"]}))

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
