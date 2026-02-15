import discord
from discord.ext import commands
from datetime import datetime

WELCOME_CHANNEL_ID = 1471979239367774248
RULES_CHANNEL_ID = 1266609104005103617
ABOUTME_CHANNEL_ID = 1266609208518774794
ROLE_ID = 1472417667670347817

BANNER_URL = "https://cdn.discordapp.com/attachments/1471998786006941828/1472416704725520537/360_F_691208506_9rYrPJctzmGP3C2sVQtM3iq1oXd9Vp2x.jpg?ex=69927e6a&is=69912cea&hm=fbd5961759eb7ea3088691880fd4f6ef396ac6e77c2739d5b6876abf228266c5&"


class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ==========================================================
    # MEMBER JOIN
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        guild = member.guild

        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
        rules_channel = guild.get_channel(RULES_CHANNEL_ID)
        aboutme_channel = guild.get_channel(ABOUTME_CHANNEL_ID)

        role = guild.get_role(ROLE_ID)

        # ======================================================
        # ROLE ADD
        # ======================================================

        if role:

            try:
                await member.add_roles(
                    role,
                    reason="AutoRole Welcome System"
                )
            except Exception as e:
                print(f"Role error: {e}")

        # ======================================================
        # EMBED
        # ======================================================

        embed = discord.Embed(

            description=(

                f"## Welcome {member.mention} ♡\n\n"

                f"you made it to our lovely community\n"
                f"before you float around the server,\n"
                f"take a sec to read the rules\n\n"

                f"❀ **verify yourself** ❀\n"
                f"head to {rules_channel.mention}\n"
                f"so you can unlock the whole server\n\n"

                f"❀ **introduce yourself** ❀\n"
                f"visit {aboutme_channel.mention}\n"
                f"and tell us more about you!\n\n"

                f"❀ **after you finished everything** ❀\n"
                f"grab snacks, get comfy and enjoy the vibes ♡"

            ),

            color=discord.Color.from_rgb(180, 140, 255),
            timestamp=datetime.utcnow()

        )

        # Banner
        embed.set_image(
            url=BANNER_URL
        )

        # Profilbild + Username
        embed.set_author(
            name=f"{member.name}",
            icon_url=member.display_avatar.url
        )

        # Thumbnail
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        # Footer
        embed.set_footer(
            text=f"{guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )

        # Send

        if welcome_channel:

            await welcome_channel.send(
                content=f"{member.mention}",
                embed=embed
            )


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):
    await bot.add_cog(Welcome(bot))

