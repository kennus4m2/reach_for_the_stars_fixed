import re

# Starter list only. Add more words your team wants to block.
BLOCKED_WORDS = [
    "fuck", "shit", "bitch", "asshole", "dick", "pussy", "cunt", "slut", "nigg",
    "puta", "putang", "tangina", "gago", "gaga", "bobo", "tanga", "ulol", "pakyu",
    "kantot", "burat", "titi", "pepe", "hindot", "lintik",
]

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def is_bad_nickname(nickname: str) -> bool:
    cleaned = re.sub(r"[^a-z]", "", nickname.lower().translate(_LEET))
    return any(word in cleaned for word in BLOCKED_WORDS)
