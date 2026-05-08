"""
bot/rpg/world_dungeon.py — World Dungeon / World Boss event system.

A server-wide cooperative boss encounter that any player can join.
Features shared boss HP, per-player damage tracking, proportional
rewards, periodic AoE attacks, and enrage mechanics.

Public API:
    WORLD_DUNGEON          — live state dict
    WORLD_BOSS_CONFIGS     — boss roster
    spawn_world_dungeon()  — initialize a new event
    join_world_dungeon()   — register a player
    start_world_fight()    — open the fighting phase
    world_boss_attack()    — process one player's attack + retaliation
    distribute_world_rewards() — calculate end-of-fight rewards
    clear_world_dungeon()  — reset to inactive
    world_dungeon_status_lines() — human-readable status
"""

import random
import time

# ------------------------------------------------------------------ #
#  WORLD BOSS CONFIGURATIONS
# ------------------------------------------------------------------ #
WORLD_BOSS_CONFIGS: dict[str, dict] = {
    "Ancient Terror": {
        "emoji":             "🐉",
        "description":       "A colossal ancient dragon awakened from eternal slumber.",
        "boss_intro": (
            "The earth convulses. Cracks split the ground as something vast and ancient tears itself free "
            "from below — scaled, furious, impossibly large. The Ancient Terror spreads its wings and "
            "the sky dims beneath them.\n"
            "*A sound leaves its throat that is less a roar and more a pronouncement of doom.*\n"
            "Every hero steadies their weapon. The ground beneath them is already shaking.\n"
            "**This is what you were built for.**"
        ),
        "aoe_roar": (
            "🌋 **The Ancient Terror slams the earth with one colossal claw — "
            "the shockwave tears through every hero on the battlefield!**"
        ),
        "victory_msg": (
            "The Ancient Terror lets out one final roar — a sound that splits clouds — "
            "then collapses, its dragonfire dying mid-breath, its wings folding like broken sails.\n"
            "The battlefield falls silent. The smoke clears slowly.\n"
            "*The ground still remembers the weight of what just ended.*\n"
            "✨ **The beast is slain. Its power now belongs to those who stood their ground.**"
        ),
        "base_hp":           5000,
        "hp_per_player":     1500,
        "base_attack":       55,
        "attack_per_player": 10,
        "defense":           20,
        "enrage_pct":        0.25,
        "aoe_every":         5,
        "xp_reward":         3000,
        "copper_reward":     2000,
        "drops": [
            {"item": "Legendary Sword",    "chance": 0.35},
            {"item": "Dragonscale Armor",  "chance": 0.30},
            {"item": "Demon King's Crown", "chance": 0.12},
            {"item": "Void Ring",          "chance": 0.18},
            {"item": "Void Cloak",         "chance": 0.20},
        ],
    },
    "Abyssal Wyrm": {
        "emoji":             "🐍",
        "description":       "A serpent older than the world itself, risen from the abyss.",
        "boss_intro": (
            "The sea tears open. Rising from the black water comes a serpent larger than memory — "
            "endlessly coiled, scales swallowing the light around it, eyes like drowned stars.\n"
            "*It does not roar. It does not need to.*\n"
            "The weight of its gaze alone is enough to make lesser hunters turn and run.\n"
            "**Every breath you take now is borrowed time. Spend it well.**"
        ),
        "aoe_roar": (
            "🌊 **The Abyssal Wyrm exhales — a wall of corrosive venom fog crashes across the entire battlefield, "
            "burning everything it touches!**"
        ),
        "victory_msg": (
            "The Wyrm sinks. Slowly. Silently. Back into the black water it crawled out of — "
            "no final roar, no dramatic collapse. Just ripples spreading outward across still water.\n"
            "*A creature that swallowed fleets is gone. And you are still standing.*\n"
            "✨ **The abyss has been answered. Claim what you've earned.**"
        ),
        "base_hp":           8000,
        "hp_per_player":     2000,
        "base_attack":       75,
        "attack_per_player": 15,
        "defense":           30,
        "enrage_pct":        0.20,
        "aoe_every":         4,
        "xp_reward":         5000,
        "copper_reward":     4000,
        "drops": [
            {"item": "Legendary Sword",    "chance": 0.20},
            {"item": "Dragonscale Armor",  "chance": 0.35},
            {"item": "Demon King's Crown", "chance": 0.18},
            {"item": "Void Ring",          "chance": 0.15},
            {"item": "Void Cloak",         "chance": 0.22},
        ],
    },
    "Void Colossus": {
        "emoji":             "🌑",
        "description":       "An entity of pure void that devours light itself.",
        "boss_intro": (
            "There is no dramatic entrance. One moment there is sky. The next — the Void Colossus simply *is*.\n"
            "A shape of pure absence, towering and silent, devouring the light and sound around it. "
            "The air forgets how to carry warmth.\n"
            "*Looking directly at it feels like forgetting who you are.*\n"
            "This is not a fight. This is a reckoning.\n"
            "**Stand together, or be erased alone.**"
        ),
        "aoe_roar": (
            "🌑 **The Void Colossus pulses — a wave of pure nothingness radiates outward, "
            "stripping warmth and will from every hero caught in its wake!**"
        ),
        "victory_msg": (
            "The Void Colossus does not die. It *unravels.*\n"
            "Piece by piece, thread by thread, it dissolves back into the darkness it was made from — "
            "taking the silence with it.\n"
            "Light rushes back in. Sound returns. The world remembers how to breathe.\n"
            "*You just destroyed something that couldn't be destroyed.*\n"
            "✨ **Hold onto that feeling. You may need it again.**"
        ),
        "base_hp":           12000,
        "hp_per_player":     2500,
        "base_attack":       90,
        "attack_per_player": 18,
        "defense":           40,
        "enrage_pct":        0.30,
        "aoe_every":         3,
        "xp_reward":         8000,
        "copper_reward":     6000,
        "drops": [
            {"item": "Demon King's Crown", "chance": 0.25},
            {"item": "Legendary Sword",    "chance": 0.25},
            {"item": "Dragonscale Armor",  "chance": 0.25},
            {"item": "Void Ring",          "chance": 0.25},
            {"item": "Void Cloak",         "chance": 0.30},
        ],
    },
}

# ------------------------------------------------------------------ #
#  GLOBAL STATE  (singleton — reset by spawn/clear functions)
# ------------------------------------------------------------------ #
WORLD_DUNGEON: dict = {
    "active":        False,
    "phase":         "none",   # "joining" | "fighting" | "ended"
    "boss_key":      "",
    "boss_hp":       0,
    "boss_max_hp":   0,
    "boss_attack":   0,
    "boss_defense":  0,
    "total_attacks": 0,        # cumulative global attack counter (for AoE tracking)
    "players":       {},       # uid → {"name": str, "damage": int, "last_attack": float}
    "channel_id":    None,
}


def get_world_dungeon() -> dict:
    """Return the live WORLD_DUNGEON state dict."""
    return WORLD_DUNGEON


def spawn_world_dungeon(boss_key: str | None = None) -> dict:
    """
    Initialize a new world dungeon event (joining phase).
    boss_key must match a key in WORLD_BOSS_CONFIGS, or None for random.
    Returns the updated WORLD_DUNGEON state.
    """
    global WORLD_DUNGEON
    if boss_key is None or boss_key not in WORLD_BOSS_CONFIGS:
        boss_key = random.choice(list(WORLD_BOSS_CONFIGS.keys()))
    cfg = WORLD_BOSS_CONFIGS[boss_key]
    WORLD_DUNGEON.update({
        "active":        True,
        "phase":         "joining",
        "boss_key":      boss_key,
        "boss_hp":       cfg["base_hp"],
        "boss_max_hp":   cfg["base_hp"],
        "boss_attack":   cfg["base_attack"],
        "boss_defense":  cfg["defense"],
        "total_attacks": 0,
        "players":       {},
        "channel_id":    None,
    })
    return WORLD_DUNGEON


def start_world_fight() -> None:
    """
    Scale boss HP/attack to registered player count and open the fighting phase.
    Must be called after the joining window closes.
    """
    global WORLD_DUNGEON
    cfg = WORLD_BOSS_CONFIGS[WORLD_DUNGEON["boss_key"]]
    n = max(1, len(WORLD_DUNGEON["players"]))
    WORLD_DUNGEON["boss_hp"]     = cfg["base_hp"] + cfg["hp_per_player"] * (n - 1)
    WORLD_DUNGEON["boss_max_hp"] = WORLD_DUNGEON["boss_hp"]
    WORLD_DUNGEON["boss_attack"] = cfg["base_attack"] + cfg["attack_per_player"] * (n - 1)
    WORLD_DUNGEON["phase"]       = "fighting"


def join_world_dungeon(uid: int, name: str) -> tuple[bool, str]:
    """
    Register a player in the current world dungeon.
    Returns (success, message).
    """
    wd = WORLD_DUNGEON
    if not wd["active"]:
        return False, "❌ No World Dungeon is currently active."
    if wd["phase"] != "joining":
        return False, "❌ The battle has already begun — too late to join!"
    if uid in wd["players"]:
        return False, "⚔️ You're already enlisted in this battle!"
    wd["players"][uid] = {"name": name, "damage": 0, "last_attack": 0.0}
    count = len(wd["players"])
    return True, f"✅ **{name}** joins the battle! ({count} hero{'es' if count != 1 else ''} assembled)"


def _simple_damage(raw: int, defense: int) -> int:
    """Basic damage-after-defense used within this module."""
    return max(1, raw - defense // 2)


def world_boss_attack(
    attacker_uid: int,
    player: dict,
) -> tuple[int, list[str], bool, list[tuple[int, int]]]:
    """
    Process one `!worldattack` from a player.

    Returns:
        boss_hp_remaining — int
        messages          — list[str] to send in the channel
        boss_is_dead      — bool
        aoe_hits          — list[(uid, damage)] when AoE fires (else [])
    """
    wd = WORLD_DUNGEON
    cfg = WORLD_BOSS_CONFIGS[wd["boss_key"]]
    msgs: list[str] = []
    aoe_hits: list[tuple[int, int]] = []

    pdata = wd["players"][attacker_uid]

    # ── Per-player cooldown (30 s) ────────────────────────────────
    cooldown = 30.0
    now = time.time()
    elapsed = now - pdata["last_attack"]
    if pdata["last_attack"] > 0 and elapsed < cooldown:
        remaining = int(cooldown - elapsed)
        return wd["boss_hp"], [f"⏳ Cooldown! Wait **{remaining}s** before attacking again."], False, []
    pdata["last_attack"] = now

    # ── Player attacks boss ───────────────────────────────────────
    base_raw = random.randint(player["attack"] - 2, player["attack"] + 2)
    crit     = random.random() < player.get("crit_chance", 0.05)
    raw      = int(base_raw * 1.5) if crit else base_raw
    dmg      = _simple_damage(raw, wd["boss_defense"])

    wd["boss_hp"]    = max(0, wd["boss_hp"] - dmg)
    pdata["damage"] += dmg
    wd["total_attacks"] += 1

    cfg_emoji  = cfg["emoji"]
    hp_now     = wd["boss_hp"]
    hp_pct     = int(hp_now / wd["boss_max_hp"] * 100) if wd["boss_max_hp"] else 0
    enraged    = hp_pct <= int(cfg["enrage_pct"] * 100)
    enrage_tag = "  😡 **[ENRAGED]**" if enraged else ""
    crit_tag   = " 💥 *CRITICAL HIT!*" if crit else ""

    msgs.append(
        f"⚔️ **{pdata['name']}** strikes {cfg_emoji} **{wd['boss_key']}** for **{dmg}** dmg!{crit_tag}\n"
        f"{cfg_emoji} Boss HP: **{hp_now:,}/{wd['boss_max_hp']:,}** ({hp_pct}%){enrage_tag}"
    )

    if hp_now <= 0:
        return hp_now, msgs, True, aoe_hits

    # ── Boss retaliates against attacker ─────────────────────────
    atk_mult = 1.5 if enraged else 1.0
    boss_raw  = random.randint(
        int(wd["boss_attack"] * 0.8),
        int(wd["boss_attack"] * 1.2),
    )
    boss_dmg  = max(1, _simple_damage(int(boss_raw * atk_mult), player.get("defense", 5)))
    player["hp"] = max(0, player["hp"] - boss_dmg)

    msgs.append(
        f"💢 {cfg_emoji} **{wd['boss_key']}** retaliates at **{pdata['name']}** for **{boss_dmg}** dmg!\n"
        f"Your HP: **{player['hp']}/{player.get('max_hp', 100)}**"
    )

    # ── AoE every N total attacks ─────────────────────────────────
    aoe_every = cfg.get("aoe_every", 5)
    if wd["total_attacks"] % aoe_every == 0:
        aoe_dmg  = max(10, wd["boss_attack"] // 3)
        aoe_roar = cfg.get("aoe_roar",
            f"🌍 {cfg_emoji} **{wd['boss_key']} UNLEASHES A DEVASTATING ATTACK!** "
            f"All heroes take **{aoe_dmg}** area damage!"
        )
        msgs.append(f"\n{aoe_roar}")
        msgs.append(f"💥 All heroes take **{aoe_dmg}** damage!")
        for uid, pinfo in wd["players"].items():
            aoe_hits.append((uid, aoe_dmg))
            msgs.append(f"  • **{pinfo['name']}** is struck for **{aoe_dmg}** dmg")

    return hp_now, msgs, False, aoe_hits


def distribute_world_rewards(
    boss_key: str,
) -> list[tuple[int, dict]]:
    """
    Calculate proportional rewards for all joined players.

    Returns list of (uid, reward_dict) where reward_dict contains:
        xp, copper, drop (item name or None), damage, pct
    """
    wd  = WORLD_DUNGEON
    cfg = WORLD_BOSS_CONFIGS[boss_key]
    total_dmg = max(1, sum(p["damage"] for p in wd["players"].values()))

    results: list[tuple[int, dict]] = []
    for uid, pdata in wd["players"].items():
        pct    = pdata["damage"] / total_dmg
        # Rewards scale from 50% base (participation) to 100% (MVP)
        xp     = int(cfg["xp_reward"]     * (0.50 + pct * 0.50))
        copper = int(cfg["copper_reward"] * (0.50 + pct * 0.50))
        # Drop roll: base chance amplified by contribution
        drop = None
        for d in cfg["drops"]:
            roll_chance = min(1.0, d["chance"] * (0.5 + pct * 1.5))
            if random.random() < roll_chance:
                drop = d["item"]
                break
        results.append((uid, {
            "xp":     xp,
            "copper": copper,
            "drop":   drop,
            "damage": pdata["damage"],
            "pct":    pct,
        }))
    return results


def clear_world_dungeon() -> None:
    """Reset the world dungeon to its inactive state."""
    global WORLD_DUNGEON
    WORLD_DUNGEON.update({
        "active": False, "phase": "none", "boss_key": "", "boss_hp": 0,
        "boss_max_hp": 0, "boss_attack": 0, "boss_defense": 0,
        "total_attacks": 0, "players": {}, "channel_id": None,
    })


def world_dungeon_status_lines() -> list[str]:
    """Return human-readable status lines for `!worldstatus`."""
    wd = WORLD_DUNGEON
    if not wd["active"]:
        return ["No World Dungeon is currently active. Admins can start one with `!spawnworld`."]
    cfg = WORLD_BOSS_CONFIGS.get(wd["boss_key"], {})
    hp_pct = int(wd["boss_hp"] / wd["boss_max_hp"] * 100) if wd["boss_max_hp"] else 0
    lines = [
        f"{cfg.get('emoji','🌍')} **{wd['boss_key']}** — Phase: `{wd['phase']}`",
        f"HP: **{wd['boss_hp']:,}/{wd['boss_max_hp']:,}** ({hp_pct}%) · "
        f"Players: **{len(wd['players'])}**",
    ]
    if wd["players"]:
        sorted_p = sorted(wd["players"].items(), key=lambda x: x[1]["damage"], reverse=True)
        lines.append("**🏆 Damage Leaderboard:**")
        for i, (uid, p) in enumerate(sorted_p, 1):
            lines.append(f"  {i}. **{p['name']}** — {p['damage']:,} dmg")
    return lines
