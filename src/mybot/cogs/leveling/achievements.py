"""Achievement checking cog — awards achievements when user stats meet requirements."""

import os
import io

import discord
from discord.ext import commands
from PIL import Image, ImageOps

from mybot.utils.paths import REPO_ROOT

from .utils.level_config import (get_achievement_channel_id,
                                 get_achievement_entries,
                                 get_message_templates)


class Achievements(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_achievements(self, member):
        guild_id = getattr(getattr(member, 'guild', None), 'id', None)

        db = self.bot.db
        user = db.get_user(member.id, guild_id=guild_id)

        unlocked: list[dict] = []

        for name, entry in get_achievement_entries(guild_id=guild_id).items():
            req = dict((entry or {}).get("requirements") or {})
            image_value = str((entry or {}).get("image", "") or "").strip()

            if name in user["achievements"]:
                continue

            valid = True

            for key, value in req.items():
                if user[key] < value:
                    valid = False
                    break

            if valid:
                user["achievements"].append(name)

                try:
                    _, achievement_tpl = get_message_templates(guild_id)
                    tpl = str(achievement_tpl or "").strip()
                    if tpl:
                        msg = tpl.format(
                            member_mention=member.mention,
                            member_name=getattr(member, "name", member.display_name),
                            member_display_name=member.display_name,
                            member_id=member.id,
                            guild_name=getattr(getattr(member, "guild", None), "name", ""),
                            achievement_name=name,
                        )
                    else:
                        msg = f"🏆 {member.mention} got Achievement **{name}**"
                except Exception:
                    msg = f"🏆 {member.mention} got Achievement **{name}**"

                unlocked.append({
                    "name": name,
                    "message": msg,
                    "image": image_value,
                })

        channel = self.bot.get_channel(get_achievement_channel_id(guild_id=guild_id))
        if channel and unlocked:
            if len(unlocked) == 1:
                item = unlocked[0]
                image_value = str(item.get("image", "") or "").strip()
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
                                with Image.open(abs_path) as img:
                                    fixed = ImageOps.exif_transpose(img).convert("RGB")
                                    buf = io.BytesIO()
                                    fixed.save(buf, format="PNG")
                                    buf.seek(0)
                                image_file = discord.File(buf, filename="achievement.png")
                            except Exception:
                                image_file = None

                if image_url or image_file is not None:
                    embed = discord.Embed(description=item.get("message", ""), color=0xF1C40F)
                    if image_url:
                        embed.set_image(url=image_url)
                        await channel.send(embed=embed)
                    else:
                        embed.set_image(url="attachment://achievement.png")
                        await channel.send(embed=embed, file=image_file)
                else:
                    await channel.send(item.get("message", ""))
            else:
                names = "\n".join(f"• {item.get('name', '')}" for item in unlocked[:15])
                extra = len(unlocked) - 15
                if extra > 0:
                    names += f"\n• +{extra} more"
                summary = discord.Embed(
                    title="🏆 Achievements unlocked",
                    description=f"{member.mention} unlocked **{len(unlocked)}** achievements:\n\n{names}",
                    color=0xF1C40F,
                )
                await channel.send(embed=summary)

        db.save(guild_id=guild_id)


async def setup(bot):
    await bot.add_cog(Achievements(bot))
