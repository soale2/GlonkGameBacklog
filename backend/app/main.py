from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers import activity, auth, backlog, games, me, recommendations

settings = get_settings()

app = FastAPI(title="Glonk Backlog Manager API")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=settings.environment == "production",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(me.router)
app.include_router(games.router)
app.include_router(backlog.router)
app.include_router(activity.router)
app.include_router(recommendations.router)


# In production the frontend is built to frontend/dist and served from here,
# so Render only needs to run this one service.
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
