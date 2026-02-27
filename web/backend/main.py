import json
import os
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import (Depends, FastAPI, File, Header, HTTPException, Query,
                     Request, UploadFile)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
# Load .env from repository root to ensure variables are available
# Force override=True so root .env takes precedence over any other env files
load_dotenv(dotenv_path=ROOT / ".env", override=True)

# Ensure fonts exist in web/backend/fonts; download basic fonts if missing
FONTS_DIR = ROOT / "web" / "backend" / "fonts"


def ensure_fonts():
    # Only ensure the local fonts directory exists. No network downloads.
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Using local fonts only; no remote font downloads will be attempted.")


ensure_fonts()
DATA_DIR = ROOT / "data" / "web"
CONFIG_DIR = DATA_DIR / "configs"
UPLOAD_DIR = DATA_DIR / "uploads"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Bot Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def internal_auth(token: Optional[str] = Header(None, alias="X-INTERNAL-TOKEN")):
    """Simple internal token check. Header: X-INTERNAL-TOKEN

    If `WEB_INTERNAL_TOKEN` is not set the check is skipped (development).
    """
    expected = os.getenv("WEB_INTERNAL_TOKEN")
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


@app.get("/api/ping")
async def ping():
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/config")
async def get_config(guild_id: int):
    path = CONFIG_DIR / f"{guild_id}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="failed to read config")


@app.get("/api/guilds/{guild_id}/channels")
async def get_guild_channels(guild_id: int, authorized: bool = Depends(internal_auth)):
    """
    Return guild channels using the bot token.
    Requires internal token (internal API).
    """
    bot_token = os.getenv("DISCORD_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="bot token not configured")
    async with httpx.AsyncClient() as client:
        url = f"https://discord.com/api/guilds/{guild_id}/channels"
        resp = await client.get(url, headers={"Authorization": f"Bot {bot_token}"})
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"failed to fetch channels: {resp.status_code}",
            )
        return resp.json()


@app.get("/api/guilds/{guild_id}/roles")
async def get_guild_roles(guild_id: int, authorized: bool = Depends(internal_auth)):
    """
    Return guild roles using the bot token.
    Requires internal token (internal API).
    """
    bot_token = os.getenv("DISCORD_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="bot token not configured")
    async with httpx.AsyncClient() as client:
        url = f"https://discord.com/api/guilds/{guild_id}/roles"
        resp = await client.get(url, headers={"Authorization": f"Bot {bot_token}"})
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502, detail=f"failed to fetch roles: {resp.status_code}"
            )
        return resp.json()


@app.get("/api/guilds/{guild_id}/channels-user")
async def get_guild_channels_user(guild_id: int, request: Request):
    """
    Attempt to fetch channels using the dashboard_access_token cookie
    (user token).

    Note: Discord may not allow user tokens for this endpoint; this is a
    best-effort fallback and may return 403. The preferred method is to use
    the bot token endpoints above.
    """
    token = request.cookies.get("dashboard_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")
    async with httpx.AsyncClient() as client:
        url = f"https://discord.com/api/guilds/{guild_id}/channels"
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"failed to fetch channels with user token: {resp.status_code}",
            )
        return resp.json()


@app.post("/api/guilds/{guild_id}/preview")
async def generate_preview(
    guild_id: int,
    data: dict = None,
    authorized: bool = Depends(internal_auth),
):
    """Generate a PNG preview for the given guild config.

    Accepts either JSON body with config fields or will read saved config file.
    Returns PNG image bytes.
    """
    # load config from body or saved file
    cfg = data
    if not cfg:
        path = CONFIG_DIR / f"{guild_id}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="config not found")
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raise HTTPException(status_code=500, detail="failed to read config")

    # Create a simple image: background + uploaded image (if any) + text
    width, height = 800, 300
    bg_color = (30, 34, 42)
    text_color = (235, 235, 235)
    im = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(im)

    # If an image path is provided, try to load from uploads
    img_path = cfg.get("image")
    if img_path:
        # expected relative path like data/web/uploads/{guild_id}/filename
        p = ROOT / img_path
        try:
            with Image.open(p) as uimg:
                uimg.thumbnail((240, 240))
                im.paste(uimg, (20, (height - uimg.height) // 2))
        except Exception:
            pass

    # Draw welcome text
    welcome = cfg.get("welcome_message", "Welcome to the server!")
    font_name = cfg.get("font", "arial")
    try:
        # Try loading a TTF from system; fallback to default
        font = ImageFont.truetype(font_name, 28)
    except Exception:
        font = ImageFont.load_default()

    text_x = 280
    draw.text(
        (text_x, 60),
        welcome,
        font=font,
        fill=text_color,
    )

    # small metadata
    channel = cfg.get("announcement_channel_id", "")
    role = cfg.get("role_id", "")
    meta = f"Channel: {channel}    Role: {role}"
    draw.text(
        (text_x, 140),
        meta,
        font=ImageFont.load_default(),
        fill=(180, 180, 180),
    )

    buf = BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.post("/api/guilds/{guild_id}/preview/save")
async def save_preview(
    guild_id: int,
    data: dict = None,
    authorized: bool = Depends(internal_auth),
):
    """Generate and save preview PNG into the guild's upload folder and return path."""
    # reuse generation logic: load cfg
    cfg = data
    if not cfg:
        path = CONFIG_DIR / f"{guild_id}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="config not found")
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raise HTTPException(status_code=500, detail="failed to read config")

    # create image as in generate_preview
    width, height = 800, 300
    bg_color = (30, 34, 42)
    text_color = (235, 235, 235)
    im = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(im)

    img_path = cfg.get("image")
    if img_path:
        p = ROOT / img_path
        try:
            with Image.open(p) as uimg:
                uimg.thumbnail((240, 240))
                im.paste(uimg, (20, (height - uimg.height) // 2))
        except Exception:
            pass

    welcome = cfg.get("welcome_message", "Welcome to the server!")
    font_name = cfg.get("font", "arial")
    # try repo fonts folder first
    fonts_dir = ROOT / "web" / "backend" / "fonts"
    font = None
    try:
        ttf = fonts_dir / f"{font_name}.ttf"
        if ttf.exists():
            font = ImageFont.truetype(str(ttf), 28)
    except Exception:
        font = None
    if not font:
        try:
            font = ImageFont.truetype(font_name, 28)
        except Exception:
            font = ImageFont.load_default()

    text_x = 280
    draw.text((text_x, 60), welcome, font=font, fill=text_color)
    channel = cfg.get("announcement_channel_id", "")
    role = cfg.get("role_id", "")
    meta = f"Channel: {channel}    Role: {role}"
    draw.text((text_x, 140), meta, font=ImageFont.load_default(), fill=(180, 180, 180))

    # save to uploads
    gdir = UPLOAD_DIR / str(guild_id)
    gdir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    name = f"preview-{int(datetime.now(timezone.utc).timestamp())}.png"
    dest = gdir / name
    im.save(dest, format="PNG")
    return {"ok": True, "path": str(dest.relative_to(ROOT))}


@app.get("/api/fonts")
async def list_fonts():
    fonts_dir = ROOT / "web" / "backend" / "fonts"
    if not fonts_dir.exists():
        return {"fonts": []}
    fonts = [p.stem for p in fonts_dir.glob("*.ttf")]
    return {"fonts": fonts}


@app.post("/api/guilds/{guild_id}/config")
async def save_config(
    guild_id: int,
    data: dict,
    authorized: bool = Depends(internal_auth),
):
    path = CONFIG_DIR / f"{guild_id}.json"
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"ok": True}
    except Exception:
        raise HTTPException(status_code=500, detail="failed to save config")


@app.post("/api/guilds/{guild_id}/upload")
async def upload_file(
    guild_id: int,
    file: UploadFile = File(...),
    authorized: bool = Depends(internal_auth),
):
    # Save uploads per-guild
    gdir = UPLOAD_DIR / str(guild_id)
    gdir.mkdir(parents=True, exist_ok=True)
    dest = gdir / file.filename
    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                fh.write(chunk)
        return {"ok": True, "path": str(dest.relative_to(ROOT))}
    except Exception:
        raise HTTPException(status_code=500, detail="upload failed")


@app.get("/api/guilds/{guild_id}/uploads/{filename}")
async def get_upload(
    guild_id: int,
    filename: str,
):
    path = UPLOAD_DIR / str(guild_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)


@app.get("/auth/login")
async def auth_login(
    state: Optional[str] = Query(None),
):
    """
    Redirect the user to Discord OAuth2 authorization page.

    Requires environment variables:
    `DISCORD_CLIENT_ID` and `OAUTH_REDIRECT_URI` (optional).
    """
    client_id = os.getenv("DISCORD_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="DISCORD_CLIENT_ID not configured")

    redirect_uri = (
        os.getenv("OAUTH_REDIRECT_URI") or "http://127.0.0.1:8000/auth/callback"
    )
    scope = "identify guilds"
    # frontend may supply a state value to validate the callback
    state = state or ""
    base = "https://discord.com/api/oauth2/authorize?response_type=code"
    url = (
        base
        + f"&client_id={client_id}"
        + f"&scope={quote(scope)}"
        + f"&redirect_uri={quote(redirect_uri)}"
        + f"&state={quote(state)}"
    )
    return RedirectResponse(url)


@app.get("/auth/callback")
async def auth_callback(
    code: str = Query(None),
):
    """Exchange authorization code for an access token and return the user's guilds.

    This is a minimal implementation for the dashboard MVP. In production the
    backend should store the token server-side and issue a session cookie.
    """
    if not code:
        raise HTTPException(status_code=400, detail="missing code")

    client_id = os.getenv("DISCORD_CLIENT_ID")
    client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    redirect_uri = (
        os.getenv("OAUTH_REDIRECT_URI") or "http://127.0.0.1:8000/auth/callback"
    )

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="OAuth client not configured")

    token_url = "https://discord.com/api/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502, detail=f"token exchange failed: {resp.status_code}"
            )
        token_json = resp.json()

        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="no access_token returned")

        # fetch user guilds
        guilds_resp = await client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if guilds_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"failed to fetch guilds: {guilds_resp.status_code}",
            )

        # guilds are not used here; token is stored in a cookie and frontend
        # will fetch guilds via `/auth/me` when needed

    # Store the access token in a HttpOnly cookie so the frontend can use authenticated
    # requests via the browser without exposing the token to JS.
    secure_flag = os.getenv("APP_ENV") == "production" or os.getenv(
        "APP_ORIGIN", ""
    ).startswith("https")
    redirect_target = (
        os.getenv("APP_ORIGIN", "http://127.0.0.1:5174") + "/oauth-success"
    )

    # Set cookie and then redirect the browser to the frontend success page.
    resp = RedirectResponse(url=redirect_target)
    resp.set_cookie(
        "dashboard_access_token",
        access_token,
        httponly=True,
        samesite="lax",
        secure=secure_flag,
        max_age=3600,
        path="/",
    )
    return resp


@app.get("/auth/me")
async def auth_me(request: Request):
    """Return current user's guilds using the `dashboard_access_token` cookie.

    Frontend should call this endpoint after the browser was redirected back
    from `/auth/callback` so the cookie is present.
    """
    token = request.cookies.get("dashboard_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")

    async with httpx.AsyncClient() as client:
        guilds_resp = await client.get(
            "https://discord.com/api/users/@me/guilds",
            headers={"Authorization": f"Bearer {token}"},
        )
        if guilds_resp.status_code != 200:
            raise HTTPException(
                status_code=502, detail=f"failed to fetch guilds: {guilds_resp.text}"
            )
        guilds = guilds_resp.json()

    return {"guilds": guilds}


if __name__ == "__main__":
    import uvicorn

    # bind to all interfaces so localhost resolves on IPv4 and IPv6
    # Use the module path when enabling reload so the reloader can import the app.
    # If you prefer to run the file directly, set reload=False.
    uvicorn.run("web.backend.main:app", host="0.0.0.0", port=8000, reload=True)
