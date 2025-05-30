import random
import discord
import os
import sys
import signal
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Import hudobného modulu
import yt_music

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Dirgovej citáty
dirgova = [
    "odkiaľ to beriete keďže toto z vašej hlavy nie je",
    "Matúš poprosím k tabuli",
    "toto by aj moja 11-ročná dcéra vedela",
    "celý tento cirkus preskočíme",
    "povedzte áno a môžeme ísť ďalej",
    "no kto vám to vypočítal? priznajte sa",
    "Kristínka dnes nemá svoj deň",
    "ešte máte nejaké otázky? nie",
    "tento príklad to je piata ľudová"
]

# Odpovede magickej gule
magicka_gula = ["Áno", "Nie", "Neviem", "Možno", "Určite áno", "Určite nie", "Mám piči", "Spýtaj sa neskôr"]

# Štatistiky bota
bot_stats = {
    "prikazy_pouzite": 0,
    "spusteny": datetime.now(),
    "najcastejsi_prikaz": {},
    "pocet_hier": 0,
    "ulozenych_hlasiek": 0,
    "prehranych_pesniciek": 0
}

def uloz_hlasku(autor, text, cas):
    hlaska = {
        "autor": autor,
        "text": text,
        "cas": cas.strftime("%d.%m.%Y %H:%M:%S"),
        "timestamp": cas
    }
    bot_stats["ulozenych_hlasiek"] += 1

    try:
        with open("hlasky.txt", "a", encoding="utf-8") as f:
            f.write(f"[{hlaska['cas']}] {hlaska['autor']}: {hlaska['text']}\n")
    except Exception as e:
        print(f"Chyba pri ukladaní do súboru: {e}")

def nacitaj_hlasky():
    try:
        if os.path.exists("hlasky.txt"):
            with open("hlasky.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                bot_stats["ulozenych_hlasiek"] = len(lines)
        else:
            print("Vytvorím nový súbor pre hlášky")
    except Exception as e:
        print(f"Chyba pri načítaní hlášok: {e}")

def najdi_hlasky(hladane_slovo, limit=5):
    vysledky = []
    try:
        if os.path.exists("hlasky.txt"):
            with open("hlasky.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if hladane_slovo.lower() in line.lower():
                        vysledky.append(line.strip())
                        if len(vysledky) >= limit:
                            break
    except Exception as e:
        print(f"Chyba pri hľadaní: {e}")
    return vysledky

def get_posledne_hlasky(pocet=5):
    vysledky = []
    try:
        if os.path.exists("hlasky.txt"):
            with open("hlasky.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                vysledky = [line.strip() for line in lines[-pocet:]]
                vysledky.reverse()
    except Exception as e:
        print(f"Chyba pri načítaní posledných hlášok: {e}")
    return vysledky

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
            title="🔴 KNX's Bot je OFFLINE!",
            description=f"KNX Discord Bot sa odpojil.\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            color=0xff0000
        )
        await kanal.send(embed=embed)
        print("Offline správa odoslaná")
    except Exception as e:
        print(f"Chyba: {e}")

@client.event
async def on_disconnect():
    print("Bot sa odpojil od Discordu!")
    await poslat_offline_spravu()

def signal_handler(sig, frame):
    print('\nBot sa vypína...')
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
    """Event keď sa bot úspešne pripojí"""
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="KNX's commands | !help 🥶"
        )
    )
    nacitaj_hlasky()
    print(f"🥶 KNX's Bot je online ako {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = message.content.lower().strip()
    mention = message.author.mention

    if msg.startswith("!help"):
        aktualizuj_statistiky("help")
        embed = discord.Embed(
            title="🥶 KNX's Bot - Príkazy",
            description="Tu sú všetky dostupné príkazy pre KNX Discord Bot:",
            color=0x9932cc
        )
        embed.add_field(name="🎮 Zábava", value="`!cicina`, `!dirgova`, `!magicka gula`, `!kocky`", inline=False)
        embed.add_field(name="🎵 Hudba", value=yt_music.get_music_help_text(), inline=False)
        embed.add_field(name="💾 Pamäť", value="`!uloz [text]`, `!hlasky`, `!najdi [slovo]`, `!posledne [počet]`", inline=False)
        embed.add_field(name="🛠️ Moderácia", value="`!clean [počet]`", inline=False)
        embed.add_field(name="📊 Ostatné", value="`!stats`, `!restart`", inline=False)
        embed.set_footer(text="Vytvoril: KNX 🥶")
        await message.channel.send(embed=embed)

    # HUDOBNÉ PRÍKAZY - delegované do music modulu
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

    # ZÁBAVNÉ PRÍKAZY
    elif msg.startswith("!cicina"):
        aktualizuj_statistiky("cicina")
        velkost = random.randint(0, 30)
        emoji = "🍆" if velkost > 20 else "🥒" if velkost > 10 else "🌶️"
        await message.channel.send(f"{mention} tvoja cicina má dĺžku {velkost} cm {emoji} <:resttr:914796576420020244>")

    elif msg.startswith("!dirgova"):
        aktualizuj_statistiky("dirgova")
        citata = random.choice(dirgova)
        await message.channel.send(f"{mention} \"{citata}\" 👩‍🏫 <:dirgova:920391929764675664>")

    elif msg.startswith("!magicka gula"):
        aktualizuj_statistiky("magicka_gula")
        odpoved = random.choice(magicka_gula)
        await message.channel.send(f"{mention} 🔮 Magická guľa hovorí: **{odpoved}**")

    elif msg.startswith("!kocky"):
        aktualizuj_statistiky("kocky")
        bot_stats["pocet_hier"] += 1

        kocka1 = random.randint(1, 6)
        kocka2 = random.randint(1, 6)
        sumkociek = kocka1 + kocka2

        botkocka1 = random.randint(1, 6)
        botkocka2 = random.randint(1, 6)
        botsumkociek = botkocka1 + botkocka2

        embed = discord.Embed(title="🎲 Hra s kockami", color=0xff6b6b)
        embed.add_field(name=f"🎯 {message.author.display_name}", value=f"🎲 {kocka1} + {kocka2} = **{sumkociek}**", inline=True)
        embed.add_field(name="🥶 KNX's Bot", value=f"🎲 {botkocka1} + {botkocka2} = **{botsumkociek}**", inline=True)

        if sumkociek > botsumkociek:
            embed.add_field(name="🏆 Výsledok", value=f"{mention} **VYHRAL SI!** 🎉", inline=False)
            embed.color = 0x9932cc
        elif sumkociek < botsumkociek:
            embed.add_field(name="💀 Výsledok", value=f"{mention} **PREHRAL SI!** 😢", inline=False)
            embed.color = 0xff0000
        else:
            embed.add_field(name="🤝 Výsledok", value=f"{mention} **REMÍZA!** Čo ti jebe 😂", inline=False)
            embed.color = 0xffff00

        await message.channel.send(embed=embed)

    # SYSTÉM UKLADANIA HLÁŠOK
    elif msg.startswith("!uloz"):
        aktualizuj_statistiky("uloz")
        parts = message.content.split(" ", 1)
        if len(parts) <= 1:
            await message.channel.send(f"{mention} ❌ Použitie: `!uloz tvoja hláška tu`")
            return

        text_na_ulozenie = parts[1]
        autor = message.author.display_name
        cas = datetime.now()
        uloz_hlasku(autor, text_na_ulozenie, cas)

        embed = discord.Embed(
            title="💾 Hláška uložená!",
            description=f"**Text:** {text_na_ulozenie}\n**Autor:** {autor}\n**Čas:** {cas.strftime('%d.%m.%Y %H:%M:%S')}",
            color=0x9932cc
        )
        await message.channel.send(embed=embed)

    elif msg.startswith("!hlasky"):
        aktualizuj_statistiky("hlasky")
        posledne = get_posledne_hlasky(5)

        if not posledne:
            embed = discord.Embed(
                title="📝 Žiadne hlášky",
                description="Zatiaľ nemám uložené žiadne hlášky! Použi `!uloz [text]`",
                color=0xff6b6b
            )
        else:
            embed = discord.Embed(
                title="📝 Posledných 5 hlášok",
                color=0x9b59b6
            )
            for i, hlaska in enumerate(posledne, 1):
                embed.add_field(name=f"{i}.", value=hlaska, inline=False)

        await message.channel.send(embed=embed)

    elif msg.startswith("!najdi"):
        aktualizuj_statistiky("najdi")
        parts = message.content.split(" ", 1)
        if len(parts) <= 1:
            await message.channel.send(f"{mention} ❌ Použitie: `!najdi hľadané_slovo`")
            return

        hladane_slovo = parts[1]
        vysledky = najdi_hlasky(hladane_slovo, 5)

        if not vysledky:
            embed = discord.Embed(
                title=f"🔍 Nič sa nenašlo",
                description=f"Žiadne hlášky neobsahujú slovo '{hladane_slovo}'",
                color=0xff6b6b
            )
        else:
            embed = discord.Embed(
                title=f"🔍 Hlášky obsahujúce '{hladane_slovo}'",
                color=0x9b59b6
            )
            for i, hlaska in enumerate(vysledky, 1):
                # Zvýrazní hľadané slovo
                zvyraznena = hlaska.replace(hladane_slovo.lower(), f"**{hladane_slovo.lower()}**")
                zvyraznena = zvyraznena.replace(hladane_slovo.upper(), f"**{hladane_slovo.upper()}**")
                zvyraznena = zvyraznena.replace(hladane_slovo.capitalize(), f"**{hladane_slovo.capitalize()}**")
                embed.add_field(name=f"{i}.", value=zvyraznena, inline=False)

        await message.channel.send(embed=embed)

    elif msg.startswith("!posledne"):
        aktualizuj_statistiky("posledne")
        parts = message.content.split(" ", 1)
        pocet = 5

        if len(parts) > 1:
            try:
                pocet = int(parts[1])
                pocet = min(max(pocet, 1), 20)  # Obmedzenie 1-20
            except ValueError:
                pocet = 5

        posledne = get_posledne_hlasky(pocet)

        if not posledne:
            embed = discord.Embed(
                title="📝 Žiadne hlášky",
                description="Zatiaľ nemám uložené žiadne hlášky!",
                color=0xff6b6b
            )
        else:
            embed = discord.Embed(
                title=f"📝 Posledných {len(posledne)} hlášok",
                color=0x9b59b6
            )
            for i, hlaska in enumerate(posledne, 1):
                embed.add_field(name=f"{i}.", value=hlaska, inline=False)

        await message.channel.send(embed=embed)

    # MODERÁTORSKÉ PRÍKAZY
    elif msg.startswith("!clean"):
        aktualizuj_statistiky("clean")

        if not (message.author.guild_permissions.administrator or
                message.author.guild_permissions.manage_messages):
            embed = discord.Embed(
                title="❌ Nedostatočné oprávnenia",
                description="Len administrátori alebo moderátori môžu čistiť správy!",
                color=0xff0000
            )
            await message.channel.send(embed=embed)
            return

        parts = message.content.split(" ", 1)
        if len(parts) < 2:
            embed = discord.Embed(
                title="❌ Nesprávne použitie",
                description="Musíš zadať počet správ na vyčistenie!",
                color=0xff0000
            )
            embed.add_field(name="💡 Použitie", value="`!clean 10` - vyčistí 10 správ", inline=False)
            embed.add_field(name="⚠️ Limit", value="Maximum 100 správ naraz", inline=False)
            await message.channel.send(embed=embed)
            return

        try:
            pocet = int(parts[1])
            pocet = min(max(pocet, 1), 100)  # Obmedzenie od 1 do 100
            await message.channel.purge(limit=pocet + 1)  # +1 pre príkaz samotný

            potvrdenie = await message.channel.send(f"✅ Vyčistených **{pocet}** správ!")
            await asyncio.sleep(3)
            await potvrdenie.delete()
        except ValueError:
            await message.channel.send(f"{mention} ❌ Neplatné číslo! Zadaj celé číslo.")
        except discord.Forbidden:
            await message.channel.send(f"{mention} ❌ Nemám oprávnenie mazať správy!")
        except Exception as e:
            await message.channel.send(f"{mention} ❌ Chyba: {str(e)}")

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
    elif msg.startswith("!restart"):
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
    print("\nKNX's Bot bol vypnutý používateľom!")
    sys.exit(2)
except Exception as e:
    print(f"Chyba pri spúšťaní KNX's Bot: {e}")
    sys.exit(2)
finally:
    print("KNX's Bot ukončený")