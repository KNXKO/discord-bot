import discord
import asyncio
import yt_dlp
from datetime import datetime
from . import spotify

# Slovníky na ukladanie stavu hudby pre každý server
music_queue = {}
current_players = {}
paused_state = {}

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
}

# Nastavenia pre FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

            if 'entries' in data:
                data = data['entries'][0]

            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            error_msg = str(e).lower()
            if 'drm' in error_msg:
                print(f"[WARNING] DRM chraneny obsah: {url}")
            elif 'private' in error_msg or 'unavailable' in error_msg:
                print(f"[WARNING] Video nie je dostupne: {url}")
            elif 'age' in error_msg:
                print(f"[WARNING] Age-restricted video: {url}")
            else:
                print(f"[ERROR] Chyba pri stahovani: {e}")
            return None

async def play_next(guild_id, client, bot_stats):
    """Prehrá nasledujúcu pesničku z fronty"""
    if guild_id not in music_queue or not music_queue[guild_id]:
        return

    guild = client.get_guild(guild_id)
    if not guild:
        return

    voice_client = guild.voice_client
    if not voice_client:
        return

    url, channel = music_queue[guild_id].pop(0)

    try:
        player = await YTDLSource.from_url(url, loop=client.loop, stream=True)
        if player:
            current_players[guild_id] = player
            paused_state[guild_id] = False  # Resetuje pozastavený stav
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(guild_id, client, bot_stats), client.loop) if not e else print(f'Chyba prehrávača: {e}'))

            bot_stats["prehranych_pesniciek"] += 1

            embed = discord.Embed(
                title="🎵 Teraz hrá",
                description=f"**{player.title}**",
                color=0x9932cc
            )
            if player.duration:
                minutes = player.duration // 60
                seconds = player.duration % 60
                embed.add_field(name="⏱️ Dĺžka", value=f"{minutes}:{seconds:02d}", inline=True)

            embed.add_field(name="📊 Vo fronte", value=str(len(music_queue[guild_id])), inline=True)
            await channel.send(embed=embed)
        else:
            error_msg = "Nepodarilo sa nacitat pesnicku!"
            if "DRM" in str(e):
                error_msg = "Video je DRM chranene a nepodporuje sa!"
            elif "private" in str(e).lower():
                error_msg = "Video je sukromne alebo zmazane!"
            elif "age" in str(e).lower():
                error_msg = "Video ma vekove obmedzenie!"

            await channel.send(f"[ERROR] {error_msg}")
            await play_next(guild_id, client, bot_stats)
    except Exception as e:
        error_msg = f"Chyba pri prehravani: {str(e)}"
        if "DRM" in str(e):
            error_msg = "Video je DRM chranene - skusaj iny link!"
        elif "private" in str(e).lower():
            error_msg = "Video nie je dostupne - skusaj iny link!"

        await channel.send(f"[ERROR] {error_msg}")
        await play_next(guild_id, client, bot_stats)

async def handle_join_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !join"""
    aktualizuj_statistiky("join")
    mention = message.author.mention

    if message.author.voice:
        voice_channel = message.author.voice.channel
        if message.guild.voice_client:
            await message.guild.voice_client.move_to(voice_channel)
        else:
            await voice_channel.connect()

async def handle_leave_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !leave"""
    aktualizuj_statistiky("leave")
    mention = message.author.mention

    if message.guild.voice_client:
        guild_id = message.guild.id
        cleanup_guild_music_data(guild_id)
        await message.guild.voice_client.disconnect()

async def handle_play_command(message, aktualizuj_statistiky, client, bot_stats):
    """Spracuje príkaz !play"""
    aktualizuj_statistiky("play")
    mention = message.author.mention
    parts = message.content.split(" ", 1)

    if len(parts) < 2:
        embed = discord.Embed(
            title="❌ Chýba URL",
            description="Musíš zadať YouTube URL!",
            color=0xff0000
        )
        embed.add_field(name="💡 Použitie", value="`!play https://youtube.com/watch?v=...`", inline=False)
        embed.add_field(name="🔍 Tip", value="Môžeš vložiť aj názov pesničky a bot ju nájde", inline=False)
        await message.channel.send(embed=embed)
        return

    url = parts[1]
    voice_channel = message.author.voice.channel
    guild_id = message.guild.id

    if not message.guild.voice_client:
        await voice_channel.connect()

    if guild_id not in music_queue:
        music_queue[guild_id] = []

    music_queue[guild_id].append((url, message.channel))

    embed = discord.Embed(
        title="🎵 Pesnička pridaná do fronty",
        description=f"Pozícia vo fronte: **{len(music_queue[guild_id])}**",
        color=0x9932cc
    )
    await message.channel.send(embed=embed)

    if not message.guild.voice_client.is_playing():
        await play_next(guild_id, client, bot_stats)

async def handle_pause_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !pause"""
    aktualizuj_statistiky("pause")
    mention = message.author.mention
    guild_id = message.guild.id

    if message.guild.voice_client and message.guild.voice_client.is_playing():
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
    elif message.guild.voice_client and message.guild.voice_client.is_paused():
        await message.channel.send(f"{mention} ❌ Hudba je už pozastavená! Použi `!resume`")

async def handle_resume_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !resume"""
    aktualizuj_statistiky("resume")
    mention = message.author.mention
    guild_id = message.guild.id

    if message.guild.voice_client and message.guild.voice_client.is_paused():
        message.guild.voice_client.resume()
        paused_state[guild_id] = False

        # Získa názov aktuálnej pesničky
        current_song = "Neznáma"
        if guild_id in current_players and current_players[guild_id]:
            current_song = current_players[guild_id].title

        embed = discord.Embed(
            title="▶️ Hudba pokračuje",
            description=f"**{current_song}**",
            color=0x9b59b6
        )
        await message.channel.send(embed=embed)
    elif message.guild.voice_client and message.guild.voice_client.is_playing():
        await message.channel.send(f"{mention} ❌ Hudba už hrá! Použi `!pause` na pozastavenie")

async def handle_skip_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !skip"""
    aktualizuj_statistiky("skip")
    mention = message.author.mention

    if message.guild.voice_client and (message.guild.voice_client.is_playing() or message.guild.voice_client.is_paused()):
        message.guild.voice_client.stop()
        await message.channel.send("⏭️ Pesnička preskočená!")

async def handle_stop_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !stop"""
    aktualizuj_statistiky("stop")
    mention = message.author.mention
    guild_id = message.guild.id

    if message.guild.voice_client:
        cleanup_guild_music_data(guild_id)
        message.guild.voice_client.stop()
        await message.channel.send("⏹️ Prehrávanie zastavené a fronta vyčistená!")

async def handle_queue_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !queue"""
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

    if guild_id in current_players and current_players[guild_id]:
        status = "⏸️ Pozastavené" if paused_state.get(guild_id, False) else "▶️ Hrá"
        embed.add_field(
            name="🎵 Teraz",
            value=f"{status}: **{current_players[guild_id].title}**",
            inline=False
        )

    # Zobrazí prvých 10 pesničiek vo fronte
    for i, (url, _, track_title) in enumerate(music_queue[guild_id][:10], 1):
        try:
            if track_title and track_title != "Neznáma skladba":
                title = track_title
                duration_str = ""
            else:
                info = ytdl.extract_info(url, download=False)
                title = info.get('title', 'Neznámy názov')
                duration = info.get('duration', 0)
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f" ({minutes}:{seconds:02d})"
                else:
                    duration_str = ""

            embed.add_field(
                name=f"{i}.",
                value=f"{title[:50]}{'...' if len(title) > 50 else ''}{duration_str}",
                inline=False
            )
        except:
            embed.add_field(name=f"{i}.", value="Chyba pri načítaní informácií", inline=False)

    if len(music_queue[guild_id]) > 10:
        embed.add_field(name="...", value=f"A ďalších {len(music_queue[guild_id]) - 10} pesničiek", inline=False)

    await message.channel.send(embed=embed)

async def handle_volume_command(message, aktualizuj_statistiky):
    """Spracuje príkaz !volume"""
    aktualizuj_statistiky("volume")
    mention = message.author.mention
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

    try:
        volume = int(parts[1])
        if volume < 0 or volume > 100:
            await message.channel.send(f"{mention} ❌ Hlasitosť musí byť medzi 0 a 100!")
            return

        guild_id = message.guild.id
        if guild_id in current_players and current_players[guild_id]:
            current_players[guild_id].volume = volume / 100.0
            await message.channel.send(f"🔊 Hlasitosť nastavená na **{volume}%**!")
    except ValueError:
        await message.channel.send(f"{mention} ❌ Neplatné číslo! Použi číslo od 0 do 100.")

def cleanup_guild_music_data(guild_id):
    """Vyčistí hudobné dáta pre server"""
    if guild_id in music_queue:
        music_queue[guild_id].clear()
    if guild_id in current_players:
        del current_players[guild_id]
    if guild_id in paused_state:
        del paused_state[guild_id]

async def handle_voice_state_update(member, before, after):
    """Spracuje zmenu hlasového stavu používateľa"""
    if member.bot:
        return

    # Skontroluje či sa niekto odpojil z kanála kde je bot
    if before.channel and member.guild.voice_client and member.guild.voice_client.channel == before.channel:
        voice_client = member.guild.voice_client
        members = [m for m in voice_client.channel.members if not m.bot]

        # Ak zostal bot sám, odpojí sa
        if len(members) == 0:
            guild_id = member.guild.id
            cleanup_guild_music_data(guild_id)
            await voice_client.disconnect()

def get_music_help_text():
    """Vráti text s hudobnými príkazmi pre help"""
    return "`!play [URL]`, `!pause/resume`, `!skip`, `!volume [0-100]`, `!queue`, `!stop`, `!join/leave`"