from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.discord import oauth
from app.auth.service import sync_user_and_workspaces
from app.config import get_settings
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.get("/login")
async def login(request: Request):
    return await oauth.discord.authorize_redirect(request, settings.discord_redirect_uri)


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.discord.authorize_access_token(request)
    discord_user = (await oauth.discord.get("users/@me", token=token)).json()
    guilds = (await oauth.discord.get("users/@me/guilds", token=token)).json()

    user = sync_user_and_workspaces(db, discord_user, guilds)
    request.session["user_id"] = user.id

    return RedirectResponse(url=settings.frontend_origin)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}
