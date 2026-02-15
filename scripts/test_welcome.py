import asyncio
import io
import os
import sys
from types import SimpleNamespace

# ensure repo root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure imports from the cog
from cogs.welcome import welcome as welcome_mod


class DummyResponse:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self, data: bytes):
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        return DummyResponse(self._data)


async def run_test():
    # Prepare a fake member
    member = SimpleNamespace()
    member.name = "empty_voidx1234"
    member.display_avatar = SimpleNamespace()
    member.display_avatar.url = "local://avatar"

    # Load a local image to act as avatar; fall back to banner image
    avatar_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'avatar.png')
    banner_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'welcome.png')
    avatar_path = os.path.abspath(avatar_path)
    banner_path = os.path.abspath(banner_path)

    if os.path.exists(avatar_path):
        with open(avatar_path, 'rb') as f:
            data = f.read()
    elif os.path.exists(banner_path):
        with open(banner_path, 'rb') as f:
            data = f.read()
    else:
        raise FileNotFoundError("No local avatar or banner found for test.")

    # Patch aiohttp.ClientSession in the imported module to our dummy session
    welcome_mod.aiohttp.ClientSession = lambda: DummySession(data)

    cog = welcome_mod.Welcome(bot=None)

    # Prepare the exact text used in the cog (we'll reuse the same logic)
    rules = SimpleNamespace(name='rules', mention='#rules')
    about = SimpleNamespace(name='aboutme', mention='#aboutme')
    # Build the text like in cog
    text = (
        f"{member.name} 𝗃𝗎𝗌𝗍 𝖼𝗁𝖾𝖼𝗄𝖾𝖽 𝗂𝗇!\n"
        "𝗒𝗈𝗎 𝗆𝖺𝖽𝖾 𝗂𝗍 𝗍𝗈 𝗈𝗎𝗋 𝗅𝗈𝗏𝖾𝗅𝗒 𝖼𝗈𝗆𝗆𝗎𝗇𝗂𝗍𝗒!\n"
        "𝖻𝖾𝖿𝗈𝗋𝖾 𝗒𝗈𝗎 𝖿𝗅𝗈𝖺𝗍 𝖺𝗋𝗈𝗎𝗇𝖽 𝗍𝗁𝖾 𝗌𝖾𝗋𝗏𝖾𝗋, 𝗍𝖺𝗄𝖾 𝖺 𝗌𝖾𝖼 𝗍𝗈 𝗋𝖾𝖺𝖽 𝗍𝗁𝖾 "
        "#rules\n\n"
        "˚◟𝗼𝗻𝗰𝗲 𝘆𝗼𝘂 𝗿𝗲𝗮𝗱 𝘁𝗵𝗲 𝗿𝘂𝗹𝗲𝘀◞˚\n\n"
        "❀ 𝘃𝗲𝗿𝗶𝗳𝘆 𝘆𝗼𝘂𝗿𝘀𝗲𝗹𝗳 ❀\n"
        "𝗁𝖾𝖺𝖽 𝗍𝗈 #rules ⁠𝗌𝗈 𝗒𝗈𝗎 𝖼𝖺𝗇 𝗎𝗇𝗅𝗈𝖼𝗄 𝗍𝗁𝖾 𝗐𝗁𝗈𝗅𝖾 𝗌𝖾𝗋𝗏𝖾𝗋\n"
        "(𝗒𝖾𝗌, 𝖺𝗅𝗅 𝗍𝗁𝖾 𝖼𝗈𝗓𝗒 & 𝖼𝗁𝖺𝗈𝗍𝗂𝖼 𝗉𝖺𝗋𝗍𝗌)\n\n"
        "❀ 𝗶𝗻𝘁𝗿𝗼𝗱𝘂𝗰𝗲 𝘆𝗼𝘂𝗿𝘀𝗲𝗹𝗳 ❀\n"
        "𝖼𝗋𝗎𝗂𝖾 𝗈𝗏𝖾𝗋 𝗍𝗈 #aboutme 𝖺𝗇𝖽 𝗍𝖾𝗅𝗅 𝗎𝗌 𝗆𝗈𝗋𝖾 𝖺𝖻𝗈𝗎𝗍 𝗒𝗈𝗎!\n"
        "𝗐𝖾 𝗐𝖺𝗇𝗍 𝗍𝗈 𝗄𝗇𝗈𝗐 𝗐𝗁𝗈 𝗒𝗈𝗎 𝖺𝗋𝖾 𝖻𝖾𝖿𝗈𝗋𝖾 𝗐𝖾 𝖺𝖽𝗈𝗉𝗍 𝗒𝗈𝗎\n\n"
        "❀ 𝗮𝗳𝘁𝗲𝗿 𝘆𝗼𝘂 𝗵𝗮𝘃𝗲 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱 𝗮𝗹𝗹 𝘁𝗵𝗲 𝗳𝗼𝗿𝗺𝗮𝗹𝗶𝘁𝗶𝗲𝘀 ❀\n"
        "𝗀𝗈, 𝗀𝗋𝖺𝖻 𝗒𝗈𝗎𝗋 𝗌𝗇𝖺𝖼𝗄𝗌, 𝗀𝖾𝗍 𝖼𝗈𝗆𝖿𝗒 𝖺𝗇𝖽 𝖾𝗇𝗃𝗈𝗒 𝗍𝗁𝖾 𝗀𝗈𝗈𝖽 𝗏𝗂𝖻𝖾𝗌!"
    )

    # Replace mentions for image text
    image_text = text.replace(member.name, welcome_mod.clean_username(member))
    image_text = image_text.replace('#rules', '#rules')
    image_text = image_text.replace('#aboutme', '#aboutme')

    # Generate banner
    file = await cog.create_banner(member, top_text=image_text)

    # Save the generated file to disk for inspection
    out_path = os.path.join(os.path.dirname(__file__), '..', 'out_test_welcome.png')
    out_path = os.path.abspath(out_path)
    # discord.File has .fp attribute
    try:
        fp = file.fp
    except AttributeError:
        # fallback: file may be a wrapper; try to read bytes
        fp = io.BytesIO()
        file.save(fp)
        fp.seek(0)

    with open(out_path, 'wb') as f:
        f.write(fp.getvalue())

    print('Test banner written to:', out_path)
    print('\n--- Message content to send ---\n')
    print(text)


if __name__ == '__main__':
    asyncio.run(run_test())
