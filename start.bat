@echo off
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit
title KNX Discord Bot
color 0B
mode con: cols=50 lines=15

:start
cls
echo Spustam KNX Discord Bot...
echo.

:: Jednoduchy loading
for %%i in (10 30 50 70 90 100) do (
    echo [Loading... %%i%%]
    ping -n 2 127.0.0.1 > nul
    cls
)

echo Status: Pripajam sa k Discord API...
echo.

REM Skusi rozne sposoby spustenia
py main.py 2>nul
if %errorlevel% NEQ 0 (
    python main.py 2>nul
    if %errorlevel% NEQ 0 (
        python3 main.py 2>nul
    )
)

echo.
echo KNX Bot sa vypol! (Exit code: %errorlevel%)
echo.

REM Ak exit code je 0, znamena to normalne vypnutie (nie restart)
if %errorlevel%==0 (
    echo Normalne vypnutie bota
    echo Pre zatvorenie stlac akukolvek klavesu...
    pause > nul
    exit
)

REM Ak exit code je iny, automaticky restartuje
echo Restart za:
for %%i in (3 2 1) do (
    echo %%i...
    timeout /t 1 /nobreak >nul
)
goto start