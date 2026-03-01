import discord
from discord import app_commands
from discord.ext import commands

from mybot.utils.i18n import translate
from mybot.utils.feature_flags import is_feature_enabled


class HelpTutorial(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        bot.remove_command("help")

    def _build_help_embed(self, guild_id: int | None) -> discord.Embed:

        embed = discord.Embed(
            title=translate("help.embed.title", guild_id=guild_id),
            description=translate("help.embed.description", guild_id=guild_id),
            color=discord.Color.blurple(),
        )

        # Each tuple: (title_key, body_key, feature_key_or_None)
        sections = (
            ("help.section.level_system.title", "help.section.level_system.body", "leveling"),
            ("help.section.polls.title", "help.section.polls.body", "polls"),
            ("help.section.birthdays.title", "help.section.birthdays.body", "birthdays"),
            ("help.section.earn_xp.title", "help.section.earn_xp.body", "leveling"),
            ("help.section.achievements.title", "help.section.achievements.body", "achievements"),
            ("help.section.general.title", "help.section.general.body", None),
            ("help.section.misc.title", "help.section.misc.body", None),
            ("help.section.counting.title", "help.section.counting.body", "counting"),
            ("help.section.tickets.title", "help.section.tickets.body", "tickets"),
            ("help.section.tempvoice.title", "help.section.tempvoice.body", "tempvoice"),
            ("help.section.music.title", "help.section.music.body", "music"),
            ("help.section.memes.title", "help.section.memes.body", "memes"),
            ("help.section.membercount.title", "help.section.membercount.body", "membercount"),
        )

        for title_key, body_key, fkey in sections:
            if fkey is not None and not is_feature_enabled(guild_id, fkey):
                continue
            embed.add_field(
                name=translate(title_key, guild_id=guild_id),
                value=translate(body_key, guild_id=guild_id),
                inline=False,
            )

        embed.set_footer(text=translate("help.embed.footer", guild_id=guild_id))

        return embed

    async def _respond_with_help_embed(self, interaction: discord.Interaction) -> None:

        guild_id = getattr(getattr(interaction, "guild", None), "id", None)
        embed = self._build_help_embed(guild_id)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @commands.command(name="help", aliases=["tutorial", "hilfe"], help="Show the help & tutorial menu.")
    async def help_prefix(self, ctx: commands.Context):

        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        await ctx.send(embed=self._build_help_embed(guild_id))

    @app_commands.command(name="help", description="Show the help & tutorial menu.")
    async def help_slash(self, interaction: discord.Interaction):

        await self._respond_with_help_embed(interaction)

    @app_commands.command(name="tutorial", description="Alias for /help.")
    async def tutorial_slash(self, interaction: discord.Interaction):

        await self._respond_with_help_embed(interaction)

    @app_commands.command(name="hilfe", description="Alias for /help.")
    async def hilfe_slash(self, interaction: discord.Interaction):

        await self._respond_with_help_embed(interaction)


async def setup(bot):

    await bot.add_cog(HelpTutorial(bot))
