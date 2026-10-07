# -*- coding: utf-8 -*-
import os, json, hashlib
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

USERS = {
    "Мама": {"password": hashlib.md5("262524".encode()).hexdigest(), "color": "#e91e63"},
    "Глеб": {"password": hashlib.md5("310315".encode()).hexdigest(), "color": "#2196f3"},
    "Даня": {"password": hashlib.md5("260817".encode()).hexdigest(), "color": "#ff9800"},
    "Папа": {"password": hashlib.md5("120479".encode()).hexdigest(), "color": "#4caf50"},
}
HISTORY = {}
ACTIVE = {}

def ck(a, b):
    return "_".join(sorted([a, b]))

@app.websocket("/ws/{u}")
async def ws(websocket: WebSocket, u: str):
    await websocket.accept()
    ACTIVE[u] = websocket
    try:
        while True:
            m = json.loads(await websocket.receive_text())
            a = m.get("action")
            if a == "login":
                p = hashlib.md5(m["password"].encode()).hexdigest()
                if u in USERS and USERS[u]["password"] == p:
                    await websocket.send_text(json.dumps({
                        "action": "login_ok", "username": u,
                        "color": USERS[u]["color"], "users": list(USERS.keys())
                    }))
                else:
                    await websocket.send_text(json.dumps({"action": "login_fail", "reason": "Неверный пароль"}))
            elif a == "register":
                if u in USERS:
                    await websocket.send_text(json.dumps({"action": "register_fail", "reason": "Занято"}))
                else:
                    USERS[u] = {"password": hashlib.md5(m["password"].encode()).hexdigest(), "color": "#9c27b0"}
                    await websocket.send_text(json.dumps({"action": "register_ok"}))
            elif a == "message":
                to, txt = m["to"], m["text"]
                k = ck(u, to)
                t = datetime.now().strftime("%H:%M")
                HISTORY.setdefault(k, []).append({"from": u, "to": to, "text": txt, "time": t})
                if to in ACTIVE:
                    await ACTIVE[to].send_text(json.dumps({"action": "new_message", "from": u, "text": txt, "time": t}))
                await websocket.send_text(json.dumps({"action": "sent", "to": to, "text": txt, "time": t}))
            elif a == "history":
                await websocket.send_text(json.dumps({"action": "history", "with": m["to"], "messages": HISTORY.get(ck(u, m["to"]), [])}))
            elif a in ("call_offer", "call_answer", "call_decline", "call_end", "webrtc"):
                to = m["to"]
                if to in ACTIVE:
                    await ACTIVE[to].send_text(json.dumps({
                        "action": "incoming_call" if a == "call_offer" else "call_accepted" if a == "call_answer" else "call_declined" if a == "call_decline" else "call_ended" if a == "call_end" else "webrtc",
                        "from": u, "data": m.get("data")
                    }))
    except WebSocketDisconnect:
        ACTIVE.pop(u, None)
        for w in ACTIVE.values():
            try:
                await w.send_text(json.dumps({"action": "online", "users": list(ACTIVE.keys())}))
            except:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
