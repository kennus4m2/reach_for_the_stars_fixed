"""Game rules for Reach for the Stars. Change the numbers here, nowhere else."""
import random

# Hub limits (also reported by GET /game-info)
MIN_PLAYERS = 1
MAX_PLAYERS = 30

# Session defaults (a host can override them when creating a session)
DEFAULT_LIVES = 3
DEFAULT_DURATION_SEC = 300

# Stars
BASE_STARS = 10          # stars for one correct answer before multipliers
WRONG_PENALTY = 5        # stars lost on a wrong answer or timeout (never below 0)

# Mystery chests
CHEST_EVERY = 5          # a chest appears on every 5th correct answer in a row
CHEST_COUNT = 3
CHEST_TIMEOUT_SEC = 30   # unopened chests expire after this long
REWARDS = ["double_star", "protection_card", "empty"]

# The server allows a little extra time for network delay
ANSWER_GRACE_MS = 2000


def streak_multiplier(streak: int) -> float:
    """Score multiplier for streak answers."""
    if streak >= 5:
        return 2.0
    if streak >= 3:
        return 1.5
    return 1.0


def score_correct(stars: int, streak: int, double_star_ready: bool) -> dict:
    new_streak = streak + 1
    earned = round(BASE_STARS * streak_multiplier(new_streak))
    if double_star_ready:
        earned *= 2
    return {
        "stars_change": earned,
        "stars": stars + earned,
        "streak": new_streak,
        "double_star_used": double_star_ready,
        "protection_used": False,
    }


def score_wrong(stars: int, streak: int, protection_ready: bool) -> dict:
    """A wrong answer always costs one life (the caller handles lives).
    A Protection Card saves the stars and the streak."""
    if protection_ready:
        return {"stars_change": 0, "stars": stars, "streak": streak,
                "double_star_used": False, "protection_used": True}
    lost = min(stars, WRONG_PENALTY)
    return {"stars_change": -lost, "stars": stars - lost, "streak": 0,
            "double_star_used": False, "protection_used": False}


def chest_earned(streak_after: int) -> bool:
    return streak_after > 0 and streak_after % CHEST_EVERY == 0


def make_chest_slots() -> list[str]:
    """One of each reward, shuffled across the 3 chests."""
    slots = list(REWARDS)
    random.shuffle(slots)
    return slots
