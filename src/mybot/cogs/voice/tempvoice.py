"""Temporary voice channel cog — join-to-create, lock, hide, rename, transfer and auto-cleanup."""

import sqlite3
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

try:
    from mybot.utils.i18n import translate, translate_for_ctx, translate_for_interaction
except Exception:  # pragma: no cover - fallback for packaging
    from src.mybot.utils.i18n import translate, translate_for_ctx, translate_for_interaction

from mybot.utils.config import load_cog_config
from mybot.utils.paths import get_db_path


def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("tempvoice", guild_id=guild_id) or {}
    except Exception:
        return {}


def _cfg_int(name: str, default: int = 0, guild_id: int | str | None = None) -> int:
    try:
        return int(_cfg(guild_id).get(name, default) or default)
    except Exception:
        return int(default)


def _cfg_str(name: str, default: str = "", guild_id: int | str | None = None) -> str:
    try:
        return str(_cfg(guild_id).get(name, default) or default)
    except Exception:
        return default


def _cfg_bool(name: str, default: bool = True, guild_id: int | str | None = None) -> bool:
    try:
        val = _cfg(guild_id).get(name, default)
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return bool(default)


class RenameModal(discord.ui.Modal):
    def __init__(self, cog: "TempVoice", guild_id: Optional[int] = None):
        title = translate("tempvoice.modal.rename.title", guild_id=guild_id, default="Rename Temp Voice")
        super().__init__(title=title)
        self.cog = cog
        self.guild_id = guild_id
        self.channel_name = discord.ui.TextInput(
            label=translate(
                "tempvoice.modal.rename.label",
                guild_id=guild_id,
                default="New channel name",
            ),
            min_length=1,
            max_length=90,
        )
        self.add_item(self.channel_name)

    async def on_submit(self, interaction: discord.Interaction):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        new_name = str(self.channel_name.value or "").strip()
        if not new_name:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.empty_name",
                    default="Name cannot be empty.",
                ),
                ephemeral=True,
            )
            return
        try:
            await channel.edit(name=new_name, reason=f"TempVoice rename by {interaction.user}")
            # Save the new name for next session
            guild_id = getattr(interaction.guild, "id", None)
            if guild_id:
                self.cog._save_channel_name(guild_id, interaction.user.id, new_name)
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.renamed",
                    default="✅ Renamed to **{name}**",
                    name=new_name,
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.rename_failed",
                    default="❌ Failed to rename: {error}",
                    error=str(exc),
                ),
                ephemeral=True,
            )


class LimitModal(discord.ui.Modal):
    def __init__(self, cog: "TempVoice", guild_id: Optional[int] = None):
        title = translate("tempvoice.modal.limit.title", guild_id=guild_id, default="Set User Limit")
        super().__init__(title=title)
        self.cog = cog
        self.guild_id = guild_id
        self.user_limit = discord.ui.TextInput(
            label=translate(
                "tempvoice.modal.limit.label",
                guild_id=guild_id,
                default="User limit (0-99)",
            ),
            placeholder=translate(
                "tempvoice.modal.limit.placeholder",
                guild_id=guild_id,
                default="0 = unlimited",
            ),
            max_length=2,
        )
        self.add_item(self.user_limit)

    async def on_submit(self, interaction: discord.Interaction):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        raw = str(self.user_limit.value or "").strip()
        if not raw.isdigit():
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.limit_digits",
                    default="❌ Please enter digits only (0-99).",
                ),
                ephemeral=True,
            )
            return
        limit = int(raw)
        if limit < 0 or limit > 99:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.limit_range",
                    default="❌ Limit must be between 0 and 99.",
                ),
                ephemeral=True,
            )
            return
        try:
            await channel.edit(user_limit=limit, reason=f"TempVoice limit by {interaction.user}")
            self.cog._set_user_limit(channel.id, limit)
            label_unlimited = translate_for_interaction(
                interaction,
                "tempvoice.label.unlimited",
                default="unlimited",
            )
            text = label_unlimited if limit == 0 else str(limit)
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.limit_set",
                    default="✅ User limit set to **{value}**",
                    value=text,
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.limit_failed",
                    default="❌ Failed to set limit: {error}",
                    error=str(exc),
                ),
                ephemeral=True,
            )


class TransferModal(discord.ui.Modal):
    def __init__(self, cog: "TempVoice", guild_id: Optional[int] = None):
        title = translate(
            "tempvoice.modal.transfer.title",
            guild_id=guild_id,
            default="Transfer Temp Voice Ownership",
        )
        super().__init__(title=title)
        self.cog = cog
        self.guild_id = guild_id
        self.member_value = discord.ui.TextInput(
            label=translate(
                "tempvoice.modal.transfer.label",
                guild_id=guild_id,
                default="Target member (ID or @mention)",
            ),
            max_length=40,
        )
        self.add_item(self.member_value)

    async def on_submit(self, interaction: discord.Interaction):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return

        raw = str(self.member_value.value or "").strip()
        target_id = self.cog._extract_int(raw)
        if not target_id:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.member_parse",
                    default="❌ Could not parse member ID.",
                ),
                ephemeral=True,
            )
            return

        target_member = interaction.guild.get_member(target_id) if interaction.guild else None
        if target_member is None:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.member_missing",
                    default="❌ Member not found in this server.",
                ),
                ephemeral=True,
            )
            return

        if target_member not in channel.members:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.member_not_in_channel",
                    default="❌ Target member must be in your temp voice channel.",
                ),
                ephemeral=True,
            )
            return

        ok, message = await self.cog._transfer_owner(channel, target_member, interaction.user)
        if ok:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.transfer_success",
                    default="✅ Ownership transferred to {member}.",
                    member=message,
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.transfer_failed",
                    default="❌ {message}",
                    message=message,
                ),
                ephemeral=True,
            )


class WhitelistModal(discord.ui.Modal):
    def __init__(self, cog: "TempVoice", guild_id: Optional[int] = None):
        title = translate("tempvoice.modal.whitelist.title", guild_id=guild_id, default="Whitelist User")
        super().__init__(title=title)
        self.cog = cog
        self.guild_id = guild_id
        self.member_value = discord.ui.TextInput(
            label=translate(
                "tempvoice.modal.whitelist.label",
                guild_id=guild_id,
                default="User (ID or @mention)",
            ),
            max_length=40,
        )
        self.add_item(self.member_value)

    async def on_submit(self, interaction: discord.Interaction):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        raw = str(self.member_value.value or "").strip()
        target_id = self.cog._extract_int(raw)
        if not target_id:
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.error.member_parse",
                                          default="❌ Could not parse member ID."),
                ephemeral=True,
            )
            return
        target = interaction.guild.get_member(target_id) if interaction.guild else None
        if target is None:
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.error.member_missing",
                                          default="❌ Member not found in this server."),
                ephemeral=True,
            )
            return
        try:
            await channel.set_permissions(target, connect=True, view_channel=True)
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.msg.whitelisted",
                                          default="✅ {member} has been whitelisted.",
                                          member=target.mention),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.error.generic",
                                          default="❌ Failed: {error}", error=str(exc)),
                ephemeral=True,
            )


class BlacklistModal(discord.ui.Modal):
    def __init__(self, cog: "TempVoice", guild_id: Optional[int] = None):
        title = translate("tempvoice.modal.blacklist.title", guild_id=guild_id, default="Blacklist User")
        super().__init__(title=title)
        self.cog = cog
        self.guild_id = guild_id
        self.member_value = discord.ui.TextInput(
            label=translate(
                "tempvoice.modal.blacklist.label",
                guild_id=guild_id,
                default="User (ID or @mention)",
            ),
            max_length=40,
        )
        self.add_item(self.member_value)

    async def on_submit(self, interaction: discord.Interaction):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        raw = str(self.member_value.value or "").strip()
        target_id = self.cog._extract_int(raw)
        if not target_id:
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.error.member_parse",
                                          default="❌ Could not parse member ID."),
                ephemeral=True,
            )
            return
        target = interaction.guild.get_member(target_id) if interaction.guild else None
        if target is None:
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.error.member_missing",
                                          default="❌ Member not found in this server."),
                ephemeral=True,
            )
            return
        try:
            await channel.set_permissions(target, connect=False, view_channel=False)
            # Disconnect the user if currently in the channel
            if target in channel.members:
                try:
                    await target.move_to(None, reason=f"TempVoice blacklist by {interaction.user}")
                except Exception:
                    pass
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.msg.blacklisted",
                                          default="✅ {member} has been blacklisted.",
                                          member=target.mention),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(interaction, "tempvoice.error.generic",
                                          default="❌ Failed: {error}", error=str(exc)),
                ephemeral=True,
            )


class TempVoicePanelView(discord.ui.View):
    def __init__(self, cog: "TempVoice", guild_id: Optional[int] = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        self._apply_labels()

    def _apply_labels(self) -> None:
        mapping = {
            "tempvoice:lock": ("tempvoice.button.lock", "Lock"),
            "tempvoice:unlock": ("tempvoice.button.unlock", "Unlock"),
            "tempvoice:hide": ("tempvoice.button.hide", "Hide"),
            "tempvoice:unhide": ("tempvoice.button.unhide", "Unhide"),
            "tempvoice:rename": ("tempvoice.button.rename", "Rename"),
            "tempvoice:limit": ("tempvoice.button.limit", "Limit"),
            "tempvoice:whitelist": ("tempvoice.button.whitelist", "Whitelist"),
            "tempvoice:blacklist": ("tempvoice.button.blacklist", "Blacklist"),
            "tempvoice:transfer": ("tempvoice.button.transfer", "Transfer"),
            "tempvoice:claim": ("tempvoice.button.claim", "Claim"),
            "tempvoice:delete": ("tempvoice.button.delete", "Delete"),
        }
        for child in self.children:
            custom_id = getattr(child, "custom_id", None)
            if custom_id in mapping:
                key, default = mapping[custom_id]
                child.label = translate(key, guild_id=self.guild_id, default=default)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="tempvoice:lock", row=0)
    async def lock_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog._handle_lock(interaction, True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.secondary, emoji="🔓", custom_id="tempvoice:unlock", row=0)
    async def unlock_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog._handle_lock(interaction, False)

    @discord.ui.button(label="Hide", style=discord.ButtonStyle.secondary, emoji="🙈", custom_id="tempvoice:hide", row=0)
    async def hide_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog._handle_hide(interaction, True)

    @discord.ui.button(label="Unhide", style=discord.ButtonStyle.secondary, emoji="👁️", custom_id="tempvoice:unhide", row=0)
    async def unhide_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog._handle_hide(interaction, False)

    @discord.ui.button(label="Rename", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="tempvoice:rename", row=1)
    async def rename_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.send_modal(
            RenameModal(self.cog, getattr(interaction.guild, "id", None))
        )

    @discord.ui.button(label="Limit", style=discord.ButtonStyle.primary, emoji="👥", custom_id="tempvoice:limit", row=1)
    async def limit_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.send_modal(
            LimitModal(self.cog, getattr(interaction.guild, "id", None))
        )

    @discord.ui.button(label="Whitelist", style=discord.ButtonStyle.success, emoji="✅", custom_id="tempvoice:whitelist", row=1)
    async def whitelist_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.send_modal(
            WhitelistModal(self.cog, getattr(interaction.guild, "id", None))
        )

    @discord.ui.button(label="Blacklist", style=discord.ButtonStyle.danger, emoji="🚫", custom_id="tempvoice:blacklist", row=1)
    async def blacklist_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.send_modal(
            BlacklistModal(self.cog, getattr(interaction.guild, "id", None))
        )

    @discord.ui.button(label="Transfer", style=discord.ButtonStyle.primary, emoji="🎯", custom_id="tempvoice:transfer", row=2)
    async def transfer_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        channel, err = self.cog._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        await interaction.response.send_modal(
            TransferModal(self.cog, getattr(interaction.guild, "id", None))
        )

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="👑", custom_id="tempvoice:claim", row=2)
    async def claim_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog._handle_claim(interaction)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="tempvoice:delete", row=2)
    async def delete_btn(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self.cog._handle_delete(interaction)


class TempVoice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = get_db_path("tempvoice")
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._setup_db()

    def cog_unload(self):
        try:
            self.db.close()
        except Exception:
            pass

    def _setup_db(self):
        cur = self.db.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS temp_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                locked INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0,
                user_limit INTEGER DEFAULT 0,
                created_at TEXT
            )
            """
        )
        # User preferences table — stores last channel name per user/guild
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_prefs (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                last_channel_name TEXT DEFAULT '',
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )
        self.db.commit()

    def _extract_int(self, text: str) -> Optional[int]:
        digits = "".join(ch for ch in str(text or "") if ch.isdigit())
        if not digits:
            return None
        try:
            return int(digits)
        except Exception:
            return None

    def _get_owner_id(self, channel_id: int) -> Optional[int]:
        try:
            cur = self.db.cursor()
            cur.execute("SELECT owner_id FROM temp_channels WHERE channel_id = ?", (int(channel_id),))
            row = cur.fetchone()
            return int(row[0]) if row else None
        except Exception:
            return None

    def _get_owned_channel_id(self, guild_id: int, owner_id: int) -> Optional[int]:
        try:
            cur = self.db.cursor()
            cur.execute(
                "SELECT channel_id FROM temp_channels WHERE guild_id = ? AND owner_id = ? LIMIT 1",
                (int(guild_id), int(owner_id)),
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
        except Exception:
            return None

    def _insert_or_update_channel(self, channel_id: int, guild_id: int, owner_id: int):
        cur = self.db.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO temp_channels
            (channel_id, guild_id, owner_id, locked, hidden, user_limit, created_at)
            VALUES (
                ?, ?, ?,
                COALESCE((SELECT locked FROM temp_channels WHERE channel_id = ?), 0),
                COALESCE((SELECT hidden FROM temp_channels WHERE channel_id = ?), 0),
                COALESCE((SELECT user_limit FROM temp_channels WHERE channel_id = ?), 0),
                COALESCE((SELECT created_at FROM temp_channels WHERE channel_id = ?), ?)
            )
            """,
            (
                int(channel_id),
                int(guild_id),
                int(owner_id),
                int(channel_id),
                int(channel_id),
                int(channel_id),
                int(channel_id),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.db.commit()

    def _set_owner(self, channel_id: int, owner_id: int):
        cur = self.db.cursor()
        cur.execute("UPDATE temp_channels SET owner_id = ? WHERE channel_id = ?", (int(owner_id), int(channel_id)))
        self.db.commit()

    def _set_lock_hidden(self, channel_id: int, *, locked: Optional[bool] = None, hidden: Optional[bool] = None):
        cur = self.db.cursor()
        if locked is not None:
            cur.execute("UPDATE temp_channels SET locked = ? WHERE channel_id = ?", (1 if locked else 0, int(channel_id)))
        if hidden is not None:
            cur.execute("UPDATE temp_channels SET hidden = ? WHERE channel_id = ?", (1 if hidden else 0, int(channel_id)))
        self.db.commit()

    def _set_user_limit(self, channel_id: int, limit: int):
        cur = self.db.cursor()
        cur.execute("UPDATE temp_channels SET user_limit = ? WHERE channel_id = ?", (int(limit), int(channel_id)))
        self.db.commit()

    def _remove_channel(self, channel_id: int):
        cur = self.db.cursor()
        cur.execute("DELETE FROM temp_channels WHERE channel_id = ?", (int(channel_id),))
        self.db.commit()

    # ------------------------------------------------------------------
    # User preferences (saved channel name)
    # ------------------------------------------------------------------

    def _get_saved_channel_name(self, guild_id: int, user_id: int) -> str:
        """Return the last channel name the user set, or empty string."""
        try:
            cur = self.db.cursor()
            cur.execute(
                "SELECT last_channel_name FROM user_prefs WHERE guild_id = ? AND user_id = ?",
                (int(guild_id), int(user_id)),
            )
            row = cur.fetchone()
            return str(row[0]) if row and row[0] else ""
        except Exception:
            return ""

    def _save_channel_name(self, guild_id: int, user_id: int, name: str):
        """Persist the channel name so it can be reused next time."""
        try:
            cur = self.db.cursor()
            cur.execute(
                """
                INSERT INTO user_prefs (guild_id, user_id, last_channel_name)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET last_channel_name = excluded.last_channel_name
                """,
                (int(guild_id), int(user_id), str(name)[:95]),
            )
            self.db.commit()
        except Exception:
            pass

    def _channel_name_for(self, member: discord.Member) -> str:
        guild_id = getattr(getattr(member, "guild", None), "id", None)
        # Check for a saved name from last session
        if guild_id:
            saved = self._get_saved_channel_name(guild_id, member.id)
            if saved:
                return saved[:95]
        template = _cfg_str("CHANNEL_NAME_TEMPLATE", "🔊 {display_name}", guild_id=guild_id)
        try:
            return template.format(
                user=member.name,
                display_name=member.display_name,
                id=member.id,
            )[:95]
        except Exception:
            return f"🔊 {member.display_name}"[:95]

    def _temp_category(self, guild: discord.Guild) -> Optional[discord.CategoryChannel]:
        cid = _cfg_int("CATEGORY_ID", 0, guild_id=getattr(guild, "id", None))
        if cid:
            c = guild.get_channel(cid)
            if isinstance(c, discord.CategoryChannel):
                return c
        for c in guild.categories:
            if "temp" in c.name.lower() and "voice" in c.name.lower():
                return c
        return None

    def _control_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        cid = _cfg_int("CONTROL_CHANNEL_ID", 0, guild_id=getattr(guild, "id", None))
        if not cid:
            return None
        ch = guild.get_channel(cid)
        return ch if isinstance(ch, discord.TextChannel) else None

    def _create_channel_hub(self, guild: discord.Guild) -> Optional[discord.VoiceChannel]:
        cid = _cfg_int("CREATE_CHANNEL_ID", 0, guild_id=getattr(guild, "id", None))
        if not cid:
            return None
        ch = guild.get_channel(cid)
        return ch if isinstance(ch, discord.VoiceChannel) else None

    def _voice_temp_channel_for_member(self, member: discord.Member) -> Optional[discord.VoiceChannel]:
        try:
            channel = member.voice.channel if member.voice else None
        except Exception:
            channel = None
        if channel is None:
            return None
        owner = self._get_owner_id(channel.id)
        return channel if owner is not None else None

    def _owned_channel_for_interaction(self, interaction: discord.Interaction) -> tuple[Optional[discord.VoiceChannel], str]:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return (
                None,
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.server_only",
                    default="❌ This can only be used in a server.",
                ),
            )

        active_temp = self._voice_temp_channel_for_member(interaction.user)
        if active_temp is not None:
            owner_id = self._get_owner_id(active_temp.id)
            if owner_id == interaction.user.id:
                return active_temp, ""

        owned_channel_id = self._get_owned_channel_id(interaction.guild.id, interaction.user.id)
        if owned_channel_id:
            channel = interaction.guild.get_channel(owned_channel_id)
            if isinstance(channel, discord.VoiceChannel):
                return channel, ""

        return (
            None,
            translate_for_interaction(
                interaction,
                "tempvoice.error.not_owner",
                default="❌ You are not the owner of a temp voice channel.",
            ),
        )

    async def _transfer_owner(self, channel: discord.VoiceChannel, new_owner: discord.Member, by_user: discord.Member) -> tuple[bool, str]:
        old_owner_id = self._get_owner_id(channel.id)
        if old_owner_id is None:
            return False, translate(
                "tempvoice.error.not_tracked",
                guild_id=getattr(channel.guild, "id", None),
                default="This is not a tracked temp channel.",
            )
        old_owner = channel.guild.get_member(old_owner_id)
        try:
            if old_owner is not None:
                await channel.set_permissions(old_owner, overwrite=None)
            await channel.set_permissions(
                new_owner,
                connect=True,
                view_channel=True,
                manage_channels=True,
                move_members=True,
            )
            self._set_owner(channel.id, new_owner.id)
            return True, new_owner.mention
        except Exception as exc:
            return False, str(exc)

    async def _create_temp_channel_for_member(self, member: discord.Member) -> tuple[Optional[discord.VoiceChannel], str]:
        if not member.guild:
            return None, translate(
                "tempvoice.error.server_only",
                guild_id=None,
                default="Server-only action.",
            )
        guild_id = getattr(getattr(member, "guild", None), "id", None)

        if not _cfg_bool("ENABLED", True, guild_id=guild_id):
            return None, translate(
                "tempvoice.error.disabled",
                guild_id=getattr(member.guild, "id", None),
                default="TempVoice is disabled in config.",
            )

        existing_id = self._get_owned_channel_id(member.guild.id, member.id)
        if existing_id:
            existing = member.guild.get_channel(existing_id)
            if isinstance(existing, discord.VoiceChannel):
                return existing, "existing"

        category = self._temp_category(member.guild)
        overwrites = {
            member.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True, move_members=True),
        }
        limit = max(0, min(99, _cfg_int("DEFAULT_USER_LIMIT", 0, guild_id=guild_id)))

        try:
            channel = await member.guild.create_voice_channel(
                self._channel_name_for(member),
                category=category,
                user_limit=limit,
                overwrites=overwrites,
                reason=f"TempVoice create by {member}",
            )
            self._insert_or_update_channel(channel.id, member.guild.id, member.id)
            self._set_user_limit(channel.id, limit)
            return channel, "created"
        except Exception as exc:
            return None, translate(
                "tempvoice.error.create_failed",
                guild_id=getattr(member.guild, "id", None),
                default="Failed to create channel: {error}",
                error=str(exc),
            )

    async def _handle_create(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.server_only",
                    default="❌ Server-only action.",
                ),
                ephemeral=True,
            )
            return
        channel, state = await self._create_temp_channel_for_member(interaction.user)
        if channel is None:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.create_generic",
                    default="❌ Failed to create channel: {error}",
                    error=state,
                ),
                ephemeral=True,
            )
            return

        try:
            if interaction.user.voice:
                await interaction.user.move_to(channel, reason="TempVoice auto-move")
        except Exception:
            pass

        if state == "existing":
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.already_exists",
                    default="✅ Your temp channel already exists: {channel}",
                    channel=channel.mention,
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.created",
                    default="✅ Created: {channel}",
                    channel=channel.mention,
                ),
                ephemeral=True,
            )

    async def _handle_lock(self, interaction: discord.Interaction, lock: bool):
        channel, err = self._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        try:
            default_role = channel.guild.default_role
            existing = channel.overwrites_for(default_role)
            existing.connect = not lock
            await channel.set_permissions(default_role, overwrite=existing)
            self._set_lock_hidden(channel.id, locked=lock)
            key = "tempvoice.msg.locked" if lock else "tempvoice.msg.unlocked"
            default = "✅ Locked." if lock else "✅ Unlocked."
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    key,
                    default=default,
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.generic",
                    default="❌ Failed: {error}",
                    error=str(exc),
                ),
                ephemeral=True,
            )

    async def _handle_hide(self, interaction: discord.Interaction, hide: bool):
        channel, err = self._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        try:
            default_role = channel.guild.default_role
            existing = channel.overwrites_for(default_role)
            existing.view_channel = not hide
            await channel.set_permissions(default_role, overwrite=existing)
            self._set_lock_hidden(channel.id, hidden=hide)
            key = "tempvoice.msg.hidden" if hide else "tempvoice.msg.unhidden"
            default = "✅ Hidden." if hide else "✅ Unhidden."
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    key,
                    default=default,
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.generic",
                    default="❌ Failed: {error}",
                    error=str(exc),
                ),
                ephemeral=True,
            )

    async def _handle_claim(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.server_only",
                    default="❌ Server-only action.",
                ),
                ephemeral=True,
            )
            return
        channel = self._voice_temp_channel_for_member(interaction.user)
        if channel is None:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.claim_join",
                    default="❌ Join a temp voice channel to claim it.",
                ),
                ephemeral=True,
            )
            return

        owner_id = self._get_owner_id(channel.id)
        if owner_id is None:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.not_tracked",
                    default="❌ This is not a tracked temp channel.",
                ),
                ephemeral=True,
            )
            return
        if owner_id == interaction.user.id:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.info.already_owner",
                    default="ℹ️ You already own this channel.",
                ),
                ephemeral=True,
            )
            return

        owner_member = interaction.guild.get_member(owner_id)
        if owner_member is not None and owner_member in channel.members:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.owner_present",
                    default="❌ Owner is still in the channel.",
                ),
                ephemeral=True,
            )
            return

        ok, message = await self._transfer_owner(channel, interaction.user, interaction.user)
        if ok:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.claim_transfer",
                    default="✅ Ownership transferred to {member}.",
                    member=message,
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.transfer_failed",
                    default="❌ {message}",
                    message=message,
                ),
                ephemeral=True,
            )

    async def _handle_delete(self, interaction: discord.Interaction):
        channel, err = self._owned_channel_for_interaction(interaction)
        if channel is None:
            await interaction.response.send_message(err, ephemeral=True)
            return
        try:
            self._remove_channel(channel.id)
            await channel.delete(reason=f"TempVoice delete by {interaction.user}")
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.msg.deleted",
                    default="✅ Channel deleted.",
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.response.send_message(
                translate_for_interaction(
                    interaction,
                    "tempvoice.error.delete_failed",
                    default="❌ Failed to delete: {error}",
                    error=str(exc),
                ),
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        after_channel = after.channel if isinstance(after.channel, discord.VoiceChannel) else None
        hub_channel = self._create_channel_hub(member.guild) if member.guild else None

        if after_channel is not None and hub_channel is not None and after_channel.id == hub_channel.id and not getattr(member, "bot", False):
            channel, state = await self._create_temp_channel_for_member(member)
            if channel is not None:
                try:
                    if member.voice and member.voice.channel and member.voice.channel.id == hub_channel.id:
                        await member.move_to(channel, reason="TempVoice join-to-create")
                except Exception:
                    pass

        before_channel = before.channel if isinstance(before.channel, discord.VoiceChannel) else None
        if before_channel is None:
            return
        owner_id = self._get_owner_id(before_channel.id)
        if owner_id is None:
            return

        remaining = [m for m in before_channel.members if not getattr(m, "bot", False)]
        if len(remaining) == 0:
            try:
                self._remove_channel(before_channel.id)
                await before_channel.delete(reason="TempVoice auto-cleanup (empty)")
            except Exception:
                pass
            return

        if member.id == owner_id:
            new_owner = remaining[0]
            await self._transfer_owner(before_channel, new_owner, member)

    @commands.hybrid_command(name="tempvoicepanel", description="Tempvoice panel command.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def tempvoice_panel(self, ctx: commands.Context):
        hub_channel = self._create_channel_hub(ctx.guild) if ctx.guild else None
        if hub_channel is not None:
            hub_hint = translate_for_ctx(
                ctx,
                "tempvoice.panel.hint_join",
                default="Join {channel} to auto-create your temp channel.",
                channel=hub_channel.mention,
            )
        else:
            configured_id = _cfg_int("CREATE_CHANNEL_ID", 0, guild_id=getattr(getattr(ctx, "guild", None), "id", None))
            if configured_id:
                hub_hint = translate_for_ctx(
                    ctx,
                    "tempvoice.panel.hint_configured",
                    default="Join your configured create channel (ID: {channel_id}) to auto-create your temp channel.",
                    channel_id=configured_id,
                )
            else:
                hub_hint = translate_for_ctx(
                    ctx,
                    "tempvoice.panel.hint_configure",
                    default="Set CREATE_CHANNEL_ID in tempvoice config to enable join-to-create.",
                )

        embed = discord.Embed(
            title=translate_for_ctx(
                ctx,
                "tempvoice.panel.title",
                default="🎙️ Temp Voice",
            ),
            description=translate_for_ctx(
                ctx,
                "tempvoice.panel.description",
                default=(
                    "Manage your temporary voice channel with the buttons below.\n\n"
                    "Features: lock/unlock, hide/unhide, rename, user limit, whitelist/blacklist, transfer, claim, delete.\n"
                    "Your channel name is saved and restored automatically.\n"
                    "{hint}"
                ),
                hint=hub_hint,
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        view = TempVoicePanelView(self, getattr(ctx.guild, "id", None))
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    cog = TempVoice(bot)
    await bot.add_cog(cog)
    bot.add_view(TempVoicePanelView(cog))
