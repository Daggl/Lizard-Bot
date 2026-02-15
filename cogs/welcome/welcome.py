import discord
import aiohttp
import io

from discord.ext import commands
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


# ==========================================================
# CONFIG
# ==========================================================

WELCOME_CHANNEL_ID = 1471979239367774248
RULES_CHANNEL_ID = 1266609104005103617
ABOUTME_CHANNEL_ID = 1266609208518774794
ROLE_ID = 1472417667670347817

BANNER_PATH = "assets/welcome.png"
FONT_PATH = "assets/fonts/aubrey.ttf"


# ==========================================================
# COG
# ==========================================================

class Welcome(commands.Cog):
    """Professional Welcome Banner System"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ======================================================
    # Banner Generator
    # ======================================================

    async def create_banner(self, member: discord.Member) -> discord.File:

        # Avatar herunterladen
        async with aiohttp.ClientSession() as session:
            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

        # Banner laden
        banner = Image.open(BANNER_PATH).convert("RGBA")

        # Avatar laden
        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")

        # Resize
        banner = banner.resize((1000, 350))
        avatar = avatar.resize((180, 180))

        # Kreis Maske
        mask = Image.new("L", avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 180, 180), fill=255)

        avatar.putalpha(mask)

        # Avatar einfügen
        banner.paste(avatar, (60, 85), avatar)

        # Text
        draw = ImageDraw.Draw(banner)

        try:
            font = ImageFont.truetype(FONT_PATH, 60)
        except Exception:
            font = ImageFont.load_default()

        draw.text(
            (260, 140),
            member.name,
            font=font,
            fill=(255, 255, 255)
        )

        # In Memory speichern
        buffer = io.BytesIO()
        banner.save(buffer, "PNG")
        buffer.seek(0)

        return discord.File(buffer, filename="welcome.png")

    # ======================================================
    # MEMBER JOIN EVENT
    # ======================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        print(f"[WELCOME] {member} joined")

        guild = member.guild

        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
        rules_channel = guild.get_channel(RULES_CHANNEL_ID)
        aboutme_channel = guild.get_channel(ABOUTME_CHANNEL_ID)

        role = guild.get_role(ROLE_ID)

        # ==================================================
        # ROLE
        # ==================================================

        if role:
            try:
                await member.add_roles(role)
            except Exception as error:
                print(f"Role Error: {error}")

        # ==================================================
        # Banner erstellen
        # ==================================================

        try:
            banner = await self.create_banner(member)
        except Exception as error:
            print(f"Banner Error: {error}")
            return

        # ==================================================
        # EMBED
        # ==================================================

        embed = discord.Embed(

            description=(

                f"{member.mention} just checked in!\n\n"

                f"❀ **verify yourself** ❀\n"
                f"{rules_channel.mention}\n\n"

                f"❀ **introduce yourself** ❀\n"
                f"{aboutme_channel.mention}\n\n"

                f"❀ grab snacks and enjoy the vibes ❀"

            ),

            color=discord.Color.from_rgb(180, 140, 255),
            timestamp=datetime.utcnow()

        )

        embed.set_image(
            url="attachment://welcome.png"
        )

        embed.set_footer(
            text=guild.name,
            icon_url=guild.icon.url if guild.icon else None
        )

        # ==================================================
        # SEND
        # ==================================================

        if welcome_channel:

            await welcome_channel.send(

                file=banner,
                embed=embed

            )

            print("Welcome message sent")

        else:

            print("Welcome channel not found")


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot: commands.Bot):

    await bot.add_cog(

        Welcome(bot)

    )
