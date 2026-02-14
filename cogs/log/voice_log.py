import discord
import json
import os

from discord.ext import commands
from datetime import datetime


CHANNEL_ID = 1472016385725956108
FILE = "data/logs/voice_logs.json"


class VoiceLog(commands.Cog):

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
    # VOICE UPDATE
    # ==========================================================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        timestamp = datetime.utcnow()

        # ======================================================
        # JOIN
        # ======================================================

        if before.channel is None and after.channel:

            embed = discord.Embed(

                title="🔊 Voice Channel beigetreten",
                color=discord.Color.green(),
                timestamp=timestamp

            )

            embed.add_field(
                name="👤 User",
                value=f"{member.mention} (`{member.id}`)",
                inline=False
            )

            embed.add_field(
                name="🎧 Channel",
                value=after.channel.mention,
                inline=False
            )

            embed.add_field(
                name="🕒 Zeitpunkt",
                value=f"<t:{int(timestamp.timestamp())}:F>",
                inline=False
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            embed.set_footer(
                text=f"Server: {member.guild.name}"
            )

            await self.send(member.guild, embed)

            self.save({

                "type": "join",
                "user": member.id,
                "channel": after.channel.id,
                "time": str(timestamp)

            })

        # ======================================================
        # LEAVE
        # ======================================================

        elif before.channel and after.channel is None:

            embed = discord.Embed(

                title="🔇 Voice Channel verlassen",
                color=discord.Color.red(),
                timestamp=timestamp

            )

            embed.add_field(
                name="👤 User",
                value=f"{member} (`{member.id}`)",
                inline=False
            )

            embed.add_field(
                name="🎧 Channel",
                value=before.channel.name,
                inline=False
            )

            embed.add_field(
                name="🕒 Zeitpunkt",
                value=f"<t:{int(timestamp.timestamp())}:F>",
                inline=False
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            embed.set_footer(
                text=f"Server: {member.guild.name}"
            )

            await self.send(member.guild, embed)

            self.save({

                "type": "leave",
                "user": member.id,
                "channel": before.channel.id,
                "time": str(timestamp)

            })

        # ======================================================
        # SWITCH
        # ======================================================

        elif before.channel != after.channel:

            embed = discord.Embed(

                title="🔄 Voice Channel gewechselt",
                color=discord.Color.orange(),
                timestamp=timestamp

            )

            embed.add_field(
                name="👤 User",
                value=f"{member.mention} (`{member.id}`)",
                inline=False
            )

            embed.add_field(
                name="📤 Von",
                value=before.channel.mention,
                inline=True
            )

            embed.add_field(
                name="📥 Zu",
                value=after.channel.mention,
                inline=True
            )

            embed.add_field(
                name="🕒 Zeitpunkt",
                value=f"<t:{int(timestamp.timestamp())}:F>",
                inline=False
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            embed.set_footer(
                text=f"Server: {member.guild.name}"
            )

            await self.send(member.guild, embed)

            self.save({

                "type": "switch",
                "user": member.id,
                "from": before.channel.id,
                "to": after.channel.id,
                "time": str(timestamp)

            })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(VoiceLog(bot))
