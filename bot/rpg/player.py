import json
import os
import copy
import random
from .data import (
    DEFAULT_PLAYER_STATE, SAVE_DIR, COPPER_PER_SILVER, SILVER_PER_GOLD,
    world_map, enemy_types, loot_table, quest_data, quest_chains, chain_rewards,
    shop_items, EQUIPMENT_DATA, CLASS_DEFINITIONS, CLASS_SKILLS, CLASS_SKILLS_T2, CLASS_SKILLS_T3, DUNGEON_DATA,
    STATUS_EFFECTS,
)


MAX_CHARACTER_SLOTS = 5
_SLOT_NAME_MAX = 20
_VALID_SLOT_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-")


def get_save_path(user_id: int) -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return os.path.join(SAVE_DIR, f"{user_id}.json")


def new_player() -> dict:
    state = copy.deepcopy(DEFAULT_PLAYER_STATE)
    state["xp_to_next_level"] = calculate_xp_for_next_level(1)
    return state


# ------------------------------------------------------------------ #
#  Internal multi-slot file helpers
# ------------------------------------------------------------------ #

def _load_save_file(user_id: int) -> dict:
    """
    Load the raw multi-slot save file for a user.
    Handles migration of legacy single-player saves.
    Returns a dict: {"_active": str, "characters": {name: state}}.
    """
    path = get_save_path(user_id)
    if not os.path.exists(path):
        return {"_active": "default", "characters": {}}
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        return {"_active": "default", "characters": {}}

    # Detect legacy format: top-level keys are player-state fields, not our envelope
    if "characters" not in data:
        # Wrap the old save as the "default" character slot
        return {"_active": "default", "characters": {"default": data}}

    return data


def _write_save_file(user_id: int, save_data: dict) -> None:
    path = get_save_path(user_id)
    with open(path, "w") as f:
        json.dump(save_data, f, indent=2)


def _migrate_state(raw: dict) -> dict:
    """Apply all field defaults / migrations to a raw player-state dict."""
    state = copy.deepcopy(DEFAULT_PLAYER_STATE)
    state.update(raw)
    if "experience_points" not in raw:
        state["experience_points"] = raw.get("xp", 0)
    if "xp_to_next_level" not in raw:
        state["xp_to_next_level"] = calculate_xp_for_next_level(state["level"])
    if "currency" not in raw:
        state["currency"] = {"gold": 0, "silver": 0, "copper": 0}
    if "quest_log" not in raw:
        state["quest_log"] = {}
    if "completed_quest_chains" not in state:
        state["completed_quest_chains"] = []
    state.setdefault("defense", 5)
    state.setdefault("vitality", 10)
    state.setdefault("mana", 50)
    state.setdefault("max_mana", 50)
    state.setdefault("intelligence", 10)
    state.setdefault("speed", 5)
    state.setdefault("luck", 5)
    state.setdefault("crit_chance", 0.05)
    state.setdefault("class_chosen", False)
    state.setdefault("demon_king_slain", False)
    state.setdefault("pvp_wins", 0)
    state.setdefault("pvp_losses", 0)
    state.setdefault("dungeons_completed", [])
    if not isinstance(state.get("equipped"), dict):
        state["equipped"] = {"weapon": None, "armor": None, "accessory": None}
    else:
        state["equipped"].setdefault("weapon", None)
        state["equipped"].setdefault("armor", None)
        state["equipped"].setdefault("accessory", None)
    state.setdefault("guild_id", None)
    state.setdefault(
        "guild_bonus",
        {"attack": 0, "defense": 0, "max_hp": 0, "crit_chance": 0.0, "speed": 0},
    )
    # ── Faction fields (added in expansion) ───────────────────────────────
    state.setdefault("faction", None)
    state.setdefault("reputation", {"Eclipse": 0, "Divine": 0, "Void": 0})
    state.setdefault("faction_missions_completed", [])
    state.setdefault("faction_kill_tracker", 0)
    state.pop("xp", None)
    return state


# ------------------------------------------------------------------ #
#  Public save / load (always operate on the active slot)
# ------------------------------------------------------------------ #

def save_game(user_id: int, player: dict) -> None:
    save_data = _load_save_file(user_id)
    active = save_data.get("_active", "default")
    save_data["characters"][active] = player
    _write_save_file(user_id, save_data)


def load_game(user_id: int) -> dict | None:
    save_data = _load_save_file(user_id)
    active = save_data.get("_active", "default")
    chars = save_data.get("characters", {})
    if active not in chars:
        return None
    try:
        return _migrate_state(chars[active])
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  Multi-character management
# ------------------------------------------------------------------ #

def _validate_slot_name(name: str) -> tuple[bool, str]:
    """Return (ok, error_message)."""
    clean = name.lower().strip()
    if not clean:
        return False, "Character name cannot be empty."
    if len(clean) > _SLOT_NAME_MAX:
        return False, f"Name too long (max {_SLOT_NAME_MAX} characters)."
    if not all(c in _VALID_SLOT_CHARS for c in clean):
        return False, "Name can only contain letters, numbers, `-` and `_`."
    return True, clean


def list_characters(user_id: int) -> list[dict]:
    """
    Return a list of character summaries for a user.
    Each entry: {"name", "level", "class", "location", "active"}.
    """
    save_data = _load_save_file(user_id)
    active = save_data.get("_active", "default")
    result = []
    for slot_name, raw in save_data.get("characters", {}).items():
        result.append({
            "name":     slot_name,
            "level":    raw.get("level", 1),
            "class":    raw.get("class", "Hunter"),
            "location": raw.get("current_location", "Aetherfall"),
            "active":   slot_name == active,
        })
    return sorted(result, key=lambda c: (not c["active"], c["name"]))


def get_active_slot_name(user_id: int) -> str:
    return _load_save_file(user_id).get("_active", "default")


def create_player_slot(user_id: int, name: str) -> tuple[bool, str]:
    """
    Create a new named character slot. Does NOT switch to it automatically.
    Returns (success, message).
    """
    ok, name_or_err = _validate_slot_name(name)
    if not ok:
        return False, f"❌ {name_or_err}"
    clean = name_or_err

    save_data = _load_save_file(user_id)
    chars = save_data.setdefault("characters", {})

    if clean in chars:
        return False, f"❌ A character named **{clean}** already exists."
    if len(chars) >= MAX_CHARACTER_SLOTS:
        return False, f"❌ You already have {MAX_CHARACTER_SLOTS} characters (the maximum). Delete one first."

    chars[clean] = new_player()
    _write_save_file(user_id, save_data)
    return True, clean


def switch_character(user_id: int, name: str) -> tuple[bool, str]:
    """
    Switch the active character slot. Returns (success, message).
    """
    ok, name_or_err = _validate_slot_name(name)
    if not ok:
        return False, f"❌ {name_or_err}"
    clean = name_or_err

    save_data = _load_save_file(user_id)
    chars = save_data.get("characters", {})
    if clean not in chars:
        names = ", ".join(f"**{n}**" for n in chars) or "none"
        return False, f"❌ No character named **{clean}**. Your characters: {names}"

    save_data["_active"] = clean
    _write_save_file(user_id, save_data)
    return True, clean


def delete_character(user_id: int, name: str) -> tuple[bool, str]:
    """
    Delete a character slot. Cannot delete the active slot.
    Returns (success, message).
    """
    ok, name_or_err = _validate_slot_name(name)
    if not ok:
        return False, f"❌ {name_or_err}"
    clean = name_or_err

    save_data = _load_save_file(user_id)
    chars = save_data.get("characters", {})
    if clean not in chars:
        return False, f"❌ No character named **{clean}**."
    active = save_data.get("_active", "default")
    if clean == active:
        return False, f"❌ Can't delete your active character. Switch to another first."
    if len(chars) <= 1:
        return False, "❌ You only have one character — use `!start` to reset instead."

    del chars[clean]
    _write_save_file(user_id, save_data)
    return True, clean


def calculate_xp_for_next_level(level: int) -> int:
    return int(100 * (level ** 1.2))


def apply_level_up(player: dict) -> list[str]:
    messages = []
    while player["experience_points"] >= player["xp_to_next_level"]:
        player["experience_points"] -= player["xp_to_next_level"]
        player["level"] += 1
        player["attack"]       += 2
        player["defense"]      += 1
        player["max_hp"]       += 10
        player["mana"]         = min(player.get("mana", 50) + 5, player.get("max_mana", 50) + 5)
        player["max_mana"]     = player.get("max_mana", 50) + 5
        player["vitality"]     = player.get("vitality", 10) + 1
        player["intelligence"] = player.get("intelligence", 10) + 1
        player["speed"]        = player.get("speed", 5) + 1
        player["luck"]         = player.get("luck", 5) + 1
        player["hp"] = player["max_hp"]
        player["xp_to_next_level"] = calculate_xp_for_next_level(player["level"])
        messages.append(
            f"⬆️ **LEVEL UP!** You are now **Level {player['level']}**!\n"
            f"ATK: **{player['attack']}** | DEF: **{player['defense']}** | "
            f"HP: **{player['max_hp']}** | SPD: **{player['speed']}** | LCK: **{player['luck']}**"
        )
        if player["level"] == 10 and not player.get("class_chosen"):
            messages.append(
                "🌟 **You've reached Level 10!** A new power awakens within you.\n"
                "Use `!choose_class` to pick your specialization! (Warrior, Mage, Assassin, Paladin, Necromancer, Ranger, Berserker, Elementalist)"
            )
        if player["level"] == 10:
            messages.append("🌑 *A dark presence awakens in Voidkand...*")
        # Level 15 — faction unlock prompt
        if player["level"] == 15 and not player.get("faction"):
            messages.append(
                "⚔️ **You've reached Level 15!** The factions of this world take notice.\n"
                "Three powers have reached out. Choose your allegiance:\n"
                "• 🌘 `!faction choose eclipse` — **Eclipse Empire** (Empress May)\n"
                "• ✨ `!faction choose divine` — **Divine Order** (Lyra)\n"
                "• 💀 `!faction choose void` — **Void Legion** (Demon King)\n"
                "*This choice is permanent. Choose wisely.*"
            )
    return messages


def add_experience(player: dict, amount: int) -> list[str]:
    player["experience_points"] += amount
    msgs = [f"✨ You gained **{amount} XP**!"]
    msgs += apply_level_up(player)
    return msgs


def add_currency(player: dict, copper_amount: int) -> str:
    player["currency"]["copper"] += copper_amount
    if player["currency"]["copper"] >= COPPER_PER_SILVER:
        silver = player["currency"]["copper"] // COPPER_PER_SILVER
        player["currency"]["silver"] += silver
        player["currency"]["copper"] %= COPPER_PER_SILVER
    if player["currency"]["silver"] >= SILVER_PER_GOLD:
        gold = player["currency"]["silver"] // SILVER_PER_GOLD
        player["currency"]["gold"] += gold
        player["currency"]["silver"] %= SILVER_PER_GOLD
    return f"💰 +{copper_amount} copper"


def total_copper(player: dict) -> int:
    c = player["currency"]
    return c["gold"] * SILVER_PER_GOLD * COPPER_PER_SILVER + c["silver"] * COPPER_PER_SILVER + c["copper"]


def spend_copper(player: dict, amount: int) -> bool:
    if total_copper(player) < amount:
        return False
    remaining = total_copper(player) - amount
    player["currency"]["gold"] = remaining // (SILVER_PER_GOLD * COPPER_PER_SILVER)
    remaining %= SILVER_PER_GOLD * COPPER_PER_SILVER
    player["currency"]["silver"] = remaining // COPPER_PER_SILVER
    player["currency"]["copper"] = remaining % COPPER_PER_SILVER
    return True


def format_currency(player: dict) -> str:
    c = player["currency"]
    parts = []
    if c["gold"]:
        parts.append(f"{c['gold']}g")
    if c["silver"]:
        parts.append(f"{c['silver']}s")
    parts.append(f"{c['copper']}c")
    return " ".join(parts)


def add_to_inventory(player: dict, item_name: str) -> str:
    player["inventory"].append(item_name)
    return f"🎒 **{item_name}** added to inventory!"


def remove_from_inventory(player: dict, item_name: str) -> bool:
    if item_name in player["inventory"]:
        player["inventory"].remove(item_name)
        return True
    return False


def advance_time(player: dict) -> str:
    if player["time_of_day"] == "day":
        player["time_of_day"] = "night"
        return "🌙 The sun sets... it is now **night**. Enemies grow stronger."
    else:
        player["time_of_day"] = "day"
        return "☀️ The sun rises... it is now **day**."


# ------------------------------------------------------------------ #
#  QUESTS
# ------------------------------------------------------------------ #
def trigger_quest(player: dict, quest_id: str) -> str | None:
    if quest_id in quest_data and quest_id not in player["quest_log"]:
        q = quest_data[quest_id]
        player["quest_log"][quest_id] = {"status": "active"}
        return f"📜 **New Quest:** {q['name']}\n{q['description']}"
    return None


def complete_quest(player: dict, quest_id: str) -> list[str]:
    msgs = []
    if quest_id not in player["quest_log"]:
        return msgs
    if player["quest_log"][quest_id].get("status") == "completed":
        return msgs
    player["quest_log"][quest_id]["status"] = "completed"
    q = quest_data[quest_id]
    msgs += add_experience(player, q["reward_experience"])
    msgs.append(add_currency(player, q["reward_copper"]))
    msgs.append(f"✅ **Quest Complete:** {q['name']}!")
    for chain_id, chain_quests in quest_chains.items():
        if chain_id in player["completed_quest_chains"]:
            continue
        if all(player["quest_log"].get(qid, {}).get("status") == "completed" for qid in chain_quests):
            player["completed_quest_chains"].append(chain_id)
            reward = chain_rewards[chain_id]
            msgs += add_experience(player, reward["experience_bonus"])
            msgs.append(add_currency(player, reward["copper_bonus"]))
            if reward.get("item"):
                msgs.append(add_to_inventory(player, reward["item"]))
            msgs.append(f"🏆 **Quest Chain Complete!** Bonus rewards received!")
    return msgs


# ------------------------------------------------------------------ #
#  CLASS SYSTEM
# ------------------------------------------------------------------ #
def apply_class(player: dict, class_name: str) -> list[str]:
    """Apply class bonuses to a player. Can only be done once."""
    if player.get("class_chosen"):
        return ["❌ You've already chosen a class."]
    if class_name not in CLASS_DEFINITIONS:
        opts = ", ".join(CLASS_DEFINITIONS.keys())
        return [f"❌ Unknown class. Choose from: {opts}"]

    cls = CLASS_DEFINITIONS[class_name]
    player["class"] = class_name
    player["class_chosen"] = True
    msgs = [f"{cls['emoji']} You became a **{class_name}**! {cls['description']}"]
    for stat, value in cls["bonuses"].items():
        if stat in player:
            player[stat] += value
        else:
            player[stat] = value

    # Make sure HP doesn't exceed max_hp and isn't negative
    player["max_hp"] = max(10, player["max_hp"])
    player["hp"] = min(player["hp"], player["max_hp"])
    player["hp"] = max(1, player["hp"])

    bonus_lines = []
    for stat, val in cls["bonuses"].items():
        sign = "+" if val >= 0 else ""
        bonus_lines.append(f"{sign}{val} {stat.replace('_', ' ').title()}")
    msgs.append("**Bonuses applied:** " + " | ".join(bonus_lines))
    return msgs


# ------------------------------------------------------------------ #
#  EQUIPMENT SYSTEM
# ------------------------------------------------------------------ #
def equip_gear(player: dict, item_name: str) -> list[str]:
    """Equip a weapon, armor, or accessory. Unequips whatever was in that slot first."""
    matched = next((i for i in player["inventory"] if i.lower() == item_name.lower()), None)
    if not matched:
        return [f"❌ **{item_name}** is not in your inventory."]

    eq_info = EQUIPMENT_DATA.get(matched)
    if not eq_info:
        return [f"❌ **{matched}** cannot be equipped."]

    slot = eq_info["slot"]
    msgs = []

    # Unequip existing item in slot first
    old = player["equipped"].get(slot)
    if old:
        msgs += _remove_gear_stats(player, old)

    # Equip new — apply all stat bonuses
    player["equipped"][slot]  = matched
    atk  = eq_info.get("attack_bonus",  0)
    def_ = eq_info.get("defense_bonus", 0)
    hp   = eq_info.get("hp_bonus",      0)
    spd  = eq_info.get("speed_bonus",   0)
    crit = eq_info.get("crit_bonus",    0.0)
    luck = eq_info.get("luck_bonus",    0)
    mana = eq_info.get("mana_bonus",    0)

    player["attack"]      += atk
    player["defense"]     += def_
    player["max_hp"]      += hp
    player["hp"]           = min(player["hp"] + hp, player["max_hp"])
    player["speed"]       += spd
    player["crit_chance"] += crit
    player["luck"]        += luck
    player["max_mana"]     = player.get("max_mana", 50) + mana
    player["mana"]         = min(player.get("mana", 0) + mana, player["max_mana"])

    label = {"weapon": "🗡️ Weapon", "armor": "🛡️ Armor", "accessory": "💍 Accessory"}.get(slot, "⚙️ Gear")
    detail_parts: list[str] = []
    if atk:  detail_parts.append(f"+{atk} ATK")
    if def_: detail_parts.append(f"+{def_} DEF")
    if hp:   detail_parts.append(f"+{hp} Max HP")
    if mana: detail_parts.append(f"+{mana} Mana")
    if spd:  detail_parts.append(f"+{spd} SPD")
    if crit: detail_parts.append(f"+{crit*100:.0f}% Crit")
    if luck: detail_parts.append(f"+{luck} Luck")
    details = " | ".join(detail_parts) if detail_parts else "No stat bonus"

    msgs.append(f"{label} equipped: **{matched}** ({details})")
    if old:
        msgs.append(f"*(Replaced **{old}**)*")
    return msgs


def unequip_gear(player: dict, slot: str) -> list[str]:
    """Unequip the item in the given slot ('weapon', 'armor', or 'accessory')."""
    slot = slot.lower()
    if slot not in ("weapon", "armor", "accessory"):
        return ["❌ Slot must be `weapon`, `armor`, or `accessory`."]
    old = player["equipped"].get(slot)
    if not old:
        return [f"You have nothing equipped in the **{slot}** slot."]
    msgs = _remove_gear_stats(player, old)
    msgs.append(f"✅ Unequipped **{old}** from the {slot} slot.")
    return msgs


def _remove_gear_stats(player: dict, item_name: str) -> list[str]:
    """Internal: strip all stat bonuses of an equipped item from the player."""
    eq_info = EQUIPMENT_DATA.get(item_name)
    if not eq_info:
        return []
    slot = eq_info["slot"]
    player["attack"]      = max(1,    player["attack"]      - eq_info.get("attack_bonus",  0))
    player["defense"]     = max(0,    player["defense"]     - eq_info.get("defense_bonus", 0))
    hp   = eq_info.get("hp_bonus",   0)
    mana = eq_info.get("mana_bonus", 0)
    player["max_hp"]      = max(10,   player["max_hp"]      - hp)
    player["hp"]           = min(player["hp"], player["max_hp"])
    player["speed"]       = max(1,    player.get("speed", 5)  - eq_info.get("speed_bonus",  0))
    player["crit_chance"] = max(0.01, player.get("crit_chance", 0.05) - eq_info.get("crit_bonus", 0.0))
    player["luck"]        = max(0,    player.get("luck", 5)   - eq_info.get("luck_bonus",   0))
    player["max_mana"]    = max(10,   player.get("max_mana", 50) - mana)
    player["mana"]         = min(player.get("mana", 0), player["max_mana"])
    player["equipped"][slot] = None
    return []


# ------------------------------------------------------------------ #
#  ENEMY GENERATION
# ------------------------------------------------------------------ #
def generate_enemy(player: dict) -> dict:
    location_name = player["current_location"]
    loc_info = world_map.get(location_name, {})
    if loc_info.get("is_boss_area"):
        enemy_name = "Demon King" if location_name == "Voidkand" else "Dungeon Lord"
    else:
        non_boss = [e for e in enemy_types if not enemy_types[e].get("is_boss")]
        enemy_name = random.choice(non_boss)

    base = enemy_types[enemy_name].copy()
    base["name"] = enemy_name

    location_level = loc_info.get("level", 1)
    effective_level = max(player["level"], location_level)
    scale = 1 + (effective_level - 1) * 0.1
    base["hp"] = int(base["hp"] * scale)
    base["attack"] = int(base["attack"] * scale)
    base["max_hp"] = base["hp"]  # track for phase detection

    if player["time_of_day"] == "night":
        base["hp"] = int(base["hp"] * 1.2)
        base["attack"] = int(base["attack"] * 1.3)
        base["max_hp"] = base["hp"]
        base["night_buffed"] = True

    return base


# ------------------------------------------------------------------ #
#  COMBAT HELPERS
# ------------------------------------------------------------------ #
def damage_after_defense(raw: int, defense: int) -> int:
    """Defense reduces damage. Minimum 1."""
    return max(1, raw - defense // 2)


def roll_loot(player: dict, enemy_name: str) -> list[str]:
    msgs = []
    for loot in loot_table.get(enemy_name, []):
        if random.random() < loot["chance"]:
            if loot["item"]:
                msgs.append(add_to_inventory(player, loot["item"]))
            elif loot["copper_amount"] > 0:
                msgs.append(add_currency(player, loot["copper_amount"]))
    if not msgs:
        msgs.append("No loot dropped.")
    return msgs


# ------------------------------------------------------------------ #
#  STATUS EFFECT HELPERS  (pure logic, no Discord)
# ------------------------------------------------------------------ #

def apply_status_effect(
    entity: dict,
    effect_name: str,
    statuses: dict,
    turns: int | None = None,
) -> str:
    """
    Apply or refresh a status effect on an entity.

    For buff/debuff effects the stat is modified immediately on the entity dict
    and reverted when the effect expires in tick_status_effects().

    Returns a human-readable notification string (empty on unknown effect).
    """
    eff = STATUS_EFFECTS.get(effect_name)
    if not eff:
        return ""

    duration = turns if turns is not None else eff["default_turns"]
    name = entity.get("name") or entity.get("class", "Target")

    if effect_name in statuses:
        # Refresh duration if already active — don't double-apply stat changes
        statuses[effect_name]["turns"] = max(statuses[effect_name]["turns"], duration)
        return (
            f"{eff['emoji']} **{name}** is already **{eff['label']}**! "
            f"Duration refreshed ({statuses[effect_name]['turns']} turns)."
        )

    entry: dict = {"turns": duration}

    if eff.get("is_dot"):
        entry["damage_per_turn"] = eff["damage_per_turn"]

    if eff.get("is_buff") or eff.get("is_debuff"):
        stat   = eff["stat"]
        amount = eff["amount"]
        entry["stat"]   = stat
        entry["amount"] = amount
        # Apply stat delta immediately; revert on expiry
        entity[stat] = max(0, entity.get(stat, 0) + amount)

    statuses[effect_name] = entry

    if eff.get("is_buff"):
        return (
            f"{eff['emoji']} **{name}** gains **{eff['label']}**! "
            f"(+{eff['amount']} {eff['stat']}, {duration} turns)"
        )
    if eff.get("is_debuff"):
        return (
            f"{eff['emoji']} **{name}** suffers **{eff['label']}**! "
            f"({eff['amount']} {eff['stat']}, {duration} turns)"
        )
    return f"{eff['emoji']} **{name}** is now **{eff['label']}**! ({duration} turns)"


def tick_status_effects(entity: dict, statuses: dict) -> tuple[int, list[str]]:
    """
    Called at the start of each entity's turn.

    - Deals DoT damage from poison / burn.
    - Decrements turn counters.
    - Removes expired effects and reverts any stat changes they applied.

    Returns (total_dot_damage, list_of_messages).
    """
    total_dmg = 0
    msgs: list[str] = []
    expired: list[str] = []
    name = entity.get("name") or entity.get("class", "?")

    for effect_name, entry in statuses.items():
        eff_def = STATUS_EFFECTS.get(effect_name, {})
        dmg = entry.get("damage_per_turn", 0)
        if dmg > 0:
            total_dmg += dmg
            msgs.append(
                f"{eff_def.get('emoji', '💢')} **{name}** takes **{dmg}** damage "
                f"from **{eff_def.get('label', effect_name)}**!"
            )
        entry["turns"] -= 1
        if entry["turns"] <= 0:
            expired.append(effect_name)

    for effect_name in expired:
        entry = statuses.pop(effect_name)
        eff_def = STATUS_EFFECTS.get(effect_name, {})
        # Revert stat changes
        if "stat" in entry and "amount" in entry:
            entity[entry["stat"]] = max(0, entity.get(entry["stat"], 0) - entry["amount"])
        msgs.append(f"✨ **{name}**'s **{eff_def.get('label', effect_name)}** wore off.")

    return total_dmg, msgs


def use_item(player: dict, item_name: str) -> tuple[bool, str]:
    """
    Universal item-use function. Works in combat and out.
    Returns (success, message).
    Passive items (Lucky Charm) and gear cannot be 'used'.
    """
    if item_name not in player["inventory"]:
        return False, f"❌ You don't have **{item_name}**."

    info = shop_items.get(item_name)
    if not info:
        return False, f"❌ **{item_name}** has no use effect."

    item_type = info.get("type", "")
    amount    = info.get("amount", 0)
    stat      = info.get("stat")
    permanent = info.get("permanent", False)

    if item_type == "passive":
        return False, f"**{item_name}** is a passive item — it works automatically while held."

    if item_type == "gear":
        return False, f"**{item_name}** must be equipped with `!equip`, not used."

    if item_type == "heal":
        restored = min(amount, player["max_hp"] - player["hp"])
        player["hp"] = min(player["max_hp"], player["hp"] + amount)
        remove_from_inventory(player, item_name)
        return True, (
            f"💊 Used **{item_name}**: restored **{restored} HP**. "
            f"HP: **{player['hp']}/{player['max_hp']}**"
        )

    if item_type == "mana":
        max_mana = player.get("max_mana", 50)
        restored = min(amount, max_mana - player.get("mana", 0))
        player["mana"] = min(max_mana, player.get("mana", 0) + amount)
        remove_from_inventory(player, item_name)
        return True, (
            f"🔵 Used **{item_name}**: restored **{restored} Mana**. "
            f"Mana: **{player['mana']}/{max_mana}**"
        )

    if item_type == "buff" and stat:
        old_val = player.get(stat, 0)
        player[stat] = old_val + amount
        remove_from_inventory(player, item_name)
        perm_note = " *(permanent)*" if permanent else " *(this fight)*"
        stat_label = stat.replace("_", " ").title()
        return True, (
            f"⚡ Used **{item_name}**: **{stat_label}** +{amount}{perm_note}. "
            f"Now: **{player[stat]}**"
        )

    if item_type == "cure":
        remove_from_inventory(player, item_name)
        cures = info.get("cures", [])
        labels = ", ".join(
            STATUS_EFFECTS.get(c, {}).get("label", c) for c in cures
        )
        return True, f"🌿 Used **{item_name}**: ready to cure **{labels}**."

    if item_type == "status_buff":
        remove_from_inventory(player, item_name)
        sname = info.get("status", "")
        eff = STATUS_EFFECTS.get(sname, {})
        label = eff.get("label", sname)
        turns = eff.get("default_turns", 3)
        return True, (
            f"⚡ Used **{item_name}**: **{label}** for **{turns} turns**!"
        )

    return False, f"**{item_name}** can't be used right now."


def use_item_in_combat(player: dict, item_name: str) -> tuple[bool, str]:
    """Alias for use_item — kept for backwards compatibility."""
    return use_item(player, item_name)


# ------------------------------------------------------------------ #
#  PvP SIMULATION  (pure logic, no Discord)
# ------------------------------------------------------------------ #

def enter_dungeon(player: dict, dungeon_name: str) -> tuple[bool, str, dict | None]:
    """
    Validate a player's ability to enter a dungeon.

    Returns:
        (success, message, dungeon_data)
        success=False if level too low, HP too low, or dungeon doesn't exist.
    """
    dungeon = DUNGEON_DATA.get(dungeon_name)
    if not dungeon:
        names = ", ".join(f"**{n}**" for n in DUNGEON_DATA)
        return False, f"❌ Unknown dungeon. Available: {names}", None

    min_level = dungeon["min_level"]
    if player["level"] < min_level:
        return (
            False,
            f"❌ **{dungeon_name}** requires Level **{min_level}+**. You are Level {player['level']}.",
            None,
        )

    hp_pct = player["hp"] / max(1, player["max_hp"])
    if hp_pct < 0.25:
        return (
            False,
            f"❌ You need at least **25% HP** to enter a dungeon. Use `!rest` first.",
            None,
        )

    return True, f"Entering **{dungeon_name}**...", dungeon


def start_pvp(p1: dict, p2: dict) -> dict:
    """
    Simulate a full automated PvP match between two player dicts.
    No items or skills are used — pure stat-based auto-combat.

    Returns:
        {
          "winner_idx": 1 | 2 | None,   # None = draw / timeout
          "rounds": int,
          "hp1_remaining": int,
          "hp2_remaining": int,
          "log": list[str],
        }
    """
    hp1 = p1["hp"]
    hp2 = p2["hp"]
    rounds = 0
    log: list[str] = []
    MAX_ROUNDS = 30

    # Higher speed goes first; ties broken randomly
    p1_first = p1.get("speed", 5) > p2.get("speed", 5) or (
        p1.get("speed", 5) == p2.get("speed", 5) and random.random() < 0.5
    )

    while hp1 > 0 and hp2 > 0 and rounds < MAX_ROUNDS:
        rounds += 1
        first, second = (p1, p2) if p1_first else (p2, p1)

        # First player attacks second
        crit = random.random() < first.get("crit_chance", 0.05)
        raw = random.randint(first["attack"] - 2, first["attack"] + 2)
        if crit:
            raw = int(raw * 1.75)
        dmg = damage_after_defense(raw, second.get("defense", 5))

        if p1_first:
            hp2 = max(0, hp2 - dmg)
        else:
            hp1 = max(0, hp1 - dmg)
        log.append(
            f"R{rounds}a: {first.get('class','?')} → {dmg} dmg"
            + (" (CRIT)" if crit else "")
        )

        if hp1 <= 0 or hp2 <= 0:
            break

        # Second player attacks first
        crit = random.random() < second.get("crit_chance", 0.05)
        raw = random.randint(second["attack"] - 2, second["attack"] + 2)
        if crit:
            raw = int(raw * 1.75)
        dmg = damage_after_defense(raw, first.get("defense", 5))

        if p1_first:
            hp1 = max(0, hp1 - dmg)
        else:
            hp2 = max(0, hp2 - dmg)
        log.append(
            f"R{rounds}b: {second.get('class','?')} → {dmg} dmg"
            + (" (CRIT)" if crit else "")
        )

    if hp1 <= 0 and hp2 <= 0:
        winner_idx = None
    elif hp1 <= 0:
        winner_idx = 2
    elif hp2 <= 0:
        winner_idx = 1
    else:
        # Round limit — whoever has more HP % wins
        pct1 = hp1 / max(1, p1["max_hp"])
        pct2 = hp2 / max(1, p2["max_hp"])
        if pct1 > pct2:
            winner_idx = 1
        elif pct2 > pct1:
            winner_idx = 2
        else:
            winner_idx = None

    return {
        "winner_idx": winner_idx,
        "rounds": rounds,
        "hp1_remaining": hp1,
        "hp2_remaining": hp2,
        "log": log,
    }


def use_skill(player: dict, enemy: dict, enemy_hp: int) -> tuple[int, list[str], dict]:
    """
    Execute the player's class skill in combat, choosing the highest
    skill tier unlocked by the player's current level:
      Tier 1 — Level 10  (base skill)
      Tier 2 — Level 20  (advanced skill, CLASS_SKILLS_T2)
      Tier 3 — Level 30  (ultimate skill, CLASS_SKILLS_T3)

    Returns:
        new_enemy_hp — updated enemy HP after skill damage
        messages     — list of strings to send
        flags        — {"stunned": bool, "apply_status": str|None}
    """
    player_class = player.get("class", "Hunter")
    msgs: list[str] = []
    flags: dict = {"stunned": False, "apply_status": None}

    # ── Select the highest unlocked skill tier ────────────────────
    level = player.get("level", 1)
    if level >= 30 and player_class in CLASS_SKILLS_T3:
        skill = CLASS_SKILLS_T3[player_class]
        tier  = 3
    elif level >= 20 and player_class in CLASS_SKILLS_T2:
        skill = CLASS_SKILLS_T2[player_class]
        tier  = 2
    else:
        skill = CLASS_SKILLS.get(player_class)
        tier  = 1

    if not skill:
        return enemy_hp, [
            "❌ **Hunter** class has no skill. "
            "Choose a class at Level 10 with `!choose_class`."
        ], flags

    mana_cost    = skill["mana_cost"]
    current_mana = player.get("mana", 0)
    if current_mana < mana_cost:
        max_mana = player.get("max_mana", 50)
        return enemy_hp, [
            f"❌ Not enough mana! **{skill['name']}** costs **{mana_cost} Mana**. "
            f"You have **{current_mana}/{max_mana}**."
        ], flags

    player["mana"] = current_mana - mana_cost
    emoji     = skill["emoji"]
    name      = skill["name"]
    mana_line = f"Mana: **{player['mana']}/{player.get('max_mana', 50)}**"
    max_hp    = player.get("max_hp", 100)

    # ── WARRIOR ───────────────────────────────────────────────────
    if player_class == "Warrior":
        if tier == 3:           # Warlord's Might: 3.5× dmg, ignore 30% def, 55% stun
            reduced_def = int(enemy.get("defense", 0) * 0.70)
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, reduced_def)
            enemy_hp = max(0, enemy_hp - dmg)
            stunned = random.random() < skill["stun_chance"]
            flags["stunned"] = stunned
            flags["apply_status"] = "stun" if stunned else None
            stun_tag = " 😵 **Enemy STUNNED!**" if stunned else ""
            msgs.append(
                f"{emoji} **{name}!** A devastating blow for **{dmg}** dmg! *(ignores 30% defense)*{stun_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Taunt: no damage, heal 30% max HP, defense buff
            heal = max(1, int(max_hp * skill.get("heal_pct_of_maxhp", 0.30)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            flags["apply_status"] = "defense_buff"
            msgs.append(
                f"{emoji} **{name}!** You issue a battle cry! **+{heal} HP** restored. "
                f"🛡️ **Defense Up!**\n"
                f"Your HP: **{player['hp']}/{max_hp}** | {mana_line}"
            )
        else:                   # Shield Bash: 1.5× dmg, 40% stun
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            stunned = random.random() < skill["stun_chance"]
            flags["stunned"] = stunned
            flags["apply_status"] = "stun" if stunned else None
            stun_tag = " 😵 **Enemy is STUNNED** — they skip their next attack!" if stunned else ""
            msgs.append(
                f"{emoji} **{name}!** You slam the enemy for **{dmg}** dmg!{stun_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── MAGE ──────────────────────────────────────────────────────
    elif player_class == "Mage":
        intel = player.get("intelligence", 10)
        if tier == 3:           # Arcane Nova: intel×4+atk, ignores ALL def, stun
            raw = intel * 4 + player["attack"]
            dmg = damage_after_defense(raw, 0)
            enemy_hp = max(0, enemy_hp - dmg)
            flags["stunned"] = True
            flags["apply_status"] = "stun"
            msgs.append(
                f"{emoji} **{name}!** Reality shatters — **{dmg}** magic dmg! *(ignores all armor)* "
                f"🌟 **Burns** and 😵 **Stuns** the enemy!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Firestorm: intel×3, ignores ALL def, burn
            raw = intel * 3
            dmg = damage_after_defense(raw, 0)
            enemy_hp = max(0, enemy_hp - dmg)
            flags["apply_status"] = "burn"
            msgs.append(
                f"{emoji} **{name}!** A raging firestorm deals **{dmg}** magic dmg! *(ignores all armor)* "
                f"🔥 **Burning!**\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Fireball: intel×2+atk, ignores half def, burn
            raw = intel * 2 + player["attack"]
            half_def = enemy.get("defense", 0) // 2
            dmg = damage_after_defense(raw, half_def)
            enemy_hp = max(0, enemy_hp - dmg)
            flags["apply_status"] = "burn"
            msgs.append(
                f"{emoji} **{name}!** A blazing fireball erupts for **{dmg}** magic dmg! "
                f"*(pierces half armor)* 🔥 Sets the enemy **Burning**!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── ASSASSIN ──────────────────────────────────────────────────
    elif player_class == "Assassin":
        if tier == 3:           # Death Mark: 4.5× guaranteed crit, poison
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            flags["apply_status"] = "poison"
            msgs.append(
                f"{emoji} **{name}!** A lethal strike for **{dmg}** dmg! 💥 *Guaranteed crit!* "
                f"🟢 **Poison** + ⚔️ **Attack Debuff** applied!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Blade Dance: 3 hits at 1.3×, 60% crit each, poison
            hit_dmgs: list[int] = []
            any_crit = False
            for _ in range(3):
                raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
                if random.random() < 0.60:
                    raw = int(raw * 1.5)
                    any_crit = True
                hit = max(1, damage_after_defense(raw, enemy.get("defense", 0)))
                enemy_hp = max(0, enemy_hp - hit)
                hit_dmgs.append(hit)
            total    = sum(hit_dmgs)
            hit_str  = " + ".join(str(h) for h in hit_dmgs)
            crit_tag = " 💥 *Multiple crits!*" if any_crit else ""
            flags["apply_status"] = "poison"
            msgs.append(
                f"{emoji} **{name}!** Three rapid strikes: {hit_str} = **{total}** dmg!{crit_tag} "
                f"🟢 **Poison** applied!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Shadow Strike: 2.5× guaranteed crit, poison
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            flags["apply_status"] = "poison"
            msgs.append(
                f"{emoji} **{name}!** You strike from the shadows for **{dmg}** dmg! 💥 *Guaranteed crit!* "
                f"🟢 Applies **Poison**!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── PALADIN ───────────────────────────────────────────────────
    elif player_class == "Paladin":
        if tier == 3:           # Sacred Judgment: 2.5× dmg, heal 60% of dmg, defense buff
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            heal = max(1, int(dmg * skill.get("heal_pct", 0.60)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            flags["apply_status"] = "defense_buff"
            msgs.append(
                f"{emoji} **{name}!** Divine light strikes for **{dmg}** dmg! "
                f"✨ Healed **{heal} HP** + 🛡️ **Defense Up!**\n"
                f"Your HP: **{player['hp']}/{max_hp}** | {mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Divine Shield: no attack, heal 50% max HP, defense buff
            heal = max(1, int(max_hp * skill.get("heal_pct_of_maxhp", 0.50)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            flags["apply_status"] = "defense_buff"
            msgs.append(
                f"{emoji} **{name}!** Holy light envelops you — **+{heal} HP** restored! 🛡️ **Defense Up!**\n"
                f"Your HP: **{player['hp']}/{max_hp}** | {mana_line}"
            )
        else:                   # Holy Strike: 1.5× dmg, heal 30% of dmg
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            heal = max(1, int(dmg * skill.get("heal_pct", 0.30)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            msgs.append(
                f"{emoji} **{name}!** A blessed strike hits for **{dmg}** dmg! "
                f"✨ Holy light heals you for **{heal} HP**!\n"
                f"Your HP: **{player['hp']}/{max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── NECROMANCER ───────────────────────────────────────────────
    elif player_class == "Necromancer":
        intel = player.get("intelligence", 10)
        if tier == 3:           # Undead Legion: 3 minion strikes at intel×0.8, ignores 50% def
            reduced_def = int(enemy.get("defense", 0) * 0.50)
            minion_dmgs: list[int] = []
            for _ in range(3):
                raw = int(intel * skill["damage_mult"])
                hit = max(1, damage_after_defense(raw, reduced_def))
                enemy_hp = max(0, enemy_hp - hit)
                minion_dmgs.append(hit)
            total    = sum(minion_dmgs)
            hits_str = " + ".join(str(h) for h in minion_dmgs)
            msgs.append(
                f"{emoji} **{name}!** Three undead minions rise and strike: "
                f"{hits_str} = **{total}** dark dmg! *(ignores 50% defense)*\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Bone Nova: intel×2, ignores 50% def, 35% stun, poison
            reduced_def = int(enemy.get("defense", 0) * 0.50)
            raw = int(intel * skill["damage_mult"])
            dmg = damage_after_defense(raw, reduced_def)
            enemy_hp = max(0, enemy_hp - dmg)
            stunned = random.random() < skill.get("stun_chance", 0.35)
            flags["stunned"] = stunned
            flags["apply_status"] = "stun" if stunned else "poison"
            stun_tag = " 😵 **Enemy STUNNED!**" if stunned else " 🟢 **Poison** applied!"
            msgs.append(
                f"{emoji} **{name}!** Bone shards explode for **{dmg}** dark dmg! "
                f"*(ignores 50% defense)*{stun_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Raise Dead: intel×1.5, ignores 30% def, 40% bonus minion
            reduced_def = int(enemy.get("defense", 0) * 0.70)
            raw = int(intel * skill["damage_mult"])
            dmg = damage_after_defense(raw, reduced_def)
            enemy_hp = max(0, enemy_hp - dmg)
            bonus_msg = ""
            if random.random() < skill.get("bonus_hit_chance", 0.40):
                bonus_raw = int(intel * 0.5)
                bonus_dmg = max(1, damage_after_defense(bonus_raw, reduced_def))
                enemy_hp  = max(0, enemy_hp - bonus_dmg)
                bonus_msg = f" 💀 A spectral minion follows up for **{bonus_dmg}** more dmg!"
            msgs.append(
                f"{emoji} **{name}!** Dark energy strikes for **{dmg}** dmg!{bonus_msg}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── RANGER ────────────────────────────────────────────────────
    elif player_class == "Ranger":
        if tier == 3:           # Sniper's Mark: 4× guaranteed crit, ignores 50% def
            half_def = enemy.get("defense", 0) // 2
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, half_def)
            enemy_hp = max(0, enemy_hp - dmg)
            msgs.append(
                f"{emoji} **{name}!** A perfect sniper shot hits for **{dmg}** dmg! "
                f"💥 *Guaranteed crit! Ignores 50% defense!*\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Explosive Shot: 2.2× dmg, 45% stun
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            stunned = random.random() < skill.get("stun_chance", 0.45)
            flags["stunned"] = stunned
            flags["apply_status"] = "stun" if stunned else None
            stun_tag = " 💥 **EXPLOSIVE!** Enemy stunned!" if stunned else ""
            msgs.append(
                f"{emoji} **{name}!** An explosive arrow detonates for **{dmg}** dmg!{stun_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Arrow Rain: 2-3 hits at 0.7×
            num_hits  = random.randint(2, 3)
            hit_dmgs2: list[int] = []
            for _ in range(num_hits):
                raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
                hit = max(1, damage_after_defense(raw, enemy.get("defense", 0)))
                enemy_hp = max(0, enemy_hp - hit)
                hit_dmgs2.append(hit)
            total   = sum(hit_dmgs2)
            hit_str = " + ".join(str(h) for h in hit_dmgs2)
            msgs.append(
                f"{emoji} **{name}!** You fire **{num_hits} arrows**: {hit_str} = **{total}** total dmg!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── BERSERKER ─────────────────────────────────────────────────
    elif player_class == "Berserker":
        berserker_max_hp = max(1, max_hp)
        hp_pct    = player.get("hp", berserker_max_hp) / berserker_max_hp
        rage_bonus = max(0.0, 1.0 - hp_pct) * 0.80
        rage_tag   = f" 🔥 *RAGE BONUS +{rage_bonus*100:.0f}%!*" if rage_bonus > 0.05 else ""
        if tier == 3:           # Apocalyptic Rage: 5× + rage, guaranteed crit, 20% recoil
            actual_mult = skill["damage_mult"] * (1.0 + rage_bonus)
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * actual_mult)
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp  = max(0, enemy_hp - dmg)
            self_dmg  = max(1, int(dmg * 0.20))
            player["hp"] = max(0, player["hp"] - self_dmg)
            msgs.append(
                f"{emoji} **{name}!** Apocalyptic fury for **{dmg}** dmg!{rage_tag} 💥 *Guaranteed crit!*\n"
                f"⚠️ Recoil: **{self_dmg}** damage to yourself!\n"
                f"Your HP: **{player['hp']}/{berserker_max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Blood Frenzy: 3× + rage, 15% recoil
            actual_mult = skill["damage_mult"] * (1.0 + rage_bonus)
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * actual_mult)
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp  = max(0, enemy_hp - dmg)
            self_dmg  = max(1, int(dmg * 0.15))
            player["hp"] = max(0, player["hp"] - self_dmg)
            msgs.append(
                f"{emoji} **{name}!** A frenzied assault for **{dmg}** dmg!{rage_tag}\n"
                f"⚠️ Blood frenzy recoil: **{self_dmg}** damage!\n"
                f"Your HP: **{player['hp']}/{berserker_max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Rage Slash: 2× + rage bonus
            actual_mult = skill["damage_mult"] * (1.0 + rage_bonus)
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * actual_mult)
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            msgs.append(
                f"{emoji} **{name}!** You slash with savage fury for **{dmg}** dmg!{rage_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── ELEMENTALIST ──────────────────────────────────────────────
    elif player_class == "Elementalist":
        intel = player.get("intelligence", 10)
        if tier == 3:           # Cataclysm: intel×4+atk, ignores ALL def, burn+freeze
            raw = int(intel * skill["damage_mult"] + player["attack"])
            dmg = damage_after_defense(raw, 0)
            enemy_hp = max(0, enemy_hp - dmg)
            flags["apply_status"] = "burn"
            msgs.append(
                f"{emoji} **{name}!** A catastrophic eruption hits for **{dmg}** dmg! "
                f"*(ignores all armor)* 🔥 **Burns** + ❄️ **Freezes** the enemy!\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Chain Lightning: intel×2.5+atk, half-def, 40% stun, 50% chain
            raw = int(intel * skill["damage_mult"] + player["attack"])
            half_def = enemy.get("defense", 0) // 2
            dmg = damage_after_defense(raw, half_def)
            enemy_hp = max(0, enemy_hp - dmg)
            bonus_msg = ""
            if random.random() < skill.get("bonus_hit_chance", 0.50):
                chain_raw = int(intel * 0.8)
                chain_dmg = max(1, damage_after_defense(chain_raw, 0))
                enemy_hp  = max(0, enemy_hp - chain_dmg)
                bonus_msg = f" ⚡ Chain bounces for **{chain_dmg}** more!"
            stunned = random.random() < skill.get("stun_chance", 0.40)
            flags["stunned"] = stunned
            flags["apply_status"] = "stun" if stunned else None
            stun_tag = " 😵 **Enemy STUNNED!**" if stunned else ""
            msgs.append(
                f"{emoji} **{name}!** Lightning arcs for **{dmg}** dmg!{bonus_msg}{stun_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Ice Storm: intel×1.8+atk, half-def, 60% freeze
            raw = int(intel * skill["damage_mult"] + player["attack"])
            half_def = enemy.get("defense", 0) // 2
            dmg = damage_after_defense(raw, half_def)
            enemy_hp = max(0, enemy_hp - dmg)
            slowed = random.random() < skill.get("slow_chance", 0.60)
            flags["apply_status"] = "attack_debuff" if slowed else None
            slow_tag = " ❄️ **Enemy FROZEN** — their attack is reduced!" if slowed else ""
            msgs.append(
                f"{emoji} **{name}!** A blizzard erupts for **{dmg}** ice dmg! *(pierces half armor)*{slow_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── TANK ──────────────────────────────────────────────────────
    elif player_class == "Tank":
        if tier == 3:           # Juggernaut: 2.8× dmg, heal 30% of dmg, defense buff
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            heal = max(1, int(dmg * skill.get("heal_pct", 0.30)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            flags["apply_status"] = "defense_buff"
            msgs.append(
                f"{emoji} **{name}!** An unstoppable charge hits for **{dmg}** dmg! "
                f"💪 Healed **{heal} HP** + 🛡️ **Defense Up!**\n"
                f"Your HP: **{player['hp']}/{max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Fortress Stance: no attack, heal 45% max HP, defense buff
            heal = max(1, int(max_hp * skill.get("heal_pct_of_maxhp", 0.45)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            flags["apply_status"] = "defense_buff"
            msgs.append(
                f"{emoji} **{name}!** You become a fortress — **+{heal} HP** + 🛡️ **Massive Defense Up!**\n"
                f"Your HP: **{player['hp']}/{max_hp}** | {mana_line}"
            )
        else:                   # Shield Wall: 0.8× dmg, heal 20% max HP, defense buff
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            heal = max(1, int(max_hp * skill.get("heal_pct_of_maxhp", 0.20)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            flags["apply_status"] = "defense_buff"
            msgs.append(
                f"{emoji} **{name}!** Your shield slams for **{dmg}** dmg! "
                f"🏰 +{heal} HP restored + 🛡️ **Defense Up!**\n"
                f"Your HP: **{player['hp']}/{max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    # ── MONK ──────────────────────────────────────────────────────
    elif player_class == "Monk":
        if tier == 3:           # Void Palm: 2.8× dmg, heal 40% of dmg, ignores 50% def
            half_def = enemy.get("defense", 0) // 2
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, half_def)
            enemy_hp = max(0, enemy_hp - dmg)
            heal = max(1, int(dmg * skill.get("heal_pct", 0.40)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            msgs.append(
                f"{emoji} **{name}!** Void energy channels for **{dmg}** dmg! *(ignores 50% defense)* "
                f"💚 Absorbed **{heal} HP**!\n"
                f"Your HP: **{player['hp']}/{max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        elif tier == 2:         # Chi Burst: 3 hits at 0.9×, 35% stun per hit
            hit_dmgs3: list[int] = []
            stunned = False
            for _ in range(3):
                raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
                hit = max(1, damage_after_defense(raw, enemy.get("defense", 0)))
                enemy_hp = max(0, enemy_hp - hit)
                hit_dmgs3.append(hit)
                if not stunned and random.random() < skill.get("stun_chance", 0.35):
                    stunned = True
            total    = sum(hit_dmgs3)
            hit_str  = " + ".join(str(h) for h in hit_dmgs3)
            flags["stunned"] = stunned
            flags["apply_status"] = "stun" if stunned else None
            stun_tag = " 😵 **Enemy STUNNED!**" if stunned else ""
            msgs.append(
                f"{emoji} **{name}!** Rapid ki strikes: {hit_str} = **{total}** total dmg!{stun_tag}\n"
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )
        else:                   # Dragon Fist: 1.8× dmg, heal 25% of dmg
            raw = int(random.randint(player["attack"] - 2, player["attack"] + 2) * skill["damage_mult"])
            dmg = damage_after_defense(raw, enemy.get("defense", 0))
            enemy_hp = max(0, enemy_hp - dmg)
            heal = max(1, int(dmg * skill.get("heal_pct", 0.25)))
            player["hp"] = min(max_hp, player["hp"] + heal)
            msgs.append(
                f"{emoji} **{name}!** A focused strike channels for **{dmg}** dmg! "
                f"💚 Lifesteal: **+{heal} HP**!\n"
                f"Your HP: **{player['hp']}/{max_hp}** | "
                f"{mana_line} | Enemy HP: **{max(0, enemy_hp)}**"
            )

    else:
        return enemy_hp, [f"❌ **{player_class}** has no defined skill."], flags

    return enemy_hp, msgs, flags
