import discord
import asyncio
import yt_dlp
from datetime import datetime
import time

# Slovníky na ukladanie stavu hudby pre každý server
music_queue = {}
current_players = {}
paused_state = {}
loop_state = {}  # Nový slovník pre loop stav
loop_queue = {}  # Slovník pre queue loop stav
loop_counter = {}  # Počítadlo loop pokusov

# Nastavenia pre yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': False,
    # Špeciálne nastavenia pre live streamy
    'live_from_start': False,  # Nezačína od začiatku live streamu
    'hls_prefer_native': True,  # Použije natívny HLS decoder
}

# Špeciálne yt-dlp nastavenia len pre live streamy
ytdl_live_format_options = {
    'format': 'best[ext=m4a]/bestaudio[ext=m4a]/best/bestaudio',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': False,
    'live_from_start': False,  # Dôležité - začne od aktuálneho času
    'hls_prefer_native': True,
}

# Nastavenia pre FFmpeg - štandardné
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# Nastavenia pre FFmpeg - live streamy
ffmpeg_live_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -fflags +discardcorrupt -analyzeduration 0 -probesize 32',
    'options': '-vn -f s16le -ar 48000 -ac 2'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
ytdl_live = yt_dlp.YoutubeDL(ytdl_live_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.is_live = data.get('is_live', False)

        # Označí live streamy v názve
        if self.is_live:
            self.title = f"🔴 LIVE: {self.title}"

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            # Najprv skúsi získať základné info pre detekciu live streamu
            print(f"[DEBUG] 🔍 Detekujem typ obsahu pre: {url}")
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

            if 'entries' in data:
                data = data['entries'][0]

            # Detekuje live stream
            is_live = data.get('is_live', False)

            if is_live:
                print(f"[DEBUG] 🔴 Live stream detekovaný, používam špeciálne nastavenia")
                # Pre live streamy používa špecializované nastavenia
                data = await loop.run_in_executor(None, lambda: ytdl_live.extract_info(url, download=False))
                if 'entries' in data:
                    data = data['entries'][0]

            filename = data['url'] if stream else ytdl.prepare_filename(data)

            # Skontroluje či sa podarilo získať stream URL
            if not filename:
                print(f"[ERROR] Nepodarilo sa získať stream URL pre: {url}")
                return None

            # Detekuje live stream
            is_live = data.get('is_live', False)

            if is_live:
                print(f"[DEBUG] 🔴 Vytváram LIVE stream player: {data.get('title')}")
                # Používa špeciálne live FFmpeg nastavenia
                source = discord.FFmpegPCMAudio(filename, **ffmpeg_live_options)
            else:
                print(f"[DEBUG] 🎵 Vytváram štandardný player: {data.get('title')}")
                # Používa štandardné FFmpeg nastavenia
                source = discord.FFmpegPCMAudio(filename, **ffmpeg_options)

            return cls(source, data=data)

        except Exception as e:
            error_msg = str(e).lower()
            if 'drm' in error_msg:
                print(f"[WARNING] DRM chránený obsah: {url}")
            elif 'private' in error_msg or 'unavailable' in error_msg:
                print(f"[WARNING] Video nie je dostupné: {url}")
            elif 'age' in error_msg:
                print(f"[WARNING] Age-restricted video: {url}")
            elif 'live' in error_msg:
                print(f"[WARNING] Live stream problém: {url}")
            else:
                print(f"[ERROR] Chyba pri sťahovaní: {e}")
            return None

# Globálne sledovanie časov začiatku pesničiek
song_start_times = {}

def set_song_start_time(guild_id):
    """Nastaví čas začiatku pesničky"""
    song_start_times[guild_id] = time.time()
    print(f"[DEBUG] ⏰ Nastavený start time pre guild {guild_id}")

def after_playing(error, guild_id, client, bot_stats):
    """Callback funkcia ktorá sa zavolá po skončení pesničky"""
    current_time = time.time()

    # Získa čas kedy sa pesnička začala
    start_time = song_start_times.get(guild_id, current_time)
    duration = current_time - start_time

    print(f"[DEBUG] 🎵 after_playing callback: error={error}, guild={guild_id}")
    print(f"[DEBUG] ⏱️  Čas prehrávání: {duration:.2f} sekúnd")

    # Ak sa callback volá príliš rýchlo (menej ako 5 sekúnd), ignoruj
    if duration < 5.0:
        print(f"[DEBUG] ⚡ Callback príliš rýchly ({duration:.2f}s) - IGNORUJEM!")
        return

    # Ak je to skutočný koniec alebo chyba, pokračuj
    if error:
        print(f'[ERROR] ❌ Chyba prehrávača: {error}')
        # Vyčisti timing data
        if guild_id in song_start_times:
            del song_start_times[guild_id]
        # Pri chybe nepokračuje v loop
        asyncio.run_coroutine_threadsafe(play_next(guild_id, client, bot_stats), client.loop)
    else:
        print(f"[DEBUG] ✅ Pesnička sa skončila prirodzene po {duration:.2f} sekundách")
        # Vyčisti timing data
        if guild_id in song_start_times:
            del song_start_times[guild_id]
        # Vytvorí úlohu pre ďalšiu pesničku alebo loop
        asyncio.run_coroutine_threadsafe(handle_song_end(guild_id, client, bot_stats), client.loop)

async def handle_song_end(guild_id, client, bot_stats):
    """Spracuje koniec pesničky - rozhodne či loopoovať alebo prehrať ďalšiu"""
    print(f"[DEBUG] 🔄 handle_song_end volaný pre guild {guild_id}")

    guild = client.get_guild(guild_id)
    if not guild or not guild.voice_client:
        print(f"[DEBUG] ❌ Guild alebo voice_client neexistuje")
        return

    # Počká chvíľu aby sa zabezpečilo, že sa pesnička skutočne skončila
    print(f"[DEBUG] ⏳ Čakám 1 sekundu pred spracovaním...")
    await asyncio.sleep(1.0)

    # Skontroluje či sa stále hrá (ak áno, callback sa zavolal predčasne)
    if guild.voice_client.is_playing():
        print(f"[DEBUG] ⚠️  Voice client stále hrá - callback bol predčasný, ignorujem")
        return

    print(f"[DEBUG] ✅ Voice client sa už nehrá, pokračujem v spracovaní...")

    # Skontroluje či je zapnutý loop pre aktuálnu pesničku
    if loop_state.get(guild_id, False) and guild_id in current_players:
        print(f"[DEBUG] 🔂 Loop je zapnutý, opakujem pesničku")
        # Opakuje aktuálnu pesničku
        await replay_current_song(guild_id, client, bot_stats)
        return

    # Skontroluje či je zapnutý queue loop
    if loop_queue.get(guild_id, False) and guild_id in music_queue:
        # Ak sa skončila pesnička a queue loop je zapnutý, pridá ju na koniec fronty
        if guild_id in current_players and current_players[guild_id]:
            current_song_data = current_players[guild_id]
            # Získa pôvodné údaje
            original_url = current_song_data.data.get('webpage_url', current_song_data.data.get('url'))
            if original_url:
                # Pridá späť na koniec fronty
                music_queue[guild_id].append((original_url, None, current_song_data.title, False))
                print(f"[DEBUG] 🔁 Pridané späť do queue loop: {current_song_data.title}")

    print(f"[DEBUG] ⏭️  Pokračujem s ďalšou pesničkou vo fronte...")
    # Pokračuje s ďalšou pesničkou vo fronte
    await play_next(guild_id, client, bot_stats)

async def replay_current_song(guild_id, client, bot_stats):
    """Opakuje aktuálnu pesničku"""
    # Inicializuje loop counter ak neexistuje
    if guild_id not in loop_counter:
        loop_counter[guild_id] = 0

    loop_counter[guild_id] += 1
    print(f"[DEBUG] 🔄 replay_current_song spustený pre guild {guild_id} (pokus #{loop_counter[guild_id]})")

    # Bezpečnostná poistka - ak sa loop pokúša spustiť príliš veľakrát za krátky čas
    if loop_counter[guild_id] > 10:
        print(f"[WARNING] ⚠️  Príliš veľa loop pokusov ({loop_counter[guild_id]}), vypínam loop")
        loop_state[guild_id] = False
        loop_counter[guild_id] = 0
        await play_next(guild_id, client, bot_stats)
        return

    if guild_id not in current_players:
        print(f"[DEBUG] ❌ Žiadny current_player pre guild {guild_id}")
        return

    guild = client.get_guild(guild_id)
    if not guild or not guild.voice_client:
        print(f"[DEBUG] ❌ Guild alebo voice_client neexistuje v replay_current_song")
        return

    # Skontroluje či sa stále niečo hrá (safety check)
    if guild.voice_client.is_playing():
        print(f"[DEBUG] ⚠️  Voice client stále hrá, nebudem spúšťať replay")
        return

    current_song_data = current_players[guild_id]

    # Skontroluje či je to live stream - live streamy sa nemôžu loopoovať
    if current_song_data.is_live:
        print(f"[DEBUG] 🔴 Live stream sa nemôže loopoovať - pokračujem ďalej")
        loop_state[guild_id] = False
        loop_counter[guild_id] = 0
        await play_next(guild_id, client, bot_stats)
        return

    # Použije pôvodnú hľadaciu frázu namiesto URL, aby získal fresh stream
    original_url = current_song_data.data.get('webpage_url', current_song_data.data.get('original_url'))

    # Ak nemáme webpage_url, použijeme title ako search query
    if not original_url or not original_url.startswith('http'):
        search_query = current_song_data.title.replace("🔴 LIVE: ", "")  # Odstráni live prefix
        print(f"[DEBUG] 🔍 Používam title ako search query: {search_query}")
    else:
        search_query = original_url
        print(f"[DEBUG] 🔗 Používam URL: {original_url}")

    print(f"[DEBUG] 📥 Pokúšam sa znovu načítať: {current_song_data.title}")

    try:
        # Získa fresh data z yt-dlp
        print(f"[DEBUG] 🔄 Získavam fresh stream pre loop...")
        loop_event = asyncio.get_event_loop()

        # Najprv detekuje typ obsahu
        data = await loop_event.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))

        if 'entries' in data:
            data = data['entries'][0]

        # Ak je to live stream, použije špecializované nastavenia
        is_live = data.get('is_live', False)
        if is_live:
            print(f"[DEBUG] 🔴 Live stream pre replay - používam live ytdl")
            data = await loop_event.run_in_executor(None, lambda: ytdl_live.extract_info(search_query, download=False))
            if 'entries' in data:
                data = data['entries'][0]

        # Vytvorí nový player s fresh stream URL
        fresh_stream_url = data.get('url')
        if not fresh_stream_url:
            print(f"[ERROR] ❌ Nepodarilo sa získať fresh stream URL")
            loop_state[guild_id] = False
            loop_counter[guild_id] = 0
            await play_next(guild_id, client, bot_stats)
            return

        print(f"[DEBUG] 🎵 Získaný fresh stream, vytváram player...")

        # Detekuje či je to live stream
        is_live = data.get('is_live', False)

        if is_live:
            print(f"[DEBUG] 🔴 Fresh live stream - používam live options")
            player = discord.FFmpegPCMAudio(fresh_stream_url, **ffmpeg_live_options)
        else:
            player = discord.FFmpegPCMAudio(fresh_stream_url, **ffmpeg_options)

        # Vytvorí YTDLSource wrapper
        volume_player = discord.PCMVolumeTransformer(player, volume=0.5)
        volume_player.title = data.get('title', current_song_data.title)
        volume_player.data = data
        volume_player.duration = data.get('duration')
        volume_player.is_live = is_live

        # Označí live streamy v názve
        if volume_player.is_live:
            volume_player.title = f"🔴 LIVE: {volume_player.title}"

        # Aktualizuje current player
        current_players[guild_id] = volume_player

        print(f"[DEBUG] ▶️  Spúšťam fresh replay prehrávanie...")

        # Spustí prehrávanie
        guild.voice_client.play(
            volume_player,
            after=lambda e: after_playing(e, guild_id, client, bot_stats)
        )

        # Nastaví čas začiatku pesničky
        set_song_start_time(guild_id)

        # Čaká dlhšie na stabilizáciu
        await asyncio.sleep(1.0)

        if guild.voice_client.is_playing():
            print(f"[DEBUG] ✅ Fresh replay úspešne spustený: {volume_player.title}")

            # Resetuje loop counter pri úspešnom spustení
            loop_counter[guild_id] = 0

            # Skontroluje či sa pesnička skutočne hrá po 3 sekundách
            await asyncio.sleep(3.0)
            if guild.voice_client.is_playing():
                print(f"[DEBUG] ✅ Replay stále beží po 4 sekundách - loop funguje!")
            else:
                print(f"[DEBUG] ❌ Replay sa zastavil po 4 sekundách - problém s stream!")
                loop_state[guild_id] = False
                loop_counter[guild_id] = 0
                await play_next(guild_id, client, bot_stats)
        else:
            print(f"[DEBUG] ❌ Fresh replay sa nespustil správne")
            # Skúsi znovu s malým delayom ak je to prvý pokus
            if loop_counter[guild_id] <= 3:
                print(f"[DEBUG] 🔄 Skúšam znovu o 2 sekundy...")
                await asyncio.sleep(2.0)
                await replay_current_song(guild_id, client, bot_stats)
            else:
                # Vypne loop po niekoľkých neúspešných pokusoch
                print(f"[DEBUG] ❌ Príliš veľa neúspešných pokusov, vypínam loop")
                loop_state[guild_id] = False
                loop_counter[guild_id] = 0
                await play_next(guild_id, client, bot_stats)

    except Exception as e:
        print(f"[ERROR] ❌ Chyba pri fresh loop prehrávaní: {e}")
        # Vypne loop pri chybe
        loop_state[guild_id] = False
        loop_counter[guild_id] = 0
        await play_next(guild_id, client, bot_stats)

async def play_next(guild_id, client, bot_stats):
    """Prehrá ďalšiu pesničku vo fronte"""
    print(f"[DEBUG] ⏭️  play_next volaný pre guild {guild_id}")

    if guild_id not in music_queue or not music_queue[guild_id]:
        print(f"[DEBUG] 📝 Fronta je prázdna pre guild {guild_id}")
        # Vyčistí current player ak je fronta prázdna
        if guild_id in current_players:
            del current_players[guild_id]
        return

    guild = client.get_guild(guild_id)
    if not guild:
        print(f"[DEBUG] ❌ Guild {guild_id} nebol nájdený")
        return

    voice_client = guild.voice_client
    if not voice_client:
        print(f"[DEBUG] ❌ Voice client neexistuje pre guild {guild_id}")
        return

    # Safety check - ak sa stále niečo hrá, nepokračuje
    if voice_client.is_playing():
        print(f"[DEBUG] ⚠️  Voice client stále hrá, play_next odložený")
        return

    # Získa ďalšiu pesničku z fronty
    queue_item = music_queue[guild_id].pop(0)
    url = queue_item[0]
    channel = queue_item[1]
    track_title = queue_item[2] if len(queue_item) > 2 else "Neznáma skladba"
    is_loop = queue_item[3] if len(queue_item) > 3 else False

    print(f"[DEBUG] 🎵 Pokúšam sa prehrať: {url}")

    try:
        # Vytvorí player pre pesničku
        player = await YTDLSource.from_url(url, loop=client.loop, stream=True)
        if player:
            current_players[guild_id] = player
            paused_state[guild_id] = False

            # Nastaví loop stav ak bola pesnička pridaná s loop parametrom
            if is_loop:
                loop_state[guild_id] = True

            print(f"[DEBUG] 🎵 Player vytvorený, spúšťam prehrávanie...")

            # Malé čakanie na stabilizáciu
            await asyncio.sleep(0.2)

            # Spustí prehrávanie s callback funkciou
            voice_client.play(
                player,
                after=lambda e: after_playing(e, guild_id, client, bot_stats)
            )

            # Nastaví čas začiatku pesničky
            set_song_start_time(guild_id)

            # Čaká kým sa nezačne prehrávanie
            await asyncio.sleep(0.5)

            if voice_client.is_playing():
                print(f"[DEBUG] ✅ Voice client potvrdil prehrávanie")
                bot_stats["prehranych_pesniciek"] += 1

                # Vytvorí embed s informáciami o pesničke
                embed = discord.Embed(
                    title="🎵 Teraz hrá",
                    description=f"**{player.title}**",
                    color=0x9932cc
                )

                # Pre live streamy zobrazí live status namiesto dĺžky
                if hasattr(player, 'is_live') and player.is_live:
                    embed.add_field(name="🔴 Status", value="LIVE STREAM", inline=True)
                    embed.color = 0xff0000  # Červená farba pre live
                elif player.duration:
                    minutes = player.duration // 60
                    seconds = player.duration % 60
                    embed.add_field(name="⏱️ Dĺžka", value=f"{minutes}:{seconds:02d}", inline=True)

                embed.add_field(name="📊 Vo fronte", value=str(len(music_queue[guild_id])), inline=True)

                # Pridá info o loop stavoch
                loop_info = []
                if loop_state.get(guild_id, False):
                    # Pre live streamy upozorní že loop nefunguje
                    if hasattr(player, 'is_live') and player.is_live:
                        loop_info.append("🔂 ⚠️ Live")
                    else:
                        loop_info.append("🔂 Pesnička")
                if loop_queue.get(guild_id, False):
                    loop_info.append("🔁 Fronta")

                if loop_info:
                    embed.add_field(name="🔄 Loop", value=" + ".join(loop_info), inline=True)

                # Pridá live stream warning ak je loop zapnutý
                if hasattr(player, 'is_live') and player.is_live and loop_state.get(guild_id, False):
                    embed.add_field(name="⚠️ Upozornenie", value="Live streamy sa nemôžu loopoovať!", inline=False)

                if channel:  # Pošle len ak má channel (nie pri queue loop)
                    await channel.send(embed=embed)

                print(f"[DEBUG] ✅ Prehrávanie úspešne spustené")

                # Test či sa pesnička skutočne hrá po 5 sekundách
                await asyncio.sleep(5.0)
                if voice_client.is_playing():
                    print(f"[DEBUG] ✅ Voice client stále hrá po 5 sekundách - pesnička sa skutočne prehrává!")
                else:
                    print(f"[DEBUG] ❌ Voice client sa zastavil po 5 sekundách - problém s stream!")
            else:
                print(f"[DEBUG] ❌ Voice client nepotvrdil prehrávanie, skúšam ďalšiu pesničku")
                await play_next(guild_id, client, bot_stats)
        else:
            if channel:
                await channel.send("❌ Nepodarilo sa načítať pesničku!")
            # Skúsi ďalšiu pesničku vo fronte
            await play_next(guild_id, client, bot_stats)
    except Exception as e:
        print(f"[ERROR] ❌ Chyba pri prehrávaní: {e}")

        error_msg = f"Chyba pri prehrávaní: {str(e)}"
        if "DRM" in str(e):
            error_msg = "Video je DRM chránené - skúsaj iný link!"
        elif "private" in str(e).lower():
            error_msg = "Video nie je dostupné - skúsaj iný link!"

        if channel:
            await channel.send(f"❌ {error_msg}")
        # Skúsi ďalšiu pesničku vo fronte
        await play_next(guild_id, client, bot_stats)

async def handle_join_command(message, aktualizuj_statistiky):
    """Pripojí bota do voice channelu"""
    aktualizuj_statistiky("join")

    # Skontroluje či je používateľ vo voice channeli
    if not message.author.voice:
        await message.channel.send("❌ Musíš byť pripojený do voice channelu!")
        return

    voice_channel = message.author.voice.channel

    if message.guild.voice_client:
        await message.guild.voice_client.move_to(voice_channel)
        await message.channel.send(f"✅ Premiestnený do **{voice_channel.name}**")
    else:
        await voice_channel.connect()
        await message.channel.send(f"✅ Pripojený do **{voice_channel.name}**")

async def handle_leave_command(message, aktualizuj_statistiky):
    """Odpojí bota z voice channelu"""
    aktualizuj_statistiky("leave")

    if message.guild.voice_client:
        guild_id = message.guild.id
        cleanup_guild_music_data(guild_id)
        await message.guild.voice_client.disconnect()
        await message.channel.send("✅ Odpojený z voice channelu!")
    else:
        await message.channel.send("❌ Bot nie je pripojený k žiadnemu voice channelu!")

async def handle_play_command(message, aktualizuj_statistiky, client, bot_stats):
    """Pridá pesničku do fronty a začne prehrávanie"""
    aktualizuj_statistiky("play")
    content = message.content[5:].strip()  # Odstráni "!play" a medzery

    if not content:
        embed = discord.Embed(
            title="❌ Chýba URL alebo hľadaný výraz",
            description="Musíš zadať YouTube URL alebo názov pesničky!",
            color=0xff0000
        )
        embed.add_field(name="💡 Použitie", value="`!play https://youtube.com/watch?v=...`\n`!play názov pesničky`\n`!play -loop kontrafakt temeraf`", inline=False)
        embed.add_field(name="🔄 Loop možnosti", value="`!play -loop [názov/URL]` - opakuje pesničku\n`!play -next [názov/URL]` - pridá na začiatok fronty", inline=False)
        await message.channel.send(embed=embed)
        return

    # Skontroluje či je používateľ vo voice channeli
    if not message.author.voice:
        await message.channel.send("❌ Musíš byť pripojený do voice channelu!")
        return

    # Parsuje parametre - lepší parsing
    parts = content.split()
    is_loop = False
    is_next = False
    search_terms = []

    # Prejde všetky časti a rozdelí parametre od hľadacích výrazov
    for part in parts:
        if part == "-loop":
            is_loop = True
        elif part == "-next":
            is_next = True
        else:
            # Všetko ostatné je časť hľadacieho výrazu
            search_terms.append(part)

    # Spojí hľadacie výrazy do jedného stringu
    if not search_terms:
        await message.channel.send("❌ Nebola nájdená platná URL alebo hľadaný výraz!")
        return

    search_query = " ".join(search_terms)
    print(f"[DEBUG] 🔍 Hľadám: '{search_query}' (loop: {is_loop}, next: {is_next})")

    voice_channel = message.author.voice.channel
    guild_id = message.guild.id

    # Pripojí bota ak nie je pripojený
    if not message.guild.voice_client:
        try:
            await voice_channel.connect()
            print(f"[DEBUG] 🔗 Bot sa pripojil do {voice_channel.name}")
        except Exception as e:
            await message.channel.send(f"❌ Nepodarilo sa pripojiť do voice channelu: {e}")
            return

    # Inicializuje frontu ak neexistuje
    if guild_id not in music_queue:
        music_queue[guild_id] = []

    # Pokúsi sa získať informácie o pesničke
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))

        if 'entries' in data:
            data = data['entries'][0]

        track_title = data.get('title', 'Neznáma skladba')
        is_live = data.get('is_live', False)

        # Označí live streamy v názve
        if is_live:
            track_title = f"🔴 LIVE: {track_title}"

        # Ak to nie je priama URL, použije nájdenú URL z YouTube vyhľadávania
        final_url = data.get('webpage_url', search_query)
    except Exception as e:
        print(f"[DEBUG] ❌ Chyba pri hľadaní '{search_query}': {e}")
        track_title = search_query  # Použije hľadaný výraz ako názov
        final_url = search_query

    # Pridá pesničku do fronty s parametrami
    queue_item = (final_url, message.channel, track_title, is_loop)

    if is_next and music_queue[guild_id]:
        # Pridá na začiatok fronty
        music_queue[guild_id].insert(0, queue_item)
        position_text = "**1** (ďalšia)"
    else:
        # Pridá na koniec fronty
        music_queue[guild_id].append(queue_item)
        position_text = f"**{len(music_queue[guild_id])}**"

    # Vytvorí embed s informáciami
    embed = discord.Embed(
        title="🎵 Pesnička pridaná do fronty",
        description=f"**{track_title}**\nPozícia vo fronte: {position_text}",
        color=0xff0000 if "🔴 LIVE:" in track_title else 0x9932cc
    )

    # Pridá info o parametroch
    params = []
    if is_loop:
        if "🔴 LIVE:" in track_title:
            params.append("🔂⚠️ Loop (nefunguje pre live)")
        else:
            params.append("🔂 Loop zapnutý")
    if is_next:
        params.append("⏭️ Pridané na začiatok")

    if params:
        embed.add_field(name="⚙️ Parametre", value="\n".join(params), inline=False)

    # Pridá info o hľadaní ak to nebola priama URL
    if not search_query.startswith("http"):
        embed.add_field(name="🔍 Hľadaný výraz", value=f"`{search_query}`", inline=False)

    # Pridá live stream info
    if "🔴 LIVE:" in track_title:
        embed.add_field(name="🔴 Live Stream", value="Prehrá sa v reálnom čase", inline=False)

    await message.channel.send(embed=embed)

    print(f"[DEBUG] ✅ Pridaná do fronty: {track_title} (hľadané: '{search_query}', loop: {is_loop}, next: {is_next})")
    print(f"[DEBUG] 🎵 Voice client playing: {message.guild.voice_client.is_playing()}")
    print(f"[DEBUG] ⏸️  Voice client paused: {message.guild.voice_client.is_paused()}")

    # Ak sa momentálne nič nehrá, začne prehrávanie
    if not message.guild.voice_client.is_playing() and not message.guild.voice_client.is_paused():
        print(f"[DEBUG] ▶️  Spúšťam play_next...")
        await play_next(guild_id, client, bot_stats)

async def handle_loop_command(message, aktualizuj_statistiky):
    """Zapína/vypína loop pre aktuálnu pesničku alebo frontu"""
    aktualizuj_statistiky("loop")
    guild_id = message.guild.id
    parts = message.content.split()

    # Parsuje parametre
    if len(parts) > 1:
        param = parts[1].lower()
        if param in ["song", "pesnička", "pesnicka"]:
            # Loop pre aktuálnu pesničku
            current_loop = loop_state.get(guild_id, False)
            loop_state[guild_id] = not current_loop
            status = "zapnutý" if loop_state[guild_id] else "vypnutý"
            await message.channel.send(f"🔂 Loop pre aktuálnu pesničku **{status}**!")

        elif param in ["queue", "fronta"]:
            # Loop pre frontu
            current_queue_loop = loop_queue.get(guild_id, False)
            loop_queue[guild_id] = not current_queue_loop
            status = "zapnutý" if loop_queue[guild_id] else "vypnutý"
            await message.channel.send(f"🔁 Loop pre frontu **{status}**!")

        elif param in ["off", "vypni", "stop"]:
            # Vypne všetky loopy
            loop_state[guild_id] = False
            loop_queue[guild_id] = False
            await message.channel.send("🔄 Všetky loopy **vypnuté**!")

        else:
            # Neznámy parameter - zobrazí nápovedu
            embed = discord.Embed(
                title="❌ Neznámy parameter",
                description="Dostupné možnosti:",
                color=0xff0000
            )
            embed.add_field(name="🔂 `!loop song`", value="Zapne/vypne loop pre aktuálnu pesničku", inline=False)
            embed.add_field(name="🔁 `!loop queue`", value="Zapne/vypne loop pre celú frontu", inline=False)
            embed.add_field(name="🔄 `!loop off`", value="Vypne všetky loopy", inline=False)
            embed.add_field(name="📊 `!loop`", value="Zobrazí aktuálny stav loopov", inline=False)
            await message.channel.send(embed=embed)
    else:
        # Bez parametra - zobrazí aktuálny stav alebo prepne song loop
        if guild_id not in current_players or not current_players[guild_id]:
            await message.channel.send("❌ Momentálne sa nič nehrá!")
            return

        # Prepne song loop
        current_loop = loop_state.get(guild_id, False)
        loop_state[guild_id] = not current_loop

        # Zobrazí aktuálny stav
        embed = discord.Embed(
            title="🔄 Loop Stav",
            color=0x9932cc
        )

        song_status = "🔂 Zapnutý" if loop_state.get(guild_id, False) else "⏹️ Vypnutý"
        queue_status = "🔁 Zapnutý" if loop_queue.get(guild_id, False) else "⏹️ Vypnutý"

        embed.add_field(name="Pesnička", value=song_status, inline=True)
        embed.add_field(name="Fronta", value=queue_status, inline=True)

        if guild_id in current_players and current_players[guild_id]:
            embed.add_field(name="🎵 Aktuálna", value=current_players[guild_id].title, inline=False)

        await message.channel.send(embed=embed)

async def handle_pause_command(message, aktualizuj_statistiky):
    """Pozastaví prehrávanie hudby"""
    aktualizuj_statistiky("pause")
    guild_id = message.guild.id

    if not message.guild.voice_client:
        await message.channel.send("❌ Bot nie je pripojený k voice channelu!")
        return

    if message.guild.voice_client.is_playing():
        message.guild.voice_client.pause()
        paused_state[guild_id] = True

        # Získa názov aktuálnej pesničky
        current_song = "Neznáma"
        if guild_id in current_players and current_players[guild_id]:
            current_song = current_players[guild_id].title

        embed = discord.Embed(
            title="⏸️ Hudba pozastavená",
            description=f"**{current_song}**\n\nPouži `!resume` na pokračovanie",
            color=0xffa500
        )
        await message.channel.send(embed=embed)
    elif message.guild.voice_client.is_paused():
        await message.channel.send("❌ Hudba je už pozastavená! Použi `!resume`")
    else:
        await message.channel.send("❌ Momentálne sa nič nehrá!")

async def handle_resume_command(message, aktualizuj_statistiky):
    """Obnoví prehrávanie hudby"""
    aktualizuj_statistiky("resume")
    guild_id = message.guild.id

    if not message.guild.voice_client:
        await message.channel.send("❌ Bot nie je pripojený k voice channelu!")
        return

    if message.guild.voice_client.is_paused():
        message.guild.voice_client.resume()
        paused_state[guild_id] = False

        # Získa názov aktuálnej pesničky
        current_song = "Neznáma"
        if guild_id in current_players and current_players[guild_id]:
            current_song = current_players[guild_id].title

        embed = discord.Embed(
            title="▶️ Hudba obnovená",
            description=f"**{current_song}**",
            color=0x00ff00
        )
        await message.channel.send(embed=embed)
    else:
        await message.channel.send("❌ Hudba nie je pozastavená!")

async def handle_skip_command(message, aktualizuj_statistiky):
    """Preskočí aktuálnu pesničku"""
    aktualizuj_statistiky("skip")

    if not message.guild.voice_client:
        await message.channel.send("❌ Bot nie je pripojený k voice channelu!")
        return

    if message.guild.voice_client.is_playing() or message.guild.voice_client.is_paused():
        # Ak je zapnutý song loop, vypne ho pred skipom
        guild_id = message.guild.id
        if loop_state.get(guild_id, False):
            loop_state[guild_id] = False

        message.guild.voice_client.stop()
        await message.channel.send("⏭️ Pesnička preskočená!")
    else:
        await message.channel.send("❌ Momentálne sa nič nehrá!")

async def handle_stop_command(message, aktualizuj_statistiky):
    """Zastaví prehrávanie a vyčistí frontu"""
    aktualizuj_statistiky("stop")
    guild_id = message.guild.id

    if not message.guild.voice_client:
        await message.channel.send("❌ Bot nie je pripojený k voice channelu!")
        return

    cleanup_guild_music_data(guild_id)
    message.guild.voice_client.stop()
    await message.channel.send("⏹️ Prehrávanie zastavené a fronta vyčistená!")

async def handle_queue_command(message, aktualizuj_statistiky):
    """Zobrazí aktuálnu frontu pesničiek"""
    aktualizuj_statistiky("queue")
    guild_id = message.guild.id

    if guild_id not in music_queue or not music_queue[guild_id]:
        embed = discord.Embed(
            title="📝 Fronta je prázdna",
            description="Použi `!play [URL]` na pridanie pesničiek!",
            color=0xff6b6b
        )
        await message.channel.send(embed=embed)
        return

    embed = discord.Embed(
        title="🎵 Aktuálna fronta",
        description=f"**{len(music_queue[guild_id])}** pesničiek vo fronte",
        color=0x9b59b6
    )

    # Zobrazí aktuálnu pesničku
    if guild_id in current_players and current_players[guild_id]:
        status_parts = []
        if paused_state.get(guild_id, False):
            status_parts.append("⏸️ Pozastavené")
        else:
            status_parts.append("▶️ Hrá")

        if loop_state.get(guild_id, False):
            # Pre live streamy upozorní že loop nefunguje
            if hasattr(current_players[guild_id], 'is_live') and current_players[guild_id].is_live:
                status_parts.append("🔂⚠️")
            else:
                status_parts.append("🔂")

        status = " ".join(status_parts)
        embed.add_field(
            name="🎵 Teraz",
            value=f"{status}: **{current_players[guild_id].title}**",
            inline=False
        )

    # Zobrazí loop stavy ak sú zapnuté
    loop_info = []
    if loop_state.get(guild_id, False):
        loop_info.append("🔂 Pesnička")
    if loop_queue.get(guild_id, False):
        loop_info.append("🔁 Fronta")

    if loop_info:
        embed.add_field(name="🔄 Aktívne loopy", value=" + ".join(loop_info), inline=False)

    # Zobrazí prvých 10 pesničiek vo fronte
    for i, queue_item in enumerate(music_queue[guild_id][:10], 1):
        url = queue_item[0]
        track_title = queue_item[2] if len(queue_item) > 2 else "Neznámy názov"
        is_loop = queue_item[3] if len(queue_item) > 3 else False

        title_display = track_title[:45] + ('...' if len(track_title) > 45 else '')
        if is_loop:
            title_display += " 🔂"

        embed.add_field(
            name=f"{i}.",
            value=title_display,
            inline=False
        )

    if len(music_queue[guild_id]) > 10:
        embed.add_field(name="...", value=f"A ďalších {len(music_queue[guild_id]) - 10} pesničiek", inline=False)

    await message.channel.send(embed=embed)

async def handle_volume_command(message, aktualizuj_statistiky):
    """Nastaví hlasitosť prehrávača"""
    aktualizuj_statistiky("volume")
    parts = message.content.split(" ", 1)

    if len(parts) < 2:
        guild_id = message.guild.id
        if guild_id in current_players and current_players[guild_id]:
            current_volume = int(current_players[guild_id].volume * 100)
            embed = discord.Embed(
                title="🔊 Aktuálna hlasitosť",
                description=f"**{current_volume}%**",
                color=0x9b59b6
            )
            embed.add_field(name="💡 Použitie", value="`!volume 50` (0-100)", inline=False)
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("❌ Momentálne sa nič nehrá!")
        return

    try:
        volume = int(parts[1])
        if volume < 0 or volume > 100:
            await message.channel.send("❌ Hlasitosť musí byť medzi 0 a 100!")
            return

        guild_id = message.guild.id
        if guild_id in current_players and current_players[guild_id]:
            current_players[guild_id].volume = volume / 100.0
            await message.channel.send(f"🔊 Hlasitosť nastavená na **{volume}%**!")
        else:
            await message.channel.send("❌ Momentálne sa nič nehrá!")
    except ValueError:
        await message.channel.send("❌ Neplatné číslo! Použi číslo od 0 do 100.")

def cleanup_guild_music_data(guild_id):
    """Vyčistí údaje o hudbe pre daný server"""
    if guild_id in music_queue:
        music_queue[guild_id].clear()
    if guild_id in current_players:
        # Cleanup live stream player ak existuje
        player = current_players[guild_id]
        if hasattr(player, 'cleanup'):
            try:
                player.cleanup()
            except:
                pass
        del current_players[guild_id]
    if guild_id in paused_state:
        del paused_state[guild_id]
    if guild_id in loop_state:
        del loop_state[guild_id]
    if guild_id in loop_queue:
        del loop_queue[guild_id]
    if guild_id in loop_counter:
        del loop_counter[guild_id]
    if guild_id in song_start_times:
        del song_start_times[guild_id]

async def handle_voice_state_update(member, before, after):
    """Spracuje zmeny vo voice channeli"""
    if member.bot:
        return

    # Skontroluje či sa niekto odpojil z kanála kde je bot
    if before.channel and member.guild.voice_client and member.guild.voice_client.channel == before.channel:
        voice_client = member.guild.voice_client
        members = [m for m in voice_client.channel.members if not m.bot]

        # Ak zostal bot sám, odpojí sa po 30 sekundách
        if len(members) == 0:
            await asyncio.sleep(30)
            # Znovu skontroluje či je stále sám
            try:
                members = [m for m in voice_client.channel.members if not m.bot]
                if len(members) == 0:
                    guild_id = member.guild.id
                    cleanup_guild_music_data(guild_id)
                    await voice_client.disconnect()
            except:
                pass  # Voice client mohol byť už odpojený

async def handle_test_command(message, aktualizuj_statistiky):
    """Testovací príkaz na otestovanie prehrávača bez loop"""
    aktualizuj_statistiky("test")
    guild_id = message.guild.id

    # Vypne všetky loopy
    loop_state[guild_id] = False
    loop_queue[guild_id] = False
    if guild_id in loop_counter:
        loop_counter[guild_id] = 0

    # Zastaví aktuálne prehrávanie
    if message.guild.voice_client and (message.guild.voice_client.is_playing() or message.guild.voice_client.is_paused()):
        message.guild.voice_client.stop()

    # Vyčistí frontu
    cleanup_guild_music_data(guild_id)

    embed = discord.Embed(
        title="🔧 Test Mode Aktivovaný",
        description="Všetky loopy vypnuté, fronta vyčistená.\n\n**Skús teraz:** `!play kontrafakt temeraf`\n**Sleduj debug logy** v konzole.",
        color=0x00ff00
    )

    embed.add_field(name="🔍 Čo sledovať", value="• `⏱️ Čas prehrávání: X.XX sekúnd`\n• `✅ Voice client stále hrá po X sekundách`\n• Či sa pesnička skutočne počúva", inline=False)
    embed.add_field(name="⚡ Ak sa nič nehrá", value="Problem je v FFmpeg alebo stream URL", inline=False)

    await message.channel.send(embed=embed)

async def handle_debug_command(message, aktualizuj_statistiky):
    """Diagnostický príkaz na testovanie FFmpeg a stream URL"""
    aktualizuj_statistiky("debug")

    embed = discord.Embed(
        title="🔍 Spúšťam diagnostiku...",
        description="Testujem FFmpeg a stream URLs",
        color=0xffa500
    )
    await message.channel.send(embed=embed)

    try:
        # Test 1: Skontroluje FFmpeg
        print("[DEBUG] 🔧 Testujem FFmpeg...")
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        ffmpeg_ok = result.returncode == 0
        ffmpeg_version = result.stdout.split('\n')[0] if ffmpeg_ok else "FFmpeg nedostupný"

        # Test 2: Testuje yt-dlp stream
        print("[DEBUG] 🔍 Testujem yt-dlp stream...")
        test_query = "never gonna give you up rick astley"
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: ytdl.extract_info(test_query, download=False)
        )

        if 'entries' in data:
            data = data['entries'][0]

        stream_url = data.get('url')
        video_title = data.get('title', 'Neznámy')

        # Test 3: Skúsi vytvoriť FFmpeg player
        print("[DEBUG] 🎵 Testujem FFmpeg player...")
        test_player = None
        player_error = None
        try:
            test_player = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
            player_ok = True
        except Exception as e:
            player_error = str(e)
            player_ok = False

        # Výsledky
        results_embed = discord.Embed(
            title="🔍 Diagnostické výsledky",
            color=0x00ff00 if (ffmpeg_ok and stream_url and player_ok) else 0xff0000
        )

        results_embed.add_field(
            name="🔧 FFmpeg",
            value=f"{'✅' if ffmpeg_ok else '❌'} {ffmpeg_version}",
            inline=False
        )

        results_embed.add_field(
            name="🔗 Stream URL",
            value=f"{'✅' if stream_url else '❌'} {video_title}\n`{stream_url[:80] + '...' if stream_url and len(stream_url) > 80 else stream_url or 'Nedostupný'}`",
            inline=False
        )

        results_embed.add_field(
            name="🎵 FFmpeg Player",
            value=f"{'✅ Úspešne vytvorený' if player_ok else f'❌ {player_error}'}",
            inline=False
        )

        if ffmpeg_ok and stream_url and player_ok:
            results_embed.add_field(
                name="✅ Záver",
                value="Všetky komponenty fungují! Problém môže byť v Discord permissions alebo voice client.",
                inline=False
            )
            results_embed.add_field(
                name="🔧 Riešenie",
                value="• Skontroluj Bot permissions v voice channeli\n• Skús iný voice channel\n• Reštartuj Discord klienta",
                inline=False
            )
        else:
            failed_components = []
            if not ffmpeg_ok:
                failed_components.append("FFmpeg")
            if not stream_url:
                failed_components.append("Stream URL")
            if not player_ok:
                failed_components.append("FFmpeg Player")

            results_embed.add_field(
                name="❌ Problém",
                value=f"Chyba v: {', '.join(failed_components)}",
                inline=False
            )

            if not ffmpeg_ok:
                results_embed.add_field(
                    name="🔧 FFmpeg fix",
                    value="Nainštaluj FFmpeg: `apt install ffmpeg` (Linux) alebo stiahni z ffmpeg.org",
                    inline=False
                )

        await message.channel.send(embed=results_embed)

        # Cleanup test player
        if test_player:
            test_player.cleanup()

    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Chyba pri diagnostike",
            description=f"```{str(e)}```",
            color=0xff0000
        )
        await message.channel.send(embed=error_embed)
        print(f"[ERROR] Diagnostika zlyhal: {e}")

async def handle_permissions_command(message, aktualizuj_statistiky):
    """Skontroluje Discord permissions"""
    aktualizuj_statistiky("permissions")

    if not message.guild.voice_client:
        await message.channel.send("❌ Bot nie je pripojený k voice channelu! Použi `!join` najprv.")
        return

    voice_channel = message.guild.voice_client.channel
    bot_member = message.guild.me

    # Skontroluje permissions
    perms = voice_channel.permissions_for(bot_member)

    embed = discord.Embed(
        title="🔐 Discord Voice Permissions",
        description=f"Channel: **{voice_channel.name}**",
        color=0x9932cc
    )

    required_perms = [
        ("Connect", perms.connect),
        ("Speak", perms.speak),
        ("Use Voice Activity", perms.use_voice_activation),
        ("View Channel", perms.view_channel)
    ]

    all_ok = True
    for perm_name, has_perm in required_perms:
        embed.add_field(
            name=f"{'✅' if has_perm else '❌'} {perm_name}",
            value="OK" if has_perm else "CHÝBA",
            inline=True
        )
        if not has_perm:
            all_ok = False

    if all_ok:
        embed.add_field(
            name="✅ Záver",
            value="Všetky potrebné permissions sú OK!",
            inline=False
        )
        embed.color = 0x00ff00
    else:
        embed.add_field(
            name="❌ Problém",
            value="Chýbajú permissions! Daj botovi Admin práva alebo správne voice permissions.",
            inline=False
        )
        embed.color = 0xff0000

    await message.channel.send(embed=embed)

async def handle_live_command(message, aktualizuj_statistiky):
    """Testuje live stream funkcionalitu"""
    aktualizuj_statistiky("live")

    embed = discord.Embed(
        title="🔴 Live Stream Test",
        description="Testujem live stream detekciu...",
        color=0xff0000
    )
    await message.channel.send(embed=embed)

    # Testuje známy live stream (môže byť offline)
    test_urls = [
        "https://www.youtube.com/watch?v=jfKfPfyJRdk",  # lofi hip hop radio
        "https://www.youtube.com/watch?v=5qap5aO4i9A"   # chillhop music
    ]

    for i, test_url in enumerate(test_urls, 1):
        try:
            print(f"[DEBUG] 🔴 Testujem live stream #{i}: {test_url}")

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(test_url, download=False))

            if 'entries' in data:
                data = data['entries'][0]

            title = data.get('title', 'Neznámy')
            is_live = data.get('is_live', False)
            duration = data.get('duration', 'N/A')

            status = "🔴 LIVE" if is_live else "📹 Nie je live"

            result_embed = discord.Embed(
                title=f"Test #{i} - {status}",
                description=f"**{title}**",
                color=0x00ff00 if is_live else 0xffa500
            )

            result_embed.add_field(name="🔗 URL", value=test_url, inline=False)
            result_embed.add_field(name="⏱️ Dĺžka", value=str(duration) if duration else "N/A", inline=True)
            result_embed.add_field(name="📡 Live Status", value="Áno" if is_live else "Nie", inline=True)

            await message.channel.send(embed=result_embed)

            if is_live:
                await message.channel.send(f"✅ **Nájdený live stream!** Skús: `!play {test_url}`")
                break

        except Exception as e:
            error_embed = discord.Embed(
                title=f"❌ Test #{i} zlyhal",
                description=f"```{str(e)}```",
                color=0xff0000
            )
            await message.channel.send(embed=error_embed)

    # Návod
    help_embed = discord.Embed(
        title="💡 Ako používať live streamy",
        color=0x9932cc
    )
    help_embed.add_field(
        name="🔴 Live stream príkazy",
        value="• `!play [live_youtube_url]` - prehrá live stream\n• `!live` - testuje live stream detekciu\n• Live streamy majú 🔴 označenie",
        inline=False
    )
    help_embed.add_field(
        name="⚠️ Obmedzenia",
        value="• Live streamy sa **nemôžu loopoovať**\n• Môžu sa občas prerušiť\n• Závisia od stability streamu",
        inline=False
    )

    await message.channel.send(embed=help_embed)

def get_music_help_text():
    """Vráti text nápovedy pre hudobné príkazy"""
    return "`!play [URL]`, `!loop`, `!pause/resume`, `!skip`, `!volume [0-100]`, `!queue`, `!stop`, `!join/leave`, `!live`"