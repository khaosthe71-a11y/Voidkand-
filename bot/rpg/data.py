COPPER_PER_SILVER = 100
SILVER_PER_GOLD = 100
SAVE_DIR = "bot/saves"
RANDOM_ENCOUNTER_CHANCE = 0.4

world_map = {
    "Aetherfall": {
        "level": 1,
        "description": "A modern city, your starting zone.",
        "lore": (
            "The last city still clinging to the illusion of order. Beyond its flickering gate-lights, "
            "the Gates have torn open and the darkness has begun its feast.\n"
            "*You begin here — unknown, untested, but chosen by fate.*"
        ),
        "realm": "Earth Layer",
        "quest_trigger": "welcome_quest",
        "has_shop": True,
    },
    "Gravefall": {
        "level": 10,
        "description": "A half-destroyed city, constant danger.",
        "lore": (
            "What was once a proud district now wears its wounds like armor. The streets are littered "
            "with the dead that refuse to stay buried.\n"
            "*Survivors don't sleep here — they just wait for morning, praying it comes.*"
        ),
        "realm": "Earth Layer",
    },
    "Rotveil": {
        "level": 20,
        "description": "A zombie-infested city.",
        "lore": (
            "The dead outnumber the living a thousand to one. Rot clings to the air like a second skin, "
            "and silence is its own kind of violence.\n"
            "*The brave come here for answers. The wise come prepared to leave without them.*"
        ),
        "realm": "Earth Layer",
    },
    "Nerathis": {
        "level": 25,
        "description": "An ancient, magical underwater city.",
        "lore": (
            "Swallowed by the sea during a war no living soul remembers, Nerathis still breathes — "
            "ancient magic pulsing through its coral towers like a heartbeat.\n"
            "*Something enormous stirs in its flooded halls, patient and waiting.*"
        ),
        "realm": "Earth Layer",
    },
    "Eclipse Citadel": {
        "level": 40,
        "description": "May's main city, powerful and untouchable.",
        "lore": (
            "The Empire does not beg for loyalty — it simply takes it. The Citadel floats between "
            "realms, its spires etched with the names of those who defied May and were erased.\n"
            "*You are not welcome here. You never were.*"
        ),
        "realm": "The Empire",
    },
    "Voidkand": {
        "level": 70,
        "description": "The Demon King's Lair. Reality warps around his throne.",
        "lore": (
            "Reality unravels at the edges. The Demon King's throne sits at the center of a wound "
            "in the universe, where time forgets itself and hope corrodes.\n"
            "*Those who enter Voidkand are already ghosts. They just haven't accepted it yet.*"
        ),
        "realm": "Void / Demon Realm",
        "is_boss_area": True,
    },
    "Dungeon Gate": {
        "level": 25,
        "description": "An ominous gate leading to a dangerous dungeon.",
        "lore": (
            "No one knows who built the Gate, or why. It simply appeared one morning, pulsing with dark "
            "energy like a second heartbeat. Those who pass through are never quite the same.\n"
            "*That is, if they return at all.*"
        ),
        "realm": "Earth Layer",
        "is_boss_area": True,
    },
    # ── New Locations ──────────────────────────────────────────────────────
    "Frostmourne Wastes": {
        "level": 15,
        "description": "A frozen wasteland where the cold itself is a predator.",
        "lore": (
            "Wind scours the ice flats without mercy. The cold here is not weather — it is intention, "
            "and it has been working at these bones for centuries.\n"
            "*Explorers who linger too long stop feeling pain. That is the last warning they get.*"
        ),
        "realm": "Frozen North",
        "special_effect": "hp_drain",
    },
    "Ashen Ruins": {
        "level": 18,
        "description": "A city reduced to ash and embers, still smoldering.",
        "lore": (
            "Something burned this city so completely that even the memory of what it was has turned to soot. "
            "The fires are old — and somehow, they never went out.\n"
            "*The heat here is not warmth. It is the last breath of something that refused to die.*"
        ),
        "realm": "Earth Layer",
        "special_effect": "burn_chance",
    },
    "Celestial Peak": {
        "level": 30,
        "description": "A sacred mountain where divine energy heals the worthy.",
        "lore": (
            "The peak pierces the clouds and touches something higher. Ancient orders carved their temples "
            "into the stone here — all of them gone, but the blessing they left behind remains.\n"
            "*The air at this altitude mends wounds and quiets minds. Even the darkness hesitates to follow you here.*"
        ),
        "realm": "The Divine Heights",
        "special_effect": "heal_bonus",
    },
    "Shadow Mire": {
        "level": 35,
        "description": "A dark swamp where predators grow stronger after sunset.",
        "lore": (
            "The mire does not sleep. It waits. Ancient pylons rise from the black water like broken fingers, "
            "circling something submerged that no one has ever seen clearly.\n"
            "*When night falls here, every sound doubles. Hunters become the hunted.*"
        ),
        "realm": "Earth Layer",
        "special_effect": "night_danger",
    },
    "Iron Bastion": {
        "level": 45,
        "description": "A fortress-city of the Empire, garrisoned by elite armored soldiers.",
        "lore": (
            "The Empire built Iron Bastion to be proof — proof that no enemy could break its walls, "
            "no rebellion could take its towers, no Gate could corrupt its garrison.\n"
            "*The proof has held. But the garrison has not been heard from in weeks.*"
        ),
        "realm": "The Empire",
        "special_effect": "armored_enemies",
    },
    "Abyssal Gate": {
        "level": 60,
        "description": "A rift between worlds — the void bleeds through here.",
        "lore": (
            "At the edge of the Void Realm, reality has torn open. Void energy crackles visibly in the air, "
            "distorting shapes and warping sound. Monsters from beyond breed here in the fracture.\n"
            "*What you kill here will not stay dead. What you find here will not stay found. But the rewards — "
            "those are as real as the danger.*"
        ),
        "realm": "Void / Demon Realm",
        "is_boss_area": True,
        "special_effect": "void_risk",
    },
}

gates = {
    # ── Original connections (expanded) ───────────────────────────────────
    "Aetherfall":         ["Gravefall", "Dungeon Gate"],
    "Gravefall":          ["Rotveil", "Aetherfall", "Frostmourne Wastes", "Ashen Ruins"],
    "Rotveil":            ["Voidkand", "Gravefall", "Shadow Mire"],
    "Nerathis":           ["Aetherfall", "Ashen Ruins", "Celestial Peak"],
    "Eclipse Citadel":    ["Voidkand", "Iron Bastion", "Celestial Peak"],
    "Voidkand":           ["Gravefall", "Eclipse Citadel", "Abyssal Gate"],
    "Dungeon Gate":       ["Aetherfall"],
    # ── New location connections ───────────────────────────────────────────
    "Frostmourne Wastes": ["Gravefall", "Shadow Mire"],
    "Ashen Ruins":        ["Gravefall", "Nerathis"],
    "Celestial Peak":     ["Nerathis", "Eclipse Citadel"],
    "Shadow Mire":        ["Rotveil", "Frostmourne Wastes"],
    "Iron Bastion":       ["Eclipse Citadel", "Abyssal Gate"],
    "Abyssal Gate":       ["Voidkand", "Iron Bastion"],
}

DEFAULT_PLAYER_STATE = {
    "current_location": "Aetherfall",
    "hp": 100,
    "class": "Hunter",
    "class_chosen": False,
    "attack": 15,
    "defense": 5,
    "vitality": 10,
    "mana": 50,
    "max_mana": 50,
    "intelligence": 10,
    "speed": 5,
    "luck": 5,
    "crit_chance": 0.05,
    "level": 1,
    "max_hp": 100,
    "time_of_day": "day",
    "inventory": [],
    "equipped": {"weapon": None, "armor": None, "accessory": None},
    "experience_points": 0,
    "xp_to_next_level": 100,
    "currency": {"gold": 0, "silver": 0, "copper": 0},
    "quest_log": {},
    "completed_quest_chains": [],
    "demon_king_slain": False,
    "pvp_wins": 0,
    "pvp_losses": 0,
    "dungeons_completed": [],
    "guild_id": None,
    "guild_bonus": {"attack": 0, "defense": 0, "max_hp": 0, "crit_chance": 0.0, "speed": 0},
    # ── Faction system ─────────────────────────────────────────────────────
    "faction":                    None,
    "reputation":                 {"Eclipse": 0, "Divine": 0, "Void": 0},
    "faction_missions_completed": [],
    "faction_kill_tracker":       0,
}

# ------------------------------------------------------------------ #
#  CLASS DEFINITIONS
# ------------------------------------------------------------------ #
CLASS_DEFINITIONS = {
    # ── Original classes ──────────────────────────────────────────────────
    "Warrior": {
        "description": "Tank class. Excels in HP and defense.",
        "emoji": "🛡️",
        "bonuses": {"max_hp": 40, "hp": 40, "defense": 12, "vitality": 8, "attack": 3},
    },
    "Mage": {
        "description": "Magic class. High mana and intelligence, bonus attack.",
        "emoji": "🔮",
        "bonuses": {"mana": 60, "max_mana": 60, "intelligence": 25, "attack": 8, "max_hp": -10, "hp": -10},
    },
    "Assassin": {
        "description": "Stealth class. High attack and critical hit chance.",
        "emoji": "🗡️",
        "bonuses": {"attack": 18, "crit_chance": 0.20, "speed": 5, "defense": -2},
    },
    # ── New classes ───────────────────────────────────────────────────────
    "Paladin": {
        "description": "Holy warrior. Great defense and HP. Can heal during combat.",
        "emoji": "✨",
        "bonuses": {"max_hp": 50, "hp": 50, "defense": 15, "vitality": 10, "attack": 2},
    },
    "Necromancer": {
        "description": "Dark caster. High intelligence and mana. Summons spectral minions.",
        "emoji": "💀",
        "bonuses": {"intelligence": 20, "mana": 70, "max_mana": 70, "attack": 5, "max_hp": -10, "hp": -10},
    },
    "Ranger": {
        "description": "Swift hunter. High speed and luck. Excels at multi-hit attacks.",
        "emoji": "🏹",
        "bonuses": {"speed": 8, "luck": 10, "crit_chance": 0.15, "attack": 6, "defense": -3},
    },
    "Berserker": {
        "description": "Savage fighter. Extreme attack. Grows stronger as HP drops.",
        "emoji": "🪓",
        "bonuses": {"attack": 25, "defense": -8, "max_hp": 20, "hp": 20, "vitality": 5},
    },
    "Elementalist": {
        "description": "Elemental mage. Controls ice and storms. Ignores half of enemy armor.",
        "emoji": "❄️",
        "bonuses": {"intelligence": 22, "mana": 80, "max_mana": 80, "attack": 4, "max_hp": -15, "hp": -15},
    },
    "Tank": {
        "description": "Immovable fortress. Extreme HP and defense. Sacrifices damage for near-impenetrable protection.",
        "emoji": "🏰",
        "bonuses": {"max_hp": 60, "hp": 60, "defense": 20, "vitality": 12, "attack": -5},
    },
    "Monk": {
        "description": "Disciplined striker. Balanced combat, lifesteal, and powerful combo attacks.",
        "emoji": "👊",
        "bonuses": {"max_hp": 20, "hp": 20, "defense": 5, "attack": 12, "mana": 30, "max_mana": 30, "speed": 3},
    },
}

# ------------------------------------------------------------------ #
#  CLASS SKILLS
# ------------------------------------------------------------------ #
# Each skill entry:
#   name        — display name
#   mana_cost   — mana spent on use
#   description — shown in !skill command
#   emoji       — prefix in combat messages
CLASS_SKILLS = {
    "Warrior": {
        "name": "Shield Bash",
        "emoji": "🛡️",
        "mana_cost": 15,
        "description": "Smash the enemy with your shield. Deals 1.5× attack damage and has a 40% chance to stun.",
        "stun_chance": 0.40,
        "damage_mult": 1.5,
    },
    "Mage": {
        "name": "Fireball",
        "emoji": "🔥",
        "mana_cost": 30,
        "description": "Launch a blazing fireball. Deals (Intelligence × 2 + Attack) magic damage, ignoring half of enemy defense.",
        "stun_chance": 0.0,
        "damage_mult": 0,          # handled specially using intelligence
    },
    "Assassin": {
        "name": "Shadow Strike",
        "emoji": "🗡️",
        "mana_cost": 20,
        "description": "Strike from the shadows. Guaranteed critical hit at 2.5× damage.",
        "stun_chance": 0.0,
        "damage_mult": 2.5,        # always crits
    },
    # ── New class skills ──────────────────────────────────────────────────
    "Paladin": {
        "name": "Holy Strike",
        "emoji": "✨",
        "mana_cost": 25,
        "description": "A blessed strike dealing 1.5× attack damage. Heals you for 30% of damage dealt.",
        "stun_chance": 0.0,
        "damage_mult": 1.5,
        "heal_pct": 0.30,
    },
    "Necromancer": {
        "name": "Raise Dead",
        "emoji": "💀",
        "mana_cost": 35,
        "description": "Deals Intelligence × 1.5 dark damage (ignores 30% defense). 40% chance to summon a spectral minion for a bonus hit.",
        "stun_chance": 0.0,
        "damage_mult": 1.5,
        "bonus_hit_chance": 0.40,
    },
    "Ranger": {
        "name": "Arrow Rain",
        "emoji": "🏹",
        "mana_cost": 20,
        "description": "Fires 2–3 arrows in rapid succession, each dealing 0.7× attack damage.",
        "stun_chance": 0.0,
        "damage_mult": 0.7,
    },
    "Berserker": {
        "name": "Rage Slash",
        "emoji": "🪓",
        "mana_cost": 15,
        "description": "A savage attack dealing 2× damage. Gains up to +80% bonus damage as your HP drops.",
        "stun_chance": 0.0,
        "damage_mult": 2.0,
    },
    "Elementalist": {
        "name": "Ice Storm",
        "emoji": "❄️",
        "mana_cost": 30,
        "description": "Deals Intelligence × 1.8 + Attack ice damage (ignores half defense). 60% chance to freeze the enemy, reducing their attack.",
        "stun_chance": 0.0,
        "damage_mult": 1.8,
        "slow_chance": 0.60,
    },
    "Tank": {
        "name": "Shield Wall",
        "emoji": "🏰",
        "mana_cost": 20,
        "description": "Slam with your shield for 0.8× damage, heal 20% of your max HP, and gain a defense buff.",
        "damage_mult": 0.8,
        "stun_chance": 0.0,
        "heal_pct_of_maxhp": 0.20,
    },
    "Monk": {
        "name": "Dragon Fist",
        "emoji": "👊",
        "mana_cost": 20,
        "description": "A focused burst dealing 1.8× damage. Heals you for 25% of damage dealt (lifesteal).",
        "damage_mult": 1.8,
        "stun_chance": 0.0,
        "heal_pct": 0.25,
    },
}

# ------------------------------------------------------------------ #
#  CLASS SKILLS — TIER 2  (unlocked at Level 20 — Advanced)
# ------------------------------------------------------------------ #
CLASS_SKILLS_T2: dict[str, dict] = {
    "Warrior": {
        "name": "Taunt",
        "emoji": "🛡️⬆️",
        "mana_cost": 25,
        "description": "Issue a battle cry. Heal 30% of your max HP and gain a powerful defense buff. No attack.",
        "damage_mult": 0.0,
        "stun_chance": 0.0,
        "heal_pct_of_maxhp": 0.30,
    },
    "Mage": {
        "name": "Firestorm",
        "emoji": "🔥🌪️",
        "mana_cost": 45,
        "description": "A raging firestorm dealing Intelligence × 3 damage, ignoring ALL armor. Burns the enemy.",
        "damage_mult": 3.0,
        "stun_chance": 0.0,
    },
    "Assassin": {
        "name": "Blade Dance",
        "emoji": "🗡️🗡️",
        "mana_cost": 35,
        "description": "Three rapid strikes at 1.3× damage each with 60% critical hit chance per hit. Applies Poison.",
        "damage_mult": 1.3,
        "stun_chance": 0.0,
    },
    "Paladin": {
        "name": "Divine Shield",
        "emoji": "✨🛡️",
        "mana_cost": 35,
        "description": "Holy light heals 50% of your max HP and grants a defense buff. No attack.",
        "damage_mult": 0.0,
        "stun_chance": 0.0,
        "heal_pct_of_maxhp": 0.50,
    },
    "Necromancer": {
        "name": "Bone Nova",
        "emoji": "💀💥",
        "mana_cost": 45,
        "description": "Bone shards explode for Intelligence × 2 damage (ignores 50% defense). 35% stun, applies Poison.",
        "damage_mult": 2.0,
        "stun_chance": 0.35,
    },
    "Ranger": {
        "name": "Explosive Shot",
        "emoji": "💥🏹",
        "mana_cost": 30,
        "description": "An explosive-tipped arrow dealing 2.2× damage with a 45% chance to stun.",
        "damage_mult": 2.2,
        "stun_chance": 0.45,
    },
    "Berserker": {
        "name": "Blood Frenzy",
        "emoji": "🪓🔴",
        "mana_cost": 25,
        "description": "3.0× damage with rage bonus. Warning: reckless fury deals 15% of damage back as recoil.",
        "damage_mult": 3.0,
        "stun_chance": 0.0,
    },
    "Elementalist": {
        "name": "Chain Lightning",
        "emoji": "⚡⚡",
        "mana_cost": 45,
        "description": "Lightning arcs for Intelligence × 2.5 + Attack (ignores half defense). 40% stun, 50% chain bounce.",
        "damage_mult": 2.5,
        "stun_chance": 0.40,
        "bonus_hit_chance": 0.50,
    },
    "Tank": {
        "name": "Fortress Stance",
        "emoji": "🏰⬆️",
        "mana_cost": 30,
        "description": "Become an immovable fortress. Heal 45% of your max HP and gain a massive defense buff. No attack.",
        "damage_mult": 0.0,
        "stun_chance": 0.0,
        "heal_pct_of_maxhp": 0.45,
    },
    "Monk": {
        "name": "Chi Burst",
        "emoji": "👊💥",
        "mana_cost": 30,
        "description": "Rapid ki strikes: 3 hits at 0.9× damage each. Each hit has a 35% chance to stun.",
        "damage_mult": 0.9,
        "stun_chance": 0.35,
    },
}

# ------------------------------------------------------------------ #
#  CLASS SKILLS — TIER 3  (unlocked at Level 30 — Ultimate)
# ------------------------------------------------------------------ #
CLASS_SKILLS_T3: dict[str, dict] = {
    "Warrior": {
        "name": "Warlord's Might",
        "emoji": "🛡️⚔️",
        "mana_cost": 40,
        "description": "A devastating blow dealing 3.5× damage ignoring 30% defense, with a 55% chance to stun.",
        "damage_mult": 3.5,
        "stun_chance": 0.55,
    },
    "Mage": {
        "name": "Arcane Nova",
        "emoji": "🌟💥",
        "mana_cost": 60,
        "description": "A reality-shattering nova: Intelligence × 4 + Attack magic damage ignoring ALL defense. Stuns the enemy.",
        "damage_mult": 4.0,
        "stun_chance": 1.0,
    },
    "Assassin": {
        "name": "Death Mark",
        "emoji": "💀🗡️",
        "mana_cost": 50,
        "description": "A lethal guaranteed-crit strike at 4.5× damage. Applies Poison and an Attack Debuff.",
        "damage_mult": 4.5,
        "stun_chance": 0.0,
    },
    "Paladin": {
        "name": "Sacred Judgment",
        "emoji": "✨⚔️",
        "mana_cost": 50,
        "description": "A divine strike at 2.5× damage. Heals 60% of damage dealt and grants a defense buff.",
        "damage_mult": 2.5,
        "stun_chance": 0.0,
        "heal_pct": 0.60,
    },
    "Necromancer": {
        "name": "Undead Legion",
        "emoji": "💀💀💀",
        "mana_cost": 55,
        "description": "Summon 3 undead minions each dealing Intelligence × 0.8 dark damage (ignores 50% defense).",
        "damage_mult": 0.8,
        "stun_chance": 0.0,
    },
    "Ranger": {
        "name": "Sniper's Mark",
        "emoji": "🎯🏹",
        "mana_cost": 45,
        "description": "A perfectly aimed shot at 4.0× damage. Guaranteed critical hit. Ignores 50% of enemy defense.",
        "damage_mult": 4.0,
        "stun_chance": 0.0,
    },
    "Berserker": {
        "name": "Apocalyptic Rage",
        "emoji": "🪓☠️",
        "mana_cost": 35,
        "description": "5.0× damage with full rage bonus. Guaranteed critical. Warning: 20% recoil damage to yourself.",
        "damage_mult": 5.0,
        "stun_chance": 0.0,
    },
    "Elementalist": {
        "name": "Cataclysm",
        "emoji": "🌑💥",
        "mana_cost": 60,
        "description": "A catastrophic elemental eruption: Intelligence × 4 + Attack. Ignores ALL defense. Burns and Freezes.",
        "damage_mult": 4.0,
        "stun_chance": 0.0,
    },
    "Tank": {
        "name": "Juggernaut",
        "emoji": "🏰⚔️",
        "mana_cost": 40,
        "description": "An unstoppable charge at 2.8× damage. Heals 30% of damage dealt and grants a defense buff.",
        "damage_mult": 2.8,
        "stun_chance": 0.0,
        "heal_pct": 0.30,
    },
    "Monk": {
        "name": "Void Palm",
        "emoji": "👊🌑",
        "mana_cost": 45,
        "description": "Channel void energy for 2.8× damage (ignores 50% defense). Absorbs 40% of damage as healing.",
        "damage_mult": 2.8,
        "stun_chance": 0.0,
        "heal_pct": 0.40,
    },
}

# ------------------------------------------------------------------ #
#  EQUIPMENT DATA  (slot / stat bonuses / cost)
# ------------------------------------------------------------------ #
EQUIPMENT_DATA = {
    # ── Weapons ───────────────────────────────────────────────────────────
    "Iron Sword":       {"slot": "weapon",    "attack_bonus": 5,  "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 150,  "sell": 75},
    "Hunter's Bow":     {"slot": "weapon",    "attack_bonus": 8,  "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 1, "crit_bonus": 0.02, "luck_bonus": 0,  "cost_copper": 250,  "sell": 125},
    "Apprentice Staff": {"slot": "weapon",    "attack_bonus": 12, "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 15, "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 300,  "sell": 150},
    "Knight's Blade":   {"slot": "weapon",    "attack_bonus": 18, "defense_bonus": 3,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 600,  "sell": 300},
    "Shadow Blade":     {"slot": "weapon",    "attack_bonus": 15, "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 3, "crit_bonus": 0.05, "luck_bonus": 0,  "cost_copper": 0,    "sell": 400},
    "Legendary Sword":  {"slot": "weapon",    "attack_bonus": 20, "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 0,    "sell": 500},
    # ── Armor ─────────────────────────────────────────────────────────────
    "Leather Armor":      {"slot": "armor",   "attack_bonus": 0,  "defense_bonus": 5,  "hp_bonus": 10, "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 120,  "sell": 60},
    "Iron Plate":         {"slot": "armor",   "attack_bonus": 0,  "defense_bonus": 12, "hp_bonus": 25, "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 400,  "sell": 200},
    "Mage's Robe":        {"slot": "armor",   "attack_bonus": 0,  "defense_bonus": 4,  "hp_bonus": 20, "mana_bonus": 20, "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 250,  "sell": 125},
    "Void Cloak":         {"slot": "armor",   "attack_bonus": 5,  "defense_bonus": 8,  "hp_bonus": 20, "mana_bonus": 0,  "speed_bonus": 2, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 0,    "sell": 600},
    "Dragonscale Armor":  {"slot": "armor",   "attack_bonus": 0,  "defense_bonus": 20, "hp_bonus": 50, "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 0,    "sell": 1200},
    "Demon King's Crown": {"slot": "armor",   "attack_bonus": 10, "defense_bonus": 10, "hp_bonus": 50, "mana_bonus": 30, "speed_bonus": 2, "crit_bonus": 0.05, "luck_bonus": 10, "cost_copper": 0,    "sell": 5000},
    # ── Accessories ───────────────────────────────────────────────────────
    "Swiftness Ring":   {"slot": "accessory", "attack_bonus": 0,  "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 4, "crit_bonus": 0.03, "luck_bonus": 0,  "cost_copper": 180,  "sell": 90},
    "Amulet of Power":  {"slot": "accessory", "attack_bonus": 10, "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 250,  "sell": 125},
    "Mage's Focus":     {"slot": "accessory", "attack_bonus": 0,  "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 30, "speed_bonus": 0, "crit_bonus": 0.03, "luck_bonus": 0,  "cost_copper": 220,  "sell": 110},
    "Lucky Pendant":    {"slot": "accessory", "attack_bonus": 0,  "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 1, "crit_bonus": 0.05, "luck_bonus": 15, "cost_copper": 200,  "sell": 100},
    "Battle Pendant":   {"slot": "accessory", "attack_bonus": 5,  "defense_bonus": 5,  "hp_bonus": 20, "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 350,  "sell": 175},
    "Scholar's Band":   {"slot": "accessory", "attack_bonus": 0,  "defense_bonus": 0,  "hp_bonus": 10, "mana_bonus": 25, "speed_bonus": 2, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 280,  "sell": 140},
    "Void Ring":          {"slot": "accessory", "attack_bonus": 15, "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 3, "crit_bonus": 0.08, "luck_bonus": 0,  "cost_copper": 0, "sell": 800},
    # ── New dungeon-exclusive weapons ─────────────────────────────────────
    "Fallen King's Blade":{"slot": "weapon",    "attack_bonus": 30, "defense_bonus": 0,  "hp_bonus": -20,"mana_bonus": 0,  "speed_bonus": 2, "crit_bonus": 0.08, "luck_bonus": 0,  "cost_copper": 0, "sell": 1500},
    # ── New dungeon-exclusive armor ───────────────────────────────────────
    "Ember Crown":        {"slot": "armor",     "attack_bonus": 8,  "defense_bonus": 15, "hp_bonus": 30, "mana_bonus": 10, "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 0,  "cost_copper": 0, "sell": 1800},
    "Ashen Mantle":       {"slot": "armor",     "attack_bonus": 0,  "defense_bonus": 18, "hp_bonus": 35, "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 5,  "cost_copper": 0, "sell": 1400},
    "Shadowweave Cloak":  {"slot": "armor",     "attack_bonus": 12, "defense_bonus": 10, "hp_bonus": 15, "mana_bonus": 0,  "speed_bonus": 5, "crit_bonus": 0.05, "luck_bonus": 0,  "cost_copper": 0, "sell": 2000},
    # ── New dungeon-exclusive accessories ─────────────────────────────────
    "Frostbite Ring":     {"slot": "accessory", "attack_bonus": 8,  "defense_bonus": 5,  "hp_bonus": 20, "mana_bonus": 0,  "speed_bonus": 0, "crit_bonus": 0.03, "luck_bonus": 5,  "cost_copper": 0, "sell": 700},
    "Celestial Pendant":  {"slot": "accessory", "attack_bonus": 0,  "defense_bonus": 5,  "hp_bonus": 30, "mana_bonus": 20, "speed_bonus": 0, "crit_bonus": 0.00, "luck_bonus": 10, "cost_copper": 0, "sell": 900},
    "Voidforged Gauntlet":{"slot": "accessory", "attack_bonus": 20, "defense_bonus": 0,  "hp_bonus": 0,  "mana_bonus": 0,  "speed_bonus": 4, "crit_bonus": 0.10, "luck_bonus": 0,  "cost_copper": 0, "sell": 1200},
}

# ------------------------------------------------------------------ #
#  STATUS EFFECTS
# ------------------------------------------------------------------ #
# is_dot    → deals damage each turn
# is_stun   → entity skips their turn
# is_buff   → raises a stat temporarily (reverted on expiry)
# is_debuff → lowers a stat temporarily (reverted on expiry)
STATUS_EFFECTS: dict[str, dict] = {
    "poison": {
        "emoji": "🟢",
        "label": "Poisoned",
        "damage_per_turn": 8,
        "default_turns": 3,
        "is_dot": True,
    },
    "burn": {
        "emoji": "🔥",
        "label": "Burning",
        "damage_per_turn": 12,
        "default_turns": 2,
        "is_dot": True,
    },
    "stun": {
        "emoji": "😵",
        "label": "Stunned",
        "damage_per_turn": 0,
        "default_turns": 1,
        "is_stun": True,
    },
    "attack_buff": {
        "emoji": "⚔️⬆️",
        "label": "Attack Up",
        "stat": "attack",
        "amount": 12,
        "default_turns": 3,
        "is_buff": True,
    },
    "defense_buff": {
        "emoji": "🛡️⬆️",
        "label": "Defense Up",
        "stat": "defense",
        "amount": 8,
        "default_turns": 3,
        "is_buff": True,
    },
    "attack_debuff": {
        "emoji": "📉",
        "label": "Attack Down",
        "stat": "attack",
        "amount": -10,
        "default_turns": 2,
        "is_debuff": True,
    },
    "defense_debuff": {
        "emoji": "🛡️💔",
        "label": "Defense Down",
        "stat": "defense",
        "amount": -6,
        "default_turns": 2,
        "is_debuff": True,
    },
}

enemy_types = {
    # ── Original enemies ──────────────────────────────────────────────────
    "Goblin": {
        "hp": 30, "attack": 5, "defense": 1,
        "experience_reward": 20, "copper_reward": 15, "crit_chance": 0.05,
        "inflicts": [],
    },
    "Shadow Beast": {
        "hp": 60, "attack": 10, "defense": 3,
        "experience_reward": 40, "copper_reward": 30, "crit_chance": 0.08,
        "inflicts": [{"effect": "poison", "chance": 0.20}],
    },
    "Corrupted Knight": {
        "hp": 100, "attack": 15, "defense": 6,
        "experience_reward": 70, "copper_reward": 50, "crit_chance": 0.10,
        "inflicts": [{"effect": "attack_debuff", "chance": 0.15}],
    },
    "Dungeon Lord": {
        "hp": 250, "attack": 30, "defense": 10,
        "experience_reward": 500, "copper_reward": 200, "crit_chance": 0.12,
        "is_boss": True,
        "inflicts": [{"effect": "stun", "chance": 0.12}],
    },
    "Demon King": {
        "hp": 1000, "attack": 70, "defense": 15,
        "experience_reward": 5000, "copper_reward": 1000, "crit_chance": 0.15,
        "is_boss": True,
        "inflicts": [{"effect": "burn", "chance": 0.30}],
    },
    # ── Crypt of the Fallen King enemies ─────────────────────────────────
    "Skeleton Archer": {
        "hp": 55, "attack": 14, "defense": 2,
        "experience_reward": 55, "copper_reward": 40, "crit_chance": 0.15,
        "inflicts": [{"effect": "attack_debuff", "chance": 0.12}],
    },
    "Spectral Guard": {
        "hp": 130, "attack": 18, "defense": 9,
        "experience_reward": 90, "copper_reward": 65, "crit_chance": 0.08,
        "inflicts": [{"effect": "defense_debuff", "chance": 0.18}],
    },
    "Fallen King": {
        "hp": 480, "attack": 48, "defense": 14,
        "experience_reward": 1200, "copper_reward": 420, "crit_chance": 0.15,
        "is_boss": True,
        "inflicts": [
            {"effect": "attack_debuff", "chance": 0.22},
            {"effect": "stun",          "chance": 0.10},
        ],
    },
    # ── Inferno Depths enemies ────────────────────────────────────────────
    "Lava Golem": {
        "hp": 160, "attack": 22, "defense": 11,
        "experience_reward": 105, "copper_reward": 75, "crit_chance": 0.07,
        "inflicts": [{"effect": "burn", "chance": 0.38}],
    },
    "Flame Wraith": {
        "hp": 80, "attack": 30, "defense": 3,
        "experience_reward": 85, "copper_reward": 60, "crit_chance": 0.14,
        "inflicts": [{"effect": "burn", "chance": 0.48}],
    },
    "Flame Tyrant": {
        "hp": 620, "attack": 62, "defense": 19,
        "experience_reward": 2000, "copper_reward": 620, "crit_chance": 0.15,
        "is_boss": True,
        "inflicts": [
            {"effect": "burn",           "chance": 0.42},
            {"effect": "defense_debuff", "chance": 0.20},
        ],
    },
    # ── Temple of Shadows enemies ─────────────────────────────────────────
    "Shadow Acolyte": {
        "hp": 72, "attack": 19, "defense": 4,
        "experience_reward": 68, "copper_reward": 48, "crit_chance": 0.18,
        "inflicts": [{"effect": "poison", "chance": 0.32}],
    },
    "Void Assassin": {
        "hp": 95, "attack": 34, "defense": 2,
        "experience_reward": 95, "copper_reward": 65, "crit_chance": 0.26,
        "inflicts": [
            {"effect": "attack_debuff", "chance": 0.18},
            {"effect": "poison",        "chance": 0.20},
        ],
    },
    "Shadow Priest": {
        "hp": 540, "attack": 52, "defense": 15,
        "experience_reward": 1800, "copper_reward": 520, "crit_chance": 0.13,
        "is_boss": True,
        "inflicts": [
            {"effect": "poison",         "chance": 0.32},
            {"effect": "defense_debuff", "chance": 0.22},
            {"effect": "attack_debuff",  "chance": 0.15},
        ],
    },
}

loot_table = {
    # ── Original enemies ──────────────────────────────────────────────────
    "Goblin": [
        {"item": "Minor Healing Potion", "chance": 0.2, "copper_amount": 0},
        {"item": None,                   "chance": 0.6, "copper_amount": 10},
    ],
    "Shadow Beast": [
        {"item": "Minor Healing Potion", "chance": 0.3, "copper_amount": 0},
        {"item": "Strength Potion",      "chance": 0.1, "copper_amount": 0},
        {"item": None,                   "chance": 0.5, "copper_amount": 25},
    ],
    "Corrupted Knight": [
        {"item": "Strength Potion",      "chance": 0.2, "copper_amount": 0},
        {"item": "Lucky Charm",          "chance": 0.05,"copper_amount": 0},
        {"item": "Shadow Blade",         "chance": 0.03,"copper_amount": 0},
        {"item": None,                   "chance": 0.7, "copper_amount": 50},
    ],
    "Dungeon Lord": [
        {"item": "Great Healing Potion", "chance": 0.5, "copper_amount": 0},
        {"item": "Legendary Sword",      "chance": 0.1, "copper_amount": 0},
        {"item": "Void Cloak",           "chance": 0.08,"copper_amount": 0},
        {"item": None,                   "chance": 0.4, "copper_amount": 100},
    ],
    "Demon King": [
        {"item": "Demon King's Crown",   "chance": 1.0, "copper_amount": 0},
        {"item": "Great Healing Potion", "chance": 0.8, "copper_amount": 0},
        {"item": "Ultimate Power Elixir","chance": 0.2, "copper_amount": 0},
    ],
    # ── Crypt enemies ─────────────────────────────────────────────────────
    "Skeleton Archer": [
        {"item": "Minor Healing Potion", "chance": 0.25, "copper_amount": 0},
        {"item": None,                   "chance": 0.60, "copper_amount": 30},
    ],
    "Spectral Guard": [
        {"item": "Great Healing Potion", "chance": 0.18, "copper_amount": 0},
        {"item": "Defense Potion",       "chance": 0.12, "copper_amount": 0},
        {"item": None,                   "chance": 0.60, "copper_amount": 55},
    ],
    "Fallen King": [
        {"item": "Fallen King's Blade",  "chance": 0.40, "copper_amount": 0},
        {"item": "Frostbite Ring",       "chance": 0.30, "copper_amount": 0},
        {"item": "Great Healing Potion", "chance": 0.60, "copper_amount": 0},
        {"item": None,                   "chance": 0.30, "copper_amount": 300},
    ],
    # ── Inferno enemies ───────────────────────────────────────────────────
    "Lava Golem": [
        {"item": "Burn Salve",           "chance": 0.30, "copper_amount": 0},
        {"item": "Strength Potion",      "chance": 0.15, "copper_amount": 0},
        {"item": None,                   "chance": 0.55, "copper_amount": 60},
    ],
    "Flame Wraith": [
        {"item": "Burn Salve",           "chance": 0.35, "copper_amount": 0},
        {"item": "Mana Potion",          "chance": 0.15, "copper_amount": 0},
        {"item": None,                   "chance": 0.55, "copper_amount": 50},
    ],
    "Flame Tyrant": [
        {"item": "Ember Crown",          "chance": 0.35, "copper_amount": 0},
        {"item": "Ashen Mantle",         "chance": 0.28, "copper_amount": 0},
        {"item": "Great Healing Potion", "chance": 0.65, "copper_amount": 0},
        {"item": None,                   "chance": 0.25, "copper_amount": 450},
    ],
    # ── Temple enemies ────────────────────────────────────────────────────
    "Shadow Acolyte": [
        {"item": "Antidote",             "chance": 0.30, "copper_amount": 0},
        {"item": "Minor Healing Potion", "chance": 0.20, "copper_amount": 0},
        {"item": None,                   "chance": 0.55, "copper_amount": 40},
    ],
    "Void Assassin": [
        {"item": "Speed Potion",         "chance": 0.20, "copper_amount": 0},
        {"item": "Antidote",             "chance": 0.20, "copper_amount": 0},
        {"item": "Shadowweave Cloak",    "chance": 0.04, "copper_amount": 0},
        {"item": None,                   "chance": 0.60, "copper_amount": 55},
    ],
    "Shadow Priest": [
        {"item": "Shadowweave Cloak",    "chance": 0.38, "copper_amount": 0},
        {"item": "Celestial Pendant",    "chance": 0.30, "copper_amount": 0},
        {"item": "Voidforged Gauntlet",  "chance": 0.25, "copper_amount": 0},
        {"item": "Great Healing Potion", "chance": 0.65, "copper_amount": 0},
        {"item": None,                   "chance": 0.20, "copper_amount": 380},
    ],
}

# ------------------------------------------------------------------ #
#  DUNGEON DATA
# ------------------------------------------------------------------ #
# Each dungeon has multiple waves. Waves are fought sequentially.
# The final wave is always the boss wave.
# Between waves the player can retreat (no rewards) or continue.
# Rare drops are rolled after all waves are cleared.
DUNGEON_DATA: dict[str, dict] = {
    "Goblin Lair": {
        "emoji": "🟤",
        "description": "A stinking cave overrun with goblins and their Shadow Beast pets.",
        "flavor": (
            "The stench reaches you long before the screaming does. "
            "Something wet drips from the ceiling — you decide not to look up."
        ),
        "boss_intro": (
            "The Dungeon Lord hauls itself upright from a throne built out of bones and broken swords. "
            "It has fed on hunters like you before — you can tell by the trophies hanging from its belt.\n"
            "*It doesn't charge. It waits. Like something that has all the time in the world.*"
        ),
        "victory_msg": (
            "The Dungeon Lord's corpse settles into the mud with a wet, final thud. "
            "The lair goes quiet — genuinely, completely quiet — for the first time in years.\n"
            "*You are the reason it will never wake again.*"
        ),
        "min_level": 1,
        "waves": [
            {
                "label": "Wave 1 — The Scouts",
                "enemies": ["Goblin", "Goblin"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 2 — The Guards",
                "enemies": ["Goblin", "Shadow Beast"],
                "is_boss_wave": False,
            },
            {
                "label": "⚠️ BOSS — Dungeon Lord",
                "enemies": ["Dungeon Lord"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp": 400,
            "copper": 200,
            "rare_drops": [
                {"item": "Great Healing Potion", "chance": 0.60},
                {"item": "Strength Potion",       "chance": 0.45},
                {"item": "Shadow Blade",          "chance": 0.08},
                {"item": "Legendary Sword",       "chance": 0.04},
            ],
        },
    },
    "Shadow Crypt": {
        "emoji": "🟣",
        "description": "Ancient ruins where corrupted knights guard a dark relic.",
        "flavor": (
            "Torches die the moment you descend. The cold that replaces them is not natural — "
            "it is grief, crystallized into stone over centuries of forgotten war."
        ),
        "boss_intro": (
            "From the far end of the crypt, a silhouette congeals from the darkness — "
            "the Dungeon Lord, armored in ancient corruption, moving without sound.\n"
            "Its hollow eyes find you across the chamber with something that might be hunger. "
            "Or recognition. Down here, there is no difference.\n"
            "*Whatever it was before, it is only this now.*"
        ),
        "victory_msg": (
            "The darkness fractures. Something that had not rested in centuries finally goes still.\n"
            "The crypt exhales — a long, slow breath it had been holding since the world was young.\n"
            "*For a moment, the cold almost feels like peace.*"
        ),
        "min_level": 5,
        "waves": [
            {
                "label": "Wave 1 — The Fallen",
                "enemies": ["Shadow Beast", "Shadow Beast"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 2 — The Corrupted",
                "enemies": ["Corrupted Knight", "Shadow Beast"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 3 — The Vanguard",
                "enemies": ["Corrupted Knight", "Corrupted Knight"],
                "is_boss_wave": False,
            },
            {
                "label": "⚠️ BOSS — Dungeon Lord",
                "enemies": ["Dungeon Lord"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp": 900,
            "copper": 400,
            "rare_drops": [
                {"item": "Great Healing Potion",  "chance": 0.70},
                {"item": "Iron Plate",            "chance": 0.25},
                {"item": "Void Cloak",            "chance": 0.10},
                {"item": "Shadow Blade",          "chance": 0.12},
                {"item": "Ultimate Power Elixir", "chance": 0.06},
            ],
        },
    },
    "Demon's Keep": {
        "emoji": "🔴",
        "description": "The Demon King's forward fortress. Only the strongest dare enter.",
        "flavor": (
            "Obsidian walls radiate heat like a fever dream. The air tastes of sulfur and burnt ambition. "
            "Every step forward is a step deeper into something that doesn't want to let you back out."
        ),
        "boss_intro": (
            "The Demon King does not enter. He *arrives* — reality peeling aside like smoke before a blade, "
            "the air pressure dropping so fast your ears ring.\n"
            "His gaze finds you instantly across the burning hall. He looks almost disappointed.\n"
            "*'Another one,'* he says, quietly. *'I had hoped you would be stronger.'*\n"
            "He raises his hand — and the fortress shudders."
        ),
        "victory_msg": (
            "The Demon King falls. Not quickly — slowly, impossibly, like a mountain deciding to become rubble.\n"
            "The fortress shudders. The fires dim. The darkness that served him recoils as if burned.\n"
            "You stand in the silence he leaves behind and realize:\n"
            "*You are the reason the world breathes again today.*"
        ),
        "min_level": 12,
        "waves": [
            {
                "label": "Wave 1 — Hell's Gate",
                "enemies": ["Corrupted Knight", "Corrupted Knight", "Shadow Beast"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 2 — The Lieutenants",
                "enemies": ["Dungeon Lord", "Corrupted Knight"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 3 — The Dread Guard",
                "enemies": ["Dungeon Lord", "Dungeon Lord"],
                "is_boss_wave": False,
            },
            {
                "label": "⚠️ BOSS — Demon King",
                "enemies": ["Demon King"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp": 6000,
            "copper": 1200,
            "rare_drops": [
                {"item": "Great Healing Potion",  "chance": 0.90},
                {"item": "Ultimate Power Elixir", "chance": 0.30},
                {"item": "Void Cloak",            "chance": 0.20},
                {"item": "Legendary Sword",       "chance": 0.18},
                {"item": "Demon King's Crown",    "chance": 0.20},
            ],
        },
    },
    # ================================================================= #
    #  NEW NAMED DUNGEONS
    # ================================================================= #
    "Crypt of the Fallen King": {
        "emoji": "🪦",
        "min_level": 20,
        "description": "A frost-encrusted royal tomb haunted by undead knights and their cursed sovereign.",
        "flavor": (
            "The crypt breathes. You can feel it — a slow exhalation of cold air from somewhere deep below. "
            "The walls are carved with the faces of the dead. They all seem to be looking at you.\n"
            "*Whatever the Fallen King was in life, death has made him worse.*"
        ),
        "boss_intro": (
            "The ice splits. A crowned skeleton rises from a throne of frozen corpses, "
            "armor fused to its bones by centuries of cold. Its eyes burn with pale blue fire.\n"
            "*It doesn't speak. It simply raises its blade — and the dead in the room begin to stir.*"
        ),
        "victory_msg": (
            "The Fallen King collapses, crown clattering across the ice. The cold that filled this place "
            "lifts in an instant, as if the crypt itself exhales in relief.\n"
            "*The buried dead are still at last. Whatever held them here — you've ended it.*"
        ),
        "waves": [
            {
                "label": "Wave 1 — The Bone Vanguard",
                "enemies": ["Skeleton Archer", "Skeleton Archer"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 2 — The Undying Guard",
                "enemies": ["Skeleton Archer", "Spectral Guard"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 3 — The Crypt Wardens",
                "enemies": ["Spectral Guard", "Spectral Guard"],
                "is_boss_wave": False,
            },
            {
                "label": "⚠️ BOSS — The Fallen King",
                "enemies": ["Fallen King"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp": 2000,
            "copper": 500,
            "rare_drops": [
                {"item": "Fallen King's Blade",  "chance": 0.45},
                {"item": "Frostbite Ring",       "chance": 0.35},
                {"item": "Great Healing Potion", "chance": 0.80},
                {"item": "Legendary Sword",      "chance": 0.10},
            ],
        },
    },

    "Inferno Depths": {
        "emoji": "🌋",
        "min_level": 28,
        "description": "A volcanic underworld of fire and molten rock, ruled by a tyrant of flame.",
        "flavor": (
            "The heat hits before the light does. Everything here shimmers and warps. "
            "The ground is warm to the touch and the air smells of sulfur and scorched stone.\n"
            "*You hear something massive moving below. The whole tunnel shakes when it breathes.*"
        ),
        "boss_intro": (
            "The lava parts. Something vast and burning heaves itself upward — the Flame Tyrant, "
            "body wreathed in living fire, eyes like forge coals.\n"
            "*It opens its mouth. What comes out is not language — it is heat, and pressure, and the promise of ash.*"
        ),
        "victory_msg": (
            "The Flame Tyrant collapses into cooling stone, fires guttering out. "
            "Steam fills the chamber as the lava retreats.\n"
            "*The depths grow quiet. You stand in the dark, catching your breath. "
            "Whatever lived here — it will not burn again.*"
        ),
        "waves": [
            {
                "label": "Wave 1 — The Stone Servants",
                "enemies": ["Lava Golem", "Lava Golem"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 2 — The Burning Chorus",
                "enemies": ["Flame Wraith", "Flame Wraith"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 3 — Fire and Stone",
                "enemies": ["Lava Golem", "Flame Wraith"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 4 — The Wraith Swarm",
                "enemies": ["Flame Wraith", "Flame Wraith", "Flame Wraith"],
                "is_boss_wave": False,
            },
            {
                "label": "⚠️ BOSS — The Flame Tyrant",
                "enemies": ["Flame Tyrant"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp": 3500,
            "copper": 750,
            "rare_drops": [
                {"item": "Ember Crown",          "chance": 0.40},
                {"item": "Ashen Mantle",         "chance": 0.32},
                {"item": "Great Healing Potion", "chance": 0.80},
                {"item": "Void Cloak",           "chance": 0.08},
            ],
        },
    },

    "Temple of Shadows": {
        "emoji": "🌑",
        "min_level": 35,
        "description": "An ancient temple of shadow-worshippers, now serving something far older and darker.",
        "flavor": (
            "The torches here burn black. Not dark — *black*, with a light that makes things harder to see, "
            "not easier. Figures drift in the periphery. You can never quite look directly at them.\n"
            "*The temple doesn't want you dead. It wants you lost. Wandering its halls forever.*"
        ),
        "boss_intro": (
            "The altar bleeds shadow upward. The Shadow Priest materializes from it — not walking, "
            "not appearing, simply *becoming* present. Its robes are woven from darkness.\n"
            "*It regards you without eyes and speaks without a mouth: 'You should not be here. "
            "But the shadows have use for you.'*"
        ),
        "victory_msg": (
            "The Shadow Priest fractures into shards of darkness that dissolve before they hit the ground. "
            "Light — real light — floods the temple for the first time in centuries.\n"
            "*The whispering stops. The shadows retreat. The temple is just stone, now. "
            "Cold, empty, and finally, finally quiet.*"
        ),
        "waves": [
            {
                "label": "Wave 1 — The Faithful",
                "enemies": ["Shadow Acolyte", "Shadow Acolyte"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 2 — Blade and Doctrine",
                "enemies": ["Void Assassin", "Shadow Acolyte"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 3 — The Void Blades",
                "enemies": ["Void Assassin", "Void Assassin"],
                "is_boss_wave": False,
            },
            {
                "label": "Wave 4 — The Inner Circle",
                "enemies": ["Shadow Acolyte", "Void Assassin", "Shadow Acolyte"],
                "is_boss_wave": False,
            },
            {
                "label": "⚠️ BOSS — The Shadow Priest",
                "enemies": ["Shadow Priest"],
                "is_boss_wave": True,
            },
        ],
        "rewards": {
            "xp": 4500,
            "copper": 900,
            "rare_drops": [
                {"item": "Shadowweave Cloak",    "chance": 0.40},
                {"item": "Celestial Pendant",    "chance": 0.32},
                {"item": "Voidforged Gauntlet",  "chance": 0.28},
                {"item": "Great Healing Potion", "chance": 0.85},
                {"item": "Void Ring",            "chance": 0.08},
            ],
        },
    },
}

# Each consumable item has:
#   type   — "heal" | "mana" | "buff" | "passive"
#   amount — HP/mana restored, or stat amount gained
#   stat   — (buff only) which stat to raise; None otherwise
#   permanent — (buff only) True = keeps bonus after fight
#   effect — display string shown in !shop / !inventory
shop_items = {
    # ── Healing ──────────────────────────────────────────────────
    "Minor Healing Potion": {
        "cost_copper": 50,
        "type": "heal", "amount": 30, "stat": None, "permanent": False,
        "effect": "Restores 30 HP",
    },
    "Great Healing Potion": {
        "cost_copper": 200,
        "type": "heal", "amount": 100, "stat": None, "permanent": False,
        "effect": "Restores 100 HP",
    },
    # ── Mana ─────────────────────────────────────────────────────
    "Mana Potion": {
        "cost_copper": 80,
        "type": "mana", "amount": 40, "stat": None, "permanent": False,
        "effect": "Restores 40 Mana",
    },
    "Greater Mana Potion": {
        "cost_copper": 200,
        "type": "mana", "amount": 100, "stat": None, "permanent": False,
        "effect": "Restores 100 Mana",
    },
    # ── Stat Buffs ────────────────────────────────────────────────
    "Strength Potion": {
        "cost_copper": 100,
        "type": "buff", "amount": 5, "stat": "attack", "permanent": False,
        "effect": "+5 Attack (lasts for the current fight)",
    },
    "Defense Potion": {
        "cost_copper": 100,
        "type": "buff", "amount": 5, "stat": "defense", "permanent": False,
        "effect": "+5 Defense (lasts for the current fight)",
    },
    "Speed Potion": {
        "cost_copper": 120,
        "type": "buff", "amount": 3, "stat": "speed", "permanent": False,
        "effect": "+3 Speed — reduces enemy counterattack chance",
    },
    "Intelligence Elixir": {
        "cost_copper": 150,
        "type": "buff", "amount": 5, "stat": "intelligence", "permanent": False,
        "effect": "+5 Intelligence (lasts for the current fight)",
    },
    "Lucky Potion": {
        "cost_copper": 180,
        "type": "buff", "amount": 10, "stat": "luck", "permanent": False,
        "effect": "+10 Luck — improves crit and flee odds",
    },
    "Ultimate Power Elixir": {
        "cost_copper": 1000,
        "type": "buff", "amount": 10, "stat": "attack", "permanent": True,
        "effect": "Permanently +10 Attack",
    },
    # ── Status Cures ──────────────────────────────────────────────
    "Antidote": {
        "cost_copper": 40,
        "type": "cure", "cures": ["poison"], "amount": 0, "stat": None, "permanent": False,
        "effect": "Cures Poisoned status effect",
    },
    "Burn Salve": {
        "cost_copper": 40,
        "type": "cure", "cures": ["burn"], "amount": 0, "stat": None, "permanent": False,
        "effect": "Cures Burning status effect",
    },
    "Elixir of Remedy": {
        "cost_copper": 100,
        "type": "cure", "cures": ["poison", "burn", "attack_debuff", "defense_debuff"], "amount": 0, "stat": None, "permanent": False,
        "effect": "Cures all negative status effects at once",
    },
    # ── Timed Buffs (tracked by status system) ────────────────────
    "Whetstone": {
        "cost_copper": 60,
        "type": "status_buff", "status": "attack_buff", "amount": 0, "stat": None, "permanent": False,
        "effect": "+12 Attack for 3 turns (combat only)",
    },
    "Arcane Shield": {
        "cost_copper": 60,
        "type": "status_buff", "status": "defense_buff", "amount": 0, "stat": None, "permanent": False,
        "effect": "+8 Defense for 3 turns (combat only)",
    },
    # ── Passive ───────────────────────────────────────────────────
    "Lucky Charm": {
        "cost_copper": 200,
        "type": "passive", "amount": 0, "stat": None, "permanent": False,
        "effect": "Passive: +15% flee chance while held in inventory",
    },
    # ── New dungeon-exclusive equipment (inventory display entries) ────────
    "Fallen King's Blade": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Weapon — +30 ATK · +2 SPD · +8% Crit · ⚠️ -20 Max HP (Cursed)",
    },
    "Ember Crown": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Armor — +8 ATK · +15 DEF · +30 Max HP · +10 Max Mana",
    },
    "Ashen Mantle": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Armor — +18 DEF · +35 Max HP · +5 Luck (fire-resistant)",
    },
    "Shadowweave Cloak": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Armor — +12 ATK · +10 DEF · +15 Max HP · +5 SPD · +5% Crit",
    },
    "Frostbite Ring": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Accessory — +8 ATK · +5 DEF · +20 Max HP · +3% Crit · +5 Luck",
    },
    "Celestial Pendant": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Accessory — +5 DEF · +30 Max HP · +20 Max Mana · +10 Luck",
    },
    "Voidforged Gauntlet": {
        "cost_copper": 0, "type": "gear", "amount": 0, "stat": None, "permanent": True,
        "effect": "Accessory — +20 ATK · +4 SPD · +10% Crit",
    },
    # ── Rift-exclusive drops ───────────────────────────────────────
    "Rift Crystal": {
        "cost_copper": 0,
        "type": "heal", "amount": 80, "stat": None, "permanent": False,
        "effect": "Restores 80 HP (Rift-exclusive drop — cannot be bought)",
    },
    "Void Fragment": {
        "cost_copper": 0,
        "type": "passive", "amount": 0, "stat": None, "permanent": False,
        "effect": "Passive: A crystallised shard of Void energy. Trophy from Void Rifts.",
    },
    # ── Equipment: Weapons ────────────────────────────────────────
    "Iron Sword":        {"cost_copper": 150,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Weapon — +5 ATK"},
    "Hunter's Bow":      {"cost_copper": 250,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Weapon — +8 ATK · +1 SPD · +2% Crit"},
    "Apprentice Staff":  {"cost_copper": 300,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Weapon — +12 ATK · +15 Max Mana"},
    "Knight's Blade":    {"cost_copper": 600,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Weapon — +18 ATK · +3 DEF"},
    # ── Equipment: Armor ──────────────────────────────────────────
    "Leather Armor":     {"cost_copper": 120,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Armor — +5 DEF · +10 Max HP"},
    "Iron Plate":        {"cost_copper": 400,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Armor — +12 DEF · +25 Max HP"},
    "Mage's Robe":       {"cost_copper": 250,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Armor — +4 DEF · +20 Max HP · +20 Max Mana"},
    # ── Equipment: Accessories ────────────────────────────────────
    "Swiftness Ring":    {"cost_copper": 180,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Accessory — +4 SPD · +3% Crit"},
    "Amulet of Power":   {"cost_copper": 250,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Accessory — +10 ATK"},
    "Mage's Focus":      {"cost_copper": 220,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Accessory — +30 Max Mana · +3% Crit"},
    "Lucky Pendant":     {"cost_copper": 200,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Accessory — +5% Crit · +15 Luck · +1 SPD"},
    "Battle Pendant":    {"cost_copper": 350,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Accessory — +5 ATK · +5 DEF · +20 Max HP"},
    "Scholar's Band":    {"cost_copper": 280,  "type": "gear", "amount": 0, "stat": None, "permanent": True, "effect": "Accessory — +25 Max Mana · +2 SPD · +10 Max HP"},
}

sell_prices = {
    "Minor Healing Potion":  25,
    "Strength Potion":       50,
    "Lucky Charm":           100,
    "Great Healing Potion":  100,
    "Antidote":              20,
    "Burn Salve":            20,
    "Elixir of Remedy":      50,
    "Whetstone":             30,
    "Arcane Shield":         30,
    "Legendary Sword":       500,
    "Shadow Blade":          400,
    "Void Cloak":            600,
    "Dragonscale Armor":     1200,
    "Demon King's Crown":    5000,
    "Ultimate Power Elixir": 500,
    "Iron Sword":            75,
    "Hunter's Bow":          125,
    "Apprentice Staff":      150,
    "Knight's Blade":        300,
    "Leather Armor":         60,
    "Iron Plate":            200,
    "Mage's Robe":           125,
    "Swiftness Ring":        90,
    "Amulet of Power":       125,
    "Mage's Focus":          110,
    "Lucky Pendant":         100,
    "Battle Pendant":        175,
    "Scholar's Band":        140,
    "Void Ring":             800,
    # ── New dungeon-exclusive items ───────────────────────────────────────
    "Fallen King's Blade":   1500,
    "Ember Crown":           1800,
    "Ashen Mantle":          1400,
    "Shadowweave Cloak":     2000,
    "Frostbite Ring":        700,
    "Celestial Pendant":     900,
    "Voidforged Gauntlet":   1200,
}

quest_data = {
    "welcome_quest": {
        "name": "A New Beginning",
        "description": "Explore Aetherfall and find your first adventure. (Try !explore or !fight!)",
        "reward_experience": 50,
        "reward_copper": 25,
        "completed": False,
    },
    "gravefall_expedition": {
        "name": "Gravefall Expedition",
        "description": "Travel to Gravefall and report back. (Use !travel Gravefall)",
        "reward_experience": 100,
        "reward_copper": 50,
        "completed": False,
    },
    "defeat_demon_king": {
        "name": "The Final Darkness",
        "description": "Travel to Voidkand and defeat the Demon King once and for all.",
        "reward_experience": 10000,
        "reward_copper": 2000,
        "completed": False,
    },
}

quest_chains = {
    "initial_journey": ["welcome_quest", "gravefall_expedition"],
    "world_salvation":  ["gravefall_expedition", "defeat_demon_king"],
}

chain_rewards = {
    "initial_journey": {"experience_bonus": 500,   "copper_bonus": 200,  "item": "Legendary Sword"},
    "world_salvation":  {"experience_bonus": 20000, "copper_bonus": 5000, "item": "Demon King's Crown"},
}

LOCATION_EMOJIS = {
    "Aetherfall":         "🏙️",
    "Gravefall":          "💀",
    "Rotveil":            "🧟",
    "Nerathis":           "🌊",
    "Eclipse Citadel":    "🏰",
    "Voidkand":           "👿",
    "Dungeon Gate":       "🚪",
    # ── New locations ──────────────────────────────────────────────────────
    "Frostmourne Wastes": "❄️",
    "Ashen Ruins":        "🔥",
    "Celestial Peak":     "✨",
    "Shadow Mire":        "🌑",
    "Iron Bastion":       "⚙️",
    "Abyssal Gate":       "🌀",
}

REALM_COLORS = {
    "Earth Layer":        0x5865F2,
    "The Empire":         0xFEE75C,
    "Void / Demon Realm": 0xED4245,
    "Frozen North":       0xA8DADC,
    "The Divine Heights": 0xFFD700,
}

# ------------------------------------------------------------------ #
#  LOCATION SPECIAL EFFECTS
# ------------------------------------------------------------------ #
# Applied when a player travels to / explores a location.
# type values:
#   "hp_drain"       — deals flat HP damage on arrival/explore
#   "burn_chance"    — chance to inflict Burning status on arrival
#   "heal_bonus"     — restores % of max HP on arrival
#   "night_danger"   — passive: enemy attack multiplied at night (display only)
#   "armored_enemies"— passive: enemies have extra defense (display only)
#   "void_risk"      — passive: enemies hit harder but rewards are amplified (display only)
LOCATION_EFFECTS: dict[str, dict] = {
    "Frostmourne Wastes": {
        "type":    "hp_drain",
        "amount":  15,
        "message": "❄️ The killing cold gnaws through your armor — you lose **{amount} HP** to frostbite.",
    },
    "Ashen Ruins": {
        "type":    "burn_chance",
        "chance":  0.35,
        "message": "🔥 Embers swirl from the ruins and sear your skin — you're **Burning**!",
    },
    "Celestial Peak": {
        "type":     "heal_bonus",
        "heal_pct": 0.10,
        "message":  "✨ The sacred mountain air mends your wounds — you recover **{amount} HP**.",
    },
    "Shadow Mire": {
        "type":           "night_danger",
        "enemy_atk_mult": 1.35,
        "message": (
            "🌑 *The mire grows restless as darkness falls. Enemies here are deadlier at night "
            "(+35% enemy attack during night hours).*"
        ),
    },
    "Iron Bastion": {
        "type":       "armored_enemies",
        "defense_add": 8,
        "message": "⚙️ *The fortress breeds warriors in thick iron — all enemies here carry +8 bonus Defense.*",
    },
    "Abyssal Gate": {
        "type":           "void_risk",
        "enemy_atk_mult": 1.25,
        "reward_mult":    1.50,
        "message": (
            "🌀 *Void energy crackles across your skin. Everything here is amplified — "
            "enemies hit 25% harder, but rewards are 50% richer.*"
        ),
    },
}

# ------------------------------------------------------------------ #
#  DUNGEON DISCOVERY — per-location flavor for explore
# ------------------------------------------------------------------ #
# Each entry is a list of (dungeon_name, discovery_message) tuples.
# A random entry is chosen when the discovery event fires.
LOCATION_DUNGEON_DISCOVER: dict[str, list[tuple[str, str]]] = {
    "Aetherfall": [
        ("Goblin Lair",
         "🚪 *You notice a grated hatch in the cobblestones. Cool, stale air rises from below. "
         "Something is down there.* Use `!dungeon Goblin Lair` to enter."),
    ],
    "Dungeon Gate": [
        ("Goblin Lair",
         "🚪 *The gate shudders. A low scraping sound echoes from deep within the passages beneath it.* "
         "Use `!dungeon Goblin Lair` to descend."),
    ],
    "Gravefall": [
        ("Shadow Crypt",
         "💀 *Beneath a collapsed building you find worn stone stairs descending into pitch darkness. "
         "The air smells of old iron and something older.* Use `!dungeon Shadow Crypt` to enter."),
    ],
    "Voidkand": [
        ("Demon's Keep",
         "👿 *The fortress walls loom ahead. Inside, something is screaming. Then it stops — "
         "suddenly and completely.* Use `!dungeon Demon's Keep` to press on."),
    ],
    "Frostmourne Wastes": [
        ("Crypt of the Fallen King",
         "🪦 *Buried deep in the ice, you find the outline of a massive stone door. "
         "Frost runes pulse faintly around its frame. The air grows colder as you approach.* "
         "Use `!dungeon Crypt of the Fallen King` to enter."),
    ],
    "Ashen Ruins": [
        ("Inferno Depths",
         "🌋 *Through the smoke you spot a great fissure in the earth. Heat pours from it like a furnace, "
         "and something glows orange far below.* Use `!dungeon Inferno Depths` to descend."),
    ],
    "Shadow Mire": [
        ("Temple of Shadows",
         "🌑 *Ancient pylons rise from the black water in a perfect circle, surrounding a submerged entrance. "
         "Black flame torches still burn on either side of the door.* "
         "Use `!dungeon Temple of Shadows` to enter."),
    ],
}
