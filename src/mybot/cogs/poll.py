import discord
from discord.ext import commands
import json
import os
import uuid
import asyncio
from mybot.utils.jsonstore import safe_load_json, safe_save_json

DATA_FOLDER = "data"
DATA_FILE = os.path.join(DATA_FOLDER, "polls.json")


def load_polls():
    return safe_load_json(DATA_FILE, default={})


def save_polls(data):
    safe_save_json(DATA_FILE, data)


class PollView(discord.ui.View):
    def __init__(self, poll_id):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.add_buttons()

    def add_buttons(self):
        polls = load_polls()
        poll = polls[self.poll_id]

        for index, option in enumerate(poll["options"]):
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.primary,
                custom_id=f"poll_{self.poll_id}_{index}"
            )
            button.callback = self.vote_callback(index)
            self.add_item(button)

        close_button = discord.ui.Button(
            label="🔒 Close",
            style=discord.ButtonStyle.danger,
            custom_id=f"close_{self.poll_id}"
        )
        close_button.callback = self.close_poll
        self.add_item(close_button)

    def vote_callback(self, index):
        async def callback(interaction: discord.Interaction):
            polls = load_polls()
            poll = polls[self.poll_id]
            user_id = str(interaction.user.id)

            if poll["closed"]:
                await interaction.response.send_message("❌ This poll is closed.", ephemeral=True)
                return

            if user_id in poll["votes"]:
                await interaction.response.send_message("❌ You have already voted!", ephemeral=True)
                return

            poll["votes"][user_id] = index
            save_polls(polls)

            await interaction.response.send_message("✅ Vote counted!", ephemeral=True)
            await self.update_message(interaction.message)

        return callback

    async def close_poll(self, interaction: discord.Interaction):
        polls = load_polls()
        poll = polls[self.poll_id]
        poll["closed"] = True
        save_polls(polls)

        await interaction.response.send_message("🔒 Poll has been closed.", ephemeral=True)
        await self.update_message(interaction.message)

    async def update_message(self, message):
        polls = load_polls()
        poll = polls[self.poll_id]

        total_votes = len(poll["votes"])
        results = [0] * len(poll["options"])

        for vote in poll["votes"].values():
            results[vote] += 1

        description = ""

        for i, option in enumerate(poll["options"]):
            count = results[i]
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            bar = "█" * int(percentage / 10)
            description += f"**{option}**\n{bar} {percentage:.1f}% ({count})\n\n"

        if poll["closed"]:
            description += "\n🔒 **Closed**"

        embed = discord.Embed(
            title=f"📊 {poll['question']}",
            description=description,
            color=discord.Color.green()
        )

        embed.set_footer(text=f"Votes: {total_votes}")

        await message.edit(embed=embed)


class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="poll")
    async def poll(self, ctx):

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("📝 What is the question?")
        try:
            question_msg = await self.bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("❌ Time's up.")

        question = question_msg.content

        await ctx.send("⏳ How many seconds should the poll run?")
        try:
            time_msg = await self.bot.wait_for("message", timeout=60, check=check)
            duration = int(time_msg.content)
        except:
            return await ctx.send("❌ Invalid time.")

        await ctx.send("📊 Please send the answer options separated by `,`.")
        try:
            options_msg = await self.bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("❌ Time's up.")

        options = [o.strip() for o in options_msg.content.split(",") if o.strip()]

        if len(options) < 2:
            return await ctx.send("❌ At least 2 options are required.")

        poll_id = str(uuid.uuid4())
        polls = load_polls()

        polls[poll_id] = {
            "question": question,
            "options": options,
            "votes": {},
            "closed": False
        }

        save_polls(polls)

        embed = discord.Embed(
            title=f"📊 {question}",
            description="No votes yet.",
            color=discord.Color.green()
        )

        view = PollView(poll_id)
        message = await ctx.send(embed=embed, view=view)

        await asyncio.sleep(duration)

        polls = load_polls()
        if not polls[poll_id]["closed"]:
            polls[poll_id]["closed"] = True
            save_polls(polls)
            await view.update_message(message)

    @commands.command(name="delete_poll")
    @commands.has_permissions(administrator=True)
    async def delete_poll(self, ctx, poll_id: str):
        polls = load_polls()

        if poll_id not in polls:
            return await ctx.send("❌ Poll ID not found.")

        del polls[poll_id]
        save_polls(polls)

        await ctx.send("🗑 Poll removed from database.")

    async def cog_load(self):
        polls = load_polls()
        for poll_id in polls:
            self.bot.add_view(PollView(poll_id))


async def setup(bot):
    await bot.add_cog(Poll(bot))
