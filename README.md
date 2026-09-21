# Glonk Backlog Manager

Glonk Backlog Manager is a shared video game backlog tracker for a Discord friend group.
Track each game as backlog, playing, completed, wishlist, or dropped. Tag a game as
"recommended by [friend]" from the web app or with the `/recommend` command in Discord.
Each Discord server that adds the bot gets its own workspace.

The stack is free end to end:
- FastAPI backend, with SQLite for local development and Postgres for production.
- React and Vite frontend.
- IGDB, through Twitch's developer console, for game data.
- Discord OAuth2 for login.
- A small discord.py bot for server setup and the `/recommend` command.
- Render and Neon for hosting.

## Project layout

- `backend/`: the FastAPI API and the Discord bot process (`bot/`). Python dependencies are
  managed with `uv` and `pyproject.toml`.
- `frontend/`: the React and TypeScript app (Vite, Framer Motion, dnd-kit, TanStack Query).

## Prerequisites

- Python 3.11 or later, and [uv](https://docs.astral.sh/uv/). Install uv with `pip install uv`
  if you do not have it.
- Node.js 20 or later, and npm.

## Local setup

### 1. Backend

Run these commands:
```
cd backend
uv sync --extra dev
cp .env.example .env
```

Open `.env` and set these values:
- `SESSION_SECRET`: any random string. Generate one with
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET`: create a free app at
  https://dev.twitch.tv/console/apps/create. Use any name. Set the OAuth Redirect URL to
  `http://localhost`. Set the Category to "Application Integration". This app is only for
  IGDB's login step. It does not use your Twitch account or stream anything.
- `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET`: get these from a Discord application at
  https://discord.com/developers/applications, on the OAuth2 page.
- `DISCORD_BOT_TOKEN`: get this from the same Discord application, on the Bot page. Click
  Reset Token to reveal it.
- Leave `DATABASE_URL` at its default value. This uses a local SQLite file.

Start the backend:
```
uv run uvicorn app.main:app --reload
```
Check it is running at http://localhost:8000/api/health.

### 2. Frontend

Open a second terminal and run:
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The frontend sends `/api` requests to the backend automatically.

### 3. Discord bot

Open a third terminal, once `DISCORD_BOT_TOKEN` is set, and run:
```
cd backend
uv run python -m bot.main
```
Keep this running. It handles new server setup and the `/recommend` command. It is a separate
process from the web backend.

## Tests

Run the backend test suite with:
```
cd backend
uv run pytest
```

## Deployment

Deployment uses two free services, defined in `render.yaml` at the repo root:
- **`glonk-web`**: the FastAPI backend and the built frontend, served from one URL. A free
  Render web service sleeps after 15 minutes with no HTTP traffic. The next visit takes about
  30 to 60 seconds to wake it up. This is fine for a page load.
- **`glonk-bot`**: the Discord bot process. It stays connected to Discord at all times. It also
  runs a small `/health` endpoint. This endpoint meets Render's port requirement, and gives a
  free external monitor something to check. Without this, a sleeping bot would disconnect from
  Discord and would not reconnect on its own, because Discord never sends it a request to wake
  it up.

### Step 1: create a database on Neon

1. Sign up at https://neon.tech.
2. Create a project.
3. Copy the connection string. It looks like `postgresql://user:pass@host/dbname`.
4. Change `postgresql://` to `postgresql+psycopg://` at the start of the string. This repo uses
   the psycopg 3 driver. The edited string is your `DATABASE_URL`.

### Step 2: prepare the Discord redirect URL

1. Open the Discord Developer Portal, your application, and the OAuth2 page.
2. Add a second redirect URL, next to your localhost one:
   ```
   https://glonk-web.onrender.com/api/auth/callback
   ```
3. Render usually keeps the service name from `render.yaml`, so this URL is a good guess. Check
   it against the real URL after step 4, and fix it if Render picked a different name.

### Step 3: push the repo to GitHub

Render deploys from a GitHub repo. Push the code before you continue:
```
git add .
git commit -m "Initial commit"
```
Create an empty repo on GitHub, then run:
```
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

### Step 4: deploy on Render

1. Sign up at https://render.com and connect your GitHub account.
2. Click **New**, then **Blueprint**. Choose the repo you pushed in step 3. Render reads
   `render.yaml` and proposes both `glonk-web` and `glonk-bot`.
3. Before the first deploy, Render asks for the environment variables marked `sync: false` in
   `render.yaml`. Set these:

   **glonk-web:**
   - `DATABASE_URL`: the Neon string from step 1.
   - `SESSION_SECRET`: generate a new one. Do not reuse your local dev secret. Use
     `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`: the same values as your local `.env`.
   - `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`: the same values as your local `.env`.
   - `DISCORD_REDIRECT_URI`: the URL from step 2.
   - `FRONTEND_ORIGIN`: the `glonk-web` URL itself. The frontend and backend share one origin
     in production.

   **glonk-bot:**
   - `DATABASE_URL`: the same Neon string.
   - `DISCORD_BOT_TOKEN`: the same value as your local `.env`.
   - `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`: the same values as your local `.env`.
4. Deploy. The `glonk-web` start command runs `alembic upgrade head` before it starts the
   server. This sets up the Neon database schema on the first deploy automatically.
5. Go back to Discord's OAuth2 page. Confirm the redirect URL matches the real `glonk-web` URL
   that Render assigned. Update it if they differ.

### Step 5: keep the bot alive with a free monitor

Render's free tier stops `glonk-bot` after 15 minutes with no HTTP traffic. Set up a free
monitor at https://uptimerobot.com, or a similar service, to check
`https://<your-glonk-bot-url>.onrender.com/health` every 5 to 10 minutes. The bot reconnects to
Discord each time it restarts, so this check keeps it from fully sleeping. Only `glonk-bot`
needs this. It is fine for `glonk-web` to sleep between visits.

### Step 6: test the live app

1. Open the `glonk-web` URL and log in with Discord. Confirm your workspace appears.
2. In your Discord server, run `/recommend` and confirm the bot responds.

## Git

This repo is set up with git, but nothing is committed automatically. The repo owner manages
all commits and pushes.
