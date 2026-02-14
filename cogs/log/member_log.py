import discord
import json
import os

from discord.ext import commands
from datetime import datetime

CHANNEL_ID = 1472016429032275968
FILE = "data/logs/member_logs.json"


class MemberLog(commands.Cog):

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self, bot):

        self.bot = bot

        os.makedirs("data/logs", exist_ok=True)

        if not os.path.exists(FILE):
            json.dump([], open(FILE, "w"))

    # ==========================================================
    # SAVE
    # ==========================================================

    def save(self, data):

        try:

            logs = json.load(open(FILE))

            logs.append(data)

            json.dump(logs, open(FILE, "w"), indent=4)

        except:

            json.dump([], open(FILE, "w"))

    # ==========================================================
    # SEND
    # ==========================================================

    async def send(self, guild, embed):

        channel = guild.get_channel(CHANNEL_ID)

        if channel:
            await channel.send(embed=embed)

    # ==========================================================
    # MEMBER JOIN
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        embed = discord.Embed(
            title="🟢 Member beigetreten",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 User",
            value=f"{member.mention} (`{member.id}`)",
            inline=False
        )

        embed.add_field(
            name="📅 Account erstellt",
            value=f"<t:{int(member.created_at.timestamp())}:F>",
            inline=False
        )

        embed.add_field(
            name="🕒 Zeitpunkt",
            value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
            inline=False
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(text=f"Server: {member.guild.name}")

        await self.send(member.guild, embed)

        self.save({
            "type": "join",
            "user": member.id,
            "time": str(datetime.utcnow())
        })

    # ==========================================================
    # MEMBER LEAVE (FIXED)
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        embed = discord.Embed(
            title="📤 Member verlassen",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 User",
            value=f"{member} (`{member.id}`)",
            inline=False
        )

        embed.add_field(
            name="🕒 Zeitpunkt",
            value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
            inline=False
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(text=f"Server: {member.guild.name}")

        await self.send(member.guild, embed)

        self.save({
            "type": "leave",
            "user": member.id,
            "time": str(datetime.utcnow())
        })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(MemberLog(bot))
