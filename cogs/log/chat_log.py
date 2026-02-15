import discord
import os

from discord.ext import commands
from datetime import datetime


CHANNEL_ID = 1472012691911737519
FILE = "data/logs/chat_logs.json"


class ChatLog(commands.Cog):

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

        # Tabelle erstellen falls nicht existiert
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
            """
        )

        # Spalten erstellen falls nicht existieren
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

        ch = guild.get_channel(CHANNEL_ID)

        if ch:
            await ch.send(embed=embed)

    # ==========================================================
    # MESSAGE SEND
    # ==========================================================

    @commands.Cog.listener()
    async def on_message(self, msg):

        if msg.author.bot:
            return

        embed = discord.Embed(
            title="Message Sent",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="User",
            value=msg.author.mention
        )

        embed.add_field(
            name="Channel",
            value=msg.channel.mention
        )

        embed.add_field(
            name="Content",
            value=msg.content or "None"
        )

        await self.send(msg.guild, embed)

        self.save({
            "type": "send",
            "user": msg.author.id
        })

    # ==========================================================
    # MESSAGE DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_message_delete(self, msg):

        if msg.author.bot:
            return

        deleter = None

        async for entry in msg.guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.message_delete
        ):

            if entry.target.id == msg.author.id:

                deleter = entry.user
                break

        embed = discord.Embed(
            title="Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="User",
            value=msg.author.mention
        )

        if deleter:

            embed.add_field(
                name="Deleted by",
                value=deleter.mention
            )

        await self.send(msg.guild, embed)

        self.save({
            "type": "delete"
        })

    # ==========================================================
    # MESSAGE EDIT
    # ==========================================================

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):

        if before.author.bot:
            return

        if before.content == after.content:
            return

        embed = discord.Embed(
            title="Message Edited",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Before",
            value=before.content
        )

        embed.add_field(
            name="After",
            value=after.content
        )

        await self.send(before.guild, embed)

        self.save({
            "type": "edit"
        })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(ChatLog(bot))
