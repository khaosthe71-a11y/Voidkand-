"""
Guild system for voidkand-rpg.

Storage : bot/guilds.json  (dict keyed by 8-char guild_id)
Each guild: {name, description, owner_id, members[], level, xp,
             xp_to_next, created_at, war_wins, war_losses}

Player fields: player["guild_id"] (str|None)
               player["guild_bonus"] (dict — currently-applied bonus snapshot)
"""
import json
import os
import random
import uuid
from datetime import datetime

GUILD_FILE = os.path.join(os.path.dirname(__file__), "..", "guilds.json")

MAX_GUILD_MEMBERS = 25

# Passive stat bonuses granted to every member at each guild level.
GUILD_BONUS_TABLE: dict[int, dict] = {
    1: {"attack": 2,  "defense": 2,  "max_hp": 0,  "crit_chance": 0.00, "speed": 0},
    2: {"attack": 4,  "defense": 4,  "max_hp": 10, "crit_chance": 0.01, "speed": 0},
    3: {"attack": 7,  "defense": 6,  "max_hp": 20, "crit_chance": 0.02, "speed": 1},
    4: {"attack": 10, "defense": 9,  "max_hp": 35, "crit_chance": 0.03, "speed": 2},
    5: {"attack": 15, "defense": 13, "max_hp": 55, "crit_chance": 0.05, "speed": 3},
}

# XP needed to advance from level N (None = already at max)
GUILD_XP_TABLE: dict[int, int | None] = {
    1: 500,
    2: 1500,
    3: 3500,
    4: 8000,
    5: None,
}

EMPTY_BONUS: dict = {
    "attack": 0, "defense": 0, "max_hp": 0, "crit_chance": 0.0, "speed": 0
}


# ------------------------------------------------------------------ #
#  Persistence
# ------------------------------------------------------------------ #

def load_guilds() -> dict:
    if not os.path.exists(GUILD_FILE):
        return {}
    try:
        with open(GUILD_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_guilds(guilds: dict) -> None:
    os.makedirs(os.path.dirname(GUILD_FILE), exist_ok=True)
    with open(GUILD_FILE, "w") as f:
        json.dump(guilds, f, indent=2)


# ------------------------------------------------------------------ #
#  Lookup helpers
# ------------------------------------------------------------------ #

def get_player_guild_id(player_id: int, guilds: dict) -> str | None:
    """Return the guild_id that player_id is a member of, or None."""
    pid = str(player_id)
    for gid, guild in guilds.items():
        if pid in guild.get("members", []):
            return gid
    return None


def find_guild_by_name(name: str, guilds: dict) -> tuple[str, dict] | tuple[None, None]:
    """Case-insensitive guild name search. Returns (guild_id, guild) or (None, None)."""
    nl = name.strip().lower()
    for gid, guild in guilds.items():
        if guild["name"].lower() == nl:
            return gid, guild
    return None, None


def get_guild_bonus_dict(guild: dict) -> dict:
    level = max(1, min(guild.get("level", 1), 5))
    return GUILD_BONUS_TABLE[level]


def bonus_summary(bonuses: dict) -> str:
    """Human-readable bonus summary, e.g. '+4 ATK · +4 DEF · +10 HP'."""
    labels = {
        "attack": "ATK", "defense": "DEF", "max_hp": "Max HP",
        "crit_chance": "Crit", "speed": "SPD",
    }
    parts = []
    for k, label in labels.items():
        v = bonuses.get(k, 0)
        if v:
            if k == "crit_chance":
                parts.append(f"+{v*100:.0f}% {label}")
            else:
                parts.append(f"+{v} {label}")
    return " · ".join(parts) if parts else "None"


# ------------------------------------------------------------------ #
#  Stat application / removal
# ------------------------------------------------------------------ #

def apply_guild_bonus(player: dict, guilds: dict) -> None:
    """
    Apply the current guild's level bonuses to player stats.
    Reverts any previously applied bonus first to avoid stacking.
    """
    gid = player.get("guild_id")
    if not gid or gid not in guilds:
        return
    remove_guild_bonus(player)
    bonuses = get_guild_bonus_dict(guilds[gid])
    player["attack"]      += bonuses.get("attack", 0)
    player["defense"]     += bonuses.get("defense", 0)
    hp_add = bonuses.get("max_hp", 0)
    player["max_hp"]      += hp_add
    player["hp"]           = min(player["hp"] + hp_add, player["max_hp"])
    player["crit_chance"] += bonuses.get("crit_chance", 0.0)
    player["speed"]       += bonuses.get("speed", 0)
    player["guild_bonus"]  = dict(bonuses)


def remove_guild_bonus(player: dict) -> None:
    """Revert guild bonuses that were applied to this player."""
    bonus = player.get("guild_bonus", {})
    if not bonus or not any(bonus.values()):
        return
    player["attack"]      = max(1, player["attack"]      - bonus.get("attack", 0))
    player["defense"]     = max(0, player["defense"]     - bonus.get("defense", 0))
    hp_drop = bonus.get("max_hp", 0)
    player["max_hp"]      = max(10, player["max_hp"]     - hp_drop)
    player["hp"]           = min(player["hp"], player["max_hp"])
    player["crit_chance"] = max(0.01, player["crit_chance"] - bonus.get("crit_chance", 0.0))
    player["speed"]       = max(1, player["speed"]       - bonus.get("speed", 0))
    player["guild_bonus"]  = dict(EMPTY_BONUS)


# ------------------------------------------------------------------ #
#  CRUD operations
# ------------------------------------------------------------------ #

def create_guild(
    owner_id: int, name: str, description: str, guilds: dict
) -> tuple[str, str]:
    """
    Create a new guild owned by owner_id.
    Returns (guild_id, success_message) or ("", error_message) on failure.
    """
    name = name.strip()
    if len(name) < 2 or len(name) > 32:
        return "", "Guild name must be 2–32 characters."
    for guild in guilds.values():
        if guild["name"].lower() == name.lower():
            return "", f"A guild named **{guild['name']}** already exists."
    gid = str(uuid.uuid4())[:8]
    guilds[gid] = {
        "name": name,
        "description": description.strip() if description else "No description.",
        "owner_id": str(owner_id),
        "members": [str(owner_id)],
        "level": 1,
        "xp": 0,
        "xp_to_next": GUILD_XP_TABLE[1],
        "created_at": datetime.utcnow().isoformat(),
        "war_wins": 0,
        "war_losses": 0,
    }
    return gid, f"🏰 Guild **{name}** has been founded!"


def join_guild(player_id: int, guild_id: str, guilds: dict) -> str:
    """Add player to guild. Returns '' on success or an error string."""
    pid = str(player_id)
    if guild_id not in guilds:
        return "Guild not found."
    guild = guilds[guild_id]
    if pid in guild["members"]:
        return "You're already in this guild."
    if len(guild["members"]) >= MAX_GUILD_MEMBERS:
        return f"**{guild['name']}** is full ({MAX_GUILD_MEMBERS}-member limit)."
    guild["members"].append(pid)
    return ""


def leave_guild(player_id: int, guilds: dict) -> tuple[str, str]:
    """
    Remove player from their guild.
    Returns (guild_name, error_msg).  error_msg == '' means success.
    Transfers ownership if owner leaves; deletes guild when empty.
    """
    pid = str(player_id)
    gid = get_player_guild_id(player_id, guilds)
    if not gid:
        return "", "You're not in a guild."
    guild = guilds[gid]
    guild_name = guild["name"]
    guild["members"].remove(pid)
    if guild["owner_id"] == pid:
        if guild["members"]:
            guild["owner_id"] = guild["members"][0]
        else:
            del guilds[gid]
            return guild_name, ""
    return guild_name, ""


# ------------------------------------------------------------------ #
#  XP and levelling
# ------------------------------------------------------------------ #

def add_guild_xp(guild_id: str, amount: int, guilds: dict) -> list[str]:
    """
    Add XP to a guild and process any level-ups.
    Returns a list of announcement strings (empty if no level-up occurred).
    """
    if guild_id not in guilds:
        return []
    guild = guilds[guild_id]
    if guild.get("level", 1) >= 5:
        return []
    guild["xp"] = guild.get("xp", 0) + amount
    msgs: list[str] = []
    while guild.get("level", 1) < 5:
        xp_needed = guild.get("xp_to_next") or GUILD_XP_TABLE.get(guild["level"])
        if not xp_needed or guild["xp"] < xp_needed:
            break
        guild["xp"] -= xp_needed
        guild["level"] += 1
        next_xp = GUILD_XP_TABLE.get(guild["level"])
        guild["xp_to_next"] = next_xp
        bonuses = GUILD_BONUS_TABLE[guild["level"]]
        msgs.append(
            f"🎉 **{guild['name']}** levelled up to **Guild Level {guild['level']}**!\n"
            f"New member bonuses: **{bonus_summary(bonuses)}**\n"
            f"Members: use `!guild_refresh` to apply your updated stats."
        )
    return msgs


# ------------------------------------------------------------------ #
#  Guild Wars
# ------------------------------------------------------------------ #

def simulate_guild_war(
    attacker_id: str, defender_id: str, guilds: dict
) -> tuple[bool, list[str]]:
    """
    Simulate a guild war. Returns (attacker_won, level_up_msgs).
    Power = guild_level * 10 + member_count * 2, with ±30% roll.
    """
    a = guilds[attacker_id]
    d = guilds[defender_id]
    a_power = a.get("level", 1) * 10 + len(a.get("members", [])) * 2
    d_power = d.get("level", 1) * 10 + len(d.get("members", [])) * 2
    a_roll = a_power * random.uniform(0.7, 1.3)
    d_roll = d_power * random.uniform(0.7, 1.3)
    attacker_won = a_roll > d_roll
    if attacker_won:
        a["war_wins"]   = a.get("war_wins", 0) + 1
        d["war_losses"] = d.get("war_losses", 0) + 1
        return True, add_guild_xp(attacker_id, 150, guilds)
    else:
        d["war_wins"]   = d.get("war_wins", 0) + 1
        a["war_losses"] = a.get("war_losses", 0) + 1
        return False, add_guild_xp(defender_id, 75, guilds)
