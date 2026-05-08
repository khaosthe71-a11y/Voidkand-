"""
bot/rpg/chest.py — Chest drop system.

Provides:
  maybe_find_chest(player, context) -> str | None
  roll_chest_rarity(player, force_min=None) -> str
  open_chest(player, rarity) -> dict
"""
import random
from .player import add_to_inventory, add_currency

# ------------------------------------------------------------------ #
#  RARITY CONFIGURATION
#  Insertion order matters — it controls rarity tier indices.
#  Common=0, Uncommon=1, Rare=2, Epic=3, Legendary=4
# ------------------------------------------------------------------ #
CHEST_RARITIES: dict[str, dict] = {
    "Common": {
        "emoji":        "📦",
        "color":        0x95A5A6,
        "weight":       55,
        "headline":     "You found a **Common Chest**.",
        "open_flavor":  "The dusty lock yields without resistance.",
        "copper_range": (20, 100),
        "potion_pool":  [
            "Minor Healing Potion", "Mana Potion", "Antidote", "Burn Salve",
        ],
        "potion_rolls":  1,
        "potion_chance": 0.45,
        "item_pool":     [],
        "item_chance":   0.0,
    },
    "Uncommon": {
        "emoji":        "💚",
        "color":        0x2ECC71,
        "weight":       25,
        "headline":     "You found an **Uncommon Chest**!",
        "open_flavor":  "The chest glows faintly as you pry it open.",
        "copper_range": (40, 180),
        "potion_pool":  [
            "Minor Healing Potion", "Great Healing Potion", "Mana Potion",
            "Antidote", "Whetstone",
        ],
        "potion_rolls":  1,
        "potion_chance": 0.60,
        "item_pool":     [
            "Iron Sword", "Hunter's Bow", "Leather Armor", "Swiftness Ring",
        ],
        "item_chance":   0.08,
    },
    "Rare": {
        "emoji":        "💙",
        "color":        0x3498DB,
        "weight":       13,
        "headline":     "✨ You found a **Rare Chest**!",
        "open_flavor":  "Blue light spills from the seams as you lift the lid.",
        "copper_range": (80, 300),
        "potion_pool":  [
            "Minor Healing Potion", "Great Healing Potion", "Mana Potion",
            "Strength Potion", "Defense Potion", "Lucky Charm",
        ],
        "potion_rolls":  2,
        "potion_chance": 0.65,
        "item_pool":     [
            "Iron Sword", "Hunter's Bow", "Apprentice Staff",
            "Leather Armor", "Swiftness Ring", "Amulet of Power",
        ],
        "item_chance":   0.18,
    },
    "Epic": {
        "emoji":        "💜",
        "color":        0x9B59B6,
        "weight":       5,
        "headline":     "💜 **EPIC CHEST FOUND!** 💜",
        "open_flavor":  "Purple energy crackles around the chest — and then it bursts open.",
        "copper_range": (250, 700),
        "potion_pool":  [
            "Great Healing Potion", "Greater Mana Potion", "Strength Potion",
            "Defense Potion", "Speed Potion", "Intelligence Elixir",
            "Lucky Potion", "Whetstone", "Arcane Shield",
        ],
        "potion_rolls":  2,
        "potion_chance": 0.85,
        "item_pool":     [
            "Knight's Blade", "Iron Plate", "Mage's Robe",
            "Battle Pendant", "Shadow Blade", "Void Cloak", "Scholar's Band",
        ],
        "item_chance":   0.40,
    },
    "Legendary": {
        "emoji":        "🔥",
        "color":        0xF39C12,
        "weight":       2,
        "headline":     "🔥 **LEGENDARY CHEST UNLOCKED!** 🔥",
        "open_flavor":  "The chest blazes with golden fire. Reality warps around the lid as it opens.",
        "copper_range": (500, 1500),
        "potion_pool":  [
            "Great Healing Potion", "Greater Mana Potion", "Ultimate Power Elixir",
            "Speed Potion", "Intelligence Elixir", "Lucky Potion",
        ],
        "potion_rolls":  3,
        "potion_chance": 1.0,
        "item_pool":     [
            "Legendary Sword", "Dragonscale Armor", "Demon King's Crown",
            "Void Cloak", "Void Ring",
        ],
        "item_chance":   1.0,
    },
}

_RARITY_NAMES   = list(CHEST_RARITIES.keys())           # insertion order preserved
_RARITY_WEIGHTS = [CHEST_RARITIES[r]["weight"] for r in _RARITY_NAMES]

# ------------------------------------------------------------------ #
#  FIND-CHANCE TABLE  (context → probability of a chest spawning)
# ------------------------------------------------------------------ #
_FIND_CHANCES: dict[str, float] = {
    "explore_peaceful":   0.07,    # wandering with no combat — events module handles most of this
    "explore_combat":     0.15,    # won a fight triggered from !explore
    "fight":              0.12,    # won a fight from !fight
    "dungeon_wave":       0.0,     # no per-wave chest (dungeon_clear handles it)
    "dungeon_clear":      1.0,     # guaranteed chest on full dungeon clear
    "boss_event_mvp":     1.0,     # MVP of the server boss event
    "boss_event_contrib": 0.55,    # other contributors
}


# ------------------------------------------------------------------ #
#  PUBLIC API
# ------------------------------------------------------------------ #

def maybe_find_chest(player: dict, context: str) -> "str | None":
    """
    Roll to see if a chest spawns in the given context.
    Returns a rarity string or None if no chest dropped.
    """
    chance = _FIND_CHANCES.get(context, 0.0)
    if chance == 0.0 or random.random() > chance:
        return None
    return roll_chest_rarity(player)


def roll_chest_rarity(player: dict, force_min: "str | None" = None) -> str:
    """
    Pick a rarity using weighted random selection.
    High Luck shifts weight away from Common toward rarer tiers:
      - each Luck point above the base (5) contributes up to 0.5 weight
        redistributed as: Uncommon 40%, Rare 35%, Epic 18%, Legendary 7%.
    force_min guarantees at least that tier (useful for boss rewards).
    """
    luck       = player.get("luck", 5)
    luck_bonus = max(0, luck - 5)
    shift      = min(luck_bonus * 0.5, 20.0)

    weights = list(_RARITY_WEIGHTS)
    weights[0] = max(8.0, weights[0] - shift)   # drain from Common
    weights[1] += shift * 0.40                   # → Uncommon
    weights[2] += shift * 0.35                   # → Rare
    weights[3] += shift * 0.18                   # → Epic
    weights[4] += shift * 0.07                   # → Legendary

    rarity = random.choices(_RARITY_NAMES, weights=weights, k=1)[0]

    if force_min and _RARITY_NAMES.index(rarity) < _RARITY_NAMES.index(force_min):
        rarity = force_min

    return rarity


def open_chest(player: dict, rarity: str) -> dict:
    """
    Generate rewards for the given rarity, apply them to the player's
    inventory and currency, then return a result dict for display.

    Return format:
        {
          "rarity":      str,
          "headline":    str,
          "open_flavor": str,
          "emoji":       str,
          "color":       int,
          "copper":      int,
          "potions":     list[str],
          "items":       list[str],
        }
    """
    cfg = CHEST_RARITIES[rarity]

    # ── Currency ──────────────────────────────────────────────────────
    copper = random.randint(*cfg["copper_range"])
    add_currency(player, copper)

    # ── Potions / consumables ─────────────────────────────────────────
    potions: list[str] = []
    for _ in range(cfg["potion_rolls"]):
        if cfg["potion_pool"] and random.random() < cfg["potion_chance"]:
            item = random.choice(cfg["potion_pool"])
            add_to_inventory(player, item)
            potions.append(item)

    # ── Equipment / rare items ────────────────────────────────────────
    items: list[str] = []
    if cfg["item_pool"] and random.random() < cfg["item_chance"]:
        item = random.choice(cfg["item_pool"])
        add_to_inventory(player, item)
        items.append(item)

    return {
        "rarity":      rarity,
        "headline":    cfg["headline"],
        "open_flavor": cfg["open_flavor"],
        "emoji":       cfg["emoji"],
        "color":       cfg["color"],
        "copper":      copper,
        "potions":     potions,
        "items":       items,
    }
