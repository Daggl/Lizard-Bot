from discord.ext import commands
import discord
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io

from cogs.leveling.levels import xp_for_level

CARD_WIDTH = 1000
CARD_HEIGHT = 300

BAR_WIDTH = 600
BAR_HEIGHT = 25

AVATAR_SIZE = 180

FONT_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_REGULAR = "assets/fonts/Poppins-Regular.ttf"


class Rank(commands.Cog):
    """Rank card and admin XP commands."""

    def __init__(self, bot):
        self.bot = bot

    # ======================================================
    # USER COMMAND
    # ======================================================

    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):
        """User rank card."""

        member = member or ctx.author

        file = await self.generate_rankcard(member)

        await ctx.send(file=file)

    # ======================================================
    # ADMIN COMMAND - rankuser
    # ======================================================

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def rankuser(self, ctx, member: discord.Member):
        """Admin rank card command."""

        file = await self.generate_rankcard(member)

        await ctx.send(file=file)

    # ======================================================
    # GENERATE CARD
    # ======================================================

    async def generate_rankcard(self, member):

        user = self.bot.db.get_user(member.id)

        level = user["level"]
        xp = user["xp"]
        needed = xp_for_level(level)

        progress = xp / needed if needed > 0 else 0

        messages = user["messages"]
        voice_minutes = user["voice_time"] // 60
        achievements = len(user["achievements"])

        card = Image.open(
            "assets/rankcard.png"
        ).convert("RGB")

        card = card.resize(
            (CARD_WIDTH, CARD_HEIGHT)
        )


        draw = ImageDraw.Draw(card)

        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

        avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE))

        mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)

        mask_draw = ImageDraw.Draw(mask)

        mask_draw.ellipse(
            (0, 0, AVATAR_SIZE, AVATAR_SIZE),
            fill=255
        )

        avatar.putalpha(mask)

        card.paste(avatar, (50, 60), avatar)

        font_big = ImageFont.truetype(FONT_BOLD, 60)
        font_medium = ImageFont.truetype(FONT_BOLD, 40)
        font_small = ImageFont.truetype(FONT_REGULAR, 22)

        draw.text(
            (260, 50),
            member.name,
            font=font_big,
            fill=(255, 255, 255)
        )

        draw.text(
            (260, 120),
            f"Level {level}",
            font=font_medium,
            fill=(200, 200, 200)
        )

        draw.text(
            (710, 140),
            f"{xp} / {needed} XP",
            font=font_small,
            fill=(200, 200, 200)
        )

        bar_x = 260
        bar_y = 180

        draw.rectangle(
            (
                bar_x,
                bar_y,
                bar_x + BAR_WIDTH,
                bar_y + BAR_HEIGHT
            ),
            fill=(50, 50, 50)
        )

        draw.rectangle(
            (
                bar_x,
                bar_y,
                bar_x + int(BAR_WIDTH * progress),
                bar_y + BAR_HEIGHT
            ),
            fill=(140, 110, 255)
        )

        draw.text(
            (260, 220),
            f"Messages: {messages}",
            font=font_small,
            fill=(180, 180, 180)
        )

        draw.text(
            (450, 220),
            f"Voice: {voice_minutes} min",
            font=font_small,
            fill=(180, 180, 180)
        )

        draw.text(
            (650, 220),
            f"Achievements: {achievements}",
            font=font_small,
            fill=(180, 180, 180)
        )

        buffer = io.BytesIO()

        card.save(buffer, "PNG")

        buffer.seek(0)

        return discord.File(
            buffer,
            filename="rank.png"
        )

    # ======================================================
    # ADMIN COMMANDS
    # ======================================================

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addxp(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        """Add XP using level system."""

        levels = self.bot.get_cog("Levels")

        await levels.add_xp(member, amount)

        achievements = self.bot.get_cog("Achievements")

        if achievements:
            await achievements.check_achievements(member)

        await ctx.send(
            f"✅ {amount} XP zu {member.mention} hinzugefügt"
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removexp(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):

        user = self.bot.db.get_user(member.id)

        user["xp"] = max(
            0,
            user["xp"] - amount
        )

        self.bot.db.save()

        await ctx.send(
            f"🗑 {amount} XP entfernt"
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset(
        self,
        ctx,
        member: discord.Member
    ):

        user = self.bot.db.get_user(member.id)

        user["xp"] = 0
        user["level"] = 1
        user["messages"] = 0
        user["voice_time"] = 0
        user["achievements"] = []

        self.bot.db.save()

        await ctx.send(
            "♻ User wurde zurückgesetzt"
        )


async def setup(bot):

    await bot.add_cog(
        Rank(bot)
    )
