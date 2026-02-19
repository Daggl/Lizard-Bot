from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import aiohttp


async def generate_rank_card(
    member,
    level,
    xp,
    voice_minutes,
    messages,
    achievements
):

    width = 800
    height = 250

    image = Image.new("RGB", (width, height), (20, 20, 30))
    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default()

    draw.text((20, 20), f"{member.name}", font=font)
    draw.text((20, 60), f"Level: {level}", font=font)
    draw.text((20, 90), f"XP: {xp}", font=font)
    draw.text((20, 120), f"Voice: {voice_minutes} min", font=font)
    draw.text((20, 150), f"Messages: {messages}", font=font)
    draw.text((20, 180), f"Achievements: {achievements}", font=font)

    buffer = BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)

    return buffer
