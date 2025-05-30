@echo off
echo ====================================
echo    KNX Discord Bot Setup s YouTube
echo ====================================
echo.

echo 1. Inštalujem Python knižnice...
echo.

REM Skúša rôzne spôsoby spustenia Python
echo Skúšam 'py -m pip'...
py -m pip install discord.py flask python-dotenv yt-dlp PyNaCl ffmpeg-python requests
if %errorlevel%==0 (
    echo ✅ Úspešne nainštalované cez 'py'!
    goto :ffmpeg_check
)

echo.
echo Skúšam 'python -m pip'...
python -m pip install discord.py flask python-dotenv yt-dlp PyNaCl ffmpeg-python requests
if %errorlevel%==0 (
    echo ✅ Úspešne nainštalované cez 'python'!
    goto :ffmpeg_check
)

echo.
echo Skúšam 'python3 -m pip'...
python3 -m pip install discord.py flask python-dotenv yt-dlp PyNaCl ffmpeg-python requests
if %errorlevel%==0 (
    echo ✅ Úspešne nainštalované cez 'python3'!
    goto :ffmpeg_check
)

echo.
echo ❌ CHYBA: Nie je možné nájsť Python!
echo.
echo 🔧 RIEŠENIA:
echo 1. Nainštaluj Python z https://python.org
echo 2. Pri inštalácii ZAŠKRTNI "Add Python to PATH"
echo 3. Reštartuj počítač
echo 4. Spusti tento script znova
goto :end

:ffmpeg_check
echo.
echo 2. Kontrolujem FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel%==0 (
    echo ✅ FFmpeg je už nainštalovaný!
    goto :test
) else (
    echo ⚠️ FFmpeg nie je nainštalovaný!
    echo.
    echo 📥 INŠTALÁCIA FFMPEG:
    echo 1. Choď na https://ffmpeg.org/download.html
    echo 2. Stiahni FFmpeg pre Windows
    echo 3. Rozbaľ súbory do priečinka 'C:\ffmpeg'
    echo 4. Pridaj 'C:\ffmpeg\bin' do PATH premennej
    echo 5. Reštartuj počítač
    echo.
    echo 💡 ALTERNATÍVA - chocolatey:
    echo choco install ffmpeg
    echo.
    echo 💡 ALTERNATÍVA - scoop:
    echo scoop install ffmpeg
    echo.
)

:test
echo.
echo 3. Testujem inštaláciu...
py -c "import discord; print(f'Discord.py: {discord.__version__}')" 2>nul || python -c "import discord; print(f'Discord.py: {discord.__version__}')" 2>nul || python3 -c "import discord; print(f'Discord.py: {discord.__version__}')"
if %errorlevel%==0 (
    echo ✅ Discord.py je nainštalované správne!
) else (
    echo ⚠️ Problém s Discord.py knižnicou
)

py -c "import yt_dlp; print('yt-dlp: OK')" 2>nul || python -c "import yt_dlp; print('yt-dlp: OK')" 2>nul || python3 -c "import yt_dlp; print('yt-dlp: OK')"
if %errorlevel%==0 (
    echo ✅ yt-dlp je nainštalované správne!
) else (
    echo ⚠️ Problém s yt-dlp knižnicou
)

echo.
echo 4. Kontrola .env súboru...
if exist ".env" (
    echo ✅ .env súbor existuje
) else (
    echo ⚠️ .env súbor neexistuje!
    echo 📝 Vytvor .env súbor s DISCORD_TOKEN=tvoj_token
)

echo.
echo ====================================
echo          HOTOVO!
echo ====================================
echo.
echo 🚀 Spusť bota pomocou: auto_start.bat
echo 🎵 Nové hudobné príkazy:
echo    !play [URL] - prehrá YouTube video
echo    !skip - preskočí pesničku
echo    !stop - zastaví prehrávanie
echo    !queue - zobrazí frontu
echo    !volume [0-100] - nastaví hlasitosť
echo    !join - pripojí sa k hlasovému kanálu
echo    !leave - odpojí sa z hlasového kanálu

:end
echo.
pause