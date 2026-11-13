import sys
import os
import threading
import time
import uvicorn
import webview

# --- Обработка путей (для .exe и для обычного запуска) ---
if getattr(sys, 'frozen', False):
    # Если запущено как .exe, сохраняем базу рядом с .exe
    EXE_DIR = os.path.dirname(sys.executable)
    os.environ["MINECHAT_DATA"] = os.path.join(EXE_DIR, "minechat_data.json")
    os.chdir(EXE_DIR)
else:
    # Если запущено как обычный скрипт Python
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Импортируем FastAPI-приложение из твоего server.py
from server import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == '__main__':
    # 1. Запускаем сервер в фоне
    threading.Thread(target=run_server, daemon=True).start()
    
    # 2. Ждем, пока сервер поднимется
    time.sleep(2)

    # 3. Открываем окно приложения
    webview.create_window(
        title='Minechat (PC)',
        url='http://127.0.0.1:8000',
        width=1200,
        height=850,
        resizable=True
    )
    webview.start()