import random
import discord

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

async def handle_cicina_command(message, aktualizuj_statistiky):
    aktualizuj_statistiky("cicina")
    mention = message.author.mention
    velkost = random.randint(0, 30)
    emoji = "🍆" if velkost > 20 else "🥒" if velkost > 10 else "🌶️"
    await message.channel.send(f"{mention} tvoja cicina má dĺžku {velkost} cm {emoji} <:resttr:914796576420020244>")

async def handle_dirgova_command(message, aktualizuj_statistiky):
    aktualizuj_statistiky("dirgova")
    mention = message.author.mention
    citata = random.choice(dirgova)
    await message.channel.send(f"{mention} \"{citata}\" 👩‍🏫 <:dirgova:920391929764675664>")

async def handle_magicka_gula_command(message, aktualizuj_statistiky):
    aktualizuj_statistiky("magicka_gula")
    mention = message.author.mention
    odpoved = random.choice(magicka_gula)
    await message.channel.send(f"{mention} 🔮 Magická guľa hovorí: **{odpoved}**")

async def handle_kocky_command(message, aktualizuj_statistiky, bot_stats):
    aktualizuj_statistiky("kocky")
    mention = message.author.mention
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