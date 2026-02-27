import os
from datetime import datetime

import discord
from discord.ext import commands

from mybot.utils.config import load_cog_config


def _cfg() -> dict:
    try:
        return load_cog_config("log_server") or {}
    except Exception:
        return {}


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
        from data.logs.storage import database as db

        # Centralized log saving
        db.save_log("server", data)

    # ==========================================================
    # SEND
    # ==========================================================

    async def send(self, guild, embed):

        channel_id = int(_cfg().get("CHANNEL_ID", 0) or 0)
        channel = guild.get_channel(channel_id)

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
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="📁 Channel", value=channel.mention)

        await self.send(channel.guild, embed)
        self.save(
            {
                "type": "channel_create",
                "channel": channel.id,
                "channel_name": channel.name,
                "guild": channel.guild.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    # ==========================================================
    # CHANNEL DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        embed = discord.Embed(
            title="🗑 Channel deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="📁 Name", value=channel.name)

        await self.send(channel.guild, embed)
        self.save(
            {
                "type": "channel_delete",
                "channel": channel.id,
                "channel_name": channel.name,
                "guild": channel.guild.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):

        if before.name == after.name:
            return

        embed = discord.Embed(
            title="✏️ Channel updated",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="Before", value=before.name, inline=True)
        embed.add_field(name="After", value=after.name, inline=True)

        await self.send(after.guild, embed)
        self.save(
            {
                "type": "channel_update",
                "channel": after.id,
                "channel_before": before.name,
                "channel_after": after.name,
                "guild": after.guild.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):

        embed = discord.Embed(
            title="🛡 Role created",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Role", value=role.mention if hasattr(role, "mention") else role.name)

        await self.send(role.guild, embed)
        self.save(
            {
                "type": "role_create",
                "role_id": role.id,
                "role_name": role.name,
                "guild": role.guild.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):

        embed = discord.Embed(
            title="🗑 Role deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Role", value=role.name)

        await self.send(role.guild, embed)
        self.save(
            {
                "type": "role_delete",
                "role_id": role.id,
                "role_name": role.name,
                "guild": role.guild.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):

        if before.name == after.name:
            return

        embed = discord.Embed(
            title="✏️ Role updated",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Before", value=before.name, inline=True)
        embed.add_field(name="After", value=after.name, inline=True)

        await self.send(after.guild, embed)
        self.save(
            {
                "type": "role_update",
                "role_id": after.id,
                "role_before": before.name,
                "role_after": after.name,
                "guild": after.guild.id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


async def setup(bot):
    await bot.add_cog(ServerLog(bot))
