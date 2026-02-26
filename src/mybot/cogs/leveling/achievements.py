from discord.ext import commands

from mybot.cogs.leveling.utils.level_config import (get_achievement_channel_id,
                                                    get_achievements,
                                                    get_message_templates)


class Achievements(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_achievements(self, member):

        db = self.bot.db
        user = db.get_user(member.id)

        for name, req in get_achievements().items():

            if name in user["achievements"]:
                continue

            valid = True

            for key, value in req.items():
                if user[key] < value:
                    valid = False

            if valid:
                user["achievements"].append(name)

                channel = self.bot.get_channel(get_achievement_channel_id())
                if channel:
                    try:
                        _, achievement_tpl, _win_emoji, _heart_emoji = get_message_templates()
                        msg = str(achievement_tpl).format(
                            member_mention=member.mention,
                            member_name=getattr(member, "name", member.display_name),
                            member_display_name=member.display_name,
                            member_id=member.id,
                            guild_name=getattr(getattr(member, "guild", None), "name", ""),
                            achievement_name=name,
                        )
                    except Exception:
                        msg = f"🏆 {member.mention} got Achievement **{name}**"
                    await channel.send(
                        msg
                    )

        db.save()


async def setup(bot):
    await bot.add_cog(Achievements(bot))
