"""
bot/rpg/rift.py — Rift encounter system.

Provides:
  maybe_encounter_rift(player)  -> str | None   (rift-type name or None)
  RIFT_TYPES                    — configuration for each rift tier
  RIFT_ENEMIES                  — stats for rift-exclusive enemies
"""

import random

# Probability a rift spawns on an explore / travel trigger
RIFT_ENCOUNTER_CHANCE: float = 0.06

# ------------------------------------------------------------------ #
#  RIFT TYPE CONFIGURATION
# ------------------------------------------------------------------ #
RIFT_TYPES: dict[str, dict] = {
    "Normal Rift": {
        "emoji":   "🌀",
        "color":   0xEB459E,
        "weight":  78,
        "tagline": "The air tears open… a **Rift** appears before you.",
        "flavor":  (
            "A swirling tear in reality crackles with unstable energy. "
            "Power radiates from within — and so does danger."
        ),
        "waves": [
            {
                "label":        "Wave 1 — Rift Shades",
                "enemies":      ["Rift Shade", "Rift Shade"],
                "is_boss_wave": False,
            },
            {
                "label":        "Wave 2 — Rift Stalker",
                "enemies":      ["Rift Stalker", "Rift Shade"],
                "is_boss_wave": False,
            },
        ],
        "rewards": {
            "xp":     500,
            "copper": 300,
            "drops": [
                {"item": "Rift Crystal",    "chance": 0.55},
                {"item": "Strength Potion", "chance": 0.40},
                {"item": "Speed Potion",    "chance": 0.30},
                {"item": "Shadow Blade",    "chance": 0.12},
                {"item": "Void Cloak",      "chance": 0.05},
            ],
        },
        "chest_min":       "Rare",
        "failure_hp_pct":  0.40,    # lose 40 % max HP on fail / flee
        "failure_message": "💥 The rift collapses and flings you out — you take heavy damage.",
    },
    "Void Rift": {
        "emoji":   "🕳️",
        "color":   0x2C2F33,
        "weight":  22,
        "tagline": "☠️ A **VOID RIFT** tears open. Reality dissolves around you.",
        "flavor":  (
            "The fabric of existence rips apart. Something ancient and terrible stirs "
            "beyond the threshold. This is no ordinary rift. Turn back while you still can."
        ),
        "waves": [
            {
                "label":        "Wave 1 — Void Colossi",
                "enemies":      ["Void Colossus", "Void Colossus"],
                "is_boss_wave": False,
            },
            {
                "label":        "⚠️ BOSS — Void Herald",
                "enemies":      ["Void Herald"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp":     2000,
            "copper": 1200,
            "drops": [
                {"item": "Rift Crystal",         "chance": 0.85},
                {"item": "Void Fragment",         "chance": 0.40},
                {"item": "Void Ring",             "chance": 0.22},
                {"item": "Void Cloak",            "chance": 0.18},
                {"item": "Legendary Sword",       "chance": 0.14},
                {"item": "Ultimate Power Elixir", "chance": 0.22},
            ],
        },
        "chest_min":       "Epic",
        "failure_hp_pct":  1.0,     # near-death (reduced to 1 HP)
        "failure_message": "☠️ **The Void tears you apart.** You barely claw your way back — 1 HP remaining.",
    },
}

# ------------------------------------------------------------------ #
#  RIFT-EXCLUSIVE ENEMIES  (not in data.py — appear only in rifts)
# ------------------------------------------------------------------ #
RIFT_ENEMIES: dict[str, dict] = {
    # ── Normal Rift enemies ───────────────────────────────────────────
    "Rift Shade": {
        "hp": 90, "attack": 16, "defense": 5,
        "experience_reward": 60,  "copper_reward": 45,
        "crit_chance": 0.12, "is_boss": False,
        "inflicts": [{"effect": "poison", "chance": 0.20}],
    },
    "Rift Stalker": {
        "hp": 140, "attack": 24, "defense": 7,
        "experience_reward": 110, "copper_reward": 80,
        "crit_chance": 0.18, "is_boss": False,
        "inflicts": [{"effect": "attack_debuff", "chance": 0.25}],
    },
    # ── Void Rift enemies ─────────────────────────────────────────────
    "Void Colossus": {
        "hp": 350, "attack": 38, "defense": 14,
        "experience_reward": 420, "copper_reward": 210,
        "crit_chance": 0.10, "is_boss": False,
        "inflicts": [{"effect": "defense_debuff", "chance": 0.22}],
    },
    "Void Herald": {
        "hp": 600, "attack": 55, "defense": 18,
        "experience_reward": 1200, "copper_reward": 600,
        "crit_chance": 0.15, "is_boss": True,
        "inflicts": [
            {"effect": "burn", "chance": 0.30},
            {"effect": "stun", "chance": 0.12},
        ],
    },
}

_RIFT_NAMES   = list(RIFT_TYPES.keys())
_RIFT_WEIGHTS = [RIFT_TYPES[r]["weight"] for r in _RIFT_NAMES]


# ------------------------------------------------------------------ #
#  PUBLIC API
# ------------------------------------------------------------------ #

def maybe_encounter_rift(player: dict) -> str | None:
    """
    Roll to see if a rift spawns.
    Returns a rift-type name ("Normal Rift" / "Void Rift") or None.
    Players level 40+ have doubled Void Rift weight — they attract darker forces.
    """
    if random.random() > RIFT_ENCOUNTER_CHANCE:
        return None

    weights = list(_RIFT_WEIGHTS)
    if player.get("level", 1) >= 40:
        weights[1] = weights[1] * 2   # double Void Rift weight at high level

    return random.choices(_RIFT_NAMES, weights=weights, k=1)[0]
