"""
bot/rpg/factions.py — Faction / Empire system.

Three factions tied to the story world:
  Eclipse Empire (May)         — balanced, +10% XP + copper rewards
  Divine Order   (Lyra)        — holy,     +20% heal · +5 defense on join
  Void Legion    (Demon King)  — dark,     +15% attack · +10% damage taken

Public API:
  FACTIONS                     — full faction definitions
  FACTION_MISSIONS             — per-faction mission dicts
  REPUTATION_TIERS             — (threshold, title, flavor) list
  MIN_FACTION_LEVEL            — minimum level to join (15)
  get_faction_key(p)           -> str | None
  get_faction(p)               -> dict | None
  get_reputation_tier(v)       -> dict
  faction_xp_mult(p)           -> float
  faction_copper_mult(p)       -> float
  faction_heal_mult(p)         -> float
  faction_attack_mult(p)       -> float
  faction_damage_taken_mult(p) -> float
  available_missions(p)        -> list[dict]
  complete_faction_mission(p, id) -> list[str]
  check_kill_missions(p)       -> list[str]
  check_travel_missions(p, loc) -> list[str]
  check_dungeon_missions(p, name) -> list[str]
  faction_join(p, key)         -> (bool, str)
"""

MIN_FACTION_LEVEL: int = 15

# ------------------------------------------------------------------ #
#  FACTION DEFINITIONS
# ------------------------------------------------------------------ #
FACTIONS: dict[str, dict] = {
    "Eclipse": {
        "name":        "Eclipse Empire",
        "leader":      "May",
        "emoji":       "🌘",
        "color":       0xFEE75C,
        "description": (
            "The Eclipse Empire rules through iron discipline and strategic brilliance. "
            "Under Empress May, it commands the greatest army this world has ever seen — "
            "and the most lucrative trade network to go with it."
        ),
        "lore": (
            "Empress May does not smile at your oath. She does not need to. "
            "Power speaks for itself — and the Empire has spoken for a thousand years.\n"
            "*The Empire's banner now flies in your heart. Bring it glory — and profit.*"
        ),
        "join_msg": (
            "🌘 **You swear loyalty to the Eclipse Empire.**\n\n"
            "Empress May's voice is precise and measured:\n"
            "*'You are mine now. Serve well — and the Empire rewards. "
            "Fail — and it forgets you ever existed.'*\n\n"
            "**Faction Bonus:** +10% XP and +10% copper from all combat and dungeon rewards."
        ),
        "bonuses": {
            "reward_xp_mult":     1.10,
            "reward_copper_mult": 1.10,
        },
        "bonus_summary": "+10% XP · +10% Copper from all rewards",
    },
    "Divine": {
        "name":        "Divine Order",
        "leader":      "Lyra",
        "emoji":       "✨",
        "color":       0xFFD700,
        "description": (
            "The Divine Order walks in Lyra's light. Its healers, paladins, and scholars "
            "have fought the darkness for centuries. They don't win through force alone — "
            "they win because they refuse to stop."
        ),
        "lore": (
            "Lyra places a hand on your shoulder. The warmth that follows is not from her touch — "
            "it comes from somewhere deeper, older, and very patient.\n"
            "*'The light sees you,' she says. 'It always has.'*"
        ),
        "join_msg": (
            "✨ **Lyra's light blesses your path.**\n\n"
            "*'Walk with us,'* she says, and the world seems a little brighter. "
            "The sigil of the Divine Order glows softly on your palm.\n\n"
            "**Faction Bonus:** +20% healing effectiveness · +5 permanent Defense (applied now)."
        ),
        "bonuses": {
            "heal_mult":   1.20,
            "defense_add": 5,
        },
        "bonus_summary": "+20% Healing · +5 Defense (applied on join)",
    },
    "Void": {
        "name":        "Void Legion",
        "leader":      "Demon King",
        "emoji":       "💀",
        "color":       0xED4245,
        "description": (
            "The Void Legion serves the Demon King — not through love, but through power. "
            "Void soldiers hit harder than anything else alive. "
            "They pay for it with their lives, slowly, in the dark."
        ),
        "lore": (
            "The Demon King does not welcome you. He simply acknowledges you — "
            "a slow, terrible turn of the head. The shadows close in.\n"
            "*Something takes root inside you. Cold. Hungry. Useful.*"
        ),
        "join_msg": (
            "💀 **The Demon King's shadow consumes your soul.**\n\n"
            "There is no ceremony. Only darkness settling into your bones "
            "like it was always waiting for an invitation.\n\n"
            "**Faction Bonus:** +15% Attack damage · ⚠️ +10% damage received (Void curse)."
        ),
        "bonuses": {
            "attack_mult":       1.15,
            "damage_taken_mult": 1.10,
        },
        "bonus_summary": "+15% Attack damage · ⚠️ +10% damage received (Void curse)",
    },
}

# ------------------------------------------------------------------ #
#  FACTION MISSIONS
# ------------------------------------------------------------------ #
# Mission types:
#   kill_count     — track combat kills via check_kill_missions()
#   travel         — triggered when player arrives at required_location
#   dungeon_clear  — triggered when player clears required_dungeon
FACTION_MISSIONS: dict[str, list[dict]] = {
    "Eclipse": [
        {
            "id":          "eclipse_m1",
            "name":        "Road Security",
            "description": "Defeat 5 enemies to secure the roads for the Empire.",
            "type":        "kill_count",
            "required":    5,
            "reward_xp":   250,
            "reward_copper": 120,
            "reward_rep":  100,
            "flavor":      "The Empire's roads must flow freely for its merchants and soldiers.",
        },
        {
            "id":          "eclipse_m2",
            "name":        "Imperial Reach",
            "description": "Travel to Iron Bastion and establish a presence there.",
            "type":        "travel",
            "required_location": "Iron Bastion",
            "reward_xp":   400,
            "reward_copper": 220,
            "reward_rep":  150,
            "flavor":      "The Empire's banner must fly over the Bastion.",
        },
        {
            "id":          "eclipse_m3",
            "name":        "Conquer the Crypt",
            "description": "Clear the Crypt of the Fallen King in the Empire's name.",
            "type":        "dungeon_clear",
            "required_dungeon": "Crypt of the Fallen King",
            "reward_xp":   700,
            "reward_copper": 500,
            "reward_rep":  250,
            "flavor":      "The Empire claims all territory — even the territory of the dead.",
        },
    ],
    "Divine": [
        {
            "id":          "divine_m1",
            "name":        "Cleanse the Fallen",
            "description": "Defeat 5 enemies in the Order's name.",
            "type":        "kill_count",
            "required":    5,
            "reward_xp":   250,
            "reward_copper": 100,
            "reward_rep":  100,
            "flavor":      "Every soul freed from darkness is a victory for the light.",
        },
        {
            "id":          "divine_m2",
            "name":        "The Sacred Summit",
            "description": "Reach Celestial Peak and receive its blessing.",
            "type":        "travel",
            "required_location": "Celestial Peak",
            "reward_xp":   400,
            "reward_copper": 180,
            "reward_rep":  150,
            "flavor":      "The mountain's blessing has waited centuries for someone worthy.",
        },
        {
            "id":          "divine_m3",
            "name":        "Trial of Devotion",
            "description": "Clear the Crypt of the Fallen King and lay its dead to rest.",
            "type":        "dungeon_clear",
            "required_dungeon": "Crypt of the Fallen King",
            "reward_xp":   700,
            "reward_copper": 400,
            "reward_rep":  250,
            "flavor":      "The dead deserve rest. Give it to them.",
        },
    ],
    "Void": [
        {
            "id":          "void_m1",
            "name":        "Blood Tribute",
            "description": "Defeat 5 enemies as a blood offering to the Void Legion.",
            "type":        "kill_count",
            "required":    5,
            "reward_xp":   300,
            "reward_copper": 150,
            "reward_rep":  100,
            "flavor":      "The Void feeds on conflict. Feed it well.",
        },
        {
            "id":          "void_m2",
            "name":        "Into the Abyss",
            "description": "Reach the Abyssal Gate and stand at the edge of the Void.",
            "type":        "travel",
            "required_location": "Abyssal Gate",
            "reward_xp":   450,
            "reward_copper": 250,
            "reward_rep":  150,
            "flavor":      "The Demon King expects nothing less.",
        },
        {
            "id":          "void_m3",
            "name":        "Descent",
            "description": "Descend into the Inferno Depths and claim it for the Legion.",
            "type":        "dungeon_clear",
            "required_dungeon": "Inferno Depths",
            "reward_xp":   800,
            "reward_copper": 600,
            "reward_rep":  250,
            "flavor":      "The Void Legion does not retreat. It consumes.",
        },
    ],
}

# ------------------------------------------------------------------ #
#  REPUTATION TIERS
# ------------------------------------------------------------------ #
# List of (min_rep, title, flavor_shown_on_rank_up)
REPUTATION_TIERS: list[tuple[int, str, str]] = [
    (0,    "Outsider",  ""),
    (100,  "Initiate",  "Your name is known within the faction."),
    (300,  "Loyal",     "The faction trusts you with greater responsibilities."),
    (700,  "Champion",  "You are called Champion. Songs are whispered about your deeds."),
    (1500, "Legend",    "Your legend is written into the faction's history forever."),
]

# Rare item rewards granted on reaching a rep tier
_FACTION_REP_ITEMS: dict[str, dict[str, str]] = {
    "Eclipse": {
        "Champion": "Void Ring",
        "Legend":   "Dragonscale Armor",
    },
    "Divine": {
        "Champion": "Celestial Pendant",
        "Legend":   "Shadowweave Cloak",
    },
    "Void": {
        "Champion": "Voidforged Gauntlet",
        "Legend":   "Fallen King's Blade",
    },
}


# ------------------------------------------------------------------ #
#  CORE HELPERS
# ------------------------------------------------------------------ #

def get_faction_key(player: dict) -> str | None:
    """Return the player's faction key ('Eclipse'|'Divine'|'Void') or None."""
    return player.get("faction")


def get_faction(player: dict) -> dict | None:
    """Return the player's faction config dict, or None if not in a faction."""
    key = get_faction_key(player)
    return FACTIONS.get(key) if key else None


def get_reputation_tier(rep_val: int) -> dict:
    """Return {threshold, title, flavor} for the current rep value."""
    tier_t, tier_title, tier_flavor = REPUTATION_TIERS[0]
    for threshold, title, flavor in REPUTATION_TIERS:
        if rep_val >= threshold:
            tier_t, tier_title, tier_flavor = threshold, title, flavor
    return {"threshold": tier_t, "title": tier_title, "flavor": tier_flavor}


# ── Stat multipliers / bonuses ─────────────────────────────────────

def faction_xp_mult(player: dict) -> float:
    """Eclipse Empire: +10% XP from all rewards."""
    return FACTIONS["Eclipse"]["bonuses"]["reward_xp_mult"] if get_faction_key(player) == "Eclipse" else 1.0


def faction_copper_mult(player: dict) -> float:
    """Eclipse Empire: +10% copper from all rewards."""
    return FACTIONS["Eclipse"]["bonuses"]["reward_copper_mult"] if get_faction_key(player) == "Eclipse" else 1.0


def faction_heal_mult(player: dict) -> float:
    """Divine Order: +20% healing effectiveness."""
    return FACTIONS["Divine"]["bonuses"]["heal_mult"] if get_faction_key(player) == "Divine" else 1.0


def faction_attack_mult(player: dict) -> float:
    """Void Legion: +15% attack damage output."""
    return FACTIONS["Void"]["bonuses"]["attack_mult"] if get_faction_key(player) == "Void" else 1.0


def faction_damage_taken_mult(player: dict) -> float:
    """Void Legion: +10% damage received (Void curse)."""
    return FACTIONS["Void"]["bonuses"]["damage_taken_mult"] if get_faction_key(player) == "Void" else 1.0


# ── Mission helpers ────────────────────────────────────────────────

def available_missions(player: dict) -> list[dict]:
    """Return faction missions the player has not yet completed."""
    key = get_faction_key(player)
    if not key:
        return []
    completed = set(player.get("faction_missions_completed", []))
    return [m for m in FACTION_MISSIONS.get(key, []) if m["id"] not in completed]


def complete_faction_mission(player: dict, mission_id: str) -> list[str]:
    """
    Mark a mission complete, award XP/copper/rep directly to player state.
    Returns list of display strings to send to Discord.
    """
    key = get_faction_key(player)
    if not key:
        return []
    mission = next(
        (m for m in FACTION_MISSIONS.get(key, []) if m["id"] == mission_id),
        None,
    )
    if not mission:
        return []
    completed = player.setdefault("faction_missions_completed", [])
    if mission_id in completed:
        return []
    completed.append(mission_id)

    # Award reputation
    rep = player.setdefault("reputation", {"Eclipse": 0, "Divine": 0, "Void": 0})
    old_rep = rep.get(key, 0)
    rep[key] = old_rep + mission["reward_rep"]

    # Award XP + copper directly
    player["experience_points"] = player.get("experience_points", 0) + mission["reward_xp"]
    player["currency"]["copper"] = player.get("currency", {}).get("copper", 0) + mission["reward_copper"]

    msgs = [
        f"📜 **Faction Mission Complete!** — *{FACTIONS[key]['name']}: {mission['name']}*",
        f"✨ +{mission['reward_xp']} XP · 💰 +{mission['reward_copper']}c · "
        f"🏅 +{mission['reward_rep']} Reputation\n"
        f"*{mission['flavor']}*",
    ]

    # Check for tier rank-up
    new_tier = get_reputation_tier(rep[key])
    old_tier = get_reputation_tier(old_rep)
    if new_tier["title"] != old_tier["title"]:
        msgs.append(
            f"🎖️ **Reputation Rank Up!** You are now a **{new_tier['title']}** "
            f"of the {FACTIONS[key]['name']}!\n*{new_tier['flavor']}*"
        )
        # Grant rare item for this tier
        rep_item = _FACTION_REP_ITEMS.get(key, {}).get(new_tier["title"])
        if rep_item:
            player.setdefault("inventory", []).append(rep_item)
            msgs.append(f"🎁 **Rank Reward:** You receive **{rep_item}**!")

    return msgs


def check_kill_missions(player: dict) -> list[str]:
    """
    Increment the faction kill tracker and complete any kill_count mission
    whose threshold is now met. Call after every combat win.
    Returns display messages.
    """
    key = get_faction_key(player)
    if not key:
        return []
    player["faction_kill_tracker"] = player.get("faction_kill_tracker", 0) + 1
    msgs = []
    for m in available_missions(player):
        if m["type"] == "kill_count" and player["faction_kill_tracker"] >= m["required"]:
            player["faction_kill_tracker"] = 0
            msgs += complete_faction_mission(player, m["id"])
            break  # complete one at a time
    return msgs


def check_travel_missions(player: dict, location: str) -> list[str]:
    """Complete any travel-type missions whose required location was just reached."""
    key = get_faction_key(player)
    if not key:
        return []
    msgs = []
    for m in available_missions(player):
        if m["type"] == "travel" and m.get("required_location") == location:
            msgs += complete_faction_mission(player, m["id"])
    return msgs


def check_dungeon_missions(player: dict, dungeon_name: str) -> list[str]:
    """Complete any dungeon_clear missions whose dungeon was just cleared."""
    key = get_faction_key(player)
    if not key:
        return []
    msgs = []
    for m in available_missions(player):
        if m["type"] == "dungeon_clear" and m.get("required_dungeon") == dungeon_name:
            msgs += complete_faction_mission(player, m["id"])
    return msgs


# ── Join ──────────────────────────────────────────────────────────

def faction_join(player: dict, faction_key: str) -> tuple[bool, str]:
    """
    Attempt to join a faction. Applies permanent stat bonuses on success.
    Returns (success, message_string).
    """
    normalized = faction_key.strip().capitalize()
    # Accept aliases
    _aliases = {
        "Eclipse": "Eclipse", "Emp": "Eclipse", "Empire": "Eclipse",
        "Divine":  "Divine",  "Order": "Divine",
        "Void":    "Void",    "Legion": "Void",  "Voidlegion": "Void",
    }
    normalized = _aliases.get(normalized, normalized)

    if normalized not in FACTIONS:
        keys = " · ".join(f"`{k.lower()}`" for k in FACTIONS)
        return False, f"❌ Unknown faction. Choose one of: {keys}."

    if player.get("faction"):
        existing = FACTIONS[player["faction"]]["name"]
        return False, (
            f"❌ You already belong to the **{existing}**. "
            f"Faction allegiance is permanent — choose wisely next time."
        )

    if player.get("level", 1) < MIN_FACTION_LEVEL:
        return False, (
            f"❌ You must be **Level {MIN_FACTION_LEVEL}** to join a faction. "
            f"You are Level **{player['level']}**."
        )

    # Commit
    player["faction"] = normalized
    player.setdefault("reputation", {"Eclipse": 0, "Divine": 0, "Void": 0})
    player.setdefault("faction_missions_completed", [])
    player.setdefault("faction_kill_tracker", 0)

    # Apply permanent stat bonus on join
    if normalized == "Divine":
        player["defense"] = player.get("defense", 5) + FACTIONS["Divine"]["bonuses"]["defense_add"]

    return True, FACTIONS[normalized]["join_msg"]
