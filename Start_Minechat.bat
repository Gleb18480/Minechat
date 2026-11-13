@echo off
title Minechat (PC)
cd /d "%~dp0"

echo =======================================
echo       Запуск Minechat для ПК...
echo =======================================
echo.

:: Запускаем сервер в скрытом фоновом режиме
start "" /B pythonw server.py

:: Ждем 2 секунды, чтобы сервер успел загрузиться
timeout /t 2 >nul

:: Открываем интерфейс в режиме приложения (через Microsoft Edge)
start msedge --app=http://127.0.0.1:11460

exit
