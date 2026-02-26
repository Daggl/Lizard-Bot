import os

import discord
from discord.ext import commands

from mybot.cogs.leveling.utils.level_config import (get_achievement_channel_id,
                                                    get_achievement_entries,
                                                    get_message_templates)
from mybot.utils.paths import REPO_ROOT


class Achievements(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_achievements(self, member):

        db = self.bot.db
        user = db.get_user(member.id)

        for name, entry in get_achievement_entries().items():
            req = dict((entry or {}).get("requirements") or {})
            image_value = str((entry or {}).get("image", "") or "").strip()

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

                    image_url = ""
                    image_file = None
                    if image_value:
                        if image_value.lower().startswith(("http://", "https://")):
                            image_url = image_value
                        else:
                            abs_path = image_value
                            if not os.path.isabs(abs_path):
                                abs_path = os.path.abspath(os.path.join(REPO_ROOT, image_value))
                            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                                try:
                                    image_file = discord.File(abs_path, filename=os.path.basename(abs_path))
                                except Exception:
                                    image_file = None

                    if image_url or image_file is not None:
                        embed = discord.Embed(description=msg, color=0xF1C40F)
                        if image_url:
                            embed.set_image(url=image_url)
                            await channel.send(embed=embed)
                        else:
                            embed.set_image(url=f"attachment://{image_file.filename}")
                            await channel.send(embed=embed, file=image_file)
                    else:
                        await channel.send(msg)

        db.save()


async def setup(bot):
    await bot.add_cog(Achievements(bot))
