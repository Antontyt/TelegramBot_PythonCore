import json
import os
import hashlib

STATS_FILE = "stats.json"


def _hash_user(user_id: int) -> str:
    """Необратимый отпечаток id: один id -> всегда один хеш."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()


def _load() -> dict:
    if not os.path.exists(STATS_FILE):
        return {"gpt_requests": 0, "user_hashes": []}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("gpt_requests", 0)
        data.setdefault("user_hashes", [])
        return data
    except (json.JSONDecodeError, OSError):
        return {"gpt_requests": 0, "user_hashes": []}


def _save(data: dict) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_gpt_request() -> None:
    data = _load()
    data["gpt_requests"] += 1
    _save(data)


def add_user(user_id: int) -> None:
    data = _load()
    h = _hash_user(user_id)
    if h not in data["user_hashes"]:
        data["user_hashes"].append(h)
        _save(data)


def get_stats() -> dict:
    data = _load()
    return {
        "gpt_requests": data["gpt_requests"],
        "users_count": len(data["user_hashes"]),
    }
