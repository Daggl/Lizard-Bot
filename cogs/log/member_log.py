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

        import sqlite3
        import os

        os.makedirs("data/logs", exist_ok=True)

        conn = sqlite3.connect("data/logs/logs.db")

        c = conn.cursor()

        table = FILE.split("/")[-1].replace(".json", "")

        # Tabelle erstellen falls nicht existiert
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """)

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
