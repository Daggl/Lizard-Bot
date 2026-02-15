import discord
from discord.ext import commands


class Say(commands.Cog):
    """
    Say Command Cog

    Funktionen:
    - Sendet Embed Nachricht
    - Optional mit Bild
    - Nur für Admins
    """

    def __init__(self, bot):
        self.bot = bot

    # ======================================================
    # SAY COMMAND
    # ======================================================

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, *, text: str):
        """
        Nutzung:

        *say TEXT
        oder
        *say TEXT | BILD_URL
        """

        await ctx.message.delete()

        # Prüfen ob Bild enthalten ist
        if "|" in text:
            text, image_url = text.split("|", 1)
            text = text.strip()
            image_url = image_url.strip()
        else:
            image_url = None

        embed = discord.Embed(
            description=text,
            color=discord.Color.from_rgb(140, 110, 255)
        )

        # Bild hinzufügen wenn vorhanden
        if image_url:
            embed.set_image(url=image_url)

        await ctx.send(embed=embed)


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):
    await bot.add_cog(Say(bot))
