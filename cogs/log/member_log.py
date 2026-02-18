import discord
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


# ==========================================================
# SAVE
# ==========================================================

    def save(self, data):
        from data.logs import database as db

        # Persist using central logs DB
        db.save_log("member", data)


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
            title="🟢 Member joined",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 User",
            value=f"{member.mention} (`{member.id}`)",
            inline=False
        )

        embed.add_field(
            name="📅 Account created",
            value=f"<t:{int(member.created_at.timestamp())}:F>",
            inline=False
        )

        embed.add_field(
            name="🕒 Time",
            value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
            inline=False
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(text=f"Server: {member.guild.name}")

        await self.send(member.guild, embed)

        self.save({
            "type": "join",
            "user": member.id,
            "user_name": str(member),
            "created_at": member.created_at.isoformat(),
            "guild": member.guild.id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # ==========================================================
    # MEMBER LEAVE (FIXED)
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        embed = discord.Embed(
            title="📤 Member left",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 User",
            value=f"{member} (`{member.id}`)",
            inline=False
        )

        embed.add_field(
            name="🕒 Time",
            value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
            inline=False
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(text=f"Server: {member.guild.name}")

        await self.send(member.guild, embed)

        self.save({
            "type": "leave",
            "user": member.id,
            "user_name": str(member),
            "guild": member.guild.id,
            "timestamp": datetime.utcnow().isoformat()
        })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(MemberLog(bot))
