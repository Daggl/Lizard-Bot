"""Meme Cog — create, store and retrieve memes per guild.

Users attach an image or GIF and provide a caption via ``/meme create``.
The image is saved to ``data/memes/{guild_id}/`` and an index JSON keeps
track of all memes (name → metadata).  Memes can be listed and retrieved
by name.
"""

import io
import json
import os
import re
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from mybot.utils.feature_flags import is_feature_enabled
from mybot.utils.i18n import translate
from mybot.utils.paths import REPO_ROOT


_MEMES_DIR = os.path.join(REPO_ROOT, "data", "memes")


def _guild_memes_dir(guild_id: int) -> str:
    d = os.path.join(_MEMES_DIR, str(guild_id))
    os.makedirs(d, exist_ok=True)
    return d


def _index_path(guild_id: int) -> str:
    return os.path.join(_guild_memes_dir(guild_id), "_index.json")


def _load_index(guild_id: int) -> dict:
    path = _index_path(guild_id)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_index(guild_id: int, data: dict):
    path = _index_path(guild_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _sanitise_name(name: str) -> str:
    """Sanitise a meme name to a filesystem-safe lowercase slug."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_\-]", "_", name)
    return name[:64] or "meme"


class MemeCog(commands.Cog, name="Memes"):
    """Create and retrieve guild memes."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Group
    # ------------------------------------------------------------------

    meme_group = app_commands.Group(name="meme", description="Meme commands")

    # ------------------------------------------------------------------
    # /meme create <name> <caption> + attached image
    # ------------------------------------------------------------------

    @meme_group.command(name="create", description="Create a meme from an attached image or GIF.")
    @app_commands.describe(
        name="A unique name to identify this meme.",
        caption="The caption / text to display with the meme.",
        image="The image or GIF for the meme.",
    )
    async def meme_create(
        self,
        interaction: discord.Interaction,
        name: str,
        caption: str,
        image: discord.Attachment,
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Server-only command.", ephemeral=True)
            return
        guild_id = guild.id

        if not is_feature_enabled(guild_id, "memes"):
            await interaction.response.send_message("❌ Memes feature is disabled.", ephemeral=True)
            return

        safe_name = _sanitise_name(name)
        index = _load_index(guild_id)
        t = translate

        if safe_name in index:
            await interaction.response.send_message(
                t("meme.error.exists", guild_id=guild_id, name=safe_name),
                ephemeral=True,
            )
            return

        # Validate attachment is an image/gif
        ct = (image.content_type or "").lower()
        if not ct.startswith("image/"):
            await interaction.response.send_message(
                t("meme.error.no_image", guild_id=guild_id),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Download and save
        ext = "gif" if "gif" in ct else "png"
        if ct.startswith("image/jpeg"):
            ext = "jpg"
        elif ct.startswith("image/webp"):
            ext = "webp"

        filename = f"{safe_name}.{ext}"
        save_path = os.path.join(_guild_memes_dir(guild_id), filename)

        try:
            data = await image.read()
            with open(save_path, "wb") as fh:
                fh.write(data)
        except Exception as exc:
            await interaction.followup.send(f"❌ Failed to save image: {exc}", ephemeral=True)
            return

        index[safe_name] = {
            "caption": caption,
            "filename": filename,
            "author_id": interaction.user.id,
            "author_name": str(interaction.user),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_index(guild_id, index)

        await interaction.followup.send(
            t("meme.msg.saved", guild_id=guild_id, name=safe_name)
        )

    # ------------------------------------------------------------------
    # /meme show <name>
    # ------------------------------------------------------------------

    @meme_group.command(name="show", description="Display a saved meme by name.")
    @app_commands.describe(name="Name of the meme to show.")
    async def meme_show(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Server-only command.", ephemeral=True)
            return
        guild_id = guild.id

        if not is_feature_enabled(guild_id, "memes"):
            await interaction.response.send_message("❌ Memes feature is disabled.", ephemeral=True)
            return

        safe_name = _sanitise_name(name)
        index = _load_index(guild_id)
        t = translate

        if safe_name not in index:
            await interaction.response.send_message(
                t("meme.error.not_found", guild_id=guild_id, name=safe_name),
                ephemeral=True,
            )
            return

        entry = index[safe_name]
        file_path = os.path.join(_guild_memes_dir(guild_id), entry["filename"])

        if not os.path.isfile(file_path):
            await interaction.response.send_message(
                t("meme.error.not_found", guild_id=guild_id, name=safe_name),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"😂 {safe_name}",
            description=entry.get("caption", ""),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"by {entry.get('author_name', 'Unknown')}")

        file = discord.File(file_path, filename=entry["filename"])
        embed.set_image(url=f"attachment://{entry['filename']}")

        await interaction.response.send_message(embed=embed, file=file)

    # ------------------------------------------------------------------
    # /meme list
    # ------------------------------------------------------------------

    @meme_group.command(name="list", description="List all saved memes.")
    async def meme_list(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Server-only command.", ephemeral=True)
            return
        guild_id = guild.id

        if not is_feature_enabled(guild_id, "memes"):
            await interaction.response.send_message("❌ Memes feature is disabled.", ephemeral=True)
            return

        index = _load_index(guild_id)
        t = translate

        if not index:
            await interaction.response.send_message(
                t("meme.error.no_memes", guild_id=guild_id), ephemeral=True
            )
            return

        lines = []
        for meme_name, entry in sorted(index.items()):
            caption_preview = (entry.get("caption", "") or "")[:60]
            if len(entry.get("caption", "")) > 60:
                caption_preview += "…"
            lines.append(f"**{meme_name}** — {caption_preview}")

        embed = discord.Embed(
            title=t("meme.list.title", guild_id=guild_id),
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(
            text=t("meme.list.footer", guild_id=guild_id, count=len(index))
        )

        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /meme delete <name>  (admin only)
    # ------------------------------------------------------------------

    @meme_group.command(name="delete", description="Delete a saved meme (Admin only).")
    @app_commands.describe(name="Name of the meme to delete.")
    @app_commands.default_permissions(administrator=True)
    async def meme_delete(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Server-only command.", ephemeral=True)
            return
        guild_id = guild.id

        safe_name = _sanitise_name(name)
        index = _load_index(guild_id)
        t = translate

        if safe_name not in index:
            await interaction.response.send_message(
                t("meme.error.not_found", guild_id=guild_id, name=safe_name),
                ephemeral=True,
            )
            return

        entry = index.pop(safe_name)
        _save_index(guild_id, index)

        # Remove image file
        file_path = os.path.join(_guild_memes_dir(guild_id), entry.get("filename", ""))
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass

        await interaction.response.send_message(
            t("meme.msg.deleted", guild_id=guild_id, name=safe_name)
        )

    # ------------------------------------------------------------------
    # Autocomplete for meme names
    # ------------------------------------------------------------------

    @meme_show.autocomplete("name")
    @meme_delete.autocomplete("name")
    async def _meme_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        guild = interaction.guild
        if guild is None:
            return []
        index = _load_index(guild.id)
        lower = current.lower()
        return [
            app_commands.Choice(name=k, value=k)
            for k in sorted(index.keys())
            if lower in k.lower()
        ][:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(MemeCog(bot))
