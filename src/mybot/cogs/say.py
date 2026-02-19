import discord
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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, *, text: str):
        await ctx.message.delete()

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

        if image_url:
            embed.set_image(url=image_url)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Say(bot))
