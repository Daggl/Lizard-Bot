import discord
import os

from discord.ext import commands
from datetime import datetime

from mybot.utils.config import load_cog_config

_CFG = load_cog_config("log_server")

CHANNEL_ID = _CFG.get("CHANNEL_ID", 1472016463207464981)
FILE = _CFG.get("FILE", "data/logs/server_logs.json")


class ServerLog(commands.Cog):

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

        # Centralized log saving
        db.save_log("server", data)

    # ==========================================================
    # SEND
    # ==========================================================

    async def send(self, guild, embed):

        channel = guild.get_channel(CHANNEL_ID)

        if channel:

            await channel.send(embed=embed)

    # ==========================================================
    # CHANNEL CREATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):

        embed = discord.Embed(
            title="📁 Channel created",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📁 Channel",
            value=channel.mention
        )

        await self.send(channel.guild, embed)
        self.save({
            "type": "channel_create",
            "channel": channel.id,
            "channel_name": channel.name,
            "guild": channel.guild.id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # ==========================================================
    # CHANNEL DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        embed = discord.Embed(
            title="🗑 Channel deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📁 Name",
            value=channel.name
        )

        await self.send(channel.guild, embed)
        self.save({
            "type": "channel_delete",
            "channel": channel.id,
            "channel_name": channel.name,
            "guild": channel.guild.id,
            "timestamp": datetime.utcnow().isoformat()
        })


async def setup(bot):
    await bot.add_cog(ServerLog(bot))

    # ==========================================================
    # ROLE CREATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):

        embed = discord.Embed(
            title="🛡 Role created",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🛡 Role",
            value=role.mention
        )
