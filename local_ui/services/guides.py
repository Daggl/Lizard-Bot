from PySide6 import QtWidgets

BOT_TUTORIAL_MD = """
# Lizard Bot — Beginner Guide

Welcome! This guide explains what every main area does, where settings are stored,
and what values you can safely put into each config.

## 0) Where files are located

- **Bot/UI root folder**: this project directory
- **Main config folder**: `config/`
- **Default template**: `data/config.example.json`
- **Persistent bot data**: `data/` (for example `data/levels.json`)
- **Assets (images/fonts)**: `assets/`

If a config file is missing, run startup once (`start_all.py`) so the project can create defaults.

## 1) Quick Start

1. Start the bot and UI with `start_all.py` (or `start_all.bat`).
2. Open the **Dashboard** tab and click **Refresh Status**.
3. Confirm the bot is **Ready** and cogs are loaded.
4. Configure **Welcome** and **Rank**, then click **Save + Reload**.

## 2) Dashboard (exact behavior)

- **Refresh Status**
    - Calls the control API status endpoint.
    - Updates Ready/User/Ping/Uptime/CPU/Memory/Cogs.
- **Reload Cogs**
    - Reloads bot modules so changed config values are used immediately.
- **Bot Tutorial**
    - Opens this guide dialog.
- **Help commands in Discord**
    - `/help` (aliases: `/tutorial`, `/hilfe`) for general help.
    - `/admin_help` (aliases: `/adminhelp`, `/ahelp`) for admin controls.
- **Shutdown Bot**
    - Sends shutdown to bot and closes UI.
- **Restart Bot & UI**
    - Full restart flow (or supervised restart if launched via `start_all.py`).

## 3) Welcome Tab (new member experience)

Use this tab to design the image + text shown for new members.

- **General**: example name, banner image path, welcome text.
- **Background**: mode (`cover`, `contain`, `stretch`), zoom, X/Y offset.
- **Typography**: title/username fonts, sizes, and colors.
- **Position**: title/username/text/avatar offsets.
- **Placeholders** in message:
    - `{mention}`, `{rules_channel}`, `{verify_channel}`, `{aboutme_channel}`

Saved primarily to: `config/welcome.json`

## 4) Rank Tab (Level card + leveling messages)

Use this tab to control rank card styling and leveling announcements.

- **General/Background/Typography**: visual style of rank image.
- **Messages**:
    - **Level-up message** (embed description)
    - **Achievement message**
- Placeholder examples:
    - Level-up: `{member_mention}`, `{member_name}`, `{member_display_name}`, `{member_id}`, `{guild_name}`, `{level}`
    - Achievement: `{member_mention}`, `{member_name}`, `{member_display_name}`, `{member_id}`, `{guild_name}`, `{achievement_name}`

Saved to:
- Visual rank settings: `config/rank.json`
- Leveling text/emoji settings: `config/leveling.json`

## 5) Birthdays Tab

Use this tab to configure birthday announcements.

- **Embed title / description / footer / color**: customize the birthday announcement embed.
- **Birthday Role ID**: A role that is automatically assigned on the user's birthday and removed the next day.
- **Birthday Panel**: Use `/birthdaypanel` in Discord to post a persistent panel where users can view all saved birthdays and upcoming ones via buttons.
- **Placeholders**: `{mention}`, `{user_name}`, `{display_name}`, `{user_id}`, `{date}`

Saved to: `config/birthdays.json`

## 6) Free Stuff Tab

Use this tab to configure which free game/software sources the bot monitors.

- **Channel ID**: Where free stuff announcements are posted.
- **Sources**: Toggle Epic Games, Steam, GOG, Humble Bundle and Misc sources on/off.
- The bot checks for free items every 30 minutes automatically.
- Use `/freestuff` in Discord to manually trigger a check.

Saved to: `config/freestuff.json`

## 6a) Social Media Tab

Use this tab to configure social media notifications (Twitch, YouTube, Twitter/X).

- **Per-source settings**: Each source has its own enable toggle, Discord channel, and credentials.
- **Twitch**: Requires a Twitch App Client ID and OAuth Token. Monitors usernames for live streams.
- **YouTube**: Uses public RSS feeds. Provide YouTube Channel IDs (UCxxxx format).
- **Twitter/X**: Requires a Bearer Token (placeholder for future implementation).
- The bot checks every 5 minutes automatically.
- Use `/socialcheck` in Discord to manually trigger a check.

Saved to: `config/social_media.json`

## 5) Configs Tab (manual JSON editing)

Use this tab when you want direct control over JSON values.

- Pick a file from `config/`.
- Edit key/value pairs.
- Save, then use **Reload Cogs** (Dashboard) if runtime refresh is needed.

### Important value types

- **IDs** (channel/role/user IDs): use integers, e.g. `123456789012345678`
- **Booleans**: `true` / `false`
- **Text**: normal string
- **Arrays**: `[1, 2, 3]`

## 6) What each config file in `config/` is for

- `welcome.json` — welcome banner/message + related channel/role IDs
- `rank.json` — rank card visual styling (background/fonts/colors/offsets)
- `leveling.json` — leveling channel, emojis, level-up/achievement templates
- `autorole.json` — verification/reaction role setup
- `tickets.json` — ticket category, support role, ticket log channel
- `log_chat.json` — destination channel for chat logs
- `log_member.json` — destination channel for member join/leave logs
- `log_mod.json` — destination channel for moderation logs
- `log_server.json` — destination channel for server-level logs
- `log_voice.json` — destination channel for voice activity logs
- `count.json` — counting game channel
- `birthdays.json` — birthday channel/settings
- `freestuff.json` — free stuff channel/sources
- `social_media.json` — social media feed config (Twitch, YouTube, Twitter/X)

If you are unsure which key is required, compare with `data/config.example.json`.

## 7) Logs Tab

- Tail log files or SQLite tables to monitor behavior.
- Best place to debug startup errors, reload problems, and missing IDs.

## 8) Common mistakes and how to avoid them

- **Bot is offline in Dashboard**
    - Check token/env setup and start through `start_all.py`.
- **Config changed but bot still uses old values**
    - Click **Save + Reload** or Dashboard **Reload Cogs**.
- **No message sent in Discord**
    - Verify channel IDs in config and bot permissions in that channel.
- **Wrong placeholder text in output**
    - Use exact placeholder names (case-sensitive).

## 9) Recommended beginner workflow

1. Start via `start_all.py`.
2. Confirm Dashboard status.
3. Configure Welcome and test preview.
4. Configure Rank visuals and messages.
5. Save + Reload.
6. Validate in Discord with a test user/event (UI Event Tester prefers `UI_TEST_MEMBER_NAME`, default `leutnantbrause`).
7. Use Logs tab for any issue.

## 10) Feature test commands (admin QA)

Use this as a practical checklist to verify the bot after config changes.

- Core health: `/testping` (checks bot responsiveness and returns latency in ms)
- Welcome: `/testwelcome` (runs the real welcome flow using your own user as target)
- Rank card: `/testrank` or `/testrank @User` (renders rank image and verifies card generation)
- Leveling admin flow: `/testlevel @User 50`, `/testlevelup @User [bonus_xp]`, `/testachievement @User Veteran` (writes XP/achievement data, forces level-up output, and verifies achievement flow)
- Counting: `/testcount` (executes `/countstats` and `/counttop` to verify stats + leaderboard reads)
- Birthdays: `/testbirthday 21.08` (stores a birthday date and confirms persistence)
- Birthday panel: `/testbirthdaypanel` (posts the birthday overview panel)
- Free Stuff: `/testfreestuff` (triggers a manual free stuff check for the guild)
- Social Media: `/testsocials` (triggers a manual social media feed check for the guild)
- Polls: `/testpoll 45 Quick system check` (starts guided interactive poll wizard; test buttons/votes manually)
- Tickets: `/testticketpanel`, then `/ticket` (posts panel and validates ticket creation path)
- Music: `/testmusic` (voice smoke test: join your voice channel, then leave; requires voice dependencies such as `PyNaCl`)
- Admin messaging: `/testsay Hello world` (sends admin-formatted embed message)
- Logs: `/testlog system Test entry` (writes DB test log; also trigger real events for chat/voice/mod logs)

## 11) Quick placeholder reference

- Welcome: `{mention}`, `{rules_channel}`, `{verify_channel}`, `{aboutme_channel}`
- Leveling: `{member_mention}`, `{member_name}`, `{member_display_name}`, `{member_id}`, `{guild_name}`, `{level}`, `{achievement_name}`
"""


COMMANDS_GUIDE_MD = """
# Lizard Bot — Full Commands Reference

This list describes all currently implemented commands in this bot build.

## Prefix

Commands are prefix commands (example prefix is often `*`), unless noted as hybrid.
Hybrid commands can also be available as slash commands depending on sync/setup.

## Quick Test Matrix (Admin)

Use these commands as the fastest per-feature smoke test:

- Core: `/testping` — confirms command dispatch + bot heartbeat and returns latency.
- Welcome: `/testwelcome` — executes full welcome message/banner path for the command caller.
- Leveling/Rank: `/testrank @User`, `/testlevel @User 50`, `/testlevelup @User [bonus_xp]`, `/testachievement @User Demo` — validates XP write, forced level-up output, rank render, and achievement write.
- Counting: `/testcount` — validates read path of counting statistics and top users.
- Birthdays: `/testbirthday 21.08` — validates birthday save format and storage.
- Polls: `/testpoll 45 Quick check` — starts normal poll wizard to test interaction flow.
- Tickets: `/testticketpanel`, `/ticket` — validates panel posting and ticket creation path.
- Music: `/testmusic` — validates voice connect/disconnect basics (requires you in voice and voice dependencies such as `PyNaCl`).
- Utility/Admin: `/testsay Hello world`, `/adminpanel` — validates admin embed send + status panel rendering.
- Logs: `/testlog system Quick check` + real events — validates DB log write plus channel log pipelines.
- Social Media: `/testsocials` — validates social media feed check for the guild.

---

## Core

### `/ping`
- **What it does:** Checks if the bot responds.
- **Usage:** `/ping`
- **Permission:** Everyone

---

## Help

### `/help` (aliases: `/tutorial`, `/hilfe`)
- **What it does:** Opens the bot help/tutorial embed in Discord.
- **Usage:** `/help`
- **Permission:** Everyone

### `/admin_help` (aliases: `/adminhelp`, `/ahelp`)
- **What it does:** Opens administrator control/help UI.
- **Usage:** `/admin_help`
- **Permission:** Administrator

---

## Welcome

### `/testwelcome`
- **What it does:** Sends the welcome flow for the command caller (admin test).
- **Usage:** `/testwelcome`
- **Permission:** Administrator

---

## Leveling / Rank

### `/rank [member]`
- **What it does:** Shows rank card for you or the specified member.
- **Usage:** `/rank` or `/rank @User`
- **Permission:** Everyone

### `/rankuser <member>`
- **What it does:** Admin rank card command for a target member.
- **Usage:** `/rankuser @User`
- **Permission:** Administrator

### `/addxp <member> <amount>`
- **What it does:** Adds XP to a member and re-checks achievements.
- **Usage:** `/addxp @User 250`
- **Permission:** Administrator

### `/removexp <member> <amount>`
- **What it does:** Removes XP from a member (not below 0).
- **Usage:** `/removexp @User 100`
- **Permission:** Administrator

### `/reset <member>`
- **What it does:** Resets one user’s leveling stats (XP/level/messages/voice/achievements).
- **Usage:** `/reset @User`
- **Permission:** Administrator

### `/givexp <member> <amount>`
- **What it does:** Directly adds XP to a member (admin utility).
- **Usage:** `/givexp @User 150`
- **Permission:** Administrator

### `/setxp <member> <amount>`
- **What it does:** Sets a member’s XP to an exact value.
- **Usage:** `/setxp @User 500`
- **Permission:** Administrator

### `/setlevel <member> <level>`
- **What it does:** Sets a member’s level directly.
- **Usage:** `/setlevel @User 10`
- **Permission:** Administrator

### `/testachievement <member> <name>`
- **What it does:** Grants a custom achievement label for testing.
- **Usage:** `/testachievement @User Veteran`
- **Permission:** Administrator

---

## Counting

### `/countstats`
- **What it does:** Shows current counter stats.
- **Usage:** `/countstats`
- **Permission:** Everyone

### `/counttop`
- **What it does:** Shows top counting contributors.
- **Usage:** `/counttop`
- **Permission:** Everyone

### `/countreset`
- **What it does:** Resets counting data.
- **Usage:** `/countreset`
- **Permission:** Administrator

---

## Birthdays

### `/birthday <DD.MM>`
- **What it does:** Saves your birthday for reminders.
- **Usage:** `/birthday 21.08`
- **Permission:** Everyone

### `/birthdaypanel`
- **What it does:** Posts a persistent birthday overview panel with buttons to view all birthdays and upcoming ones.
- **Usage:** `/birthdaypanel`
- **Permission:** Administrator

---

## Free Stuff

### `/freestuff`
- **What it does:** Manually triggers a free stuff check for the current guild.
- **Usage:** `/freestuff`
- **Permission:** Administrator

### `/freestuffsources`
- **What it does:** Shows which free stuff sources are enabled for the guild.
- **Usage:** `/freestuffsources`
- **Permission:** Everyone

---

## Social Media

### `/socialcheck`
- **What it does:** Manually triggers a social media feed check for the current guild.
- **Usage:** `/socialcheck`
- **Permission:** Administrator

### `/socialsources`
- **What it does:** Shows configured social media sources and their status.
- **Usage:** `/socialsources`
- **Permission:** Everyone

---

## Polls

### `/poll`
- **What it does:** Starts an interactive poll setup (question, duration, options).
- **Usage:** `/poll`
- **Permission:** Everyone

### `/delete_poll <poll_id>`
- **What it does:** Deletes a saved poll by ID.
- **Usage:** `/delete_poll <id>`
- **Permission:** Administrator

---

## Tickets

### `/ticketpanel`
- **What it does:** Posts the ticket panel with open-ticket button.
- **Usage:** `/ticketpanel`
- **Permission:** Administrator

### `/ticket`
- **What it does:** Creates a support ticket for the caller.
- **Usage:** `/ticket`
- **Permission:** Everyone

### `/transcript <#channel>`
- **What it does:** Exports a transcript file for a ticket channel.
- **Usage:** `/transcript #ticket-channel`
- **Permission:** Administrator

### `/close_ticket <#channel>`
- **What it does:** Closes a ticket channel.
- **Usage:** `/close_ticket #ticket-channel`
- **Permission:** Administrator

---

## Music (hybrid where noted)

### `/join` (hybrid)
- **What it does:** Bot joins your current voice channel.
- **Usage:** `/join`

### `/leave` (hybrid)
- **What it does:** Leaves voice and clears queue.
- **Usage:** `/leave`

### `/play <query|url>` (hybrid)
- **What it does:** Queues/plays from YouTube URL or search query.
- **Usage:** `/play never gonna give you up`

### `/spotify <url> [max_tracks]` (hybrid)
- **What it does:** Imports Spotify track/playlist into queue.
- **Usage:** `/spotify <spotify_url> 25`
- **Note:** Requires Spotify client credentials in environment.

### `/skip` (hybrid)
- **What it does:** Skips the current track.
- **Usage:** `/skip`

### `/queue` (hybrid)
- **What it does:** Shows current queue.
- **Usage:** `/queue`

### `/now` (hybrid)
- **What it does:** Shows current track.
- **Usage:** `/now`

### `/stop` (hybrid)
- **What it does:** Stops playback, disconnects, clears queue.
- **Usage:** `/stop`

---

## Utility / Messaging

### `/say <text> [| image_url]`
- **What it does:** Sends a styled embed message as admin tool.
- **Usage:** `/say Hello world` or `/say Hello | https://.../image.png`
- **Permission:** Administrator

### `/adminpanel`
- **What it does:** Opens the live admin status panel message.
- **Usage:** `/adminpanel`
- **Permission:** Administrator

---

## Admin Test Commands

### `/testping`
- **What it does:** Runs a lightweight bot health check and prints measured websocket latency.
- **Usage:** `/testping`
- **Permission:** Administrator

### `/testrank [member]`
- **What it does:** Calls rank rendering for yourself or a target user to validate image generation and rank data read.
- **Usage:** `/testrank` or `/testrank @User`
- **Permission:** Administrator

### `/testcount`
- **What it does:** Executes counting summary and top list commands to verify stored counting data can be read correctly.
- **Usage:** `/testcount`
- **Permission:** Administrator

### `/testbirthday [DD.MM]`
- **What it does:** Writes a birthday date for the caller (or today if omitted) and confirms persistence command output.
- **Usage:** `/testbirthday 21.08`
- **Permission:** Administrator

### `/testbirthdaypanel`
- **What it does:** Posts the birthday overview panel for testing.
- **Usage:** `/testbirthdaypanel`
- **Permission:** Administrator

### `/testfreestuff`
- **What it does:** Triggers a manual free stuff check to verify the feature works correctly.
- **Usage:** `/testfreestuff`
- **Permission:** Administrator

### `/testsocials`
- **What it does:** Triggers a manual social media feed check for the current guild.
- **Usage:** `/testsocials`
- **Permission:** Administrator

### `/testpoll [seconds] [question]`
- **What it does:** Starts the regular interactive poll flow and provides suggested input so poll UI/buttons can be tested quickly.
- **Usage:** `/testpoll 45 Quick check`
- **Permission:** Administrator

### `/testticketpanel`
- **What it does:** Posts the ticket creation panel so you can validate open-ticket button behavior end-to-end.
- **Usage:** `/testticketpanel`
- **Permission:** Administrator

### `/testmusic`
- **What it does:** Performs a minimal voice pipeline test by joining your current channel and leaving shortly after.
- **Usage:** `/testmusic`
- **Requirements:** You must be in a voice channel and voice dependencies (notably `PyNaCl`) must be installed.
- **Permission:** Administrator

### `/testsay [text]`
- **What it does:** Calls the admin `/say` flow to verify embed formatting and message dispatch permissions.
- **Usage:** `/testsay Hello world`
- **Permission:** Administrator

### `/testlevel <member> [xp]`
- **What it does:** Adds XP through the leveling system and then displays rank card for quick before/after validation.
- **Usage:** `/testlevel @User 50`
- **Permission:** Administrator

### `/testlog [category] [message]`
- **What it does:** Writes a manual test entry into the log database so storage/log tooling can be validated independently of live events.
- **Usage:** `/testlog system Quick check`
- **Permission:** Administrator

---

## Where command behavior/config comes from

- Welcome behavior: `config/welcome.json`
- Rank visuals: `config/rank.json`
- Leveling templates/channels/emojis: `config/leveling.json`
- Tickets: `config/tickets.json`
- Logging channels: `config/log_*.json`
- Birthday channel: `config/birthdays.json`
- Free stuff channel/sources: `config/freestuff.json`
- Social media feeds: `config/social_media.json`
- Counter channel/settings: `config/count.json`

If a command seems inactive, check:
1. Bot status on Dashboard
2. Correct channel/role IDs in config
3. Permissions for the bot and the user
4. Logs tab for runtime errors
"""


def _open_markdown_dialog(parent, title: str, content: str, width: int, height: int):
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(width, height)

    layout = QtWidgets.QVBoxLayout(dlg)
    guide = QtWidgets.QTextBrowser()
    guide.setOpenExternalLinks(True)
    guide.setMarkdown(content)
    layout.addWidget(guide)

    close_btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
    close_btns.rejected.connect(dlg.reject)
    close_btns.accepted.connect(dlg.accept)
    layout.addWidget(close_btns)

    dlg.exec()


def open_bot_tutorial(parent):
    _open_markdown_dialog(parent, "Lizard Bot — Beginner Guide", BOT_TUTORIAL_MD, 900, 680)


def open_commands_guide(parent):
    _open_markdown_dialog(parent, "Lizard Bot — Commands Reference", COMMANDS_GUIDE_MD, 980, 720)
