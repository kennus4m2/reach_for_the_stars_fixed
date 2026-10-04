import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.errors import register_error_handlers
from app.routes import auth, game_info, gameplay, health, players, question_sets, sessions

load_dotenv()

app = FastAPI(title="Reach for the Stars API", version="1.0.0")
register_error_handlers(app)

# Hub Contract: allow CORS from the hub's address only. Set CORS_ORIGINS in .env
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# If the hub does NOT remove /games/reach-for-the-stars before forwarding to
# your port, set API_PREFIX=/games/reach-for-the-stars in .env
PREFIX = os.getenv("API_PREFIX", "").rstrip("/") + "/api/v1"

for module in (game_info, health, auth, question_sets, sessions, players, gameplay):
    app.include_router(module.router, prefix=PREFIX)

THUMBNAIL = Path(__file__).parent / "assets" / "thumbnail.png"


@app.get("/thumbnail.png", include_in_schema=False)
@app.get("/games/reach-for-the-stars/thumbnail.png", include_in_schema=False)
def thumbnail():
    """The 400 x 300 PNG that game-info points to."""
    return FileResponse(THUMBNAIL, media_type="image/png")
