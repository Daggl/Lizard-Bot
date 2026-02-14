import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import datetime
import json

from data.logs import database


load_dotenv()
token = os.getenv("DISCORD_TOKEN")


handler = logging.FileHandler(
    filename="discord.log",
    encoding="utf-8",
    mode="w"
)


intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="*",
    intents=intents
)


welcome_channel_id = 1266608956659470346


@bot.event
async def on_ready():

    database.setup()

    print(f"{bot.user.name} ist online!")


@bot.command()
async def ping(ctx):

    await ctx.send("🏓 Pong! Alles Fit im Schritt!")


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    await bot.process_commands(message)


async def main():

    if not token:

        print(
            "DISCORD_TOKEN nicht gesetzt. "
            "Lege eine .env mit DISCORD_TOKEN=... an."
        )

        return


    async with bot:


        try:
            await bot.load_extension("cogs.birthdays")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.welcome")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.poll")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.leveling.levels")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.leveling.rank")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.leveling.achievements")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.leveling.rewards")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.leveling.tracking")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.help_tutorial")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.admin.admin_panel")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.admin.admin_tools")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.admin.admin_tutorial")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.count")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.log.chat_log")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.log.mod_log")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.log.member_log")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.log.voice_log")
        except Exception as e:
            print(e)


        try:
            await bot.load_extension("cogs.log.server_log")
        except Exception as e:
            print(e)


        try:

            await bot.start(token)

        except asyncio.CancelledError:

            print("Cancelled")

            raise

        except Exception:

            import traceback

            traceback.print_exc()

            await bot.close()

            raise


if __name__ == "__main__":

    asyncio.run(main())
