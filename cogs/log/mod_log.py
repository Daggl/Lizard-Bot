import discord
import json
import os

from discord.ext import commands
from datetime import datetime, timezone

CHANNEL_ID = 1472016339966234698
FILE = "data/logs/mod_logs.json"


class ModLog(commands.Cog):

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
    # MEMBER BAN
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):

        executor = None
        reason = "Kein Grund angegeben"

        async for entry in guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.ban
        ):

            if entry.target.id == user.id:

                executor = entry.user

                if entry.reason:
                    reason = entry.reason

                break

        embed = discord.Embed(
            title="🔨 Member gebannt",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="👤 User",
            value=f"{user} (`{user.id}`)",
            inline=False
        )

        if executor:

            embed.add_field(
                name="🛡 Moderator",
                value=executor.mention,
                inline=False
            )

        embed.add_field(
            name="📄 Grund",
            value=reason,
            inline=False
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        await self.send(guild, embed)

        self.save({
            "type": "ban",
            "user": user.id,
            "by": executor.id if executor else None,
            "reason": reason,
            "time": str(datetime.utcnow())
        })

    # ==========================================================
    # MEMBER KICK (FIXED)
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        guild = member.guild

        async for entry in guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.kick
        ):

            if entry.target.id == member.id:

                # ✅ FIX: Nur wenn Kick wirklich aktuell ist
                now = datetime.now(timezone.utc)
                diff = (now - entry.created_at).total_seconds()

                if diff > 5:
                    return

                embed = discord.Embed(
                    title="👢 Member gekickt",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )

                embed.add_field(
                    name="👤 User",
                    value=f"{member} (`{member.id}`)",
                    inline=False
                )

                embed.add_field(
                    name="🛡 Moderator",
                    value=entry.user.mention,
                    inline=False
                )

                embed.add_field(
                    name="🕒 Zeit",
                    value=f"<t:{int(now.timestamp())}:F>",
                    inline=False
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                await self.send(guild, embed)

                self.save({
                    "type": "kick",
                    "user": member.id,
                    "by": entry.user.id,
                    "time": str(datetime.utcnow())
                })

                break

    # ==========================================================
    # MEMBER TIMEOUT
    # ==========================================================

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if before.timed_out_until == after.timed_out_until:
            return

        executor = None

        async for entry in after.guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.member_update
        ):

            if entry.target.id == after.id:

                executor = entry.user
                break

        # Timeout gesetzt

        if after.timed_out_until:

            embed = discord.Embed(
                title="⏱ Member Timeout",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="👤 User",
                value=f"{after} (`{after.id}`)",
                inline=False
            )

            embed.add_field(
                name="⏰ Bis",
                value=f"<t:{int(after.timed_out_until.timestamp())}:F>",
                inline=False
            )

            log_type = "timeout"

        # Timeout entfernt

        else:

            embed = discord.Embed(
                title="✅ Timeout entfernt",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="👤 User",
                value=f"{after} (`{after.id}`)",
                inline=False
            )

            log_type = "untimeout"

        if executor:

            embed.add_field(
                name="🛡 Moderator",
                value=executor.mention,
                inline=False
            )

        embed.set_thumbnail(
            url=after.display_avatar.url
        )

        await self.send(after.guild, embed)

        self.save({
            "type": log_type,
            "user": after.id,
            "by": executor.id if executor else None,
            "time": str(datetime.utcnow())
        })


# ==========================================================
# SETUP
# ==========================================================

async def setup(bot):

    await bot.add_cog(ModLog(bot))
