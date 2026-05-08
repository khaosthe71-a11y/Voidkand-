"""
bot/rpg/random_dungeon.py — Procedurally generated random dungeon system.

Provides:
    generate_dungeon(player)     -> dict        (full dungeon descriptor)
    maybe_spawn_dungeon(player)  -> dict | None
    RAND_DUNGEON_BOSSES          — exclusive boss stat blocks
"""

import random

RANDOM_DUNGEON_CHANCE: float = 0.05

# ------------------------------------------------------------------ #
#  ROOM TYPE CONFIG
# ------------------------------------------------------------------ #
ROOM_TYPES = {
    "enemy":    {"emoji": "⚔️",  "label": "Combat Chamber"},
    "treasure": {"emoji": "💰",  "label": "Treasure Vault"},
    "trap":     {"emoji": "⚠️",  "label": "Trap Corridor"},
    "rest":     {"emoji": "🏕️",  "label": "Rest Alcove"},
    "boss":     {"emoji": "☠️",  "label": "Boss Lair"},
}

# Weight table for non-boss rooms
_ROOM_WEIGHTS    = {"enemy": 40, "treasure": 20, "trap": 20, "rest": 20}
_ROOM_TYPE_NAMES = list(_ROOM_WEIGHTS.keys())
_ROOM_TYPE_WVALS = list(_ROOM_WEIGHTS.values())

# ------------------------------------------------------------------ #
#  PROCEDURAL NAME POOLS
# ------------------------------------------------------------------ #
_ADJECTIVES = [
    "Forsaken", "Blighted", "Ancient", "Sunken", "Haunted",
    "Ruined",   "Cursed",   "Shattered", "Rotting", "Forgotten",
    "Crumbling","Infested", "Twisted",  "Overgrown","Decayed",
    "Darkened", "Writhing", "Hollow",   "Flooded",  "Shrouded",
]
_NOUNS = [
    "Catacombs", "Vault",    "Sanctum",    "Passage",    "Depths",
    "Crypt",     "Keep",     "Chambers",   "Labyrinth",  "Ruins",
    "Tombs",     "Fortress", "Underhalls", "Lair",       "Hollow",
    "Dungeon",   "Caverns",  "Corridors",  "Citadel",    "Abyss",
]

# Per-room title variants (for visual variety)
_ROOM_TITLES = {
    "enemy":    ["Combat Chamber", "Monster Den", "Ambush Hall", "Guard Room", "Beast Pit"],
    "treasure": ["Treasure Vault", "Hidden Cache", "Plunder Room", "Loot Chamber", "Gold Alcove"],
    "trap":     ["Trap Corridor", "Hazard Hall", "Spike Pit", "Cursed Chamber", "Pressure Plate Hall"],
    "rest":     ["Rest Alcove", "Healing Spring", "Sanctuary Nook", "Safe Passage", "Healer's Corner"],
    "boss":     ["Boss Lair", "Final Chamber", "Throne Room", "Dark Sanctum", "Inner Keep"],
}

# Room-specific flavor
_TRAP_FLAVOR = [
    "A floor panel collapses — spikes shoot upward!",
    "Poison darts fly from hidden wall slits!",
    "A boulder rumbles down the corridor at you!",
    "Arcane runes explode beneath your feet!",
    "Concealed blades sweep across the passage!",
]
_REST_FLAVOR = [
    "A healing spring bubbles up from the stone floor.",
    "A shimmering ward left by a long-dead healer mends your wounds.",
    "You find a stash of rations and bandages stuffed behind a loose brick.",
    "Peaceful runes glow on the walls — you feel your wounds knit closed.",
]

# ------------------------------------------------------------------ #
#  EXCLUSIVE BOSS STAT BLOCKS
# ------------------------------------------------------------------ #
RAND_DUNGEON_BOSSES: dict[str, dict] = {
    "Dungeon Warden": {
        "hp": 220, "attack": 28, "defense": 8,
        "experience_reward": 350, "copper_reward": 180,
        "crit_chance": 0.12, "is_boss": True,
        "inflicts": [{"effect": "attack_debuff", "chance": 0.20}],
    },
    "Cursed Champion": {
        "hp": 380, "attack": 42, "defense": 13,
        "experience_reward": 650, "copper_reward": 300,
        "crit_chance": 0.14, "is_boss": True,
        "inflicts": [
            {"effect": "stun", "chance": 0.18},
            {"effect": "burn", "chance": 0.22},
        ],
    },
    "Void Warlord": {
        "hp": 700, "attack": 65, "defense": 20,
        "experience_reward": 1500, "copper_reward": 600,
        "crit_chance": 0.15, "is_boss": True,
        "inflicts": [
            {"effect": "burn",           "chance": 0.28},
            {"effect": "defense_debuff", "chance": 0.25},
        ],
    },
}

# Level thresholds → boss
_BOSS_TIER: list[tuple[int, str]] = [
    (15,  "Dungeon Warden"),
    (30,  "Cursed Champion"),
    (999, "Void Warlord"),
]

# Boss → minimum chest rarity on clear
BOSS_CHEST_MIN: dict[str, str] = {
    "Dungeon Warden":  "Uncommon",
    "Cursed Champion": "Rare",
    "Void Warlord":    "Epic",
}

# Boss → base reward (non-enemy rooms don't add combat XP)
_BOSS_BASE_REWARDS: dict[str, dict] = {
    "Dungeon Warden":  {"xp": 300,  "copper": 150},
    "Cursed Champion": {"xp": 600,  "copper": 280},
    "Void Warlord":    {"xp": 1400, "copper": 550},
}

# ------------------------------------------------------------------ #
#  ENEMY POOLS  (for enemy rooms, by player level)
# ------------------------------------------------------------------ #
_ENEMY_POOLS: list[tuple[int, list[str]]] = [
    (15,  ["Goblin",       "Shadow Beast"]),
    (30,  ["Shadow Beast", "Corrupted Knight"]),
    (999, ["Corrupted Knight", "Dungeon Lord"]),
]


# ------------------------------------------------------------------ #
#  INTERNAL HELPERS
# ------------------------------------------------------------------ #
def _pick_boss(level: int) -> str:
    for threshold, name in _BOSS_TIER:
        if level < threshold:
            return name
    return "Void Warlord"


def _pick_enemy_pool(level: int) -> list[str]:
    for threshold, pool in _ENEMY_POOLS:
        if level < threshold:
            return pool
    return ["Corrupted Knight", "Dungeon Lord"]


def _build_room(rtype: str, room_num: int, enemy_pool: list[str], boss_name: str) -> dict:
    room: dict = {
        "type":   rtype,
        "number": room_num,
        "emoji":  ROOM_TYPES[rtype]["emoji"],
        "title":  random.choice(_ROOM_TITLES[rtype]),
    }
    if rtype in ("enemy", "boss"):
        room["enemy"] = boss_name if rtype == "boss" else random.choice(enemy_pool)
    elif rtype == "trap":
        room["damage_pct"] = round(random.uniform(0.10, 0.20), 2)
        room["flavor"]     = random.choice(_TRAP_FLAVOR)
    elif rtype == "rest":
        room["heal_pct"] = round(random.uniform(0.20, 0.30), 2)
        room["flavor"]   = random.choice(_REST_FLAVOR)
    return room


# ------------------------------------------------------------------ #
#  PUBLIC API
# ------------------------------------------------------------------ #
def generate_dungeon(player: dict) -> dict:
    """
    Procedurally generate a dungeon scaled to `player`.
    Returns a dungeon descriptor with keys:
        name, rooms, room_count, boss_name, chest_min, rewards
    """
    level      = player.get("level", 1)
    room_count = random.randint(3, 6)
    boss_name  = _pick_boss(level)
    pool       = _pick_enemy_pool(level)

    # Non-boss rooms (first room_count−1 rooms)
    mid_types = random.choices(_ROOM_TYPE_NAMES, weights=_ROOM_TYPE_WVALS, k=room_count - 1)
    rooms = [_build_room(rt, i + 1, pool, boss_name) for i, rt in enumerate(mid_types)]
    rooms.append(_build_room("boss", room_count, pool, boss_name))

    # Reward scaling
    base      = _BOSS_BASE_REWARDS[boss_name]
    enemy_cnt = sum(1 for r in rooms if r["type"] == "enemy")
    total_xp     = base["xp"]     + enemy_cnt * 60 + level * 10
    total_copper = base["copper"] + enemy_cnt * 35 + level * 5

    return {
        "name":       f"{random.choice(_ADJECTIVES)} {random.choice(_NOUNS)}",
        "rooms":      rooms,
        "room_count": room_count,
        "boss_name":  boss_name,
        "chest_min":  BOSS_CHEST_MIN[boss_name],
        "rewards":    {"xp": total_xp, "copper": total_copper},
    }


def maybe_spawn_dungeon(player: dict) -> "dict | None":
    """
    5% chance to spawn a procedurally-generated dungeon.
    Returns a dungeon descriptor dict, or None.
    """
    if random.random() > RANDOM_DUNGEON_CHANCE:
        return None
    return generate_dungeon(player)
