import discord

from discord.ext import commands
from datetime import datetime


CHANNEL_ID = 1472016463207464981


class ServerLog(commands.Cog):

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self, bot):

        self.bot = bot

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
            title="📁 Channel erstellt",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📁 Channel",
            value=channel.mention
        )

        await self.send(channel.guild, embed)

    # ==========================================================
    # CHANNEL DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        embed = discord.Embed(
            title="🗑 Channel gelöscht",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📁 Name",
            value=channel.name
        )

        await self.send(channel.guild, embed)

    # ==========================================================
    # ROLE CREATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):

        embed = discord.Embed(
            title="🛡 Rolle erstellt",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🛡 Rolle",
            value=role.mention
        )

        await self.send(role.guild, embed)

    # ==========================================================
    # ROLE DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):

        embed = discord.Embed(
            title="🗑 Rolle gelöscht",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="🛡 Rolle",
            value=role.name
        )

        await self.send(role.guild, embed)

    # ==========================================================
    # MEMBER UPDATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        # Nickname

        if before.nick != after.nick:

            embed = discord.Embed(
                title="✏ Nickname geändert",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="👤 User",
                value=after.mention
            )

            embed.add_field(
                name="Vorher",
                value=before.nick or before.name
            )

            embed.add_field(
                name="Nachher",
                value=after.nick or after.name
            )

            await self.send(after.guild, embed)

        # Role add

        added_roles = [
            r for r in after.roles if r not in before.roles
        ]

        for role in added_roles:

            embed = discord.Embed(
                title="✅ Rolle hinzugefügt",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="User",
                value=after.mention
            )

            embed.add_field(
                name="Rolle",
                value=role.mention
            )

            await self.send(after.guild, embed)

        # Role remove

        removed_roles = [
            r for r in before.roles if r not in after.roles
        ]

        for role in removed_roles:

            embed = discord.Embed(
                title="❌ Rolle entfernt",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="User",
                value=after.mention
            )

            embed.add_field(
                name="Rolle",
                value=role.name
            )

            await self.send(after.guild, embed)


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(ServerLog(bot))
