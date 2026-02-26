import os
from datetime import datetime

import discord
from discord.ext import commands

from mybot.utils.config import load_cog_config


def _cfg() -> dict:
    try:
        return load_cog_config("log_chat") or {}
    except Exception:
        return {}


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
        from data.logs import database as db

        # Use central logs DB; db.save_log will store the raw dict
        db.save_log("chat", data)

    # ==========================================================
    # SEND
    # ==========================================================

    async def send(self, guild, embed):

        channel_id = int(_cfg().get("CHANNEL_ID", 0) or 0)
        ch = guild.get_channel(channel_id)

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
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="User", value=msg.author.mention)

        embed.add_field(name="Channel", value=msg.channel.mention)

        embed.add_field(name="Content", value=msg.content or "None")

        await self.send(msg.guild, embed)

        self.save(
            {
                "type": "send",
                "user": msg.author.id,
                "user_name": str(msg.author),
                "channel": msg.channel.id,
                "channel_name": getattr(msg.channel, "name", None),
                "message": msg.content,
                "message_id": msg.id,
                "attachments": [a.url for a in msg.attachments],
                "guild": msg.guild.id if msg.guild else None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    # ==========================================================
    # MESSAGE DELETE
    # ==========================================================

    @commands.Cog.listener()
    async def on_message_delete(self, msg):

        if msg.author.bot:
            return

        deleter = None

        async for entry in msg.guild.audit_logs(
            limit=5, action=discord.AuditLogAction.message_delete
        ):

            if entry.target.id == msg.author.id:

                deleter = entry.user
                break

        embed = discord.Embed(
            title="Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="User", value=msg.author.mention)

        if deleter:

            embed.add_field(name="Deleted by", value=deleter.mention)

        await self.send(msg.guild, embed)

        self.save(
            {
                "type": "delete",
                "user": msg.author.id,
                "user_name": str(msg.author),
                "channel": msg.channel.id if msg.channel else None,
                "channel_name": getattr(msg.channel, "name", None),
                "message": msg.content,
                "message_id": msg.id,
                "deleted_by": deleter.id if deleter else None,
                "deleted_by_name": str(deleter) if deleter else None,
                "guild": msg.guild.id if msg.guild else None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

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
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="Before", value=before.content)

        embed.add_field(name="After", value=after.content)

        await self.send(before.guild, embed)

        self.save(
            {
                "type": "edit",
                "user": before.author.id,
                "user_name": str(before.author),
                "channel": before.channel.id,
                "channel_name": getattr(before.channel, "name", None),
                "message_id": before.id,
                "before": before.content,
                "after": after.content,
                "guild": before.guild.id if before.guild else None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


# ==========================================================
# SETUP
# ==========================================================


async def setup(bot):

    await bot.add_cog(ChatLog(bot))
