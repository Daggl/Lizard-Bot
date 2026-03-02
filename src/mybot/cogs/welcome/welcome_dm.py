"""Welcome DM cog — sends a private message to newly joined members.

All settings are per-guild and stored in welcome_dm.json.
"""

import discord
from discord import app_commands
from discord.ext import commands

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import translate
from mybot.utils.feature_flags import is_feature_enabled
from mybot.utils.jsonstore import safe_load_json, safe_save_json
from mybot.utils.paths import guild_data_path


def _cfg(guild_id) -> dict:
    try:
        return load_cog_config("welcome_dm", guild_id=guild_id) or {}
    except Exception:
        return {}


class WelcomeDM(commands.Cog):
    """Sends a configurable DM to new server members."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Listener
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild_id = member.guild.id
        if not is_feature_enabled(guild_id, "welcome_dm"):
            return

        cfg = _cfg(guild_id)
        if not cfg.get("ENABLED", False):
            return

        message = str(cfg.get("MESSAGE", "") or "").strip()
        embed_title = str(cfg.get("EMBED_TITLE", "") or "").strip()
        embed_desc = str(cfg.get("EMBED_DESCRIPTION", "") or "").strip()
        embed_color_str = str(cfg.get("EMBED_COLOR", "#5865F2") or "#5865F2").strip()

        # Nothing configured
        if not message and not embed_title and not embed_desc:
            return

        # Resolve placeholders
        placeholders = {
            "mention": member.mention,
            "user_name": str(member.name),
            "display_name": str(member.display_name),
            "user_id": str(member.id),
            "guild_name": str(member.guild.name),
            "member_count": str(member.guild.member_count or 0),
        }

        def _fmt(text: str) -> str:
            try:
                return text.format(**placeholders)
            except Exception:
                return text

        try:
            if embed_title or embed_desc:
                try:
                    color = discord.Color(int(embed_color_str.lstrip("#"), 16))
                except Exception:
                    color = discord.Color.blurple()
                embed = discord.Embed(
                    title=_fmt(embed_title) if embed_title else None,
                    description=_fmt(embed_desc) if embed_desc else None,
                    color=color,
                )
                embed.set_footer(text=member.guild.name)
                if message:
                    await member.send(content=_fmt(message), embed=embed)
                else:
                    await member.send(embed=embed)
            else:
                await member.send(_fmt(message))
        except discord.Forbidden:
            pass  # User has DMs disabled
        except Exception as exc:
            print(f"[WelcomeDM] Failed to DM {member}: {exc}")

    # ------------------------------------------------------------------
    # /setwelcomedm — set the DM message
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="setwelcomedm",
        description="Set the welcome DM message for new members.",
    )
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(message="The message to send. Use {user_name}, {guild_name}, {mention} etc.")
    async def setwelcomedm(self, ctx: commands.Context, *, message: str):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        if guild_id is None:
            await ctx.send("❌ Server-only command.")
            return

        cfg_path = guild_data_path(guild_id, "welcome_dm.json")
        cfg = safe_load_json(cfg_path, default={})
        cfg["MESSAGE"] = message
        cfg["ENABLED"] = True
        safe_save_json(cfg_path, cfg)

        await ctx.send(translate(
            "welcome_dm.msg.set", guild_id=guild_id,
            default="✅ Welcome DM message updated.",
        ))

    # ------------------------------------------------------------------
    # /testwelcomedm — test the DM
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="testwelcomedm",
        description="Test the welcome DM by sending it to yourself.",
    )
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def testwelcomedm(self, ctx: commands.Context):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        if guild_id is None:
            await ctx.send("❌ Server-only command.")
            return

        cfg = _cfg(guild_id)
        message = str(cfg.get("MESSAGE", "") or "").strip()
        embed_title = str(cfg.get("EMBED_TITLE", "") or "").strip()
        embed_desc = str(cfg.get("EMBED_DESCRIPTION", "") or "").strip()

        if not message and not embed_title and not embed_desc:
            await ctx.send(translate(
                "welcome_dm.error.not_configured", guild_id=guild_id,
                default="❌ No welcome DM configured. Use `/setwelcomedm` or the UI.",
            ))
            return

        # Simulate on_member_join for the caller
        member = ctx.author
        placeholders = {
            "mention": member.mention,
            "user_name": str(member.name),
            "display_name": str(member.display_name),
            "user_id": str(member.id),
            "guild_name": str(ctx.guild.name),
            "member_count": str(ctx.guild.member_count or 0),
        }

        def _fmt(text: str) -> str:
            try:
                return text.format(**placeholders)
            except Exception:
                return text

        embed_color_str = str(cfg.get("EMBED_COLOR", "#5865F2") or "#5865F2").strip()
        try:
            if embed_title or embed_desc:
                try:
                    color = discord.Color(int(embed_color_str.lstrip("#"), 16))
                except Exception:
                    color = discord.Color.blurple()
                embed = discord.Embed(
                    title=_fmt(embed_title) if embed_title else None,
                    description=_fmt(embed_desc) if embed_desc else None,
                    color=color,
                )
                embed.set_footer(text=ctx.guild.name)
                if message:
                    await member.send(content=_fmt(message), embed=embed)
                else:
                    await member.send(embed=embed)
            else:
                await member.send(_fmt(message))
            await ctx.send(translate(
                "welcome_dm.msg.test_sent", guild_id=guild_id,
                default="✅ Test DM sent. Check your DMs!",
            ))
        except discord.Forbidden:
            await ctx.send(translate(
                "welcome_dm.error.dm_blocked", guild_id=guild_id,
                default="❌ Could not send DM — your DMs are disabled.",
            ))
        except Exception as exc:
            await ctx.send(f"❌ Error: {exc}")

    # ------------------------------------------------------------------
    # /welcomedminfo — show current config
    # ------------------------------------------------------------------

    @commands.hybrid_command(
        name="welcomedminfo",
        description="Show the current welcome DM configuration.",
    )
    async def welcomedminfo(self, ctx: commands.Context):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        cfg = _cfg(guild_id)

        enabled = bool(cfg.get("ENABLED", False))
        message = str(cfg.get("MESSAGE", "") or "—")
        embed_title = str(cfg.get("EMBED_TITLE", "") or "—")
        embed_desc = str(cfg.get("EMBED_DESCRIPTION", "") or "—")

        embed = discord.Embed(
            title=translate("welcome_dm.info.title", guild_id=guild_id,
                            default="📨 Welcome DM Configuration"),
            color=discord.Color.blue(),
        )
        embed.add_field(name="Enabled", value="✅" if enabled else "❌", inline=True)
        embed.add_field(name="Message", value=message[:200], inline=False)
        embed.add_field(name="Embed Title", value=embed_title[:100], inline=True)
        embed.add_field(name="Embed Description", value=embed_desc[:200], inline=False)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeDM(bot))
