import os
from datetime import datetime

import discord
from discord.ext import commands

from mybot.utils.config import load_cog_config


def _cfg() -> dict:
    try:
        return load_cog_config("log_voice") or {}
    except Exception:
        return {}


class VoiceLog(commands.Cog):

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

        # Persist voice logs centrally
        db.save_log("voice", data)

    # ==========================================================
    # SEND
    # ==========================================================

    async def send(self, guild, embed):

        channel_id = int(_cfg().get("CHANNEL_ID", 0) or 0)
        channel = guild.get_channel(channel_id)

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
                title="🔊 Voice Channel joined",
                color=discord.Color.green(),
                timestamp=timestamp,
            )

            embed.add_field(
                name="👤 User", value=f"{member.mention} (`{member.id}`)", inline=False
            )

            embed.add_field(
                name="🎧 Channel", value=after.channel.mention, inline=False
            )

            embed.add_field(
                name="🕒 Time",
                value=f"<t:{int(timestamp.timestamp())}:F>",
                inline=False,
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            embed.set_footer(text=f"Server: {member.guild.name}")

            await self.send(member.guild, embed)

            self.save(
                {
                    "type": "join",
                    "user": member.id,
                    "user_name": str(member),
                    "channel": after.channel.id,
                    "channel_name": after.channel.name,
                    "guild": member.guild.id,
                    "timestamp": timestamp.isoformat(),
                }
            )

        # ======================================================
        # LEAVE
        # ======================================================

        elif before.channel and after.channel is None:

            embed = discord.Embed(
                title="🔇 Voice Channel left",
                color=discord.Color.red(),
                timestamp=timestamp,
            )

            embed.add_field(
                name="👤 User", value=f"{member} (`{member.id}`)", inline=False
            )

            embed.add_field(name="🎧 Channel", value=before.channel.name, inline=False)

            embed.add_field(
                name="🕒 Time",
                value=f"<t:{int(timestamp.timestamp())}:F>",
                inline=False,
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            embed.set_footer(text=f"Server: {member.guild.name}")

            await self.send(member.guild, embed)

            self.save(
                {
                    "type": "leave",
                    "user": member.id,
                    "user_name": str(member),
                    "channel": before.channel.id,
                    "channel_name": before.channel.name,
                    "guild": member.guild.id,
                    "timestamp": timestamp.isoformat(),
                }
            )

        # ======================================================
        # SWITCH
        # ======================================================

        elif before.channel != after.channel:

            embed = discord.Embed(
                title="🔄 Voice Channel switched",
                color=discord.Color.orange(),
                timestamp=timestamp,
            )

            embed.add_field(
                name="👤 User", value=f"{member.mention} (`{member.id}`)", inline=False
            )

            embed.add_field(name="📤 Von", value=before.channel.mention, inline=True)

            embed.add_field(name="📥 To", value=after.channel.mention, inline=True)

            embed.add_field(
                name="🕒 Time",
                value=f"<t:{int(timestamp.timestamp())}:F>",
                inline=False,
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            embed.set_footer(text=f"Server: {member.guild.name}")

            await self.send(member.guild, embed)

            self.save(
                {
                    "type": "switch",
                    "user": member.id,
                    "user_name": str(member),
                    "from": before.channel.id,
                    "from_name": before.channel.name,
                    "to": after.channel.id,
                    "to_name": after.channel.name,
                    "guild": member.guild.id,
                    "timestamp": timestamp.isoformat(),
                }
            )


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):

    await bot.add_cog(VoiceLog(bot))
