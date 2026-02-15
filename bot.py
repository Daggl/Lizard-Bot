# ==========================================================
# IMPORTS
# ==========================================================

import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import datetime
import json

# eigene Datenbank für Logs
from data.logs import database


# ==========================================================
# ENVIRONMENT / TOKEN LADEN
# ==========================================================

# lädt Variablen aus der .env Datei
load_dotenv()

# Discord Bot Token aus .env
token = os.getenv("DISCORD_TOKEN")


# ==========================================================
# LOGGING SETUP
# ==========================================================

# erstellt Log Datei für Discord Events / Fehler
handler = logging.FileHandler(
    filename="discord.log",
    encoding="utf-8",
    mode="w"
)


# ==========================================================
# BOT SETUP
# ==========================================================

# aktiviert alle Intents (Mitglieder, Nachrichten etc.)
intents = discord.Intents.all()

# erstellt Bot Instanz mit Prefix *
bot = commands.Bot(
    command_prefix="*",
    intents=intents
)

# Welcome Channel ID (aktuell ungenutzt in diesem Script)
welcome_channel_id = 1266608956659470346


# ==========================================================
# READY EVENT
# ==========================================================

@bot.event
async def on_ready():

    # initialisiert Datenbank
    database.setup()

    # zeigt an dass Bot online ist
    print(f"{bot.user.name} ist online!")


# ==========================================================
# TEST COMMAND
# ==========================================================

@bot.command()
async def ping(ctx):

    # einfacher Test Command um zu prüfen ob Bot reagiert
    await ctx.send("🏓 Pong! Alles Fit im Schritt!")


# ==========================================================
# MESSAGE EVENT
# ==========================================================

@bot.event
async def on_message(message):

    # verhindert dass Bot auf sich selbst reagiert
    if message.author == bot.user:
        return

    # wichtig damit Commands weiterhin funktionieren
    await bot.process_commands(message)


# ==========================================================
# MAIN FUNCTION
# ==========================================================

async def main():

    # prüft ob Token existiert
    if not token:

        print(
            "DISCORD_TOKEN nicht gesetzt. "
            "Lege eine .env mit DISCORD_TOKEN=... an."
        )

        return

    # startet Bot Kontext
    async with bot:

        # ==================================================
        # COGS LADEN
        # ==================================================

        try:
            await bot.load_extension("cogs.birthdays")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.birthdays: {e}")

        try:
            await bot.load_extension("cogs.welcome.welcome")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.welcome.welcome: {e}")

        try:
            await bot.load_extension("cogs.poll")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.poll: {e}")

        try:
            await bot.load_extension("cogs.leveling.levels")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.leveling.levels: {e}")

        try:
            await bot.load_extension("cogs.leveling.rank")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.leveling.rank: {e}")

        try:
            await bot.load_extension("cogs.leveling.achievements")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.leveling.achievements: {e}")

        try:
            await bot.load_extension("cogs.leveling.rewards")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.leveling.rewards: {e}")

        try:
            await bot.load_extension("cogs.leveling.tracking")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.leveling.tracking: {e}")

        try:
            await bot.load_extension("cogs.help_tutorial")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.help_tutorial: {e}")

        try:
            await bot.load_extension("cogs.admin.admin_panel")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.admin.admin_panel: {e}")

        try:
            await bot.load_extension("cogs.admin.admin_tools")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.admin.admin_tools: {e}")

        try:
            await bot.load_extension("cogs.admin.admin_tutorial")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.admin.admin_tutorial: {e}")

        try:
            await bot.load_extension("cogs.count")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.count: {e}")

        try:
            await bot.load_extension("cogs.log.chat_log")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.log.chat_log: {e}")

        try:
            await bot.load_extension("cogs.log.mod_log")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.log.mod_log: {e}")

        try:
            await bot.load_extension("cogs.log.member_log")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.log.member_log: {e}")

        try:
            await bot.load_extension("cogs.log.voice_log")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.log.voice_log: {e}")

        try:
            await bot.load_extension("cogs.log.server_log")
        except Exception as e:
            print(f"Fehler beim Laden von cogs.log.server_log: {e}")

        # ==================================================
        # BOT STARTEN
        # ==================================================

        try:

            # verbindet Bot mit Discord
            await bot.start(token)

        except asyncio.CancelledError:

            print("Cancelled")

            raise

        except Exception:

            import traceback

            # zeigt vollständigen Fehler an
            traceback.print_exc()

            # schließt Bot sauber
            await bot.close()

            raise


# ==========================================================
# SCRIPT START
# ==========================================================

# startet main Funktion
if __name__ == "__main__":

    asyncio.run(main())
