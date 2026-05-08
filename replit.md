# Workspace

## Overview

pnpm workspace monorepo using TypeScript, plus a Python Discord bot.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)
- **Discord bot**: Python 3.11 + discord.py (slash commands)

## Discord Bot

Located in `bot/`. Uses prefix commands (`!`). Full multi-user RPG system.

### Structure
- `bot/main.py` — entry point, bot setup, cog loading
- `bot/cogs/rpg.py` — all RPG commands (travel, explore, fight, dungeon, shop, etc.)
- `bot/rpg/data.py` — world_map, gates, enemy_types, loot_table, EQUIPMENT_DATA, DUNGEON_DATA, LOCATION_EFFECTS, LOCATION_DUNGEON_DISCOVER
- `bot/rpg/explore_events.py` — LOCATION_EXPLORE_INTRO, LOCATION_EXPLORE_COLOR, EVENT_CONFIG
- `bot/rpg/player.py` — player state, combat, skills, equipment
- `bot/rpg/random_dungeon.py` — procedural random dungeon generation
- `bot/rpg/world_dungeon.py` — multiplayer world boss system
- `bot/rpg/rift.py` — void rift encounters
- `bot/rpg/chest.py` — chest / loot rarity system
- `bot/saves/` — per-user JSON save files

### World Map (13 locations)
Original: Aetherfall (Lv1), Gravefall (Lv10), Rotveil (Lv20), Nerathis (Lv30), Eclipse Citadel (Lv40), Voidkand (Lv50), Dungeon Gate (Lv25)
New: Frostmourne Wastes (Lv15, ❄️ HP drain), Ashen Ruins (Lv18, 🔥 burn chance), Celestial Peak (Lv30, ✨ heal bonus), Shadow Mire (Lv35, 🌑 night danger), Iron Bastion (Lv45, ⚙️ armored enemies), Abyssal Gate (Lv60, 🌀 void risk/reward)

### Named Dungeons (6 total)
- Goblin Lair, Shadow Crypt, Demon's Keep (original wave-based)
- Crypt of the Fallen King (Lv20, undead, boss: Fallen King, drops: Fallen King's Blade / Frostbite Ring)
- Inferno Depths (Lv28, fire, boss: Flame Tyrant, drops: Ember Crown / Ashen Mantle)
- Temple of Shadows (Lv35, shadow, boss: Shadow Priest, drops: Shadowweave Cloak / Celestial Pendant / Voidforged Gauntlet)

### Enemy Types (14 total)
Original: Goblin, Shadow Beast, Corrupted Knight, Dungeon Lord, Demon King
New: Skeleton Archer, Spectral Guard, Fallen King, Lava Golem, Flame Wraith, Flame Tyrant, Shadow Acolyte, Void Assassin, Shadow Priest

### Unique Items (7 new dungeon-exclusive)
Fallen King's Blade (+30 ATK, cursed -20 HP), Ember Crown (+8 ATK/+15 DEF), Ashen Mantle (+18 DEF/+35 HP), Shadowweave Cloak (+12 ATK/+10 DEF/+5 SPD/+5% Crit), Frostbite Ring (+8 ATK/+5 DEF/+20 HP), Celestial Pendant (+30 HP/+20 Mana/+10 Luck), Voidforged Gauntlet (+20 ATK/+10% Crit)

### LOCATION_EFFECTS system
Defined in `data.py` as `LOCATION_EFFECTS` dict. Applied in `!travel` on arrival.
Types: hp_drain, burn_chance, heal_bonus (active), night_danger, armored_enemies, void_risk (passive/informational).

### Dungeon Discovery (explore event)
`LOCATION_DUNGEON_DISCOVER` in `data.py` maps locations to dungeon discovery messages.
During `!explore`, 10% chance fires an immersive discovery embed pointing the player to a named dungeon.

### Secrets
- `DISCORD_TOKEN` — Discord bot token (set in Replit Secrets)

### Workflow
- **Discord Bot** — `python bot/main.py` (console output)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
