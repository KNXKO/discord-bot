import discord
import asyncio

async def handle_clean_command(message, aktualizuj_statistiky):
    aktualizuj_statistiky("clean")
    mention = message.author.mention

    # Kontrola oprávnení
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