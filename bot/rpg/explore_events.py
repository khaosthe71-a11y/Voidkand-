"""
bot/rpg/explore_events.py — Mini-event system for peaceful explores.

When no combat / rift / dungeon encounter fires during exploration,
one of these events is chosen to replace the flat "nothing happened" message.

Public API:
    pick_explore_event()    -> str             (event name)
    EVENT_CONFIG            — per-event configuration dict
    LOCATION_EXPLORE_INTRO  — per-location immersive intro text
    LOCATION_EXPLORE_COLOR  — per-location embed color
"""

import random

# ------------------------------------------------------------------ #
#  EVENT REGISTRY  (name, weight)
# ------------------------------------------------------------------ #
_EVENTS: list[tuple[str, int]] = [
    ("healing_spring",    15),
    ("treasure_cache",    14),
    ("hidden_notes",      18),
    ("rare_find",         10),
    ("wandering_merchant", 9),
    ("echo_of_battle",     9),
    ("ominous_silence",   25),
]
_EVENT_NAMES   = [e[0] for e in _EVENTS]
_EVENT_WEIGHTS = [e[1] for e in _EVENTS]

# ------------------------------------------------------------------ #
#  PER-LOCATION IMMERSIVE INTRO TEXT
# ------------------------------------------------------------------ #
LOCATION_EXPLORE_INTRO: dict[str, str] = {
    # ── Original locations ─────────────────────────────────────────────────
    "Aetherfall":
        "You navigate the crumbling outer districts, stepping over broken glass and rusted fencing. "
        "The city feels more dangerous every time.",
    "Gravefall":
        "The half-destroyed city groans around you. Every shadow hides something hungry. "
        "Fires still burn in the distance — the siege never truly ended.",
    "Rotveil":
        "The stench of rot is everywhere. Undead drag themselves through the fog ahead. "
        "The city died long ago; the dead just haven't accepted it.",
    "Nerathis":
        "Bioluminescent organisms pulse on the underwater walls, casting the ruins in pale blue light. "
        "The pressure is immense. The silence down here is total.",
    "Eclipse Citadel":
        "The Empire's power radiates through every stone. Guards patrol in formation. "
        "Everything here is a statement of dominance — including the architecture.",
    "Voidkand":
        "Reality stutters. Time moves strangely. The Demon King's throne can't be far now. "
        "The air tastes of copper and ozone. Something vast is nearby.",
    "Dungeon Gate":
        "The gate looms above — massive, ancient, carved with warnings in a dead language. "
        "Whatever built this wanted to keep something in. Or keep you out.",
    # ── New locations ──────────────────────────────────────────────────────
    "Frostmourne Wastes":
        "The wind cuts like a blade. Ice stretches to every horizon, broken only by the bones of "
        "things that didn't survive. Your breath mists instantly. The cold wants inside you.",
    "Ashen Ruins":
        "Ash drifts in lazy spirals. The ruins still glow in places — not with warmth, "
        "but with something that refuses to go out. The streets crunch under your boots.",
    "Celestial Peak":
        "The air is thin and bright and smells of something ancient and clean. "
        "Far below, clouds fill the valleys. Up here, nothing feels entirely mortal.",
    "Shadow Mire":
        "Black water reflects nothing. The reeds don't move even when you disturb them. "
        "Somewhere ahead, something large shifts its weight and goes still again.",
    "Iron Bastion":
        "The fortress breathes discipline. Walls within walls. Checkpoints with no one at them. "
        "The garrison is here — you can feel it — but they are not moving. Not anymore.",
    "Abyssal Gate":
        "The Gate stands open. It has always been open. The void on the other side isn't "
        "dark exactly — it's the absence of anything to call dark. You step forward anyway.",
}

LOCATION_EXPLORE_COLOR: dict[str, int] = {
    # ── Original locations ─────────────────────────────────────────────────
    "Aetherfall":         0x6C757D,
    "Gravefall":          0x343A40,
    "Rotveil":            0x4A5240,
    "Nerathis":           0x17A2B8,
    "Eclipse Citadel":    0x4B0082,
    "Voidkand":           0x2C2F33,
    "Dungeon Gate":       0x6F4E37,
    # ── New locations ──────────────────────────────────────────────────────
    "Frostmourne Wastes": 0xA8DADC,
    "Ashen Ruins":        0x8B3A1F,
    "Celestial Peak":     0xFFD700,
    "Shadow Mire":        0x1A1A2E,
    "Iron Bastion":       0x555C6E,
    "Abyssal Gate":       0x2E003E,
}

# ------------------------------------------------------------------ #
#  PER-EVENT CONFIGURATION
# ------------------------------------------------------------------ #
EVENT_CONFIG: dict[str, dict] = {
    "healing_spring": {
        "emoji": "💧",
        "title": "Healing Spring",
        "color": 0x2ECC71,
        "flavors": [
            "A glimmering spring bubbles from between the rocks. You cup the cool water and drink deep.",
            "Ancient runes mark a mossy font — its waters pulse with restorative energy.",
            "Hidden behind a collapsed wall: a pool of shimmering liquid. It tastes of starlight.",
            "A ley-line convergence draws water to the surface here. You bathe your wounds in it.",
            "The spring hums faintly. Whatever caused this phenomenon, you're grateful for it.",
        ],
        "heal_pct": (0.12, 0.22),
    },

    "treasure_cache": {
        "emoji": "📦",
        "title": "Hidden Cache",
        "color": 0xF39C12,
        "flavors": [
            "A loose flagstone shifts under your boot — beneath it, a wrapped bundle.",
            "A skeleton slumped against the wall still clutches a leather satchel.",
            "Worn markings scratched into the wall point to a hollow behind a brick.",
            "Half-buried in old debris: a sealed container, dusty but intact.",
            "Behind a false panel in the wall, someone stashed something valuable and never came back.",
        ],
    },

    "hidden_notes": {
        "emoji": "📜",
        "title": "Found: Hidden Notes",
        "color": 0x95A5A6,
        "xp_range": (25, 70),
        "lore_entries": [
            ("A Soldier's Diary",
             "*\"Day 47 — We found the rift. Captain says to seal it. Nobody has come back from the sealing team.\"*"),
            ("Arcane Research Notes",
             "*\"Void Fragments resonate at class-F mana frequencies. Do NOT touch with bare hands. I cannot stress this enough.\"*"),
            ("A Wanted Poster",
             "*\"WANTED: The Rift Walker. Reward: 500 gold. Last seen near Gravefall. Approach with extreme caution.\"*"),
            ("Cave Markings",
             "*\"← Safe.  → Monsters.  ↓ Do not go down.  ↑ Also no.  Please.\"*"),
            ("A Merchant's Letter",
             "*\"If you find this: the chest is real — behind the third pillar on the left. I hid it before the monsters came. —G\"*"),
            ("A Child's Note",
             "*\"I lost my cat near the big glowing door. His name is Whiskers. If you find him please let me know. He likes fish.\"*"),
            ("Battle Plans — Torn",
             "*\"Phase 1: lure them to the rift. Phase 2: collapse the walls. Phase 3:\"* …the rest is burned away."),
            ("An Inscription",
             "*\"Beneath the deepest dungeon lies a door with no handle. Those who find it do not return. Those who do not — the lucky ones.\"*"),
            ("A Map Fragment",
             "*A rough tunnel sketch with one location circled and labeled: \"REAL TREASURE HERE.\" The circle is scribbled out violently.*"),
            ("An Old Recipe",
             "*\"For strength: three parts cave moss, one part dried shadow beast gland, boil until it stops screaming.\"*"),
        ],
    },

    "rare_find": {
        "emoji": "✨",
        "title": "Rare Find",
        "color": 0xF1C40F,
        "flavors": [
            "Half-buried in the dirt — something catches the light at just the right angle.",
            "A shimmer at the edge of your vision. Your fingers close around something solid.",
            "Scratch marks on the wall lead you to a small hidden alcove.",
            "Beneath an ancient blood stain, the floor is not quite solid. Something was buried here.",
            "The glint of metal beneath debris — someone dropped this in a hurry.",
        ],
        "items": [
            ("Minor Healing Potion", 0.34),
            ("Great Healing Potion", 0.20),
            ("Strength Potion",      0.14),
            ("Speed Potion",         0.12),
            ("Defense Potion",       0.09),
            ("Lucky Charm",          0.07),
            ("Rift Crystal",         0.04),
        ],
    },

    "wandering_merchant": {
        "emoji": "🧙",
        "title": "Wandering Merchant",
        "color": 0x9B59B6,
        "flavors": [
            "A hunched figure emerges from the shadows with a cart full of wares. *\"Supplies for the weary!\"*",
            "A merchant's cart sits improbably in the middle of nowhere. The merchant winks at you.",
            "From an alcove, a robed figure gestures you over with one bony finger.",
            "*\"Ah, a traveler! You look like you could use this.\"* The merchant doesn't wait for an answer.",
            "A masked figure drops from a ledge, landing quietly. *\"I have something for you. No charge. Consider it goodwill.\"*",
        ],
        "items": [
            ("Minor Healing Potion", 0.50),
            ("Great Healing Potion", 0.26),
            ("Mana Potion",          0.14),
            ("Strength Potion",      0.07),
            ("Whetstone",            0.03),
        ],
    },

    "echo_of_battle": {
        "emoji": "⚔️",
        "title": "Echo of Battle",
        "color": 0xE74C3C,
        "flavors": [
            "Scorch marks and blood stains tell the story of a fight that happened here — recently.",
            "The bodies of two monsters lie cooling on the ground. Rivals, by the look of it.",
            "Broken weapons litter the ground. Someone fought here hard, and didn't come out ahead.",
            "Spent arrows, shattered armor, dried blood. A battle was lost in this corridor.",
            "The smell of burning. Ash on the floor. Something powerful passed through here not long ago.",
            "A toppled camp: scattered coins, a cracked lantern, a bloodied journal with no name.",
        ],
        "copper_range": (30, 130),
    },

    "ominous_silence": {
        "emoji": "🌫️",
        "title": "Unsettling Silence",
        "color": 0x2C2F33,
        "flavors": [
            "Nothing stirs. The silence is so complete you can hear your own heartbeat.",
            "Old footprints in the dust — something large came through here recently.",
            "A cold draft from nowhere. You press on, unsettled.",
            "Scorch marks on the walls. Something burned here, and not long ago.",
            "The echoes here carry wrong. Like the place itself is listening.",
            "You find only shadows and the smell of old stone. The area is quiet… for now.",
            "A faint hum, felt more than heard, vibrates through the floor. Then nothing.",
            "Something drips in the darkness ahead. You decide not to investigate.",
            "You turn a corner and stop dead. Then realize: nothing is there. Which is somehow worse.",
            "The air grows cold, then warm, then cold again. No wind. No explanation.",
        ],
    },
}


def pick_explore_event() -> str:
    """Randomly select a peaceful explore event by weight."""
    return random.choices(_EVENT_NAMES, weights=_EVENT_WEIGHTS, k=1)[0]
