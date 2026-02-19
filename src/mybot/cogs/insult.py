import asyncio
import platform
import random

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import os

class Fun(commands.Cog, name="fun stuff"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="insult",
        description="Insult someone",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def insult(self, context: Context, name: str):
        ephem = False
        try:
            if context.guild.member_count == None:
                ephem = False
        except:
            pass  
        with open(os.path.join(os.getcwd(), 'files', 'insults.txt'), encoding='utf-8') as f:
            phrases = f.readlines()
        random_line = random.choice(phrases)

        member = context.author.id

        if "maninthewall" in name.lower() or "<@685211167047942280>" in name or "wally" in name.lower()  or "wallman" in name.lower() or "wall" in name.lower() or name == "WickedMan420" or name == "287264198470139905" or "waii" in name.lower():
            message = "You tried insulting a superior being. \n"
            random_line = random_line.replace("<name>", ("<@" + str(member) + ">"))
            message = message + random_line
        
        elif name == "@everyone" or name == "@here" or name == "@Arbinitiate":
            message = "Nice try, noob. \n"
            random_line = random_line.replace("<name>", ("<@" + str(member) + ">"))
            message = message + random_line
        else:
            random_line = random_line.replace("<name>", name)
            message = random_line

        await context.send(message, ephemeral=ephem)

    @commands.hybrid_command(
        name="secretinsult",
        description="Insult someone secretly",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def secretinsult(self, context: Context, name: str):
        with open(os.path.join(os.getcwd(), 'files', 'insults.txt'), encoding='utf-8') as f:
            phrases = f.readlines()
        random_line = random.choice(phrases)

        member = context.author.id
        
        if "maninthewall" in name.lower() or "<@685211167047942280>" in name or "wally" in name.lower()  or "wallman" in name.lower() or "wall" in name.lower() or name.lower == "WickedMan420" or name == "287264198470139905"or "waii" in name.lower():
            message = "You tried insulting a superior being. \n"
            random_line = random_line.replace("<name>", ("<@" + str(member) + ">"))
            message = message + random_line
        elif name == "@everyone" or name == "@here" or name == "@Arbinitiate":
            message = "Nice try, noob. \n"
            random_line = random_line.replace("<name>", ("<@" + str(member) + ">"))
            message = message + random_line
        else:
            random_line = random_line.replace("<name>", name)
            message = random_line

        await context.send("Done", ephemeral=True)
        await self.send_message_to_specific_channel(context.channel.id, message)

    async def send_message_to_specific_channel(self, channel_id, message):
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(message)
            print(f"Message sent to {channel.name}")
        else:
            print("Channel not found.")

async def setup(bot):
    await bot.add_cog(Fun(bot))
