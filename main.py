import discord
import os
import sys
import signal
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Import modulov z modules priečinka
from modules import yt_music, storage, clean, commands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Štatistiky bota
bot_stats = {
    "prikazy_pouzite": 0,
    "spusteny": datetime.now(),
    "najcastejsi_prikaz": {},
    "pocet_hier": 0,
    "ulozenych_hlasiek": 0,
    "prehranych_pesniciek": 0
}

def aktualizuj_statistiky(prikaz):
    bot_stats["prikazy_pouzite"] += 1
    if prikaz in bot_stats["najcastejsi_prikaz"]:
        bot_stats["najcastejsi_prikaz"][prikaz] += 1
    else:
        bot_stats["najcastejsi_prikaz"][prikaz] = 1

async def poslat_offline_spravu():
    try:
        kanal = client.get_channel(1375790882749419560)
        if not kanal:
            return

        async for message in kanal.history(limit=5):
            if (message.author == client.user and message.embeds and
                "OFFLINE" in message.embeds[0].title):
                return

        embed = discord.Embed(
            title="🔴  KNX's Bot je OFFLINE!",
            description=f"KNX's Bot sa odpojil.\n⏰  {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            color=0xff0000
        )
        await kanal.send(embed=embed)
    except Exception as e:
        print(f"Chyba: {e}")

@client.event
async def on_disconnect():
    print("KNX's Bot sa odpojil!")
    await poslat_offline_spravu()

def signal_handler(sig, frame):
    print("\nKNX's Bot sa vypína...")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(poslat_offline_spravu())
    except:
        pass
    sys.exit(2)

signal.signal(signal.SIGINT, signal_handler)

@client.event
async def on_ready():
    """Event pri spustení bota"""
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="KNX's commands | !help 🥶"
        )
    )
    storage.nacitaj_hlasky(bot_stats)
    print(f"KNX's Bot je online!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = message.content.lower().strip()
    mention = message.author.mention

    # HELP PRÍKAZ
    if msg.startswith("!help"):
        aktualizuj_statistiky("help")
        embed = discord.Embed(
            title="🥶  KNX's Bot - Príkazy",
            description="Dostupné príkazy: ",
            color=0x9932cc
        )
        embed.add_field(name="🎮  Zábava", value="`!cicina`, `!dirgova`, `!magicka gula`, `!kocky`", inline=False)
        embed.add_field(name="🎵  Hudba", value=yt_music.get_music_help_text(), inline=False)
        embed.add_field(name="💾  Pamäť", value="`!uloz [text]`, `!hlasky`, `!najdi [slovo]`, `!posledne [počet]`", inline=False)
        embed.add_field(name="📊  Ostatné", value="`!stats`, `!restart`, `!clean`", inline=False)
        await message.channel.send(embed=embed)

    # HUDOBNÉ PRÍKAZY - delegované do yt_music modulu
    elif msg.startswith("!join"):
        await yt_music.handle_join_command(message, aktualizuj_statistiky)

    elif msg.startswith("!leave"):
        await yt_music.handle_leave_command(message, aktualizuj_statistiky)

    elif msg.startswith("!play"):
        await yt_music.handle_play_command(message, aktualizuj_statistiky, client, bot_stats)

    elif msg.startswith("!pause"):
        await yt_music.handle_pause_command(message, aktualizuj_statistiky)

    elif msg.startswith("!resume"):
        await yt_music.handle_resume_command(message, aktualizuj_statistiky)

    elif msg.startswith("!skip"):
        await yt_music.handle_skip_command(message, aktualizuj_statistiky)

    elif msg.startswith("!stop"):
        await yt_music.handle_stop_command(message, aktualizuj_statistiky)

    elif msg.startswith("!queue"):
        await yt_music.handle_queue_command(message, aktualizuj_statistiky)

    elif msg.startswith("!volume"):
        await yt_music.handle_volume_command(message, aktualizuj_statistiky)

    # ZÁBAVNÉ PRÍKAZY - delegované do commands modulu
    elif msg.startswith("!cicina"):
        await commands.handle_cicina_command(message, aktualizuj_statistiky)

    elif msg.startswith("!dirgova"):
        await commands.handle_dirgova_command(message, aktualizuj_statistiky)

    elif msg.startswith("!magicka gula"):
        await commands.handle_magicka_gula_command(message, aktualizuj_statistiky)

    elif msg.startswith("!kocky"):
        await commands.handle_kocky_command(message, aktualizuj_statistiky, bot_stats)

    # SYSTÉM UKLADANIA HLÁŠOK - delegované do storage modulu
    elif msg.startswith("!uloz"):
        await storage.handle_uloz_command(message, aktualizuj_statistiky, bot_stats)

    elif msg.startswith("!hlasky"):
        await storage.handle_hlasky_command(message, aktualizuj_statistiky)

    elif msg.startswith("!najdi"):
        await storage.handle_najdi_command(message, aktualizuj_statistiky)

    elif msg.startswith("!posledne"):
        await storage.handle_posledne_command(message, aktualizuj_statistiky)

    # MODERÁTORSKÉ PRÍKAZY - delegované do clean modulu
    elif msg.startswith("!clean"):
        await clean.handle_clean_command(message, aktualizuj_statistiky)

    # ŠTATISTIKY
    elif msg.startswith("!stats"):
        aktualizuj_statistiky("stats")
        uptime = datetime.now() - bot_stats["spusteny"]
        dni = uptime.days
        hodiny = uptime.seconds // 3600
        minuty = (uptime.seconds % 3600) // 60

        embed = discord.Embed(
            title="📊 KNX's Bot Štatistiky",
            color=0x9932cc
        )
        embed.add_field(name="⏰ Beží", value=f"{dni}d {hodiny}h {minuty}m", inline=True)
        embed.add_field(name="🔧 Príkazy použité", value=bot_stats["prikazy_pouzite"], inline=True)
        embed.add_field(name="🎵 Pesničiek prehrané", value=bot_stats["prehranych_pesniciek"], inline=True)
        embed.add_field(name="🎮 Hier zahraných", value=bot_stats["pocet_hier"], inline=True)
        embed.add_field(name="💾 Hlášok uložených", value=bot_stats["ulozenych_hlasiek"], inline=True)

        if bot_stats["najcastejsi_prikaz"]:
            najcastejsi = max(bot_stats["najcastejsi_prikaz"], key=bot_stats["najcastejsi_prikaz"].get)
            embed.add_field(name="🏆 Najčastejší príkaz", value=f"{najcastejsi} ({bot_stats['najcastejsi_prikaz'][najcastejsi]}x)", inline=True)

        await message.channel.send(embed=embed)

    # ADMIN PRÍKAZY
    elif msg.startswith("!rr"):
        aktualizuj_statistiky("restart")
        if not message.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Nedostatočné oprávnenia",
                description="Len administrátori môžu reštartovať KNX's Bot!",
                color=0xff0000
            )
            embed.add_field(name="🔐 Požadované oprávnenie", value="Administrator", inline=True)
            await message.channel.send(embed=embed)
            return

        embed = discord.Embed(
            title="🔄 KNX's Bot sa reštartuje!",
            description=f"Bot sa vypne a znovu spustí...\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            color=0xffa500
        )
        await message.channel.send(embed=embed)

        print(f"🔄 Reštart iniciovaný používateľom {message.author}")
        await poslat_offline_spravu()
        await client.close()
        sys.exit(2)

@client.event
async def on_voice_state_update(member, before, after):
    await yt_music.handle_voice_state_update(member, before, after)

print("\nSpúštam KNX's Bot...")

try:
    client.run(os.getenv('DISCORD_TOKEN'))
except KeyboardInterrupt:
    print("\nKNX's Bot bol manuálne vypnutý.")
    sys.exit(2)
except Exception as e:
    print(f"Chyba pri spúšťaní KNX's Bot: {e}")
    sys.exit(2)
finally:
    print("KNX's Bot ukončený.")