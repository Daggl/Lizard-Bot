import discord
import os

from discord.ext import commands
from datetime import datetime

CHANNEL_ID = 1472016463207464981
FILE = "data/logs/server_logs.json"


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

        await self.send(role.guild, embed)
        self.save({
            "type": "role_create",
            "role": role.id,
            "role_name": role.name,
            "guild": role.guild.id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # ==========================================================
    # ROLE DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):

        embed = discord.Embed(
            title="🗑 Role deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🛡 Role",
            value=role.name
        )

        await self.send(role.guild, embed)
        self.save({
            "type": "role_delete",
            "role": role.id,
            "role_name": role.name,
            "guild": role.guild.id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # ==========================================================
    # MEMBER UPDATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if before.nick != after.nick:

            embed = discord.Embed(
                title="✏ Nickname changed",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="👤 User",
                value=after.mention
            )

            embed.add_field(
                name="Before",
                value=before.nick or before.name
            )

            embed.add_field(
                name="After",
                value=after.nick or after.name
            )

            await self.send(after.guild, embed)
            self.save({
                "type": "nickname_change",
                "user": after.id,
                "user_name": str(after),
                "before": before.nick or before.name,
                "after": after.nick or after.name,
                "guild": after.guild.id,
                "timestamp": datetime.utcnow().isoformat()
            })

        added_roles = [
            r for r in after.roles if r not in before.roles
        ]

        for role in added_roles:

            embed = discord.Embed(
                title="✅ Role added",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="User",
                value=after.mention
            )

            embed.add_field(
                name="Role",
                value=role.mention
            )

            await self.send(after.guild, embed)
            self.save({
                "type": "role_add",
                "user": after.id,
                "user_name": str(after),
                "role": role.id,
                "role_name": role.name,
                "guild": after.guild.id,
                "timestamp": datetime.utcnow().isoformat()
            })

        removed_roles = [
            r for r in before.roles if r not in after.roles
        ]

        for role in removed_roles:

            embed = discord.Embed(
                title="❌ Role removed",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="User",
                value=after.mention
            )

            embed.add_field(
                name="Role",
                value=role.name
            )

            await self.send(after.guild, embed)
            self.save({
                "type": "role_remove",
                "user": after.id,
                "user_name": str(after),
                "role": role.id,
                "role_name": role.name,
                "guild": after.guild.id,
                "timestamp": datetime.utcnow().isoformat()
            })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(ServerLog(bot))
