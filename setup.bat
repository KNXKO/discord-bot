@echo off
echo ====================================
echo    KNX Discord Bot Setup s YouTube + Spotify
echo ====================================
echo.

echo 1. Inštalujem/Aktualizujem Python knižnice...
echo.

REM Skúša rôzne spôsoby spustenia Python
echo Skúšam 'py -m pip'...
py -m pip install -r requirements.txt --upgrade
if %errorlevel%==0 (
    echo ✅ Úspešne nainštalované/aktualizované cez 'py'!
    goto :ffmpeg_check
)

echo.
echo Skúšam 'python -m pip'...
python -m pip install -r requirements.txt --upgrade
if %errorlevel%==0 (
    echo ✅ Úspešne nainštalované/aktualizované cez 'python'!
    goto :ffmpeg_check
)

echo.
echo Skúšam 'python3 -m pip'...
python3 -m pip install -r requirements.txt --upgrade
if %errorlevel%==0 (
    echo ✅ Úspešne nainštalované/aktualizované cez 'python3'!
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

py -c "import spotipy; print('Spotipy: OK')" 2>nul || python -c "import spotipy; print('Spotipy: OK')" 2>nul || python3 -c "import spotipy; print('Spotipy: OK')"
if %errorlevel%==0 (
    echo ✅ Spotipy je nainštalované správne!
) else (
    echo ⚠️ Problém so Spotipy knižnicou
)

echo.
echo 4. Kontrola .env súboru...
if exist ".env" (
    echo ✅ .env súbor existuje

    findstr /C:"DISCORD_TOKEN=" .env >nul
    if %errorlevel%==0 (
        echo ✅ Discord token nastavený
    ) else (
        echo ⚠️ Discord token chýba v .env
    )

    findstr /C:"SPOTIFY_CLIENT_ID=" .env >nul
    if %errorlevel%==0 (
        echo ✅ Spotify Client ID nastavené
    ) else (
        echo ⚠️ Spotify Client ID chýba v .env
    )

    findstr /C:"SPOTIFY_CLIENT_SECRET=" .env >nul
    if %errorlevel%==0 (
        echo ✅ Spotify Client Secret nastavené
    ) else (
        echo ⚠️ Spotify Client Secret chýba v .env
    )
) else (
    echo ⚠️ .env súbor neexistuje!
    echo.
    echo 📝 Vytvor .env súbor s:
    echo DISCORD_TOKEN=tvoj_discord_token
    echo SPOTIFY_CLIENT_ID=tvoj_spotify_client_id
    echo SPOTIFY_CLIENT_SECRET=tvoj_spotify_client_secret
)

echo.
echo ====================================
echo          HOTOVO!
echo ====================================

:end
echo.
pause