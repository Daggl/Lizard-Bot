import discord
from discord.ext import commands

from .utils.level_config import get_level_rewards


class Rewards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def check_rewards(self, member):
        guild_id = getattr(getattr(member, 'guild', None), 'id', None)

        user = self.bot.db.get_user(member.id, guild_id=guild_id)
        level = user["level"]
        level_rewards = get_level_rewards(guild_id=guild_id)

        if level not in level_rewards:
            return

        current_reward = level_rewards[level]

        # Resolve the target role — prefer role_id, fall back to name
        role = None
        if isinstance(current_reward, dict):
            role_id = current_reward.get("role_id")
            role_name = current_reward.get("name", "")
            if role_id:
                role = member.guild.get_role(int(role_id))
            if role is None and role_name:
                role = discord.utils.get(member.guild.roles, name=role_name)
        else:
            # Legacy string format
            role = discord.utils.get(member.guild.roles, name=str(current_reward))

        if role is None:
            return

        # Collect all reward roles that are LOWER level than the current one
        # so we can remove them (auto role upgrade)
        roles_to_remove = []
        for rw_level, rw_data in level_rewards.items():
            if rw_level >= level:
                continue  # Only remove lower-level rewards
            rw_role = None
            if isinstance(rw_data, dict):
                rw_id = rw_data.get("role_id")
                rw_name = rw_data.get("name", "")
                if rw_id:
                    rw_role = member.guild.get_role(int(rw_id))
                if rw_role is None and rw_name:
                    rw_role = discord.utils.get(member.guild.roles, name=rw_name)
            else:
                rw_role = discord.utils.get(member.guild.roles, name=str(rw_data))
            if rw_role and rw_role in member.roles:
                roles_to_remove.append(rw_role)

        # Remove old reward roles
        for old_role in roles_to_remove:
            try:
                await member.remove_roles(old_role)
            except (discord.Forbidden, discord.HTTPException) as exc:
                print(f"[Rewards] Failed to remove old role '{old_role.name}' from {member}: {exc}")

        # Add new reward role
        if role not in member.roles:
            try:
                await member.add_roles(role)
            except (discord.Forbidden, discord.HTTPException) as exc:
                print(f"[Rewards] Failed to assign role '{role.name}' to {member}: {exc}")


async def setup(bot):
    await bot.add_cog(Rewards(bot))
