import discord
from discord.ext import commands
from datetime import datetime


WELCOME_CHANNEL_ID = 1471979239367774248
ROLE_ID = 1269213126356897885


class Welcome(commands.Cog):
    """
    Welcome System
    - Sendet Welcome Nachricht
    - Fügt AutoRole hinzu
    """

    def __init__(self, bot):
        self.bot = bot


    # ==========================================================
    # MEMBER JOIN EVENT
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        guild = member.guild

        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)

        role = guild.get_role(ROLE_ID)

        role_added = False


        # ======================================================
        # AUTO ROLE
        # ======================================================

        if role:

            try:

                await member.add_roles(
                    role,
                    reason="AutoRole System"
                )

                role_added = True

            except Exception as error:

                print(
                    f"[Welcome System] Role Error: {error}"
                )


        # ======================================================
        # WELCOME EMBED
        # ======================================================

        embed = discord.Embed(

            title="👋 Willkommen auf dem Server",

            description=(
                f"{member.mention} ist dem Server beigetreten.\n\n"
                f"**Account erstellt:** "
                f"<t:{int(member.created_at.timestamp())}:R>"
            ),

            color=discord.Color.green(),

            timestamp=datetime.utcnow()

        )


        # Thumbnail

        embed.set_thumbnail(
            url=member.display_avatar.url
        )


        # Fields

        embed.add_field(
            name="User",
            value=f"{member} (`{member.id}`)",
            inline=False
        )


        embed.add_field(
            name="AutoRole",
            value="✅ Erfolgreich" if role_added else "❌ Fehlgeschlagen",
            inline=False
        )


        # Footer

        embed.set_footer(
            text=f"{guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )


        # Send Message

        if welcome_channel:

            await welcome_channel.send(
                embed=embed
            )


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(
        Welcome(bot)
    )
