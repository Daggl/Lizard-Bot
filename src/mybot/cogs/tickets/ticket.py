import asyncio
import os
import sqlite3
from datetime import datetime
from typing import Optional
from uuid import uuid4

import discord
from discord.ext import commands

from mybot.utils.config import load_cog_config
from mybot.utils.paths import (
    ensure_dirs,
    get_db_path,
    get_ticket_transcript_path,
    migrate_old_paths,
)

_CFG = load_cog_config("tickets")

TICKET_CATEGORY_ID: Optional[int] = _CFG.get("TICKET_CATEGORY_ID", None)
SUPPORT_ROLE_ID: Optional[int] = _CFG.get("SUPPORT_ROLE_ID", None)
TICKET_LOG_CHANNEL_ID: Optional[int] = _CFG.get("TICKET_LOG_CHANNEL_ID", None)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


class TicketPanelView(discord.ui.View):
    def __init__(self, cog: "TicketCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="ticket_panel:create",
    )
    async def create_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.cog._create_ticket_for_user(
            interaction.guild, interaction.user, interaction.channel
        )
        await interaction.followup.send(
            "✅ Your support ticket has been created.", ephemeral=True
        )


class TicketControls(discord.ui.View):
    def __init__(self, cog: "TicketCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket_controls:close",
    )
    async def close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.cog.close_ticket(interaction.channel, interaction.user)
        await interaction.followup.send("✅ Ticket closed.", ephemeral=True)

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.secondary,
        emoji="👑",
        custom_id="ticket_controls:claim",
    )
    async def claim(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.cog.claim_ticket(interaction.channel, interaction.user)
        await interaction.followup.send("✅ You claimed this ticket.", ephemeral=True)

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.blurple,
        emoji="📄",
        custom_id="ticket_controls:transcript",
    )
    async def transcript(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        path = await self.cog.save_transcript(interaction.channel)
        if path:
            await interaction.followup.send("✅ Transcript saved.", ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Failed to save transcript.", ephemeral=True
            )


class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        try:
            migrate_old_paths()
        except Exception:
            pass
        ensure_dirs()
        self.db_path = get_db_path("tickets")
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()
        self.panel_message_id: Optional[int] = None

    def _init_db(self) -> None:
        cur = self.db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE,
                user_id INTEGER,
                channel_name TEXT,
                created_at TEXT,
                closed_at TEXT,
                closed_by INTEGER,
                claimed_by INTEGER,
                status TEXT,
                transcript_path TEXT
            )
            """)
        self.db.commit()

    def _execute_sync(self, query: str, params: tuple = (), fetch: bool = False):
        cur = self.db.cursor()
        cur.execute(query, params)
        if fetch:
            rows = cur.fetchall()
        else:
            rows = None
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE")):
            self.db.commit()
        return rows

    async def _db_execute(self, query: str, params: tuple = (), fetch: bool = False):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._execute_sync, query, params, fetch
        )

    def _support_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        if SUPPORT_ROLE_ID:
            return guild.get_role(SUPPORT_ROLE_ID)
        for role in guild.roles:
            if role.permissions.manage_messages or role.name.lower() in (
                "support",
                "mod",
                "moderator",
            ):
                return role
        return None

    async def _ticket_category(
        self, guild: discord.Guild
    ) -> Optional[discord.CategoryChannel]:
        # If a category ID is configured, try to resolve it. Accept either a
        # category ID or a channel ID (channel's parent category will be used).
        if TICKET_CATEGORY_ID:
            try:
                cid = int(TICKET_CATEGORY_ID)
            except Exception:
                cid = TICKET_CATEGORY_ID

            # Try cache first
            ch = guild.get_channel(cid)
            # If it's already a CategoryChannel, return it
            if isinstance(ch, discord.CategoryChannel):
                return ch
            # If it's a Text/Voice channel inside a category, return its category
            if (
                isinstance(ch, (discord.TextChannel, discord.VoiceChannel))
                and ch.category
            ):
                return ch.category

            # Not in cache — try fetching from API
            try:
                fetched = await self.bot.fetch_channel(cid)
                if isinstance(fetched, discord.CategoryChannel):
                    return fetched
                if (
                    isinstance(fetched, (discord.TextChannel, discord.VoiceChannel))
                    and fetched.category
                ):
                    return fetched.category
            except Exception:
                pass

        # fallback: try to find a category by name hints
        for category in guild.categories:
            if "ticket" in category.name.lower() or "support" in category.name.lower():
                return category

        return None

    async def _create_ticket_for_user(
        self,
        guild: discord.Guild,
        user: discord.Member,
        origin_channel: Optional[discord.TextChannel],
    ) -> discord.TextChannel:
        now = datetime.utcnow().strftime("%y%m%d-%H%M")
        short = uuid4().hex[:6]
        name = f"ticket-{user.display_name.lower().replace(' ', '-')}-{short}"
        category = await self._ticket_category(guild)

        # (debug instrumentation removed)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }

        support_role = self._support_role(guild)
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        channel = await guild.create_text_channel(
            name,
            overwrites=overwrites,
            category=category,
            topic=f"Ticket for {user.id} • created {now}",
        )

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Hello {user.mention}, thank you for contacting support!\n"
                "A staff member will be with you shortly."
            ),
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        view = TicketControls(self)
        await channel.send(content=user.mention, embed=embed, view=view)

        await self._log_action(
            guild,
            f"Ticket created: {channel.name} by {user} "
            f"(id {user.id})",
        )

        try:
            sql = (
                "INSERT OR REPLACE INTO tickets (channel_id, user_id, "
                "channel_name, created_at, status) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            await self._db_execute(
                sql,
                (
                    channel.id,
                    user.id,
                    channel.name,
                    datetime.utcnow().isoformat(),
                    "open",
                ),
            )
        except Exception as exc:
            print("[TICKET][DB] Failed to insert ticket:", exc)

        return channel

    async def save_transcript(self, channel: discord.TextChannel) -> Optional[str]:
        try:
            ensure_dirs()
            path = get_ticket_transcript_path(channel.id)
            messages = []
            async for msg in channel.history(limit=None, oldest_first=True):
                ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                author = f"{msg.author} ({msg.author.id})"
                content = msg.content.replace("\n", " ") if msg.content else ""
                attachments = ", ".join(a.url for a in msg.attachments)
                line = f"[{ts}] {author}: {content} {attachments}\n"
                messages.append(line)

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(messages)

            await self._log_action(
                channel.guild, f"Transcript saved for {channel.name} -> {path}"
            )
            try:
                update_sql = (
                    "UPDATE tickets SET transcript_path = ? "
                    "WHERE channel_id = ?"
                )
                await self._db_execute(update_sql, (path, channel.id))
            except Exception as exc:
                print("[TICKET][DB] Failed to update transcript_path:", exc)
            return path
        except Exception:
            return None

    async def close_ticket(
        self, channel: discord.TextChannel, by: discord.Member
    ) -> None:
        await self.save_transcript(channel)
        await self._log_action(
            channel.guild,
            f"Ticket closed: {channel.name} by {by}",
        )
        try:
            close_sql = (
                "UPDATE tickets SET closed_at = ?, closed_by = ?, status = ? "
                "WHERE channel_id = ?"
            )
            await self._db_execute(
                close_sql,
                (datetime.utcnow().isoformat(), by.id, "closed", channel.id),
            )
        except Exception as exc:
            print("[TICKET][DB] Failed to update closed state:", exc)
        try:
            await channel.delete(reason=f"Ticket closed by {by}")
        except Exception:
            pass

    async def claim_ticket(
        self, channel: discord.TextChannel, by: discord.Member
    ) -> None:
        topic = channel.topic or ""
        claimed_tag = f"claimed_by={by.id}"
        if "claimed_by=" in topic:
            topic = topic.split("claimed_by=")[0]
        topic = topic.strip() + (" • " + claimed_tag)
        await channel.edit(topic=topic)
        try:
            if not channel.name.startswith("[Claimed]"):
                new_name = f"[Claimed] {channel.name}"
                await channel.edit(name=new_name)
                try:
                    await self._db_execute(
                        "UPDATE tickets SET channel_name = ? WHERE channel_id = ?",
                        (new_name, channel.id),
                    )
                except Exception as exc:
                    print("[TICKET][DB] Failed to update channel_name on claim:", exc)
        except Exception:
            pass

        await channel.send(f"👑 Ticket claimed by {by.mention}")
        await self._log_action(channel.guild, f"Ticket {channel.name} claimed by {by}")
        try:
            await self._db_execute(
                "UPDATE tickets SET claimed_by = ? WHERE channel_id = ?",
                (by.id, channel.id),
            )
        except Exception as exc:
            print("[TICKET][DB] Failed to update claimed_by:", exc)

    async def _log_action(self, guild: discord.Guild, text: str) -> None:
        if TICKET_LOG_CHANNEL_ID:
            ch = guild.get_channel(TICKET_LOG_CHANNEL_ID)
            if ch:
                await ch.send(text)
                return
        print(f"[TICKET] {text}")

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Need help? Open a ticket",
            description=("Click the button below to open a private support ticket."),
            color=discord.Color.blurple(),
        )

        view = TicketPanelView(self)
        msg = await ctx.send(embed=embed, view=view)
        self.panel_message_id = msg.id

    @commands.command(name="ticket")
    async def ticket_command(self, ctx: commands.Context) -> None:
        await ctx.message.delete()
        await self._create_ticket_for_user(ctx.guild, ctx.author, ctx.channel)
        await ctx.author.send("Your ticket was created.")

    @commands.command(name="transcript")
    @commands.has_permissions(administrator=True)
    async def transcript_cmd(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        path = await self.save_transcript(channel)
        if path and os.path.exists(path):
            await ctx.send(file=discord.File(path))
        else:
            await ctx.send("Failed to save transcript.")

    @commands.command(name="close_ticket")
    @commands.has_permissions(administrator=True)
    async def close_ticket_cmd(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        await self.close_ticket(channel, ctx.author)
        await ctx.send("Ticket closed.")


async def setup(bot: commands.Bot) -> None:
    cog = TicketCog(bot)
    await bot.add_cog(cog)
    bot.add_view(TicketPanelView(cog))
    bot.add_view(TicketControls(cog))
