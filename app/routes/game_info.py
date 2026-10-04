import os

from fastapi import APIRouter

from app import rules

router = APIRouter()


@router.get("/game-info")
def game_info():
    return {
        "slug": "reach-for-the-stars",
        "name": "Reach for the Stars",
        "team": os.getenv("TEAM_NAME", "Team 5 (BSCS 3-_)"),   # set TEAM_NAME in .env
        "description": "Answer trivia questions, collect stars, open mystery chests, "
                       "and climb the leaderboard.",
        "min_players": rules.MIN_PLAYERS,
        "max_players": rules.MAX_PLAYERS,
        "thumbnail_url": "/games/reach-for-the-stars/thumbnail.png",
        "play_url": "/games/reach-for-the-stars/",
        "version": "1.0.0",
    }
