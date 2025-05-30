import os
import discord
from datetime import datetime

def uloz_hlasku(autor, text, cas, bot_stats):
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

def nacitaj_hlasky(bot_stats):
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
    """Vráti posledné hlášky z súboru"""
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

async def handle_uloz_command(message, aktualizuj_statistiky, bot_stats):
    aktualizuj_statistiky("uloz")
    mention = message.author.mention
    parts = message.content.split(" ", 1)

    if len(parts) <= 1:
        await message.channel.send(f"{mention} ❌ Použitie: `!uloz tvoja hláška tu`")
        return

    text_na_ulozenie = parts[1]
    autor = message.author.display_name
    cas = datetime.now()
    uloz_hlasku(autor, text_na_ulozenie, cas, bot_stats)

    embed = discord.Embed(
        title="💾 Hláška uložená!",
        description=f"**Text:** {text_na_ulozenie}\n**Autor:** {autor}\n**Čas:** {cas.strftime('%d.%m.%Y %H:%M:%S')}",
        color=0x9932cc
    )
    await message.channel.send(embed=embed)

async def handle_hlasky_command(message, aktualizuj_statistiky):
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

async def handle_najdi_command(message, aktualizuj_statistiky):
    aktualizuj_statistiky("najdi")
    mention = message.author.mention
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

async def handle_posledne_command(message, aktualizuj_statistiky):
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