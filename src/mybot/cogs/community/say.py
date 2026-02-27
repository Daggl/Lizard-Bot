import discord
from discord import app_commands
from discord.ext import commands


class Say(commands.Cog):
    """
    Say Command Cog

    Functions:
    - Sends an embed message
    - Optional image
    - Admins only
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description="Say command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, *, text: str):
        try:
            if getattr(ctx, "message", None) is not None:
                await ctx.message.delete()
        except Exception:
            pass

        if "|" in text:
            text, image_url = text.split("|", 1)
            text = text.strip()
            image_url = image_url.strip()
        else:
            image_url = None

        embed = discord.Embed(
            description=text, color=discord.Color.from_rgb(140, 110, 255)
        )

        if image_url:
            embed.set_image(url=image_url)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Say(bot))
