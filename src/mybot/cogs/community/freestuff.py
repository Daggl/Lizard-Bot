"""Free Stuff cog — posts free game / software giveaways from various sources.

Sources are toggleable per guild via freestuff.json config.
Supported sources: Epic Games, Steam, GOG, Humble Bundle, misc.
"""

import asyncio
import datetime
import traceback

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from mybot.utils.config import load_cog_config
from mybot.utils.i18n import translate
from mybot.utils.jsonstore import safe_load_json, safe_save_json
from mybot.utils.paths import guild_data_path

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _cfg(guild_id: int | str | None = None) -> dict:
    try:
        return load_cog_config("freestuff", guild_id=guild_id) or {}
    except Exception:
        return {}


def _channel_id(guild_id: int | str | None = None) -> int:
    try:
        return int(_cfg(guild_id).get("CHANNEL_ID", 0) or 0)
    except Exception:
        return 0


def _source_enabled(guild_id: int | str | None, source: str) -> bool:
    """Check if a specific free-stuff source is enabled for a guild."""
    cfg = _cfg(guild_id)
    return bool(cfg.get(f"SOURCE_{source.upper()}", True))


def _all_sources(guild_id: int | str | None = None) -> dict[str, bool]:
    """Return dict of source_key -> enabled for all sources."""
    cfg = _cfg(guild_id)
    return {
        "epic": bool(cfg.get("SOURCE_EPIC", True)),
        "steam": bool(cfg.get("SOURCE_STEAM", True)),
        "gog": bool(cfg.get("SOURCE_GOG", True)),
        "humble": bool(cfg.get("SOURCE_HUMBLE", True)),
        "misc": bool(cfg.get("SOURCE_MISC", True)),
    }


# ---------------------------------------------------------------------------
# Tracking already-posted items
# ---------------------------------------------------------------------------

def _load_posted(guild_id: int | str | None) -> list:
    path = guild_data_path(guild_id, "freestuff_data.json")
    if not path:
        return []
    data = safe_load_json(path, default={"posted": []})
    return data.get("posted", [])


def _save_posted(guild_id: int | str | None, posted: list):
    path = guild_data_path(guild_id, "freestuff_data.json")
    if path:
        # Keep only the last 200 entries to avoid unbounded growth
        safe_save_json(path, {"posted": posted[-200:]})


# ---------------------------------------------------------------------------
# RSS / API fetching (lightweight – no external library needed)
# ---------------------------------------------------------------------------

async def _fetch_epic_free_games() -> list[dict]:
    """Fetch currently free games from Epic Games Store API."""
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US"
    items = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        elements = (
            data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        for elem in elements:
            title = elem.get("title", "Unknown")
            promos = elem.get("promotions")
            if not promos:
                continue
            offers = promos.get("promotionalOffers", [])
            for offer_group in offers:
                for offer in offer_group.get("promotionalOffers", []):
                    discount = offer.get("discountSetting", {}).get("discountPercentage", 100)
                    if discount != 0:
                        continue
                    start = offer.get("startDate", "")
                    end = offer.get("endDate", "")
                    # Build a store URL slug
                    slug = ""
                    for mapping in elem.get("catalogNs", {}).get("mappings", []):
                        slug = mapping.get("pageSlug", "")
                        if slug:
                            break
                    if not slug:
                        slug = elem.get("productSlug") or elem.get("urlSlug") or ""
                    store_url = f"https://store.epicgames.com/en-US/p/{slug}" if slug else ""
                    # Thumbnail
                    image_url = ""
                    for img in elem.get("keyImages", []):
                        if img.get("type") in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail"):
                            image_url = img.get("url", "")
                            break
                    items.append({
                        "source": "Epic Games",
                        "title": title,
                        "url": store_url,
                        "image": image_url,
                        "id": f"epic:{slug or title}",
                    })
    except Exception:
        traceback.print_exc()
    return items


async def _fetch_all_sources(guild_id: int | str | None) -> list[dict]:
    """Aggregate free stuff from all enabled sources."""
    sources = _all_sources(guild_id)
    items: list[dict] = []

    if sources.get("epic"):
        items.extend(await _fetch_epic_free_games())

    # Future: add Steam, GOG, Humble, misc fetchers here.
    # They follow the same pattern: return list of dicts with
    # source, title, url, image, id keys.

    return items


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class FreeStuff(commands.Cog):
    """Posts free game / software deals to a configured channel."""

    def __init__(self, bot):
        self.bot = bot
        self.check_free_stuff.start()

    def cog_unload(self):
        self.check_free_stuff.cancel()

    # ------------------------------------------------------------------
    # /freestuff — manual trigger
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="freestuff", description="Check for current free games/offers now.")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def freestuff_cmd(self, ctx: commands.Context):
        """Manually trigger a free stuff check for the current guild."""
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        if guild_id is None:
            await ctx.send("❌ This command must be used in a server.")
            return

        channel_id = _channel_id(guild_id)
        if not channel_id:
            await ctx.send(translate(
                "freestuff.error.no_channel", guild_id=guild_id,
                default="❌ No free stuff channel configured. Set CHANNEL_ID in freestuff config.",
            ))
            return

        await ctx.send(translate(
            "freestuff.msg.checking", guild_id=guild_id,
            default="🔍 Checking for free stuff...",
        ))
        count = await self._check_guild(ctx.guild)
        await ctx.send(translate(
            "freestuff.msg.check_done", guild_id=guild_id,
            default="✅ Check complete. {count} new item(s) posted.",
            count=count,
        ))

    # ------------------------------------------------------------------
    # /freestuffsources — show enabled sources
    # ------------------------------------------------------------------

    @commands.hybrid_command(name="freestuffsources", description="Show which free stuff sources are enabled.")
    async def freestuffsources(self, ctx: commands.Context):
        guild_id = getattr(getattr(ctx, "guild", None), "id", None)
        sources = _all_sources(guild_id)
        lines = []
        for key, enabled in sources.items():
            icon = "✅" if enabled else "❌"
            lines.append(f"{icon} **{key.title()}**")
        embed = discord.Embed(
            title=translate("freestuff.sources.title", guild_id=guild_id,
                            default="🎁 Free Stuff Sources"),
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------
    # Automated loop
    # ------------------------------------------------------------------

    @tasks.loop(hours=6)
    async def check_free_stuff(self):
        """Periodically check all guilds for free stuff."""
        for guild in self.bot.guilds:
            try:
                await self._check_guild(guild)
            except Exception as exc:
                print(f"[FreeStuff] Error checking guild {guild.id}: {exc}")
            await asyncio.sleep(2)  # small delay between guilds

    @check_free_stuff.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def _check_guild(self, guild: discord.Guild) -> int:
        """Check and post free stuff for a single guild. Returns count of new items posted."""
        guild_id = guild.id
        channel_id = _channel_id(guild_id)
        if not channel_id:
            return 0

        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            channel = guild.get_channel(int(channel_id))
        if channel is None:
            return 0

        items = await _fetch_all_sources(guild_id)
        posted = _load_posted(guild_id)
        posted_set = set(posted)
        new_count = 0

        for item in items:
            item_id = item.get("id", "")
            if not item_id or item_id in posted_set:
                continue

            embed = discord.Embed(
                title=f"🎁 {item.get('title', 'Free!')}",
                description=f"**Source:** {item.get('source', 'Unknown')}\n\n"
                            f"[Get it here!]({item.get('url', '')})" if item.get("url") else "",
                color=discord.Color.green(),
                url=item.get("url", ""),
            )
            if item.get("image"):
                embed.set_image(url=item["image"])

            try:
                await channel.send(embed=embed)
                posted.append(item_id)
                posted_set.add(item_id)
                new_count += 1
            except Exception as exc:
                print(f"[FreeStuff] Failed to post item {item_id}: {exc}")

        if new_count:
            _save_posted(guild_id, posted)

        return new_count


async def setup(bot):
    await bot.add_cog(FreeStuff(bot))
