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

        import sqlite3
        import os

        os.makedirs("data/logs", exist_ok=True)

        conn = sqlite3.connect("data/logs/logs.db")

        c = conn.cursor()

        table = FILE.split("/")[-1].replace(".json", "")

        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """)

        for key in data.keys():

            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {key} TEXT")
            except:
                pass

        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)

        c.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(str(v) for v in data.values())
        )

        conn.commit()
        conn.close()

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
            "time": str(datetime.utcnow())
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
            "time": str(datetime.utcnow())
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
            "time": str(datetime.utcnow())
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
            "time": str(datetime.utcnow())
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
                "time": str(datetime.utcnow())
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
                "role": role.id,
                "time": str(datetime.utcnow())
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
                "role": role.id,
                "time": str(datetime.utcnow())
            })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(ServerLog(bot))
