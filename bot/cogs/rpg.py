import asyncio
import random
import discord
from discord.ext import commands

from bot.rpg.data import (
    world_map, gates, shop_items, sell_prices, quest_data,
    LOCATION_EMOJIS, REALM_COLORS, RANDOM_ENCOUNTER_CHANCE,
    EQUIPMENT_DATA, CLASS_DEFINITIONS, CLASS_SKILLS, CLASS_SKILLS_T2, CLASS_SKILLS_T3, DUNGEON_DATA,
    STATUS_EFFECTS, enemy_types as _enemy_types,
    LOCATION_EFFECTS, LOCATION_DUNGEON_DISCOVER,
)
from bot.rpg.factions import (
    FACTIONS, FACTION_MISSIONS, REPUTATION_TIERS, MIN_FACTION_LEVEL,
    get_faction_key, get_faction, get_reputation_tier,
    faction_xp_mult, faction_copper_mult, faction_heal_mult,
    faction_attack_mult, faction_damage_taken_mult,
    available_missions, check_kill_missions,
    check_travel_missions, check_dungeon_missions,
    faction_join,
)
from bot.rpg.world_dungeon import (
    WORLD_BOSS_CONFIGS,
    get_world_dungeon, spawn_world_dungeon, join_world_dungeon,
    start_world_fight, world_boss_attack,
    distribute_world_rewards, clear_world_dungeon,
    world_dungeon_status_lines,
)
from bot.rpg.player import (
    new_player, save_game, load_game,
    add_experience, add_currency, format_currency, total_copper, spend_copper,
    add_to_inventory, remove_from_inventory, advance_time,
    trigger_quest, complete_quest,
    generate_enemy, roll_loot, use_item, use_item_in_combat, use_skill, start_pvp, enter_dungeon,
    apply_class, equip_gear, unequip_gear,
    damage_after_defense,
    apply_status_effect, tick_status_effects,
    list_characters, create_player_slot, switch_character, delete_character,
    get_active_slot_name, MAX_CHARACTER_SLOTS,
)
from bot.rpg.chest import maybe_find_chest, open_chest, roll_chest_rarity
from bot.rpg.rift import maybe_encounter_rift, RIFT_ENEMIES, RIFT_TYPES
from bot.rpg.random_dungeon import (
    maybe_spawn_dungeon, RAND_DUNGEON_BOSSES, generate_dungeon,
)
from bot.rpg.explore_events import (
    pick_explore_event, EVENT_CONFIG,
    LOCATION_EXPLORE_INTRO, LOCATION_EXPLORE_COLOR,
)
from bot.rpg.guild import (
    load_guilds, save_guilds,
    get_player_guild_id, find_guild_by_name,
    apply_guild_bonus, remove_guild_bonus, bonus_summary,
    create_guild, join_guild, leave_guild,
    add_guild_xp, simulate_guild_war,
    GUILD_BONUS_TABLE, GUILD_XP_TABLE,
)

ACTIVE_COMBATS:       dict[int, bool] = {}
ACTIVE_DUNGEONS:      dict[int, str]  = {}   # uid → dungeon_name
ACTIVE_RIFTS:         set[int]        = set()
ACTIVE_RAND_DUNGEONS: set[int]        = set()
players: dict[int, dict] = {}

# Track whether the Demon King server event is active
DEMON_KING_EVENT_ACTIVE = False


def ensure_player(user_id: int) -> dict | None:
    if user_id not in players:
        p = load_game(user_id)
        if p:
            players[user_id] = p
    return players.get(user_id)


def hp_bar(current: int, maximum: int, length: int = 10) -> str:
    filled = max(0, round((current / maximum) * length))
    return "█" * filled + "░" * (length - filled)


def location_color(loc_name: str) -> int:
    loc = world_map.get(loc_name, {})
    return REALM_COLORS.get(loc.get("realm", ""), 0x5865F2)


# ------------------------------------------------------------------ #
#  DEMON KING PHASE LOGIC
# ------------------------------------------------------------------ #
def get_demon_king_phase(enemy_hp: int, enemy_max_hp: int) -> int:
    ratio = enemy_hp / enemy_max_hp
    if ratio > 0.5:
        return 1
    elif ratio > 0.2:
        return 2
    else:
        return 3


def demon_king_turn(enemy: dict, enemy_hp: int, player: dict) -> tuple[int, int, list[str]]:
    """
    Returns (damage_dealt, messages).
    Phase 1: normal attacks.
    Phase 2: stronger attack, occasional Heavy Strike.
    Phase 3: rage — can attack twice, may heal.
    """
    msgs = []
    max_hp = enemy.get("max_hp", enemy["hp"])
    phase = get_demon_king_phase(enemy_hp, max_hp)
    total_dmg = 0

    def _attack(multiplier=1.0, label="attacks"):
        raw = random.randint(enemy["attack"] - 3, enemy["attack"] + 3)
        raw = int(raw * multiplier)
        dmg = damage_after_defense(raw, player.get("defense", 5))
        player["hp"] = max(0, player["hp"] - dmg)
        msgs.append(
            f"👿 **Demon King {label}** you for **{dmg}** dmg! "
            f"HP: **{player['hp']}/{player['max_hp']}** `{hp_bar(player['hp'], player['max_hp'])}`"
        )
        return dmg

    if phase == 1:
        total_dmg += _attack(1.0, "attacks")

    elif phase == 2:
        if enemy_hp / max_hp <= 0.5 and not enemy.get("phase2_announced"):
            msgs.insert(0, "🔥 **Phase 2!** The Demon King's power surges — his attacks grow deadlier!")
            enemy["phase2_announced"] = True
            enemy["attack"] = int(enemy["attack"] * 1.3)
        if random.random() < 0.3:
            total_dmg += _attack(1.8, "**Heavy Strikes**")
        else:
            total_dmg += _attack(1.0, "attacks")

    elif phase == 3:
        if not enemy.get("phase3_announced"):
            msgs.insert(0, "💀 **RAGE MODE!** The Demon King enters his final, berserk phase!")
            enemy["phase3_announced"] = True
            enemy["attack"] = int(enemy["attack"] * 1.5)
        # Chance to heal when low
        if enemy_hp < max_hp * 0.15 and not enemy.get("has_healed") and random.random() < 0.4:
            heal = int(max_hp * 0.1)
            enemy_hp += heal
            enemy["has_healed"] = True
            msgs.append(f"✨ **The Demon King absorbs dark energy** and heals **{heal} HP**!")
        # Always attacks; 50% chance to attack twice
        total_dmg += _attack(1.0, "attacks")
        if random.random() < 0.5:
            msgs.append("⚡ *The Demon King strikes again!*")
            total_dmg += _attack(1.0, "attacks")

    return enemy_hp, total_dmg, msgs


# ------------------------------------------------------------------ #
#  ENEMY AI: standard enemies
# ------------------------------------------------------------------ #
def enemy_turn(enemy: dict, player: dict) -> list[str]:
    """Standard enemy turn with crits, occasional power strike, and boss heal."""
    msgs = []
    is_boss = enemy.get("is_boss", False)
    crit_chance = enemy.get("crit_chance", 0.08)

    # Bosses (non-Demon-King) can heal once when below 25% HP
    if is_boss and not enemy.get("has_healed"):
        max_hp = enemy.get("max_hp", enemy["hp"])
        if enemy["hp"] < max_hp * 0.25 and random.random() < 0.35:
            heal = int(max_hp * 0.12)
            enemy["hp"] = min(max_hp, enemy["hp"] + heal)
            msgs.append(f"💚 **{enemy['name']} recovers {heal} HP!** (HP: {enemy['hp']})")
            enemy["has_healed"] = True

    # Power strike (20% chance for bosses, 10% normal)
    power_chance = 0.20 if is_boss else 0.10
    if random.random() < power_chance:
        raw = random.randint(enemy["attack"], int(enemy["attack"] * 1.5))
        dmg = damage_after_defense(raw, player.get("defense", 5))
        player["hp"] = max(0, player["hp"] - dmg)
        msgs.append(
            f"💢 **{enemy['name']} uses Power Strike** for **{dmg}** dmg! "
            f"HP: **{player['hp']}/{player['max_hp']}** `{hp_bar(player['hp'], player['max_hp'])}`"
        )
    else:
        raw = random.randint(enemy["attack"] - 2, enemy["attack"] + 2)
        is_crit = random.random() < crit_chance
        if is_crit:
            raw = int(raw * 1.5)
        dmg = damage_after_defense(raw, player.get("defense", 5))
        player["hp"] = max(0, player["hp"] - dmg)
        crit_tag = " 💥 *CRITICAL HIT!*" if is_crit else ""
        msgs.append(
            f"⚔️ **{enemy['name']}** hits you for **{dmg}** dmg!{crit_tag} "
            f"HP: **{player['hp']}/{player['max_hp']}** `{hp_bar(player['hp'], player['max_hp'])}`"
        )
    return msgs


# ------------------------------------------------------------------ #
#  DUNGEON RUNNER  (multi-wave, interactive)
# ------------------------------------------------------------------ #
async def _run_dungeon(
    ctx: commands.Context,
    player: dict,
    dungeon_name: str,
    dungeon: dict,
    bot,
) -> None:
    """
    Run a full dungeon session for one player.
    Fights each enemy per wave using _run_combat().
    Between waves: 25% HP restore + continue/retreat prompt.
    After all waves: award dungeon rewards and rare drop roll.
    """
    uid = ctx.author.id
    waves = dungeon["waves"]
    total_waves = len(waves)
    ACTIVE_DUNGEONS[uid] = dungeon_name

    # ── Dungeon intro embed ──────────────────────────────────────────
    intro = discord.Embed(
        title=f"{dungeon['emoji']} Entering: {dungeon_name}",
        description=(
            f"*{dungeon['flavor']}*\n\n"
            f"{dungeon['description']}\n\n"
            f"**{total_waves} waves** stand between you and victory. Good luck."
        ),
        color=0xED4245,
    )
    intro.add_field(
        name="Your Stats",
        value=(
            f"❤️ HP: **{player['hp']}/{player['max_hp']}**\n"
            f"⚔️ ATK: **{player['attack']}** · 🛡️ DEF: **{player.get('defense',5)}**\n"
            f"🔵 Mana: **{player.get('mana',0)}/{player.get('max_mana',50)}**"
        ),
        inline=True,
    )
    wave_list = "\n".join(
        f"{'⚠️' if w.get('is_boss_wave') else f'Wave {i+1}'}: {w['label'].split('—')[-1].strip()} "
        f"({'BOSS' if w.get('is_boss_wave') else ', '.join(w['enemies'])})"
        for i, w in enumerate(waves)
    )
    intro.add_field(name="Wave Preview", value=wave_list, inline=False)
    await ctx.send(embed=intro)

    try:
        for wave_idx, wave in enumerate(waves):
            wave_num  = wave_idx + 1
            is_boss   = wave.get("is_boss_wave", False)
            wave_enemies = wave["enemies"]

            # ── Wave announcement ────────────────────────────────────
            wave_color = 0xFEE75C if not is_boss else 0xED4245
            boss_lore  = dungeon.get("boss_intro", "") if is_boss else ""
            wave_embed = discord.Embed(
                title=f"{'☠️ BOSS WAVE' if is_boss else f'Wave {wave_num}/{total_waves}'} — {wave['label'].split('—')[-1].strip()}",
                description=(
                    (f"*{boss_lore}*\n\n" if boss_lore else "")
                    + f"Enemies: **{', '.join(wave_enemies)}**\n"
                    + f"Your HP: **{player['hp']}/{player['max_hp']}** "
                    + f"`{hp_bar(player['hp'], player['max_hp'])}`"
                ),
                color=wave_color,
            )
            if is_boss:
                wave_embed.set_footer(text="This is the final trial. Give everything you have.")
            await ctx.send(embed=wave_embed)

            # ── Fight each enemy in the wave ─────────────────────────
            for enemy_name in wave_enemies:
                if player["hp"] <= 0:
                    break

                enemy_data = _enemy_types.get(enemy_name)
                if not enemy_data:
                    await ctx.send(f"⚠️ Unknown enemy `{enemy_name}` — skipping.")
                    continue

                enemy: dict = {
                    "name":               enemy_name,
                    "hp":                 enemy_data["hp"],
                    "attack":             enemy_data["attack"],
                    "defense":            enemy_data["defense"],
                    "experience_reward":  enemy_data["experience_reward"],
                    "copper_reward":      enemy_data["copper_reward"],
                    "crit_chance":        enemy_data["crit_chance"],
                    "is_boss":            enemy_data.get("is_boss", False),
                    "inflicts":           enemy_data.get("inflicts", []),
                }
                if player.get("time_of_day") == "night":
                    enemy["attack"]      = int(enemy["attack"] * 1.2)
                    enemy["night_buffed"] = True

                ACTIVE_COMBATS[uid] = True
                outcome = await _run_combat(ctx, player, enemy, bot, chest_context="dungeon_wave")

                if outcome in ("lose", "timeout"):
                    fail = discord.Embed(
                        title="💀 Dungeon Failed!",
                        description=(
                            f"You were defeated in **{dungeon_name}** during **{wave['label']}**.\n"
                            f"Progress: Wave **{wave_num}/{total_waves}**"
                        ),
                        color=0xED4245,
                    )
                    fail.set_footer(text="Rest up and try again with !dungeon")
                    await ctx.send(embed=fail)
                    return

                if outcome == "flee":
                    fled = discord.Embed(
                        title="💨 Fled the Dungeon",
                        description=f"You escaped **{dungeon_name}** during Wave **{wave_num}**. No rewards.",
                        color=0x95A5A6,
                    )
                    await ctx.send(embed=fled)
                    return

            # Safety: player died during this wave
            if player["hp"] <= 0:
                await ctx.send(f"💀 You fell in **{dungeon_name}**. No rewards.")
                return

            # ── Between waves: heal + continue/retreat prompt ────────
            if wave_idx < total_waves - 1:
                heal = max(1, int(player["max_hp"] * 0.25))
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                save_game(uid, player)

                next_wave = waves[wave_idx + 1]
                between = discord.Embed(
                    title=f"✅ Wave {wave_num} Cleared!",
                    description=(
                        f"You catch your breath. Recovered **{heal} HP**.\n"
                        f"HP: **{player['hp']}/{player['max_hp']}** "
                        f"`{hp_bar(player['hp'], player['max_hp'])}`\n\n"
                        f"**Next:** {next_wave['label']}\n"
                        f"Enemies: {', '.join(next_wave['enemies'])}"
                    ),
                    color=0x57F287,
                )
                between.set_footer(text="Type 'continue' to advance or 'retreat' to exit (no rewards).")
                await ctx.send(embed=between)

                def wave_check(m: discord.Message) -> bool:
                    return (
                        m.author == ctx.author
                        and m.channel == ctx.channel
                        and m.content.strip().lower() in ("continue", "retreat")
                    )

                try:
                    resp = await bot.wait_for("message", timeout=90.0, check=wave_check)
                except asyncio.TimeoutError:
                    await ctx.send(
                        f"⏱️ No response — you retreat from **{dungeon_name}**. No rewards."
                    )
                    return

                if resp.content.strip().lower() == "retreat":
                    retreat = discord.Embed(
                        title="🚪 Retreated",
                        description=(
                            f"You escaped **{dungeon_name}** safely after Wave {wave_num}.\n"
                            f"Come back stronger! (`!dungeon {dungeon_name}`)"
                        ),
                        color=0x95A5A6,
                    )
                    await ctx.send(embed=retreat)
                    return

        # ─────────────────────────────────────────────────────────────
        # ALL WAVES CLEARED — award rewards
        # ─────────────────────────────────────────────────────────────
        rewards = dungeon["rewards"]
        # Apply Eclipse Empire reward bonus (+10% XP + copper)
        _dxp  = int(rewards["xp"]     * faction_xp_mult(player))
        _dcop = int(rewards["copper"] * faction_copper_mult(player))
        xp_msgs  = add_experience(player, _dxp)
        gold_msg = add_currency(player, _dcop)

        # Roll rare drops
        rare_drops: list[str] = []
        for drop in rewards.get("rare_drops", []):
            if random.random() < drop["chance"]:
                add_to_inventory(player, drop["item"])
                rare_drops.append(drop["item"])

        # First-time clear bonus
        completed_list: list = player.setdefault("dungeons_completed", [])
        first_clear = dungeon_name not in completed_list
        if first_clear:
            completed_list.append(dungeon_name)
            bonus_xp   = rewards["xp"] // 2
            bonus_msg  = f"\n✨ **First Clear Bonus:** +{bonus_xp} XP!"
            xp_msgs   += add_experience(player, bonus_xp)
        else:
            bonus_msg  = ""

        # Check faction dungeon-clear missions
        _faction_dungeon_msgs = check_dungeon_missions(player, dungeon_name)

        save_game(uid, player)

        for _fdm in _faction_dungeon_msgs:
            await ctx.send(_fdm)

        victory_lore = dungeon.get("victory_msg", "")
        victory = discord.Embed(
            title=f"🏆 {dungeon_name} — Cleared!",
            description=(
                (f"*{victory_lore}*\n\n" if victory_lore else "")
                + f"**All {total_waves} waves conquered!**{bonus_msg}\n\n"
                + f"HP remaining: **{player['hp']}/{player['max_hp']}** "
                + f"`{hp_bar(player['hp'], player['max_hp'])}`"
            ),
            color=0x57F287,
        )
        victory.add_field(name="⭐ XP Gained",      value=f"+{rewards['xp']} XP", inline=True)
        victory.add_field(name="💰 Copper Gained",  value=f"+{rewards['copper']}c", inline=True)
        if rare_drops:
            victory.add_field(
                name="✨ Rare Drops",
                value="\n".join(f"• **{item}**" for item in rare_drops),
                inline=False,
            )
        else:
            victory.add_field(
                name="🎲 Rare Drops",
                value="No rare drops this run — better luck next time!",
                inline=False,
            )
        clears = len(completed_list)
        victory.set_footer(text=f"Dungeons cleared: {clears} total")
        for msg in xp_msgs:
            if msg:
                victory.description = (victory.description or "") + f"\n{msg}"
        await ctx.send(embed=victory)

        # ── Guaranteed chest on dungeon clear ─────────────────────────────
        _dc_rarity = maybe_find_chest(player, "dungeon_clear")
        if _dc_rarity:
            # Higher-tier dungeons skew toward rarer chests
            if dungeon_name == "Demon's Keep":
                _dc_rarity = roll_chest_rarity(player, force_min="Epic")
            elif dungeon_name == "Shadow Crypt":
                _dc_rarity = roll_chest_rarity(player, force_min="Rare")
            _dc_result = open_chest(player, _dc_rarity)
            save_game(uid, player)
            await ctx.send(embed=_chest_embed(_dc_result))

        # ── Guild XP for dungeon clear ─────────────────────────────────────
        if player.get("guild_id"):
            try:
                _guilds = load_guilds()
                _lvl_msgs = add_guild_xp(player["guild_id"], 50, _guilds)
                save_guilds(_guilds)
                for _m in _lvl_msgs:
                    await ctx.send(_m)
            except Exception:
                pass

    finally:
        ACTIVE_DUNGEONS.pop(uid, None)
        ACTIVE_COMBATS.pop(uid, None)


# ------------------------------------------------------------------ #
#  RIFT EVENT RUNNER
# ------------------------------------------------------------------ #
async def _run_rift(
    ctx: commands.Context,
    player: dict,
    rift_type_name: str,
    bot,
) -> None:
    """
    Run a full rift encounter for one player.
    Announces the rift, prompts enter/ignore, then runs waves sequentially.
    Awards high rewards on full clear; applies HP penalty on failure / flee.
    """
    uid    = ctx.author.id
    rift   = RIFT_TYPES[rift_type_name]
    is_void = rift_type_name == "Void Rift"

    ACTIVE_RIFTS.add(uid)
    try:
        # ── Dramatic announcement ──────────────────────────────────────────
        wave_preview = "\n".join(
            f"{'⚠️ BOSS' if w.get('is_boss_wave') else f'Wave {i+1}'}: "
            f"{', '.join(w['enemies'])}"
            for i, w in enumerate(rift["waves"])
        )
        announce = discord.Embed(
            title=f"{rift['emoji']} RIFT ENCOUNTERED",
            description=(
                f"{rift['tagline']}\n\n"
                f"*{rift['flavor']}*\n\n"
                f"**Rewards:** High XP · High Currency · Rare Loot\n"
                f"**Failure:** {'Near death — 1 HP remaining' if is_void else 'Heavy damage (−40% max HP)'}"
            ),
            color=rift["color"],
        )
        announce.add_field(name="Waves Inside", value=wave_preview, inline=False)
        announce.add_field(
            name="Your Current HP",
            value=f"**{player['hp']}/{player['max_hp']}** `{hp_bar(player['hp'], player['max_hp'])}`",
            inline=False,
        )
        announce.set_footer(text="Type 'enter' to brave the rift · 'ignore' to walk away (60 s)")
        await ctx.send(embed=announce)

        # ── Enter / ignore prompt ──────────────────────────────────────────
        def decision_check(m: discord.Message) -> bool:
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content.strip().lower() in ("enter", "ignore")
            )

        try:
            resp = await bot.wait_for("message", timeout=60.0, check=decision_check)
        except asyncio.TimeoutError:
            await ctx.send(
                f"{rift['emoji']} The rift flickers and collapses. You chose caution."
            )
            return

        if resp.content.strip().lower() == "ignore":
            await ctx.send(
                f"{rift['emoji']} You step back. The rift tears itself shut with a thunderous crack."
            )
            return

        # ── Player enters ──────────────────────────────────────────────────
        enter_embed = discord.Embed(
            title=f"{rift['emoji']} ENTERING THE {'VOID ' if is_void else ''}RIFT…",
            description=(
                "You leap through the threshold — reality warps around you.\n"
                "Fight your way through or suffer the consequences."
            ),
            color=rift["color"],
        )
        await ctx.send(embed=enter_embed)

        waves      = rift["waves"]
        total_waves = len(waves)
        all_won    = True

        for wave_idx, wave in enumerate(waves):
            wave_num    = wave_idx + 1
            is_boss_wave = wave.get("is_boss_wave", False)

            # ── Wave announcement ────────────────────────────────────────
            wave_embed = discord.Embed(
                title=(
                    f"{'☠️ BOSS WAVE' if is_boss_wave else f'Rift Wave {wave_num}/{total_waves}'}"
                    f" — {wave['label'].split('—')[-1].strip()}"
                ),
                description=(
                    f"Enemies: **{', '.join(wave['enemies'])}**\n"
                    f"HP: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                ),
                color=0xED4245 if is_boss_wave else rift["color"],
            )
            await ctx.send(embed=wave_embed)

            # ── Fight each enemy in the wave ─────────────────────────────
            for enemy_name in wave["enemies"]:
                if player["hp"] <= 0:
                    break

                enemy_data = RIFT_ENEMIES.get(enemy_name)
                if not enemy_data:
                    await ctx.send(f"⚠️ Unknown rift enemy `{enemy_name}` — skipping.")
                    continue

                _rift_level = player.get("level", 1)
                _rift_scale = 1 + (_rift_level - 1) * 0.07
                enemy: dict = {
                    "name":              enemy_name,
                    "hp":                int(enemy_data["hp"] * _rift_scale),
                    "max_hp":            int(enemy_data["hp"] * _rift_scale),
                    "attack":            int(enemy_data["attack"] * _rift_scale),
                    "defense":           enemy_data["defense"],
                    "experience_reward": enemy_data["experience_reward"],
                    "copper_reward":     enemy_data["copper_reward"],
                    "crit_chance":       enemy_data["crit_chance"],
                    "is_boss":           enemy_data.get("is_boss", False),
                    "inflicts":          enemy_data.get("inflicts", []),
                }

                ACTIVE_COMBATS[uid] = True
                outcome = await _run_combat(
                    ctx, player, enemy, bot, chest_context="dungeon_wave"
                )

                if outcome in ("lose", "timeout", "flee"):
                    all_won = False
                    break

            if not all_won:
                break

            # ── Between waves: heal + continue/retreat prompt ────────────
            if wave_idx < total_waves - 1 and all_won:
                heal = max(1, int(player["max_hp"] * 0.20))
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                save_game(uid, player)

                next_wave = waves[wave_idx + 1]
                between = discord.Embed(
                    title=f"✅ Rift Wave {wave_num} Cleared!",
                    description=(
                        f"The rift shudders. You catch your breath. **+{heal} HP** recovered.\n"
                        f"HP: **{player['hp']}/{player['max_hp']}** "
                        f"`{hp_bar(player['hp'], player['max_hp'])}`\n\n"
                        f"**Next:** {', '.join(next_wave['enemies'])}"
                    ),
                    color=rift["color"],
                )
                between.set_footer(
                    text="Type 'continue' to press on · 'retreat' to escape (no rewards, no penalty)"
                )
                await ctx.send(embed=between)

                def wave_check(m: discord.Message) -> bool:
                    return (
                        m.author == ctx.author
                        and m.channel == ctx.channel
                        and m.content.strip().lower() in ("continue", "retreat")
                    )

                try:
                    wr = await bot.wait_for("message", timeout=90.0, check=wave_check)
                except asyncio.TimeoutError:
                    await ctx.send(
                        f"⏱️ No response — the rift expels you. No rewards."
                    )
                    all_won = False
                    break

                if wr.content.strip().lower() == "retreat":
                    await ctx.send(
                        f"{rift['emoji']} You scramble out of the rift. No rewards — but you escaped."
                    )
                    all_won = False
                    break

        # ── Failure penalty ────────────────────────────────────────────────
        if not all_won:
            fail_pct = rift["failure_hp_pct"]
            if fail_pct >= 1.0 or player["hp"] - int(player["max_hp"] * fail_pct) <= 0:
                player["hp"] = 1
            else:
                penalty = int(player["max_hp"] * fail_pct)
                player["hp"] = max(1, player["hp"] - penalty)
            save_game(uid, player)
            await ctx.send(
                rift["failure_message"]
                + f"\nHP: **{player['hp']}/{player['max_hp']}** "
                + f"`{hp_bar(player['hp'], player['max_hp'])}`"
            )
            return

        # ── All waves cleared — award rewards ──────────────────────────────
        rewards  = rift["rewards"]
        xp_msgs  = add_experience(player, rewards["xp"])
        add_currency(player, rewards["copper"])

        drops: list[str] = []
        for drop in rewards.get("drops", []):
            if random.random() < drop["chance"]:
                add_to_inventory(player, drop["item"])
                drops.append(drop["item"])

        # Guaranteed chest, minimum tier based on rift type
        _rc = roll_chest_rarity(player, force_min=rift["chest_min"])
        _cr = open_chest(player, _rc)
        save_game(uid, player)

        victory = discord.Embed(
            title=f"{rift['emoji']} {'VOID RIFT' if is_void else 'RIFT'} CONQUERED!",
            description=(
                f"**The rift tears itself apart as you emerge victorious!**\n\n"
                f"HP: **{player['hp']}/{player['max_hp']}** "
                f"`{hp_bar(player['hp'], player['max_hp'])}`"
            ),
            color=0x57F287,
        )
        victory.add_field(name="⭐ XP Gained",     value=f"+{rewards['xp']}", inline=True)
        victory.add_field(name="💰 Copper Gained", value=f"+{rewards['copper']}c", inline=True)
        if drops:
            victory.add_field(
                name="✨ Rare Drops",
                value="\n".join(f"• **{d}**" for d in drops),
                inline=False,
            )
        for msg in xp_msgs:
            if msg:
                victory.description = (victory.description or "") + f"\n{msg}"
        await ctx.send(embed=victory)

        # Show guaranteed chest
        await ctx.send(embed=_chest_embed(_cr))

        # Normal Rift: 15% chance its collapse tears open a dungeon passage
        if not is_void and random.random() < 0.15 and player["hp"] > 1:
            await ctx.send(
                "🌀 **The rift's collapse tears open a passage in the fabric of space…**\n"
                "A dungeon entrance materializes before you — something was hiding behind the rift!"
            )
            _portal = generate_dungeon(player)
            await _run_random_dungeon(ctx, player, _portal, bot)

    finally:
        ACTIVE_RIFTS.discard(uid)
        ACTIVE_COMBATS.pop(uid, None)


# ------------------------------------------------------------------ #
#  RANDOM DUNGEON RUNNER  (procedural, room-by-room)
# ------------------------------------------------------------------ #
async def _run_random_dungeon(
    ctx: commands.Context,
    player: dict,
    dungeon: dict,
    bot,
) -> None:
    """
    Run a procedurally-generated random dungeon room by room.
    Handles enemy, treasure, trap, rest, and boss rooms.
    Prompts 'continue' / 'leave' between rooms.
    Awards scaled rewards and a guaranteed chest on full clear.
    """
    uid          = ctx.author.id
    dungeon_name = dungeon["name"]
    rooms        = dungeon["rooms"]
    total        = dungeon["room_count"]

    ACTIVE_RAND_DUNGEONS.add(uid)
    try:
        # ── Intro embed ──────────────────────────────────────────────────
        room_preview = "\n".join(
            f"Room {r['number']}: {r['emoji']} {r['title']}"
            + (f" — **{r['enemy']}**" if r["type"] in ("enemy", "boss") else "")
            for r in rooms
        )
        intro = discord.Embed(
            title=f"🏚️ Random Dungeon: {dungeon_name}",
            description=(
                f"A dungeon has materialized in your path!\n\n"
                f"**{total} rooms** stand between you and the boss.\n"
                f"*Navigate room by room — fight, loot, rest, or survive traps.*"
            ),
            color=0xE67E22,
        )
        intro.add_field(
            name="Your Stats",
            value=(
                f"❤️ HP: **{player['hp']}/{player['max_hp']}**\n"
                f"⚔️ ATK: **{player['attack']}** · 🛡️ DEF: **{player.get('defense', 5)}**"
            ),
            inline=True,
        )
        intro.add_field(name="Room Layout",  value=room_preview,                             inline=False)
        intro.add_field(name="Final Boss",   value=f"☠️ **{dungeon['boss_name']}**",        inline=False)
        intro.add_field(name="Boss Victory", value=f"Guaranteed **{dungeon['chest_min']}+** chest", inline=False)
        intro.set_footer(text="Type 'enter' to begin · 'skip' to ignore this dungeon (60 s)")
        await ctx.send(embed=intro)

        # ── Enter / skip prompt ──────────────────────────────────────────
        def enter_check(m: discord.Message) -> bool:
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.content.strip().lower() in ("enter", "skip")
            )

        try:
            resp = await bot.wait_for("message", timeout=60.0, check=enter_check)
        except asyncio.TimeoutError:
            await ctx.send("🏚️ The dungeon fades away — you took too long to decide.")
            return

        if resp.content.strip().lower() == "skip":
            await ctx.send("🏚️ You step around the dungeon entrance. Perhaps another time.")
            return

        await ctx.send(f"🏚️ **Entering {dungeon_name}!** Prepare yourself…")

        # ── Room loop ────────────────────────────────────────────────────
        all_cleared = True

        for room in rooms:
            rtype   = room["type"]
            rnum    = room["number"]
            is_boss = rtype == "boss"

            if player["hp"] <= 1 and rtype in ("enemy", "boss"):
                await ctx.send(
                    "💀 You're too wounded to fight on — you collapse at the dungeon entrance."
                )
                all_cleared = False
                break

            # ── Room header embed ─────────────────────────────────────
            room_embed = discord.Embed(
                title=f"{room['emoji']} Room {rnum}/{total} — {room['title']}",
                description=(
                    f"HP: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                ),
                color=0xED4245 if is_boss else 0xE67E22,
            )
            if rtype in ("enemy", "boss"):
                room_embed.add_field(
                    name="👹 Enemy",
                    value=f"**{room['enemy']}**" + ("  ⚠️ **BOSS**" if is_boss else ""),
                    inline=False,
                )
            elif rtype == "trap":
                room_embed.add_field(name="⚠️ Danger!", value=room["flavor"], inline=False)
            elif rtype == "rest":
                room_embed.add_field(name="🏕️ Safe Haven", value=room["flavor"], inline=False)
            elif rtype == "treasure":
                room_embed.add_field(
                    name="💰 Treasure",
                    value="A chest sits in the corner, gleaming with promise.",
                    inline=False,
                )
            await ctx.send(embed=room_embed)

            # ── Handle room ──────────────────────────────────────────────
            if rtype in ("enemy", "boss"):
                enemy_name = room["enemy"]
                if is_boss:
                    base = dict(RAND_DUNGEON_BOSSES[enemy_name])
                else:
                    base = dict(_enemy_types.get(enemy_name, {}))
                    if not base:
                        await ctx.send(f"⚠️ Unknown enemy `{enemy_name}` — skipping room.")
                        continue

                level = player.get("level", 1)
                scale = 1 + (level - 1) * 0.08
                enemy: dict = {
                    "name":              enemy_name,
                    "hp":                int(base["hp"] * scale),
                    "max_hp":            int(base["hp"] * scale),
                    "attack":            int(base["attack"] * scale),
                    "defense":           base.get("defense", 3),
                    "experience_reward": base["experience_reward"],
                    "copper_reward":     base["copper_reward"],
                    "crit_chance":       base["crit_chance"],
                    "is_boss":           base.get("is_boss", False),
                    "inflicts":          base.get("inflicts", []),
                }

                ACTIVE_COMBATS[uid] = True
                outcome = await _run_combat(
                    ctx, player, enemy, bot, chest_context="dungeon_wave"
                )

                if outcome in ("lose", "timeout"):
                    fail = discord.Embed(
                        title="💀 Dungeon Failed!",
                        description=(
                            f"You were defeated in **{dungeon_name}** "
                            f"at Room **{rnum}/{total}** — {room['title']}.\n"
                            f"Rest up and explore again for another dungeon!"
                        ),
                        color=0xED4245,
                    )
                    fail.set_footer(text="Use !rest to recover HP.")
                    await ctx.send(embed=fail)
                    all_cleared = False
                    break

                if outcome == "flee":
                    await ctx.send(
                        f"💨 You flee **{dungeon_name}**! No full rewards — but you survived."
                    )
                    all_cleared = False
                    break

            elif rtype == "treasure":
                t_rarity = roll_chest_rarity(player, force_min="Common")
                t_result = open_chest(player, t_rarity)
                save_game(uid, player)
                await ctx.send(embed=_chest_embed(t_result))

            elif rtype == "trap":
                dmg = max(1, int(player["max_hp"] * room["damage_pct"]))
                player["hp"] = max(1, player["hp"] - dmg)
                save_game(uid, player)
                await ctx.send(
                    f"⚠️ **Trap!** {room['flavor']}\n"
                    f"You take **{dmg} damage**! "
                    f"HP: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                )

            elif rtype == "rest":
                heal = max(1, int(player["max_hp"] * room["heal_pct"]))
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                save_game(uid, player)
                await ctx.send(
                    f"🏕️ **Rest.** {room['flavor']}\n"
                    f"You recover **{heal} HP**. "
                    f"HP: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                )

            # ── Between-room prompt (not after the final boss) ────────
            if rnum < total and all_cleared:
                next_r = rooms[rnum]   # rooms is 0-indexed; rnum is 1-indexed
                next_label = (
                    f"{next_r['emoji']} {next_r['title']}"
                    + (f" — **{next_r['enemy']}**" if next_r["type"] in ("enemy", "boss") else "")
                )
                between = discord.Embed(
                    title=f"✅ Room {rnum} Complete!",
                    description=(
                        f"HP: **{player['hp']}/{player['max_hp']}** "
                        f"`{hp_bar(player['hp'], player['max_hp'])}`\n\n"
                        f"**Next:** {next_label}"
                    ),
                    color=0xED4245 if next_r["type"] == "boss" else 0x57F287,
                )
                between.set_footer(
                    text="Type 'continue' to press on · 'leave' to exit safely (no full rewards)"
                )
                await ctx.send(embed=between)

                def cont_check(m: discord.Message) -> bool:
                    return (
                        m.author == ctx.author
                        and m.channel == ctx.channel
                        and m.content.strip().lower() in ("continue", "leave")
                    )

                try:
                    cr = await bot.wait_for("message", timeout=90.0, check=cont_check)
                except asyncio.TimeoutError:
                    await ctx.send("⏱️ No response — you slip out of the dungeon. No full rewards.")
                    all_cleared = False
                    break

                if cr.content.strip().lower() == "leave":
                    await ctx.send(
                        f"🚪 You exit **{dungeon_name}** early. "
                        f"No full rewards — but you keep what you found along the way."
                    )
                    all_cleared = False
                    break

        # ── Boss defeated: award full dungeon rewards ─────────────────────
        if all_cleared:
            rewards = dungeon["rewards"]
            xp_msgs = add_experience(player, rewards["xp"])
            add_currency(player, rewards["copper"])
            save_game(uid, player)

            victory = discord.Embed(
                title=f"🏆 {dungeon_name} — Cleared!",
                description=(
                    f"**{dungeon['boss_name']} has fallen!**\n"
                    f"You conquer all **{total} rooms** and emerge victorious.\n\n"
                    f"HP remaining: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                ),
                color=0x57F287,
            )
            victory.add_field(name="⭐ XP Gained",     value=f"+{rewards['xp']}",     inline=True)
            victory.add_field(name="💰 Copper Gained", value=f"+{rewards['copper']}c", inline=True)
            for msg in xp_msgs:
                if msg:
                    victory.description = (victory.description or "") + f"\n{msg}"
            await ctx.send(embed=victory)

            # Guaranteed chest based on boss tier
            _rc = roll_chest_rarity(player, force_min=dungeon["chest_min"])
            _cr = open_chest(player, _rc)
            save_game(uid, player)
            await ctx.send(embed=_chest_embed(_cr))

            # Guild XP
            if player.get("guild_id"):
                try:
                    _guilds   = load_guilds()
                    _lvl_msgs = add_guild_xp(player["guild_id"], 30, _guilds)
                    save_guilds(_guilds)
                    for _m in _lvl_msgs:
                        await ctx.send(_m)
                except Exception:
                    pass

    finally:
        ACTIVE_RAND_DUNGEONS.discard(uid)
        ACTIVE_COMBATS.pop(uid, None)


# ------------------------------------------------------------------ #
#  PvP COMBAT RUNNER  (interactive, two live Discord users)
# ------------------------------------------------------------------ #
async def _run_pvp(
    ctx: commands.Context,
    p1_member: discord.Member, p1: dict,
    p2_member: discord.Member, p2: dict,
    bot,
) -> str:
    """
    Full interactive PvP loop. Both players type their actions in Discord.
    Returns 'p1_win' | 'p2_win' | 'draw'.
    Saves both players and updates pvp_wins / pvp_losses in the finally block.
    """
    uid1, uid2 = p1_member.id, p2_member.id
    hp = {uid1: p1["hp"], uid2: p2["hp"]}
    pdata = {uid1: p1, uid2: p2}
    pmembers = {uid1: p1_member, uid2: p2_member}
    pnames = {uid1: p1_member.display_name, uid2: p2_member.display_name}
    opp = {uid1: uid2, uid2: uid1}

    # Higher Speed goes first; ties broken by coin flip
    if p1.get("speed", 5) >= p2.get("speed", 5):
        turn_order = [uid1, uid2]
    else:
        turn_order = [uid2, uid1]

    # Intro embed — full stat summary for both fighters
    intro = discord.Embed(
        title="⚔️ PvP Duel!",
        description=(
            f"**{pnames[uid1]}** vs **{pnames[uid2]}**\n"
            f"⚡ **{pnames[turn_order[0]]}** goes first (higher Speed)!\n\n"
            f"Each turn: `attack` · `flee` · `use <item>` · `skill`"
        ),
        color=0xEB459E,
    )
    for uid in [uid1, uid2]:
        p = pdata[uid]
        sk = CLASS_SKILLS.get(p.get("class", "Hunter"))
        intro.add_field(
            name=f"{'▶' if uid == turn_order[0] else '○'} {pnames[uid]} — Lv {p['level']} {p['class']}",
            value=(
                f"❤️ **{hp[uid]}/{p['max_hp']}** HP\n"
                f"⚔️ ATK **{p['attack']}** · 🛡️ DEF **{p.get('defense',5)}**\n"
                f"🔵 Mana **{p.get('mana',0)}/{p.get('max_mana',50)}**\n"
                f"💨 Spd **{p.get('speed',5)}** · 💥 Crit **{p.get('crit_chance',0.05)*100:.0f}%**\n"
                + (f"⚡ Skill: **{sk['name']}** ({sk['mana_cost']} mana)" if sk else "No class skill")
            ),
            inline=True,
        )
    await ctx.send(embed=intro)

    outcome = "draw"
    stun_skip: set[int] = set()          # UIDs whose next turn is skipped (legacy skill stun)
    p_statuses: dict[int, dict] = {uid1: {}, uid2: {}}   # DoT / buff statuses per player
    turn_idx = 0
    MAX_ACTIONS = 60              # hard cap (30 rounds × 2 players)

    def _pvp_status_line(uid: int) -> str:
        statuses = p_statuses[uid]
        if not statuses:
            return ""
        parts = [
            f"{STATUS_EFFECTS.get(n, {}).get('emoji', '💢')} "
            f"**{STATUS_EFFECTS.get(n, {}).get('label', n)}** ({e['turns']}t)"
            for n, e in statuses.items()
        ]
        return " | ".join(parts)

    try:
        for _ in range(MAX_ACTIONS):
            if hp[uid1] <= 0 or hp[uid2] <= 0:
                break

            uid = turn_order[turn_idx % 2]
            opp_uid = opp[uid]
            actor = pdata[uid]
            opponent = pdata[opp_uid]

            # ── Tick DoT for this player ───────────────────────────────────
            dot_dmg, tick_msgs = tick_status_effects(pdata[uid], p_statuses[uid])
            if dot_dmg:
                hp[uid] = max(0, hp[uid] - dot_dmg)
            if tick_msgs:
                await ctx.send("\n".join(tick_msgs))
            if hp[uid] <= 0:
                outcome = "p2_win" if uid == uid1 else "p1_win"
                await ctx.send(
                    f"💀 **{pnames[uid]}** was slain by status effects! "
                    f"**{pnames[opp_uid]}** wins!"
                )
                break

            # Stun check (from skill stun_skip)
            if uid in stun_skip:
                stun_skip.discard(uid)
                await ctx.send(f"😵 **{pnames[uid]}** is stunned and loses their turn!")
                turn_idx += 1
                continue

            # Prompt
            sk = CLASS_SKILLS.get(actor.get("class", "Hunter"))
            skill_hint = f" · `skill` ({sk['name']})" if sk else ""
            my_status = _pvp_status_line(uid)
            their_status = _pvp_status_line(opp_uid)
            status_footer = ""
            if my_status:
                status_footer += f"\nYour status: {my_status}"
            if their_status:
                status_footer += f"\n{pnames[opp_uid]}'s status: {their_status}"
            await ctx.send(
                f"⚔️ {pmembers[uid].mention}'s turn!\n"
                f"Your HP: **{hp[uid]}/{actor['max_hp']}** `{hp_bar(max(0,hp[uid]), actor['max_hp'])}`"
                f" | Mana: **{actor.get('mana',0)}/{actor.get('max_mana',50)}**\n"
                f"Type: `attack` · `flee` · `use <item>`{skill_hint}{status_footer}"
            )

            def pvp_check(m: discord.Message) -> bool:
                return m.author == pmembers[uid] and m.channel == ctx.channel

            try:
                msg = await bot.wait_for("message", timeout=60.0, check=pvp_check)
            except asyncio.TimeoutError:
                await ctx.send(f"⏱️ **{pnames[uid]}** took too long and forfeits the duel!")
                outcome = "p2_win" if uid == uid1 else "p1_win"
                break

            content = msg.content.strip().lower()
            round_msgs: list[str] = []
            advance_turn = True     # set False if the action was invalid / failed

            # ── attack ───────────────────────────────────────────────
            if content == "attack":
                crit = random.random() < actor.get("crit_chance", 0.05)
                raw  = random.randint(actor["attack"] - 2, actor["attack"] + 2)
                if crit:
                    raw = int(raw * 1.75)
                dmg = damage_after_defense(raw, opponent.get("defense", 5))
                hp[opp_uid] = max(0, hp[opp_uid] - dmg)
                crit_tag = " 💥 *CRIT!*" if crit else ""
                round_msgs.append(
                    f"🗡️ **{pnames[uid]}** strikes **{pnames[opp_uid]}** for **{dmg}** dmg!{crit_tag}\n"
                    f"**{pnames[opp_uid]}** HP: **{max(0,hp[opp_uid])}/{opponent['max_hp']}** "
                    f"`{hp_bar(max(0,hp[opp_uid]), opponent['max_hp'])}`"
                )

            # ── flee ─────────────────────────────────────────────────
            elif content == "flee":
                lucky = "Lucky Charm" in actor.get("inventory", [])
                # Flee chance reduced by opponent's speed advantage
                spd_diff = opponent.get("speed", 5) - actor.get("speed", 5)
                flee_chance = max(0.1, 0.40 - spd_diff * 0.02)
                if lucky:
                    flee_chance = min(1.0, flee_chance + 0.15)
                if random.random() < flee_chance:
                    charm_note = " *(Lucky Charm helped!)*" if lucky else ""
                    await ctx.send(f"💨 **{pnames[uid]}** flees the duel!{charm_note}")
                    outcome = "p2_win" if uid == uid1 else "p1_win"
                    break
                else:
                    penalty = random.randint(3, 10)
                    hp[uid] = max(0, hp[uid] - penalty)
                    round_msgs.append(
                        f"❌ **{pnames[uid]}** failed to flee and took **{penalty}** dmg!\n"
                        f"HP: **{max(0,hp[uid])}/{actor['max_hp']}** `{hp_bar(max(0,hp[uid]), actor['max_hp'])}`"
                    )

            # ── use <item> ────────────────────────────────────────────
            elif content.startswith("use "):
                item_name = content[4:].strip()
                matched = next(
                    (i for i in actor.get("inventory", []) if i.lower() == item_name.lower()),
                    None,
                )
                if matched:
                    success, item_msg = use_item(actor, matched)
                    round_msgs.append(item_msg)
                    if not success:
                        advance_turn = False
                else:
                    await ctx.send(f"❌ **{pnames[uid]}** doesn't have **{item_name}**.")
                    advance_turn = False

            # ── skill ─────────────────────────────────────────────────
            elif content == "skill":
                opp_as_enemy = {"defense": opponent.get("defense", 5), "name": pnames[opp_uid]}
                new_opp_hp, skill_msgs, flags = use_skill(actor, opp_as_enemy, hp[opp_uid])
                if skill_msgs and skill_msgs[0].startswith("❌"):
                    # Not enough mana or no skill — don't advance turn
                    await ctx.send("\n".join(skill_msgs))
                    advance_turn = False
                else:
                    hp[opp_uid] = max(0, new_opp_hp)
                    round_msgs += skill_msgs
                    if flags.get("stunned"):
                        stun_skip.add(opp_uid)
                    # Apply DoT/debuff status from skill (burn, poison — stun is via stun_skip)
                    apply_eff = flags.get("apply_status")
                    if apply_eff and apply_eff != "stun":
                        m = apply_status_effect(pdata[opp_uid], apply_eff, p_statuses[opp_uid])
                        if m:
                            round_msgs.append(m)
                    if hp[opp_uid] > 0:
                        round_msgs.append(
                            f"**{pnames[opp_uid]}** HP: **{hp[opp_uid]}/{opponent['max_hp']}** "
                            f"`{hp_bar(hp[opp_uid], opponent['max_hp'])}`"
                        )

            # ── unknown ───────────────────────────────────────────────
            else:
                sk2 = CLASS_SKILLS.get(actor.get("class", "Hunter"))
                hint = " · `skill`" if sk2 else ""
                await ctx.send(f"❓ Type `attack`, `flee`, `use <item>`{hint}.")
                advance_turn = False

            if round_msgs:
                await ctx.send("\n".join(round_msgs))

            # Check defeat
            if hp[opp_uid] <= 0:
                outcome = "p1_win" if uid == uid1 else "p2_win"
                break
            if hp[uid] <= 0:
                outcome = "p2_win" if uid == uid1 else "p1_win"
                break

            if advance_turn:
                turn_idx += 1

        else:
            # Hit action cap — higher remaining HP% wins
            pct1 = hp[uid1] / max(1, p1["max_hp"])
            pct2 = hp[uid2] / max(1, p2["max_hp"])
            if pct1 > pct2:
                outcome = "p1_win"
            elif pct2 > pct1:
                outcome = "p2_win"
            else:
                outcome = "draw"

    finally:
        ACTIVE_COMBATS.pop(uid1, None)
        ACTIVE_COMBATS.pop(uid2, None)

        # Persist HP / mana changes (items used, mana spent are real costs)
        p1["hp"] = max(1, hp[uid1])
        p2["hp"] = max(1, hp[uid2])

        # Update win/loss records
        if outcome == "p1_win":
            p1["pvp_wins"]   = p1.get("pvp_wins", 0) + 1
            p2["pvp_losses"] = p2.get("pvp_losses", 0) + 1
            winner_name, loser_name = pnames[uid1], pnames[uid2]
        elif outcome == "p2_win":
            p2["pvp_wins"]   = p2.get("pvp_wins", 0) + 1
            p1["pvp_losses"] = p1.get("pvp_losses", 0) + 1
            winner_name, loser_name = pnames[uid2], pnames[uid1]
        else:
            winner_name = loser_name = None

        save_game(uid1, p1)
        save_game(uid2, p2)

        # ── Guild XP for PvP win ───────────────────────────────────────────
        try:
            _guilds = load_guilds()
            _changed = False
            if outcome == "p1_win" and p1.get("guild_id"):
                _msgs = add_guild_xp(p1["guild_id"], 10, _guilds)
                _changed = True
            elif outcome == "p2_win" and p2.get("guild_id"):
                _msgs = add_guild_xp(p2["guild_id"], 10, _guilds)
                _changed = True
            else:
                _msgs = []
            if _changed:
                save_guilds(_guilds)
        except Exception:
            _msgs = []

        # Result embed
        if outcome == "draw":
            result = discord.Embed(
                title="⚔️ Duel ends in a Draw!",
                description="Neither fighter could overcome the other.",
                color=0x95A5A6,
            )
        else:
            result = discord.Embed(
                title=f"🏆 {winner_name} wins the duel!",
                description=f"**{loser_name}** has been defeated!",
                color=0x57F287,
            )
        result.add_field(name=f"{pnames[uid1]} HP", value=f"{p1['hp']}/{p1['max_hp']}", inline=True)
        result.add_field(name=f"{pnames[uid2]} HP", value=f"{p2['hp']}/{p2['max_hp']}", inline=True)
        result.add_field(
            name=f"{pnames[uid1]} Record",
            value=f"W **{p1.get('pvp_wins',0)}** · L **{p1.get('pvp_losses',0)}**",
            inline=True,
        )
        result.add_field(
            name=f"{pnames[uid2]} Record",
            value=f"W **{p2.get('pvp_wins',0)}** · L **{p2.get('pvp_losses',0)}**",
            inline=True,
        )
        await ctx.send(embed=result)

    return outcome


# ------------------------------------------------------------------ #
#  SHARED COMBAT RUNNER
# ------------------------------------------------------------------ #
def _chest_embed(result: dict) -> "discord.Embed":
    """Build a Discord embed from an open_chest() result dict."""
    import discord as _discord
    rewards: list[str] = [f"💰 **{result['copper']} copper**"]
    for p in result["potions"]:
        rewards.append(f"🧪 {p}")
    for it in result["items"]:
        rewards.append(f"⚔️ **{it}**")
    flavor = result.get("open_flavor", "")
    desc   = f"*{flavor}*\n\n{result['headline']}" if flavor else result["headline"]
    embed  = _discord.Embed(
        title=f"{result['emoji']} {result['rarity']} Chest Opened!",
        description=desc,
        color=result["color"],
    )
    embed.add_field(name="Rewards", value="\n".join(rewards), inline=False)
    embed.set_footer(text=f"Rarity: {result['rarity']} · Items added to your inventory")
    return embed


async def _run_combat(
    ctx: commands.Context,
    player: dict,
    enemy: dict,
    bot,
    chest_context: str = "fight",
) -> str:
    """
    Full combat loop. Returns 'win' | 'lose' | 'flee' | 'timeout'.
    Caller sets ACTIVE_COMBATS[uid] before calling; this clears it in finally.
    """
    uid = ctx.author.id
    enemy_hp = enemy["hp"]
    enemy["max_hp"] = enemy_hp
    is_demon_king = enemy["name"] == "Demon King"

    night_note = " *(stronger at night)*" if enemy.get("night_buffed") else ""
    intro = discord.Embed(
        title=f"⚔️ Battle Start! {'☠️' if enemy.get('is_boss') else ''}",
        description=f"A **{enemy['name']}** appears in **{player['current_location']}**!{night_note}",
        color=0xED4245,
    )
    intro.add_field(name="Enemy HP", value=str(enemy_hp), inline=True)
    intro.add_field(name="Enemy ATK", value=str(enemy["attack"]), inline=True)
    intro.add_field(name="Enemy DEF", value=str(enemy.get("defense", 0)), inline=True)
    intro.add_field(
        name=f"Your HP",
        value=f"{player['hp']}/{player['max_hp']} `{hp_bar(player['hp'], player['max_hp'])}`",
        inline=False,
    )
    intro.add_field(name="Your ATK", value=str(player["attack"]), inline=True)
    intro.add_field(name="Your DEF", value=str(player.get("defense", 5)), inline=True)
    player_class = player.get("class", "Hunter")
    skill_info = CLASS_SKILLS.get(player_class)
    skill_hint = f" · skill ({skill_info['name']})" if skill_info else ""
    intro.set_footer(text=f"Type: attack · flee · use <item name>{skill_hint}")
    await ctx.send(embed=intro)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # ── Status effect tracking (local to this fight) ──────────────────────
    player_statuses: dict[str, dict] = {}
    enemy_statuses:  dict[str, dict] = {}

    def _status_line(statuses: dict) -> str:
        """One-line summary of active status effects for display."""
        if not statuses:
            return ""
        parts = [
            f"{STATUS_EFFECTS.get(n, {}).get('emoji', '💢')} "
            f"**{STATUS_EFFECTS.get(n, {}).get('label', n)}** ({e['turns']}t)"
            for n, e in statuses.items()
        ]
        return "⚠️ " + " | ".join(parts)

    def _build_win_msgs() -> list[str]:
        """Assemble XP / copper / loot messages after defeating the enemy."""
        w: list[str] = [f"💀 You defeated the **{enemy['name']}**!"]
        # Apply Eclipse Empire reward bonus (+10% XP + copper)
        _xp_reward  = int(enemy["experience_reward"] * faction_xp_mult(player))
        _cop_reward = int(enemy["copper_reward"]      * faction_copper_mult(player))
        w += add_experience(player, _xp_reward)
        w.append(add_currency(player, _cop_reward))
        w.append("**— Loot —**")
        w += roll_loot(player, enemy["name"])
        # Check faction kill-count missions
        w += check_kill_missions(player)
        if is_demon_king:
            player["demon_king_slain"] = True
            w.append(
                "☠️ **THE DEMON KING HAS FALLEN!** His dark reign is over.\n"
                "The world breathes again."
            )
            w += complete_quest(player, "defeat_demon_king")
        return w

    outcome = "timeout"
    try:
        while player["hp"] > 0 and enemy_hp > 0:

            # ── Player turn: tick DoT, handle stun ────────────────────────
            p_stunned = "stun" in player_statuses
            dot_dmg, tick_msgs = tick_status_effects(player, player_statuses)
            if dot_dmg:
                player["hp"] = max(0, player["hp"] - dot_dmg)
            if tick_msgs:
                await ctx.send("\n".join(tick_msgs))
            if player["hp"] <= 0:
                player["hp"] = 1
                await ctx.send(
                    "💀 Your wounds proved fatal. You survive with **1 HP**. Use `!rest`."
                )
                outcome = "lose"
                break

            round_msgs: list[str] = []
            do_enemy_turn = True

            if p_stunned:
                p_sl = _status_line(player_statuses)
                await ctx.send(
                    f"😵 You are **Stunned** and lose your turn!\n"
                    f"HP: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                    + (f"\n{p_sl}" if p_sl else "")
                )
                # Fall through to enemy turn below
            else:
                # ── Show prompt with active status lines ──────────────────
                p_sl = _status_line(player_statuses)
                e_sl = _status_line(enemy_statuses)
                status_footer = ""
                if p_sl:
                    status_footer += f"\nYou: {p_sl}"
                if e_sl:
                    status_footer += f"\nEnemy: {e_sl}"
                sk_info = CLASS_SKILLS.get(player.get("class", "Hunter"))
                sk_hint = f" · skill ({sk_info['name']})" if sk_info else ""
                await ctx.send(
                    f"HP: **{player['hp']}/{player['max_hp']}** "
                    f"`{hp_bar(player['hp'], player['max_hp'])}`"
                    f" | Mana: **{player.get('mana', 0)}/{player.get('max_mana', 50)}**\n"
                    f"Type: attack · flee · use <item>{sk_hint}{status_footer}"
                )

                try:
                    msg = await bot.wait_for("message", timeout=90.0, check=check)
                except asyncio.TimeoutError:
                    await ctx.send(
                        "⏱️ Combat timed out — you slipped away into the shadows."
                    )
                    outcome = "timeout"
                    break

                content = msg.content.strip().lower()

                # ── attack ────────────────────────────────────────────────
                if content == "attack":
                    crit = random.random() < player.get("crit_chance", 0.05)
                    raw  = random.randint(player["attack"] - 2, player["attack"] + 2)
                    # Void Legion: +15% attack damage
                    raw  = int(raw * faction_attack_mult(player))
                    if crit:
                        raw = int(raw * 1.75)
                    dmg = damage_after_defense(raw, enemy.get("defense", 0))
                    enemy_hp -= dmg
                    crit_tag = " 💥 *CRIT!*" if crit else ""
                    round_msgs.append(
                        f"🗡️ You strike for **{dmg}** dmg!{crit_tag} "
                        f"Enemy HP: **{max(0, enemy_hp)}**"
                    )
                    if is_demon_king:
                        phase = get_demon_king_phase(max(0, enemy_hp), enemy["max_hp"])
                        if phase == 2 and not enemy.get("phase2_announced") and enemy_hp > 0:
                            round_msgs.append(
                                "🔥 **Phase 2!** The Demon King's power surges — his attacks grow deadlier!"
                            )
                            enemy["phase2_announced"] = True
                            enemy["attack"] = int(enemy["attack"] * 1.3)
                        elif phase == 3 and not enemy.get("phase3_announced") and enemy_hp > 0:
                            round_msgs.append(
                                "💀 **RAGE MODE!** The Demon King enters his final berserk phase!"
                            )
                            enemy["phase3_announced"] = True
                            enemy["attack"] = int(enemy["attack"] * 1.5)

                # ── flee ──────────────────────────────────────────────────
                elif content == "flee":
                    lucky = "Lucky Charm" in player["inventory"]
                    flee_chance = 0.65 if lucky else 0.5
                    if is_demon_king:
                        flee_chance = 0.15
                    if random.random() < flee_chance:
                        charm_note = " *(Lucky Charm helped!)*" if lucky else ""
                        await ctx.send(f"💨 You successfully fled!{charm_note}")
                        outcome = "flee"
                        break
                    else:
                        penalty = random.randint(5, 15)
                        player["hp"] = max(0, player["hp"] - penalty)
                        round_msgs.append(
                            f"❌ Failed to flee! Took **{penalty}** dmg. "
                            f"HP: **{player['hp']}/{player['max_hp']}**"
                        )
                    do_enemy_turn = False   # flee attempt never triggers enemy turn

                # ── use <item> ────────────────────────────────────────────
                elif content.startswith("use "):
                    item_name = content[4:].strip()
                    matched = next(
                        (i for i in player["inventory"] if i.lower() == item_name.lower()),
                        None,
                    )
                    if matched:
                        success, item_msg = use_item(player, matched)
                        round_msgs.append(item_msg)
                        if not success:
                            await ctx.send("\n".join(round_msgs))
                            round_msgs = []
                            do_enemy_turn = False
                        else:
                            # Status-cure: clear matching effects from player
                            item_data = shop_items.get(matched, {})
                            if item_data.get("type") == "cure":
                                for eff in item_data.get("cures", []):
                                    if player_statuses.pop(eff, None) is not None:
                                        eff_def = STATUS_EFFECTS.get(eff, {})
                                        round_msgs.append(
                                            f"✨ **{eff_def.get('label', eff)}** cured!"
                                        )
                            # Status-buff: apply timed buff to player
                            elif item_data.get("type") == "status_buff":
                                sname = item_data.get("status")
                                if sname:
                                    round_msgs.append(
                                        apply_status_effect(player, sname, player_statuses)
                                    )
                            # Potion counterattack: boss always, others speed-scaled
                            if do_enemy_turn and enemy_hp > 0:
                                spd = player.get("speed", 5)
                                counter_chance = (
                                    1.0
                                    if (is_demon_king or enemy.get("is_boss"))
                                    else max(0.0, 0.20 - spd * 0.01)
                                )
                                if random.random() < counter_chance:
                                    round_msgs.append(
                                        f"⚡ **{enemy['name']}** sees the opening and strikes back!"
                                    )
                                    if is_demon_king:
                                        enemy_hp, _, ct_msgs = demon_king_turn(enemy, enemy_hp, player)
                                        round_msgs += ct_msgs
                                    else:
                                        enemy["hp"] = enemy_hp
                                        round_msgs += enemy_turn(enemy, player)
                                        enemy_hp = enemy["hp"]
                                    # Inflict on counter
                                    if player["hp"] > 0:
                                        for inflict in enemy.get("inflicts", []):
                                            if random.random() < inflict["chance"]:
                                                m = apply_status_effect(
                                                    player, inflict["effect"], player_statuses
                                                )
                                                if m:
                                                    round_msgs.append(m)
                                    if player["hp"] <= 0:
                                        round_msgs.append(
                                            f"💀 You were defeated by the **{enemy['name']}**..."
                                        )
                                        player["hp"] = 1
                                        await ctx.send("\n".join(round_msgs))
                                        await ctx.send(
                                            "You barely survive with 1 HP. Use `!rest` to recover."
                                        )
                                        outcome = "lose"
                                        break
                                    await ctx.send("\n".join(round_msgs))
                                    round_msgs = []
                                    do_enemy_turn = False
                    else:
                        await ctx.send(f"❌ You don't have **{item_name}** in your inventory.")
                        do_enemy_turn = False

                # ── skill ─────────────────────────────────────────────────
                elif content == "skill":
                    enemy_hp, skill_msgs, flags = use_skill(player, enemy, enemy_hp)
                    round_msgs += skill_msgs
                    if not skill_msgs or skill_msgs[0].startswith("❌"):
                        await ctx.send("\n".join(round_msgs))
                        round_msgs = []
                        do_enemy_turn = False
                    else:
                        # Apply status from skill (burn, poison, or stun)
                        apply_eff = flags.get("apply_status")
                        if apply_eff:
                            m = apply_status_effect(enemy, apply_eff, enemy_statuses)
                            if m:
                                round_msgs.append(m)
                        # Legacy stunned flag → also register in statuses if not there yet
                        if flags.get("stunned") and "stun" not in enemy_statuses:
                            enemy_statuses["stun"] = {"turns": 1, "damage_per_turn": 0}
                        if enemy_hp <= 0:
                            round_msgs += _build_win_msgs()
                            await ctx.send("\n".join(round_msgs))
                            outcome = "win"
                            break

                # ── unknown ───────────────────────────────────────────────
                else:
                    sk2 = CLASS_SKILLS.get(player.get("class", "Hunter"))
                    hint = " · `skill`" if sk2 else ""
                    await ctx.send(f"❓ Type `attack`, `flee`, `use <item name>`{hint}.")
                    do_enemy_turn = False

                # Flush any player-action messages
                if round_msgs:
                    await ctx.send("\n".join(round_msgs))
                    round_msgs = []

                # Enemy defeated by player action?
                if enemy_hp <= 0:
                    await ctx.send("\n".join(_build_win_msgs()))
                    outcome = "win"
                    break

                if not do_enemy_turn:
                    continue

            # ── Enemy turn: tick DoT, handle stun ─────────────────────────
            e_stunned = "stun" in enemy_statuses
            e_dot_dmg, e_tick_msgs = tick_status_effects(enemy, enemy_statuses)
            enemy_hp = max(0, enemy_hp - e_dot_dmg)
            if e_tick_msgs:
                await ctx.send("\n".join(e_tick_msgs))

            if enemy_hp <= 0:
                await ctx.send(
                    "\n".join(
                        [f"☠️ **{enemy['name']}** succumbs to their wounds!"]
                        + _build_win_msgs()
                    )
                )
                outcome = "win"
                break

            if e_stunned:
                await ctx.send(
                    f"😵 **{enemy['name']}** is **Stunned** and skips their attack!"
                )
                continue

            # Normal enemy attack
            eturn_msgs: list[str] = []
            if is_demon_king:
                enemy_hp, _, eturn_msgs = demon_king_turn(enemy, enemy_hp, player)
            else:
                enemy["hp"] = enemy_hp
                _hp_pre_eturn = player["hp"]
                eturn_msgs = enemy_turn(enemy, player)
                enemy_hp = enemy["hp"]
                # Void curse: +10% bonus damage received
                if faction_damage_taken_mult(player) > 1.0 and player["hp"] < _hp_pre_eturn:
                    _void_extra = max(1, int(
                        (_hp_pre_eturn - player["hp"]) * (faction_damage_taken_mult(player) - 1.0)
                    ))
                    player["hp"] = max(0, player["hp"] - _void_extra)
                    eturn_msgs.append(f"💀 *Void curse: +{_void_extra} extra damage!*")

            # Enemy may inflict a status on the player after attacking
            if player["hp"] > 0:
                for inflict in enemy.get("inflicts", []):
                    if random.random() < inflict["chance"]:
                        m = apply_status_effect(player, inflict["effect"], player_statuses)
                        if m:
                            eturn_msgs.append(m)

            if player["hp"] <= 0:
                eturn_msgs.append(f"💀 You were defeated by the **{enemy['name']}**...")
                player["hp"] = 1
                await ctx.send("\n".join(eturn_msgs))
                await ctx.send("You barely survive with 1 HP. Use `!rest` to recover.")
                outcome = "lose"
                break

            if eturn_msgs:
                await ctx.send("\n".join(eturn_msgs))

    finally:
        ACTIVE_COMBATS.pop(uid, None)
        save_game(uid, player)

    # ── Guild XP contribution (runs after finally, before return) ─────────
    if outcome == "win" and player.get("guild_id"):
        try:
            _guilds = load_guilds()
            _gxp = 30 if enemy.get("is_boss") else 10
            _lvl_msgs = add_guild_xp(player["guild_id"], _gxp, _guilds)
            save_guilds(_guilds)
            for _m in _lvl_msgs:
                await ctx.send(_m)
        except Exception:
            pass

    # ── Chest drop chance ──────────────────────────────────────────────────
    if outcome == "win":
        _rarity = maybe_find_chest(player, chest_context)
        if _rarity:
            _chest = open_chest(player, _rarity)
            save_game(uid, player)
            await ctx.send(embed=_chest_embed(_chest))

    return outcome


class RPG(commands.Cog, name="RPG"):
    """Full RPG game commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------ #
    #  !start
    # ------------------------------------------------------------------ #
    @commands.command(name="start", brief="Begin your RPG adventure")
    async def start(self, ctx: commands.Context):
        uid = ctx.author.id
        existing = load_game(uid)
        if existing:
            players[uid] = existing
            slot = get_active_slot_name(uid)
            all_chars = list_characters(uid)
            slot_info = f"Character: **{slot}**" if len(all_chars) > 1 else ""
            embed = discord.Embed(
                title="⚔️ Welcome back, Hunter!",
                description=f"Your adventure continues in **{existing['current_location']}**. {slot_info}",
                color=location_color(existing["current_location"]),
            )
            embed.add_field(name="Level", value=str(existing["level"]), inline=True)
            embed.add_field(name="Class", value=existing["class"], inline=True)
            embed.add_field(name="HP", value=f"{existing['hp']}/{existing['max_hp']}", inline=True)
            embed.add_field(name="ATK / DEF", value=f"{existing['attack']} / {existing.get('defense', 5)}", inline=True)
            embed.add_field(name="Currency", value=format_currency(existing), inline=True)
            embed.set_footer(text="!stats for full sheet · !characters to manage slots · !help for all commands")
            await ctx.send(embed=embed)
            return

        player = new_player()
        players[uid] = player
        save_game(uid, player)

        embed = discord.Embed(
            title="⚔️ A New Legend Begins",
            description=(
                "You awaken in **Aetherfall**, a modern city at the edge of chaos.\n\n"
                "You are a **Hunter** — one of the few gifted with the power to fight back.\n\n"
                "Reach **Level 10** and use `!choose_class` to specialise your character.\n"
                f"Want a second character? Use `!newchar <name>` (up to {MAX_CHARACTER_SLOTS} slots)."
            ),
            color=0x5865F2,
        )
        embed.add_field(name="Class", value="Hunter", inline=True)
        embed.add_field(name="Level", value="1", inline=True)
        embed.add_field(name="Location", value="🏙️ Aetherfall", inline=True)
        embed.add_field(
            name="Core Commands",
            value=(
                "`!stats` · `!map` · `!travel <loc>` · `!explore`\n"
                "`!fight` · `!inventory` · `!equip <item>` · `!use <item>`\n"
                "`!shop` · `!buy <item>` · `!sell <item>` · `!rest`\n"
                "`!quests` · `!choose_class` · `!pvp <@user>` · `!save`\n"
                "`!characters` · `!newchar <name>` · `!switchchar <name>`"
            ),
            inline=False,
        )
        embed.set_footer(text="Try !explore to begin your journey.")
        await ctx.send(embed=embed)

        qm = trigger_quest(player, "welcome_quest")
        if qm:
            await ctx.send(f"📜 {qm}")

    # ------------------------------------------------------------------ #
    #  !characters  — list all character slots
    # ------------------------------------------------------------------ #
    @commands.command(name="characters", aliases=["chars", "charlist"], brief="List your character slots")
    async def characters(self, ctx: commands.Context):
        uid = ctx.author.id
        chars = list_characters(uid)
        if not chars:
            await ctx.send("You have no characters yet. Use `!start` to create one.")
            return
        embed = discord.Embed(
            title="🧑‍💼 Your Characters",
            description=f"Up to **{MAX_CHARACTER_SLOTS}** slots · `!newchar <name>` · `!switchchar <name>` · `!deletechar <name>`",
            color=0x5865F2,
        )
        for c in chars:
            tag = " ◀ **active**" if c["active"] else ""
            embed.add_field(
                name=f"{'▶' if c['active'] else '○'} {c['name']}{tag}",
                value=(
                    f"**{c['class']}** · Lv {c['level']}\n"
                    f"📍 {c['location']}"
                ),
                inline=True,
            )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !newchar  — create a new character slot
    # ------------------------------------------------------------------ #
    @commands.command(name="newchar", aliases=["createchar"], brief="Create a new character slot")
    async def newchar(self, ctx: commands.Context, *, name: str = None):
        """Create a new character. Example: `!newchar mywarrior`"""
        uid = ctx.author.id
        if not name:
            await ctx.send(
                f"Usage: `!newchar <name>`\n"
                f"Name: letters, numbers, `-`, `_` only (max 20 chars).\n"
                f"After creating, use `!switchchar <name>` to play it."
            )
            return
        if uid in ACTIVE_COMBATS:
            await ctx.send("❌ Finish your current fight before managing characters.")
            return

        success, result = create_player_slot(uid, name)
        if not success:
            await ctx.send(result)
            return

        await ctx.send(
            f"✅ Created character **{result}**!\n"
            f"Use `!switchchar {result}` to switch to them, then `!start` to begin."
        )

    # ------------------------------------------------------------------ #
    #  !switchchar  — switch active character
    # ------------------------------------------------------------------ #
    @commands.command(name="switchchar", aliases=["swapchar", "playchar"], brief="Switch active character")
    async def switchchar(self, ctx: commands.Context, *, name: str = None):
        """Switch to a different character slot. Example: `!switchchar mywarrior`"""
        uid = ctx.author.id
        if not name:
            await ctx.send("Usage: `!switchchar <name>`. See `!characters` for your slots.")
            return
        if uid in ACTIVE_COMBATS:
            await ctx.send("❌ Finish your current fight before switching characters.")
            return

        success, result = switch_character(uid, name)
        if not success:
            await ctx.send(result)
            return

        # Reload the new active character into memory
        players.pop(uid, None)
        new_active = load_game(uid)
        if new_active:
            players[uid] = new_active
            await ctx.send(
                f"✅ Switched to **{result}**! "
                f"Lv {new_active['level']} {new_active['class']} in **{new_active['current_location']}**.\n"
                f"Use `!start` to see your full welcome-back screen."
            )
        else:
            players[uid] = new_player()
            await ctx.send(
                f"✅ Switched to **{result}** (new character). Use `!start` to begin their adventure!"
            )

    # ------------------------------------------------------------------ #
    #  !deletechar  — delete a character slot
    # ------------------------------------------------------------------ #
    @commands.command(name="deletechar", aliases=["delchar", "removechar"], brief="Delete a character slot")
    async def deletechar(self, ctx: commands.Context, *, name: str = None):
        """Permanently delete a character slot. Example: `!deletechar mywarrior`"""
        uid = ctx.author.id
        if not name:
            await ctx.send("Usage: `!deletechar <name>`. This is permanent! See `!characters` for your slots.")
            return
        if uid in ACTIVE_COMBATS:
            await ctx.send("❌ Finish your current fight before managing characters.")
            return

        # Confirm before deleting
        await ctx.send(
            f"⚠️ **Are you sure?** This will permanently delete character **{name}**.\n"
            f"Type `confirm` within 15 seconds to proceed, or anything else to cancel."
        )

        def confirm_check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            reply = await self.bot.wait_for("message", timeout=15.0, check=confirm_check)
        except asyncio.TimeoutError:
            await ctx.send("❌ Deletion cancelled — timed out.")
            return

        if reply.content.strip().lower() != "confirm":
            await ctx.send("❌ Deletion cancelled.")
            return

        success, result = delete_character(uid, name)
        if not success:
            await ctx.send(result)
            return

        await ctx.send(f"🗑️ Character **{result}** has been deleted.")

    # ------------------------------------------------------------------ #
    #  !stats
    # ------------------------------------------------------------------ #
    @commands.command(name="stats", brief="View your character stats")
    async def stats(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        loc = player["current_location"]
        time_icon = "🌙" if player["time_of_day"] == "night" else "☀️"
        equipped = player.get("equipped", {})
        weapon    = equipped.get("weapon")    or "None"
        armor     = equipped.get("armor")     or "None"
        accessory = equipped.get("accessory") or "None"

        # Guild info
        _gid = player.get("guild_id")
        guild_line = "None"
        if _gid:
            _guilds = load_guilds()
            _g = _guilds.get(_gid, {})
            if _g:
                _lvl = _g.get("level", 1)
                _bs  = bonus_summary(GUILD_BONUS_TABLE[_lvl])
                guild_line = f"**{_g['name']}** (Lv {_lvl})\n{_bs}"

        embed = discord.Embed(
            title=f"⚔️ {ctx.author.display_name}'s Character Sheet",
            color=location_color(loc),
        )
        embed.add_field(name="Class",    value=player["class"],                                    inline=True)
        embed.add_field(name="Level",    value=str(player["level"]),                               inline=True)
        embed.add_field(name="Location", value=f"{LOCATION_EMOJIS.get(loc,'📍')} {loc}",          inline=True)
        embed.add_field(
            name=f"HP  {player['hp']}/{player['max_hp']}",
            value=f"`{hp_bar(player['hp'], player['max_hp'])}`",
            inline=False,
        )
        embed.add_field(
            name=f"XP  {player['experience_points']}/{player['xp_to_next_level']}",
            value=f"`{hp_bar(player['experience_points'], player['xp_to_next_level'])}`",
            inline=False,
        )
        embed.add_field(name="⚔️ Attack",       value=str(player["attack"]),                                  inline=True)
        embed.add_field(name="🛡️ Defense",     value=str(player.get("defense", 5)),                          inline=True)
        embed.add_field(name="❤️ Vitality",    value=str(player.get("vitality", 10)),                        inline=True)
        embed.add_field(name="🔵 Mana",        value=f"{player.get('mana',50)}/{player.get('max_mana',50)}", inline=True)
        embed.add_field(name="🧠 Intelligence", value=str(player.get("intelligence", 10)),                    inline=True)
        embed.add_field(name="💨 Speed",       value=str(player.get("speed", 5)),                            inline=True)
        embed.add_field(name="🍀 Luck",        value=str(player.get("luck", 5)),                             inline=True)
        embed.add_field(name="💥 Crit",        value=f"{player.get('crit_chance',0.05)*100:.0f}%",           inline=True)
        embed.add_field(name="🗡️ Weapon",      value=weapon,    inline=True)
        embed.add_field(name="🛡 Armor",       value=armor,     inline=True)
        embed.add_field(name="💍 Accessory",   value=accessory, inline=True)
        embed.add_field(name="🏰 Guild",       value=guild_line, inline=False)
        embed.add_field(name="💰 Currency",    value=format_currency(player), inline=True)
        embed.add_field(name="🕐 Time",        value=f"{time_icon} {player['time_of_day'].capitalize()}", inline=True)
        if not player.get("class_chosen") and player["level"] >= 10:
            embed.add_field(name="⚠️ Action Required", value="Use `!choose_class` to pick your specialisation!", inline=False)
        embed.set_footer(text="!inventory · !equip <item> · !guild_info · !guilds")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !skill  — show class skill info
    # ------------------------------------------------------------------ #
    @commands.command(name="skill", brief="Show your class skill info")
    async def skill_info(self, ctx: commands.Context):
        """Show your active skill tier, mana cost, and upcoming tier previews."""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        player_class = player.get("class", "Hunter")
        level = player.get("level", 1)

        # Determine active tier
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
            await ctx.send(
                f"**{player_class}** class has no skill.\n"
                "Reach **Level 10** and use `!choose_class` to unlock a class with a skill."
            )
            return

        mana     = player.get("mana", 0)
        max_mana = player.get("max_mana", 50)
        can_use  = "✅ Ready" if mana >= skill["mana_cost"] else f"❌ Need {skill['mana_cost']} mana"
        tier_labels = {1: "Tier 1 (Basic)", 2: "Tier 2 (Advanced)", 3: "Tier 3 (Ultimate)"}
        embed = discord.Embed(
            title=f"{skill['emoji']} {skill['name']} — {player_class} · {tier_labels[tier]}",
            description=skill["description"],
            color=0x5865F2,
        )
        embed.add_field(name="Mana Cost", value=str(skill["mana_cost"]), inline=True)
        embed.add_field(name="Your Mana", value=f"{mana}/{max_mana}", inline=True)
        embed.add_field(name="Status",    value=can_use, inline=True)

        # Next tier previews
        if tier < 2 and player_class in CLASS_SKILLS_T2:
            t2 = CLASS_SKILLS_T2[player_class]
            embed.add_field(
                name=f"🔒 Tier 2 at Level 20 — {t2['name']} ({t2['mana_cost']} mana)",
                value=t2["description"],
                inline=False,
            )
        if tier < 3 and player_class in CLASS_SKILLS_T3:
            t3 = CLASS_SKILLS_T3[player_class]
            embed.add_field(
                name=f"🔒 Tier 3 at Level 30 — {t3['name']} ({t3['mana_cost']} mana)",
                value=t3["description"],
                inline=False,
            )
        embed.set_footer(text="Type 'skill' during combat to use your active skill.")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !choose_class
    # ------------------------------------------------------------------ #
    @commands.command(name="choose_class", aliases=["class"], brief="Choose your class (Level 10+)")
    async def choose_class(self, ctx: commands.Context, *, class_name: str = None):
        """Choose your class at Level 10. 10 classes available. Example: `!choose_class Tank`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        if player.get("class_chosen"):
            await ctx.send(f"You're already a **{player['class']}**. Class cannot be changed.")
            return

        if player["level"] < 10:
            await ctx.send(f"⚠️ You need to be **Level 10** to choose a class. You are Level {player['level']}.")
            return

        if not class_name:
            embed = discord.Embed(
                title="🌟 Choose Your Class",
                description="You've reached Level 10! Pick your specialisation with `!choose_class <name>`.",
                color=0xFEE75C,
            )
            for cname, info in CLASS_DEFINITIONS.items():
                bonuses = " | ".join(
                    f"{'+' if v >= 0 else ''}{v} {k.replace('_',' ').title()}"
                    for k, v in info["bonuses"].items()
                )
                sk = CLASS_SKILLS.get(cname)
                skill_line = f"\n⚡ T1: **{sk['name']}** ({sk['mana_cost']} mana) — {sk['description']}" if sk else ""
                t2 = CLASS_SKILLS_T2.get(cname)
                t2_line = f"\n🔹 T2 (Lv 20): **{t2['name']}**" if t2 else ""
                t3 = CLASS_SKILLS_T3.get(cname)
                t3_line = f"\n🔸 T3 (Lv 30): **{t3['name']}**" if t3 else ""
                embed.add_field(
                    name=f"{info['emoji']} {cname}",
                    value=f"{info['description']}\n*{bonuses}*{skill_line}{t2_line}{t3_line}",
                    inline=False,
                )
            await ctx.send(embed=embed)
            return

        msgs = apply_class(player, class_name.title())
        save_game(ctx.author.id, player)
        for m in msgs:
            await ctx.send(m)

    # ------------------------------------------------------------------ #
    #  !map
    # ------------------------------------------------------------------ #
    @commands.command(name="map", brief="View the world map")
    async def world_map_cmd(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        current = player["current_location"] if player else None
        embed = discord.Embed(title="🗺️ World Map", description="Use `!travel <location>` to move.", color=0x57F287)
        for name, info in world_map.items():
            emoji = LOCATION_EMOJIS.get(name, "📍")
            marker = " ◀ **YOU ARE HERE**" if name == current else ""
            tags = ""
            if info.get("is_boss_area"): tags += " ☠️ BOSS"
            if info.get("has_shop"):     tags += " 🛒"
            connected = ", ".join(gates.get(name, [])) or "None"
            embed.add_field(
                name=f"{emoji} {name} (Lv.{info['level']}){tags}{marker}",
                value=f"{info['description']}\n*Realm: {info['realm']} · Paths: {connected}*",
                inline=False,
            )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !travel
    # ------------------------------------------------------------------ #
    @commands.command(name="travel", brief="Travel to another location")
    async def travel(self, ctx: commands.Context, *, destination: str = None):
        """Travel to a connected location. Example: `!travel Gravefall`"""
        uid = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if uid in ACTIVE_COMBATS:
            await ctx.send("⚔️ Finish your fight first!")
            return
        if uid in ACTIVE_DUNGEONS:
            await ctx.send(f"🏰 You're in a dungeon (**{ACTIVE_DUNGEONS[uid]}**)! Finish it first.")
            return
        if uid in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through.")
            return
        if uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        if not destination:
            current = player["current_location"]
            connected = gates.get(current, [])
            locs = "\n".join(f"• **{l}** (Lv.{world_map[l]['level']})" for l in connected) if connected else "None"
            await ctx.send(f"📍 You're in **{current}**. Connected:\n{locs}\n\nUse `!travel <location>`.")
            return

        destination = destination.strip().title()
        if destination not in world_map:
            matches = [l for l in world_map if destination.lower() in l.lower()]
            destination = matches[0] if len(matches) == 1 else None
            if not destination:
                await ctx.send("❌ Unknown location. Use `!map` to see all locations.")
                return

        current = player["current_location"]
        if destination == current:
            await ctx.send(f"You're already in **{destination}**!")
            return
        if destination not in gates.get(current, []):
            await ctx.send(f"❌ No direct path from **{current}** to **{destination}**.")
            return

        dest_info = world_map[destination]
        warning = ""
        if player["level"] < dest_info["level"]:
            warning = f"\n⚠️ *Recommended Level {dest_info['level']}+. You are Level {player['level']}.*"

        player["current_location"] = destination
        time_msg = advance_time(player)

        lore_text = dest_info.get("lore") or dest_info.get("description", "")
        embed = discord.Embed(
            title=f"{LOCATION_EMOJIS.get(destination,'📍')} Arrived in {destination}",
            description=lore_text + (f"\n\n{warning}" if warning else ""),
            color=location_color(destination),
        )
        embed.add_field(name="Realm", value=dest_info["realm"], inline=True)
        embed.add_field(name="Rec. Level", value=str(dest_info["level"]), inline=True)
        embed.set_footer(text=time_msg)
        await ctx.send(embed=embed)

        # ── Location special effects on arrival ───────────────────────────
        _loc_eff = LOCATION_EFFECTS.get(destination)
        if _loc_eff:
            _eff_type = _loc_eff["type"]
            if _eff_type == "hp_drain":
                _drain = _loc_eff["amount"]
                player["hp"] = max(1, player["hp"] - _drain)
                await ctx.send(_loc_eff["message"].format(amount=_drain))
            elif _eff_type == "burn_chance" and random.random() < _loc_eff["chance"]:
                apply_status_effect(player, "burn")
                await ctx.send(_loc_eff["message"])
            elif _eff_type == "heal_bonus":
                _heal_amt = max(1, int(player["max_hp"] * _loc_eff["heal_pct"]))
                player["hp"] = min(player["max_hp"], player["hp"] + _heal_amt)
                await ctx.send(_loc_eff["message"].format(amount=_heal_amt))
            elif _eff_type in ("night_danger", "armored_enemies", "void_risk"):
                # Passive effects — show informational message only
                await ctx.send(_loc_eff["message"])

        extra = []
        if destination == "Gravefall":
            extra += complete_quest(player, "welcome_quest")
            qm = trigger_quest(player, "gravefall_expedition")
            if qm: extra.append(qm)
        elif destination == "Rotveil":
            extra += complete_quest(player, "gravefall_expedition")
        elif destination == "Voidkand":
            qm = trigger_quest(player, "defeat_demon_king")
            if qm: extra.append(qm)
        if dest_info.get("quest_trigger"):
            qm = trigger_quest(player, dest_info["quest_trigger"])
            if qm: extra.append(qm)
        for m in extra:
            if m: await ctx.send(m)

        # Check faction travel-type missions
        for _ftm in check_travel_missions(player, destination):
            await ctx.send(_ftm)

        save_game(uid, player)

        # Priority order: rift (6%) → random dungeon (5%) → combat (40%)
        if player["hp"] > 1:
            _rt = maybe_encounter_rift(player)
            if _rt:
                await _run_rift(ctx, player, _rt, self.bot)
            elif _rdu := maybe_spawn_dungeon(player):
                await _run_random_dungeon(ctx, player, _rdu, self.bot)
            elif random.random() < RANDOM_ENCOUNTER_CHANCE:
                await ctx.send(f"🚨 **Ambush!** A monster attacks you on the road to {destination}!")
                ACTIVE_COMBATS[uid] = True
                await _run_combat(ctx, player, generate_enemy(player), self.bot, chest_context="explore_combat")

    # ------------------------------------------------------------------ #
    #  !explore
    # ------------------------------------------------------------------ #
    @commands.command(name="explore", brief="Explore your current location")
    async def explore(self, ctx: commands.Context):
        uid = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if uid in ACTIVE_COMBATS:
            await ctx.send("⚔️ Finish your fight first!")
            return
        if uid in ACTIVE_DUNGEONS:
            await ctx.send(f"🏰 You're in a dungeon (**{ACTIVE_DUNGEONS[uid]}**)! Finish it first.")
            return
        if uid in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through.")
            return
        if uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        if player["hp"] <= 1:
            await ctx.send("❤️ You're too wounded to explore. Use `!rest` first.")
            return

        loc = player["current_location"]
        _intro_desc  = LOCATION_EXPLORE_INTRO.get(loc, f"You venture deeper into **{loc}**…")
        _intro_color = LOCATION_EXPLORE_COLOR.get(loc, location_color(loc))
        _intro_embed = discord.Embed(
            title=f"{LOCATION_EMOJIS.get(loc, '📍')} Exploring {loc}",
            description=_intro_desc,
            color=_intro_color,
        )
        _intro_embed.add_field(
            name="Status",
            value=(
                f"❤️ **{player['hp']}/{player['max_hp']}** "
                f"`{hp_bar(player['hp'], player['max_hp'])}`  "
                f"⚔️ Lv **{player['level']}** {player.get('class', 'Hunter')}  "
                f"🕐 {player.get('time_of_day', 'day').title()}"
            ),
            inline=False,
        )
        await ctx.send(embed=_intro_embed)

        extra = []
        if player["quest_log"].get("welcome_quest", {}).get("status") == "active":
            await ctx.send("You feel more acquainted with Aetherfall after exploring.")
            extra += complete_quest(player, "welcome_quest")
        for m in extra:
            if m: await ctx.send(m)

        advance_time(player)
        save_game(uid, player)

        # Priority: rift (6%) → random dungeon (5%) → dungeon discover (10%) → combat (40%) → peaceful
        _rift_type = maybe_encounter_rift(player)
        _disc_entries = LOCATION_DUNGEON_DISCOVER.get(loc)
        if _rift_type:
            await _run_rift(ctx, player, _rift_type, self.bot)
        elif _rdungeon := maybe_spawn_dungeon(player):
            await _run_random_dungeon(ctx, player, _rdungeon, self.bot)
        elif _disc_entries and random.random() < 0.10:
            # ── Dungeon discovery event ───────────────────────────────────
            _disc_dungeon, _disc_msg = random.choice(_disc_entries)
            _disc_embed = discord.Embed(
                title="🔍 You Discover Something...",
                description=_disc_msg,
                color=LOCATION_EXPLORE_COLOR.get(loc, 0x8B0000),
            )
            _disc_embed.set_footer(
                text=f"Hint: use !dungeon \"{_disc_dungeon}\" to enter, or keep exploring."
            )
            await ctx.send(embed=_disc_embed)
        elif random.random() < RANDOM_ENCOUNTER_CHANCE:
            await ctx.send("⚠️ **You're not alone!** Something stirs...")
            ACTIVE_COMBATS[uid] = True
            await _run_combat(ctx, player, generate_enemy(player), self.bot, chest_context="explore_combat")
        else:
            # Peaceful explore — run a mini-event instead of a flat message
            _event = pick_explore_event()
            _cfg   = EVENT_CONFIG[_event]

            if _event == "healing_spring":
                # Apply Divine Order healing bonus (+20%)
                _heal = max(1, int(player["max_hp"] * random.uniform(*_cfg["heal_pct"]) * faction_heal_mult(player)))
                player["hp"] = min(player["max_hp"], player["hp"] + _heal)
                save_game(uid, player)
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}",
                    description=random.choice(_cfg["flavors"]),
                    color=_cfg["color"],
                )
                _ev.add_field(
                    name="Restored",
                    value=(
                        f"**+{_heal} HP**  ·  "
                        f"HP: **{player['hp']}/{player['max_hp']}** "
                        f"`{hp_bar(player['hp'], player['max_hp'])}`"
                    ),
                    inline=False,
                )
                await ctx.send(embed=_ev)

            elif _event == "treasure_cache":
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}",
                    description=random.choice(_cfg["flavors"]),
                    color=_cfg["color"],
                )
                await ctx.send(embed=_ev)
                _tc_rarity = roll_chest_rarity(player)
                _tc_result = open_chest(player, _tc_rarity)
                save_game(uid, player)
                await ctx.send(embed=_chest_embed(_tc_result))

            elif _event == "hidden_notes":
                _title, _note = random.choice(_cfg["lore_entries"])
                _xp_gain = random.randint(*_cfg["xp_range"])
                _xp_msgs = add_experience(player, _xp_gain)
                save_game(uid, player)
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}: *{_title}*",
                    description=_note,
                    color=_cfg["color"],
                )
                _ev.set_footer(text=f"Reading enlightened you. +{_xp_gain} XP")
                await ctx.send(embed=_ev)
                for _m in _xp_msgs:
                    if _m: await ctx.send(_m)

            elif _event == "rare_find":
                _item_names  = [n for n, _ in _cfg["items"]]
                _item_weights = [w for _, w in _cfg["items"]]
                _item = random.choices(_item_names, weights=_item_weights, k=1)[0]
                add_to_inventory(player, _item)
                save_game(uid, player)
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}",
                    description=random.choice(_cfg["flavors"]),
                    color=_cfg["color"],
                )
                _ev.add_field(name="Found", value=f"**{_item}** added to inventory.", inline=False)
                await ctx.send(embed=_ev)

            elif _event == "wandering_merchant":
                _item_names  = [n for n, _ in _cfg["items"]]
                _item_weights = [w for _, w in _cfg["items"]]
                _item = random.choices(_item_names, weights=_item_weights, k=1)[0]
                add_to_inventory(player, _item)
                save_game(uid, player)
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}",
                    description=random.choice(_cfg["flavors"]),
                    color=_cfg["color"],
                )
                _ev.add_field(
                    name="Free Gift",
                    value=f"*\"Take it — you'll need it more than I do.\"*\n**{_item}** added to inventory.",
                    inline=False,
                )
                await ctx.send(embed=_ev)

            elif _event == "echo_of_battle":
                _copper = random.randint(*_cfg["copper_range"])
                add_currency(player, _copper)
                save_game(uid, player)
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}",
                    description=random.choice(_cfg["flavors"]),
                    color=_cfg["color"],
                )
                _ev.add_field(name="Salvaged", value=f"**{_copper} copper** from the wreckage.", inline=False)
                await ctx.send(embed=_ev)

            else:  # ominous_silence
                _ev = discord.Embed(
                    title=f"{_cfg['emoji']} {_cfg['title']}",
                    description=random.choice(_cfg["flavors"]),
                    color=_cfg["color"],
                )
                await ctx.send(embed=_ev)

    # ------------------------------------------------------------------ #
    #  !fight
    # ------------------------------------------------------------------ #
    @commands.command(name="fight", brief="Start a combat encounter")
    async def fight(self, ctx: commands.Context):
        uid = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if uid in ACTIVE_COMBATS:
            await ctx.send("⚔️ Already in combat! Type `attack`, `flee`, or `use <item>`.")
            return
        if uid in ACTIVE_DUNGEONS:
            await ctx.send(f"🏰 You're in a dungeon (**{ACTIVE_DUNGEONS[uid]}**)! Finish it first.")
            return
        if uid in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through.")
            return
        if uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        if player["hp"] <= 1:
            await ctx.send("💀 Critically wounded! Use `!rest` first.")
            return
        ACTIVE_COMBATS[uid] = True
        await _run_combat(ctx, player, generate_enemy(player), self.bot, chest_context="fight")

    # ------------------------------------------------------------------ #
    #  !pvp
    # ------------------------------------------------------------------ #
    @commands.command(name="pvp", brief="Challenge another player to a duel")
    async def pvp(self, ctx: commands.Context, opponent: discord.Member = None):
        """
        Challenge a player to a full PvP duel.
        Both players use attack / flee / use <item> / skill each turn.
        Example: `!pvp @username`
        """
        uid = ctx.author.id
        if not opponent:
            await ctx.send("Usage: `!pvp @username`")
            return
        if opponent.id == uid:
            await ctx.send("You can't fight yourself!")
            return
        if uid in ACTIVE_COMBATS or opponent.id in ACTIVE_COMBATS:
            await ctx.send("❌ One of you is already in combat!")
            return
        if uid in ACTIVE_DUNGEONS:
            await ctx.send(f"🏰 You're in a dungeon (**{ACTIVE_DUNGEONS[uid]}**)! Finish it first.")
            return
        if opponent.id in ACTIVE_DUNGEONS:
            await ctx.send(f"🏰 **{opponent.display_name}** is in a dungeon! They can't duel right now.")
            return
        if uid in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through first.")
            return
        if opponent.id in ACTIVE_RIFTS:
            await ctx.send(f"🌀 **{opponent.display_name}** is inside a rift! They can't duel right now.")
            return
        if uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        if opponent.id in ACTIVE_RAND_DUNGEONS:
            await ctx.send(f"🏚️ **{opponent.display_name}** is inside a random dungeon! They can't duel right now.")
            return

        attacker = ensure_player(uid)
        defender = ensure_player(opponent.id)
        if not attacker:
            await ctx.send("Use `!start` first!")
            return
        if not defender:
            await ctx.send(f"**{opponent.display_name}** hasn't started yet (`!start`).")
            return

        if attacker["hp"] <= 1:
            await ctx.send("💀 You're critically wounded! Use `!rest` first.")
            return
        if defender["hp"] <= 1:
            await ctx.send(f"💀 **{opponent.display_name}** is too wounded to duel.")
            return

        # Challenge embed + accept prompt
        challenge = discord.Embed(
            title="⚔️ PvP Challenge!",
            description=(
                f"{ctx.author.mention} challenges {opponent.mention} to a duel!\n\n"
                f"**{ctx.author.display_name}** — Lv {attacker['level']} {attacker['class']} "
                f"| HP {attacker['hp']}/{attacker['max_hp']}\n"
                f"**{opponent.display_name}** — Lv {defender['level']} {defender['class']} "
                f"| HP {defender['hp']}/{defender['max_hp']}\n\n"
                f"{opponent.mention}, type `accept` within 30 seconds to fight."
            ),
            color=0xEB459E,
        )
        await ctx.send(embed=challenge)

        def accept_check(m: discord.Message) -> bool:
            return (
                m.author == opponent
                and m.channel == ctx.channel
                and m.content.strip().lower() == "accept"
            )

        try:
            await self.bot.wait_for("message", timeout=30.0, check=accept_check)
        except asyncio.TimeoutError:
            await ctx.send(f"⏱️ **{opponent.display_name}** didn't respond. Challenge cancelled.")
            return

        ACTIVE_COMBATS[uid] = True
        ACTIVE_COMBATS[opponent.id] = True
        await _run_pvp(ctx, ctx.author, attacker, opponent, defender, self.bot)

    # ------------------------------------------------------------------ #
    #  !pvpstats
    # ------------------------------------------------------------------ #
    @commands.command(name="pvpstats", aliases=["pvprecord"], brief="View your PvP win/loss record")
    async def pvpstats(self, ctx: commands.Context, target: discord.Member = None):
        """View PvP record for yourself or another player. Example: `!pvpstats @username`"""
        member = target or ctx.author
        player = ensure_player(member.id)
        if not player:
            await ctx.send(f"**{member.display_name}** hasn't started yet.")
            return
        wins   = player.get("pvp_wins",   0)
        losses = player.get("pvp_losses", 0)
        total  = wins + losses
        rate   = f"{wins/total*100:.0f}%" if total else "N/A"
        embed  = discord.Embed(
            title=f"⚔️ {member.display_name}'s PvP Record",
            color=0xEB459E,
        )
        embed.add_field(name="🏆 Wins",       value=str(wins),   inline=True)
        embed.add_field(name="💀 Losses",     value=str(losses), inline=True)
        embed.add_field(name="📊 Win Rate",   value=rate,        inline=True)
        embed.add_field(name="Class",         value=player["class"],    inline=True)
        embed.add_field(name="Level",         value=str(player["level"]), inline=True)
        embed.set_footer(text="Challenge someone with !pvp @user")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !dungeons  (list)
    # ------------------------------------------------------------------ #
    @commands.command(name="dungeons", aliases=["dlist"], brief="List all available dungeons")
    async def dungeons_list(self, ctx: commands.Context):
        """Show all dungeons, their level requirements, and your clear history."""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        completed = player.get("dungeons_completed", [])
        embed = discord.Embed(
            title="🏰 Dungeon Registry",
            description="Clear dungeons for bonus XP, gold, and rare item drops.",
            color=0xED4245,
        )
        for name, data in DUNGEON_DATA.items():
            cleared = name in completed
            locked  = player["level"] < data["min_level"]
            status  = "✅ Cleared" if cleared else ("🔒 Locked" if locked else "⚔️ Available")
            wave_count = len(data["waves"])
            rare_names = ", ".join(d["item"] for d in data["rewards"]["rare_drops"])
            embed.add_field(
                name=f"{data['emoji']} {name}  [{status}]",
                value=(
                    f"Min Level: **{data['min_level']}** | Waves: **{wave_count}**\n"
                    f"{data['description']}\n"
                    f"🎲 Rare: *{rare_names}*"
                ),
                inline=False,
            )
        embed.set_footer(text="Enter with: !dungeon <name>")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !dungeon  (enter)
    # ------------------------------------------------------------------ #
    @commands.command(name="dungeon", brief="Enter a dungeon")
    async def dungeon_enter(self, ctx: commands.Context, *, dungeon_name: str = None):
        """
        Enter a dungeon and fight through its waves.
        Example: `!dungeon Goblin Lair`
        See all dungeons with `!dungeons`.
        """
        uid = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        if uid in ACTIVE_COMBATS:
            await ctx.send("⚔️ Finish your current fight first!")
            return
        if uid in ACTIVE_DUNGEONS:
            await ctx.send(f"🏰 You're already in **{ACTIVE_DUNGEONS[uid]}**!")
            return
        if uid in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through first.")
            return
        if uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return

        if not dungeon_name:
            names = " · ".join(
                f"`{n}`" + (" 🔒" if player["level"] < d["min_level"] else "")
                for n, d in DUNGEON_DATA.items()
            )
            await ctx.send(
                f"🏰 **Available dungeons:** {names}\n"
                f"Use `!dungeons` for full details, or `!dungeon <name>` to enter."
            )
            return

        # Fuzzy-match the dungeon name (case-insensitive)
        matched_name = next(
            (k for k in DUNGEON_DATA if k.lower() == dungeon_name.lower()),
            None,
        )
        if not matched_name:
            # Try partial match
            matched_name = next(
                (k for k in DUNGEON_DATA if dungeon_name.lower() in k.lower()),
                None,
            )
        if not matched_name:
            names = ", ".join(f"**{n}**" for n in DUNGEON_DATA)
            await ctx.send(f"❌ Unknown dungeon. Available: {names}")
            return

        ok, msg, dungeon = enter_dungeon(player, matched_name)
        if not ok:
            await ctx.send(msg)
            return

        await _run_dungeon(ctx, player, matched_name, dungeon, self.bot)

    # ------------------------------------------------------------------ #
    #  !inventory
    # ------------------------------------------------------------------ #
    @commands.command(name="inventory", aliases=["inv"], brief="View your inventory")
    async def inventory(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        equipped_items = set(v for v in player.get("equipped", {}).values() if v)
        embed = discord.Embed(title=f"🎒 {ctx.author.display_name}'s Inventory", color=0xEB459E)

        if not player["inventory"]:
            embed.description = "Your inventory is empty."
        else:
            counts: dict[str, int] = {}
            for item in player["inventory"]:
                counts[item] = counts.get(item, 0) + 1
            lines = []
            for item, qty in counts.items():
                # Determine item description
                if item in EQUIPMENT_DATA:
                    eq = EQUIPMENT_DATA[item]
                    parts = []
                    if eq["attack_bonus"]:  parts.append(f"+{eq['attack_bonus']} ATK")
                    if eq["defense_bonus"]: parts.append(f"+{eq['defense_bonus']} DEF")
                    if eq["hp_bonus"]:      parts.append(f"+{eq['hp_bonus']} HP")
                    effect = f"{eq['slot'].title()} — " + " ".join(parts)
                else:
                    effect = shop_items.get(item, {}).get("effect", "Unique item")
                sell = sell_prices.get(item)
                sell_str = f" · {sell}c" if sell else ""
                eq_tag = " *[equipped]*" if item in equipped_items else ""
                lines.append(f"**{item}** x{qty}{eq_tag}\n*{effect}{sell_str}*")
            embed.description = "\n\n".join(lines)

        embed.set_footer(text="!equip <item> · !use <item> · !sell <item> · !unequip <slot>")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !equip
    # ------------------------------------------------------------------ #
    @commands.command(name="equip", brief="Equip a weapon or armor")
    async def equip(self, ctx: commands.Context, *, item_name: str = None):
        """Equip gear from your inventory. Example: `!equip Legendary Sword`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not item_name:
            slot_icon = {"weapon": "🗡️", "armor": "🛡️", "accessory": "💍"}
            lines: list[str] = []
            for n, i in EQUIPMENT_DATA.items():
                icon = slot_icon.get(i["slot"], "⚙️")
                parts: list[str] = []
                if i.get("attack_bonus"):  parts.append(f"+{i['attack_bonus']} ATK")
                if i.get("defense_bonus"): parts.append(f"+{i['defense_bonus']} DEF")
                if i.get("hp_bonus"):      parts.append(f"+{i['hp_bonus']} HP")
                if i.get("mana_bonus"):    parts.append(f"+{i['mana_bonus']} Mana")
                if i.get("speed_bonus"):   parts.append(f"+{i['speed_bonus']} SPD")
                if i.get("crit_bonus"):    parts.append(f"+{i['crit_bonus']*100:.0f}% Crit")
                if i.get("luck_bonus"):    parts.append(f"+{i['luck_bonus']} Luck")
                stat_str = " | ".join(parts) if parts else "No bonus"
                avail = "" if i.get("cost_copper") else " *(rare drop)*"
                lines.append(f"{icon} **{n}**{avail} — {stat_str}")
            embed = discord.Embed(title="⚙️ Equippable Gear", color=0x95A5A6)
            embed.add_field(name="Weapons 🗡️",    value="\n".join(l for l in lines if "🗡️" in l) or "—", inline=False)
            embed.add_field(name="Armor 🛡️",      value="\n".join(l for l in lines if "🛡️" in l) or "—", inline=False)
            embed.add_field(name="Accessories 💍", value="\n".join(l for l in lines if "💍" in l) or "—", inline=False)
            embed.set_footer(text="!equip <item name>  ·  !unequip weapon | armor | accessory")
            await ctx.send(embed=embed)
            return
        msgs = equip_gear(player, item_name)
        save_game(ctx.author.id, player)
        for m in msgs:
            await ctx.send(m)

    # ------------------------------------------------------------------ #
    #  !unequip
    # ------------------------------------------------------------------ #
    @commands.command(name="unequip", brief="Unequip a weapon or armor slot")
    async def unequip(self, ctx: commands.Context, *, slot: str = None):
        """Unequip from a slot. Example: `!unequip weapon` or `!unequip armor`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if ctx.author.id in ACTIVE_COMBATS:
            await ctx.send("⚔️ Can't unequip during combat!")
            return
        if ctx.author.id in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through first.")
            return
        if ctx.author.id in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        if not slot:
            await ctx.send("Usage: `!unequip weapon` · `!unequip armor` · `!unequip accessory`")
            return
        msgs = unequip_gear(player, slot)
        save_game(ctx.author.id, player)
        for m in msgs:
            await ctx.send(m)

    # ------------------------------------------------------------------ #
    #  !use
    # ------------------------------------------------------------------ #
    @commands.command(name="use", brief="Use a consumable item")
    async def use_item(self, ctx: commands.Context, *, item_name: str = None):
        """Use an item outside combat. Example: `!use Minor Healing Potion`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if ctx.author.id in ACTIVE_COMBATS:
            await ctx.send("You're in combat! Type `use <item>` directly.")
            return
        if ctx.author.id in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through first.")
            return
        if ctx.author.id in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        if not item_name:
            await ctx.send("Usage: `!use <item name>`. Check `!inventory`.")
            return
        matched = next((i for i in player["inventory"] if i.lower() == item_name.lower()), None)
        if not matched:
            await ctx.send(f"❌ You don't have **{item_name}**.")
            return
        success, msg = use_item(player, matched)
        if success:
            save_game(ctx.author.id, player)
        await ctx.send(msg)

    # ------------------------------------------------------------------ #
    #  !rest
    # ------------------------------------------------------------------ #
    @commands.command(name="rest", brief="Rest to recover HP")
    async def rest(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if ctx.author.id in ACTIVE_COMBATS:
            await ctx.send("❌ Can't rest during combat!")
            return
        if ctx.author.id in ACTIVE_RIFTS:
            await ctx.send("🌀 You're inside a rift! Fight your way through first.")
            return
        if ctx.author.id in ACTIVE_RAND_DUNGEONS:
            await ctx.send("🏚️ You're inside a random dungeon! Finish it first.")
            return
        _base_rest = random.randint(20, 40)
        restored = int(_base_rest * faction_heal_mult(player))
        player["hp"] = min(player["max_hp"], player["hp"] + restored)
        time_msg = advance_time(player)
        save_game(ctx.author.id, player)
        _heal_bonus_note = " *(Divine blessing!)*" if get_faction_key(player) == "Divine" else ""
        embed = discord.Embed(
            title="😴 Resting...",
            description=(
                f"You find a safe spot.\n\n"
                f"💚 Recovered **{restored} HP**!{_heal_bonus_note} "
                f"HP: **{player['hp']}/{player['max_hp']}** "
                f"`{hp_bar(player['hp'], player['max_hp'])}`\n\n{time_msg}"
            ),
            color=0x57F287,
        )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !shop
    # ------------------------------------------------------------------ #
    @commands.command(name="shop", brief="Browse the shop (Aetherfall only)")
    async def shop(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not world_map.get(player["current_location"], {}).get("has_shop"):
            await ctx.send(f"🚫 No shop in **{player['current_location']}**. Travel to **Aetherfall** 🏙️.")
            return
        funds = total_copper(player)
        embed = discord.Embed(
            title="🛒 Aetherfall Shop",
            description=f"Balance: **{format_currency(player)}** ({funds}c)\n`!buy <item>` to purchase · `!sell <item>` to sell",
            color=0xFEE75C,
        )
        # Group items by type for readability
        type_labels = {
            "heal":    "💊 Healing Potions",
            "mana":    "🔵 Mana Potions",
            "buff":    "⚡ Stat Buffs",
            "passive": "🍀 Passives",
            "gear":    "⚙️ Equipment",
        }
        grouped: dict[str, list[str]] = {}
        for item, info in shop_items.items():
            t = info.get("type", "other")
            grouped.setdefault(t, [])
            can = "✅" if funds >= info["cost_copper"] else "❌"
            grouped[t].append(f"{can} **{item}** — {info['cost_copper']}c\n*{info['effect']}*")
        for t, label in type_labels.items():
            if t in grouped:
                embed.add_field(name=label, value="\n".join(grouped[t]), inline=False)
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !buy
    # ------------------------------------------------------------------ #
    @commands.command(name="buy", brief="Buy an item from the shop")
    async def buy(self, ctx: commands.Context, *, item_name: str = None):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not world_map.get(player["current_location"], {}).get("has_shop"):
            await ctx.send("🚫 No shop here. Travel to **Aetherfall**.")
            return
        if not item_name:
            await ctx.send("Usage: `!buy <item name>`. Check `!shop`.")
            return
        matched = next((i for i in shop_items if i.lower() == item_name.lower()), None)
        if not matched:
            await ctx.send(f"❌ **{item_name}** not sold here.")
            return
        cost = shop_items[matched]["cost_copper"]
        if not spend_copper(player, cost):
            await ctx.send(f"❌ Need {cost}c. You have {total_copper(player)}c.")
            return
        add_to_inventory(player, matched)
        save_game(ctx.author.id, player)
        await ctx.send(f"✅ Bought **{matched}** for {cost}c! Balance: **{format_currency(player)}**")

    # ------------------------------------------------------------------ #
    #  !sell
    # ------------------------------------------------------------------ #
    @commands.command(name="sell", brief="Sell an item from your inventory")
    async def sell(self, ctx: commands.Context, *, item_name: str = None):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not item_name:
            sellable = [(i, sell_prices[i]) for i in set(player["inventory"]) if i in sell_prices]
            if not sellable:
                await ctx.send("Nothing to sell. Check `!inventory`.")
                return
            lines = "\n".join(f"• **{i}** — {p}c" for i, p in sorted(sellable))
            await ctx.send(f"Sellable items:\n{lines}\n\nUsage: `!sell <item name>`")
            return
        matched = next((i for i in player["inventory"] if i.lower() == item_name.lower()), None)
        if not matched:
            await ctx.send(f"❌ You don't have **{item_name}**.")
            return
        price = sell_prices.get(matched)
        if not price:
            await ctx.send(f"❌ **{matched}** can't be sold.")
            return
        remove_from_inventory(player, matched)
        # Auto-unequip if selling equipped item
        for slot, eq_item in list(player.get("equipped", {}).items()):
            if eq_item == matched:
                unequip_gear(player, slot)
                break
        add_currency(player, price)
        save_game(ctx.author.id, player)
        await ctx.send(f"💰 Sold **{matched}** for **{price}c**! Balance: **{format_currency(player)}**")

    # ------------------------------------------------------------------ #
    #  !quests
    # ------------------------------------------------------------------ #
    @commands.command(name="quests", aliases=["quest", "questlog"], brief="View your quest log")
    async def quests(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        embed = discord.Embed(title="📜 Quest Log", color=0xEB459E)
        active = [(qid, q) for qid, q in quest_data.items() if player["quest_log"].get(qid, {}).get("status") == "active"]
        done   = [(qid, q) for qid, q in quest_data.items() if player["quest_log"].get(qid, {}).get("status") == "completed"]
        if active:
            for qid, q in active:
                embed.add_field(
                    name=f"🔵 {q['name']}",
                    value=f"{q['description']}\n*Reward: {q['reward_experience']} XP · {q['reward_copper']}c*",
                    inline=False,
                )
        if done:
            embed.add_field(name="✅ Completed", value=" · ".join(f"~~{q['name']}~~" for _, q in done), inline=False)
        if not active and not done:
            embed.description = "No quests yet. Explore to find them!"
        if player["completed_quest_chains"]:
            embed.set_footer(text="Chains: " + ", ".join(player["completed_quest_chains"]))
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !location
    # ------------------------------------------------------------------ #
    @commands.command(name="location", aliases=["loc", "where"], brief="Your current location")
    async def location(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        loc = player["current_location"]
        info = world_map.get(loc, {})
        time_icon = "🌙" if player["time_of_day"] == "night" else "☀️"
        connected = gates.get(loc, [])
        embed = discord.Embed(
            title=f"{LOCATION_EMOJIS.get(loc,'📍')} {loc}",
            description=info.get("lore") or info.get("description", ""),
            color=location_color(loc),
        )
        embed.add_field(name="Realm", value=info.get("realm","?"), inline=True)
        embed.add_field(name="Rec. Level", value=str(info.get("level","?")), inline=True)
        embed.add_field(name="Time", value=f"{time_icon} {player['time_of_day'].capitalize()}", inline=True)
        embed.add_field(name="Paths", value=", ".join(f"**{c}**" for c in connected) or "None", inline=False)
        if info.get("is_boss_area"):
            embed.add_field(
                name="☠️ Danger Zone",
                value="*The air here is wrong. Something powerful watches from the dark. Prepare before you engage.*",
                inline=False,
            )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !save / !load
    # ------------------------------------------------------------------ #
    @commands.command(name="save", brief="Save your game")
    async def save(self, ctx: commands.Context):
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Nothing to save. Use `!start` first!")
            return
        save_game(ctx.author.id, player)
        await ctx.send("💾 Game saved!")

    @commands.command(name="load", brief="Load your saved game")
    async def load(self, ctx: commands.Context):
        uid = ctx.author.id
        p = load_game(uid)
        if not p:
            await ctx.send("No save file found. Use `!start`.")
            return
        players[uid] = p
        loc = p["current_location"]
        await ctx.send(
            f"📂 Loaded! {LOCATION_EMOJIS.get(loc,'📍')} **{loc}** — "
            f"Level {p['level']} {p['class']}, HP {p['hp']}/{p['max_hp']}."
        )

    # ------------------------------------------------------------------ #
    #  !demonking  —  Server-wide Demon King Event
    # ------------------------------------------------------------------ #
    @commands.command(name="demonking", aliases=["kingevent"], brief="[Admin] Start the Demon King server event")
    @commands.has_permissions(administrator=True)
    async def demon_king_event(self, ctx: commands.Context):
        """
        Starts a server-wide Demon King event visible to everyone.
        Any player can deal damage; the event ends when the king reaches 0 HP.
        Requires Administrator permission.
        """
        global DEMON_KING_EVENT_ACTIVE
        if DEMON_KING_EVENT_ACTIVE:
            await ctx.send("☠️ The Demon King is already rampaging! Type `strike` to attack!")
            return

        DEMON_KING_EVENT_ACTIVE = True

        # Scale the King's HP to the number of participants (minimum 1000)
        from bot.rpg.data import enemy_types as et
        base_hp = et["Demon King"]["hp"] * 3  # 3x for server event
        enemy_event = {
            "name": "Demon King",
            "hp": base_hp,
            "max_hp": base_hp,
            "attack": et["Demon King"]["attack"],
            "defense": et["Demon King"]["defense"],
            "crit_chance": et["Demon King"]["crit_chance"],
            "is_boss": True,
            "phase2_announced": False,
            "phase3_announced": False,
            "has_healed": False,
        }

        embed = discord.Embed(
            title="☠️ SERVER EVENT: THE DEMON KING AWAKENS",
            description=(
                "**The Demon King has broken free from Voidkand and is attacking the realm!**\n\n"
                "All hunters must unite! Type `strike` to deal damage.\n"
                "The event ends when the king reaches **0 HP**.\n\n"
                f"👿 **Demon King HP: {base_hp}**"
            ),
            color=0xED4245,
        )
        embed.set_footer(text="Every registered player can strike. React fast — the king hits back!")
        event_msg = await ctx.send(embed=embed)

        contributors: dict[int, int] = {}  # user_id -> total damage dealt

        def strike_check(m):
            return m.channel == ctx.channel and m.content.lower() == "strike"

        while enemy_event["hp"] > 0 and DEMON_KING_EVENT_ACTIVE:
            try:
                msg = await self.bot.wait_for("message", timeout=120.0, check=strike_check)
            except asyncio.TimeoutError:
                await ctx.send("⏱️ The Demon King vanishes into the void... event timed out.")
                DEMON_KING_EVENT_ACTIVE = False
                return

            striker = ensure_player(msg.author.id)
            if not striker:
                await msg.channel.send(f"{msg.author.mention} — use `!start` to join the hunt!")
                continue

            # Damage based on striker's attack
            crit = random.random() < striker.get("crit_chance", 0.05)
            raw = random.randint(striker["attack"], striker["attack"] + 10)
            if crit:
                raw = int(raw * 1.75)
            dmg = damage_after_defense(raw, enemy_event.get("defense", 15))
            enemy_event["hp"] = max(0, enemy_event["hp"] - dmg)
            contributors[msg.author.id] = contributors.get(msg.author.id, 0) + dmg

            crit_tag = " 💥 CRIT!" if crit else ""
            phase = get_demon_king_phase(enemy_event["hp"], enemy_event["max_hp"])

            phase_msg = ""
            if phase == 2 and not enemy_event["phase2_announced"]:
                enemy_event["phase2_announced"] = True
                enemy_event["attack"] = int(enemy_event["attack"] * 1.3)
                phase_msg = "\n🔥 **PHASE 2!** The Demon King's power surges!"
            elif phase == 3 and not enemy_event["phase3_announced"]:
                enemy_event["phase3_announced"] = True
                enemy_event["attack"] = int(enemy_event["attack"] * 1.5)
                phase_msg = "\n💀 **RAGE MODE!** The Demon King is in his final phase!"

            bar = hp_bar(enemy_event["hp"], enemy_event["max_hp"], 15)
            await ctx.send(
                f"⚔️ **{msg.author.display_name}** strikes for **{dmg}** dmg!{crit_tag}"
                f"{phase_msg}\n"
                f"👿 King HP: **{enemy_event['hp']}/{enemy_event['max_hp']}** `{bar}`"
            )

            # King retaliates against the striker
            if enemy_event["hp"] > 0:
                k_raw = random.randint(enemy_event["attack"] - 5, enemy_event["attack"] + 5)
                k_dmg = damage_after_defense(k_raw, striker.get("defense", 5))
                striker["hp"] = max(1, striker["hp"] - k_dmg)
                save_game(msg.author.id, striker)
                await ctx.send(
                    f"👿 The **Demon King** retaliates at {msg.author.mention} for **{k_dmg}** dmg! "
                    f"HP: **{striker['hp']}/{striker['max_hp']}**"
                )

        DEMON_KING_EVENT_ACTIVE = False

        # Victory!
        if enemy_event["hp"] <= 0:
            # Award everyone who contributed
            sorted_contribs = sorted(contributors.items(), key=lambda x: x[1], reverse=True)
            mvp_uid = sorted_contribs[0][0] if sorted_contribs else None
            award_lines = []
            for uid, dealt in sorted_contribs[:10]:
                p = ensure_player(uid)
                if p:
                    xp_msgs = add_experience(p, 2000)
                    add_currency(p, 500)
                    if uid == mvp_uid:
                        add_to_inventory(p, "Demon King's Crown")
                        award_lines.append(f"👑 <@{uid}> — **{dealt} dmg** *(MVP — received Demon King's Crown!)*")
                    else:
                        award_lines.append(f"• <@{uid}> — **{dealt} dmg**")
                    p["demon_king_slain"] = True
                    msgs_q = complete_quest(p, "defeat_demon_king")
                    save_game(uid, p)

            embed = discord.Embed(
                title="🎉 THE DEMON KING HAS FALLEN!",
                description=(
                    "**The realm is saved!** Hunters of the world unite in victory!\n\n"
                    "**Top Contributors:**\n" + "\n".join(award_lines)
                ),
                color=0x57F287,
            )
            embed.set_footer(text="All contributors received 2000 XP + 500 copper. MVP got the Demon King's Crown!")
            await ctx.send(embed=embed)

            # ── Per-player chest drops after boss falls ────────────────────
            for uid, dealt in sorted_contribs[:10]:
                p = ensure_player(uid)
                if not p:
                    continue
                _ctx_key = "boss_event_mvp" if uid == mvp_uid else "boss_event_contrib"
                _be_rarity = maybe_find_chest(p, _ctx_key)
                if uid == mvp_uid:
                    _be_rarity = roll_chest_rarity(p, force_min="Legendary")
                if _be_rarity:
                    _be_result = open_chest(p, _be_rarity)
                    save_game(uid, p)
                    await ctx.send(
                        f"<@{uid}> " + _be_result["headline"],
                        embed=_chest_embed(_be_result),
                    )

    # ================================================================== #
    #  FACTION COMMANDS
    # ================================================================== #

    # ------------------------------------------------------------------ #
    #  !faction
    # ------------------------------------------------------------------ #
    @commands.command(name="faction", brief="View or manage your faction allegiance")
    async def faction_cmd(self, ctx: commands.Context, *, args: str = ""):
        """
        !faction                  — show your faction or invite to join
        !faction choose <name>    — pledge allegiance (Eclipse / Divine / Void)
        !faction missions         — view your faction missions
        !faction rep              — view reputation standings
        !faction info <name>      — learn about a faction before joining
        """
        uid = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        parts = args.strip().lower().split(None, 1)
        sub   = parts[0] if parts else ""
        rest  = parts[1].strip() if len(parts) > 1 else ""

        # ── !faction choose <name> ──────────────────────────────────────
        if sub == "choose":
            if not rest:
                await ctx.send(
                    "❓ Specify a faction: `!faction choose eclipse` · "
                    "`!faction choose divine` · `!faction choose void`"
                )
                return
            success, msg = faction_join(player, rest)
            if success:
                save_game(uid, player)
                fkey = get_faction_key(player)
                fdata = FACTIONS[fkey]
                embed = discord.Embed(
                    title=f"{fdata['emoji']} {fdata['name']}",
                    description=msg,
                    color=fdata["color"],
                )
                embed.set_footer(text=f"Leader: {fdata['leader']} · Use !faction missions to begin serving.")
                await ctx.send(embed=embed)
            else:
                await ctx.send(msg)
            return

        # ── !faction info <name> ────────────────────────────────────────
        if sub == "info":
            lookup = rest.strip().capitalize()
            _aliases = {
                "Eclipse": "Eclipse", "Empire": "Eclipse",
                "Divine": "Divine", "Order": "Divine",
                "Void": "Void", "Legion": "Void",
            }
            fkey = _aliases.get(lookup)
            if not fkey or fkey not in FACTIONS:
                keys = " · ".join(f"`{k.lower()}`" for k in FACTIONS)
                await ctx.send(f"❓ Unknown faction. Choose one of: {keys}.")
                return
            fdata = FACTIONS[fkey]
            embed = discord.Embed(
                title=f"{fdata['emoji']} {fdata['name']}",
                description=fdata["description"],
                color=fdata["color"],
            )
            embed.add_field(name="Leader",       value=fdata["leader"],       inline=True)
            embed.add_field(name="Faction Bonus", value=fdata["bonus_summary"], inline=False)
            embed.add_field(name="Lore",          value=f"*{fdata['lore']}*",  inline=False)
            missions = FACTION_MISSIONS.get(fkey, [])
            mission_list = "\n".join(
                f"**{m['name']}** — {m['description']}" for m in missions
            )
            embed.add_field(name="📜 Missions",   value=mission_list,          inline=False)
            embed.set_footer(text=f"Join at Level {MIN_FACTION_LEVEL}: !faction choose {fkey.lower()}")
            await ctx.send(embed=embed)
            return

        # ── !faction missions ───────────────────────────────────────────
        if sub == "missions":
            fkey = get_faction_key(player)
            if not fkey:
                await ctx.send(
                    f"❌ You aren't in a faction yet. Reach Level {MIN_FACTION_LEVEL} "
                    f"and use `!faction choose <name>` to join one."
                )
                return
            fdata = FACTIONS[fkey]
            pending = available_missions(player)
            completed_ids = set(player.get("faction_missions_completed", []))
            all_missions  = FACTION_MISSIONS.get(fkey, [])
            done_missions  = [m for m in all_missions if m["id"] in completed_ids]

            embed = discord.Embed(
                title=f"{fdata['emoji']} {fdata['name']} — Missions",
                color=fdata["color"],
            )
            if pending:
                for m in pending:
                    _type_hint = {
                        "kill_count":    f"Defeat {m['required']} enemies",
                        "travel":        f"Travel to **{m.get('required_location', '?')}**",
                        "dungeon_clear": f"Clear **{m.get('required_dungeon', '?')}**",
                    }.get(m["type"], m["type"])
                    embed.add_field(
                        name=f"📜 {m['name']}",
                        value=(
                            f"{m['description']}\n"
                            f"*{_type_hint}*\n"
                            f"Reward: ✨ {m['reward_xp']} XP · 💰 {m['reward_copper']}c · "
                            f"🏅 +{m['reward_rep']} Rep\n"
                            f"*\"{m['flavor']}\"*"
                        ),
                        inline=False,
                    )
            else:
                embed.description = "✅ **All missions complete!** Check back — more may come."

            if done_missions:
                embed.add_field(
                    name="✅ Completed",
                    value="\n".join(f"~~{m['name']}~~" for m in done_missions),
                    inline=False,
                )
            embed.set_footer(text="Kill and travel missions track automatically. Dungeons: !dungeon <name>")
            await ctx.send(embed=embed)
            return

        # ── !faction rep ────────────────────────────────────────────────
        if sub == "rep":
            rep = player.get("reputation", {"Eclipse": 0, "Divine": 0, "Void": 0})
            embed = discord.Embed(
                title="🏅 Faction Reputation",
                description="Your standing with each faction in Voidkand:",
                color=0x5865F2,
            )
            for fkey, fdata in FACTIONS.items():
                rep_val = rep.get(fkey, 0)
                tier    = get_reputation_tier(rep_val)
                # Find next tier threshold
                next_tier = next(
                    (t for t in REPUTATION_TIERS if t[0] > rep_val), None
                )
                progress = (
                    f" *(next rank at {next_tier[0]})*" if next_tier else " *(Max rank!)*"
                )
                embed.add_field(
                    name=f"{fdata['emoji']} {fdata['name']}",
                    value=f"**{tier['title']}** — {rep_val} rep{progress}",
                    inline=False,
                )
            await ctx.send(embed=embed)
            return

        # ── !faction (no subcommand) ────────────────────────────────────
        fkey = get_faction_key(player)
        if not fkey:
            embed = discord.Embed(
                title="⚔️ The Factions Call",
                description=(
                    "Three great powers have noticed your growing strength.\n"
                    f"Reach **Level {MIN_FACTION_LEVEL}** and swear allegiance to one.\n\n"
                    "Use `!faction info <name>` to learn about each faction.\n"
                    "Use `!faction choose <name>` to pledge your loyalty.\n\n"
                    "⚠️ *Your choice is permanent.*"
                ),
                color=0x5865F2,
            )
            for fk, fd in FACTIONS.items():
                embed.add_field(
                    name=f"{fd['emoji']} {fd['name']} (led by {fd['leader']})",
                    value=fd["bonus_summary"],
                    inline=False,
                )
            embed.set_footer(
                text=f"Current level: {player['level']} · Required: {MIN_FACTION_LEVEL}"
            )
            await ctx.send(embed=embed)
            return

        # Player is in a faction — show status
        fdata = FACTIONS[fkey]
        rep_val  = player.get("reputation", {}).get(fkey, 0)
        tier     = get_reputation_tier(rep_val)
        pending  = available_missions(player)
        all_missions = FACTION_MISSIONS.get(fkey, [])
        done_count   = len(player.get("faction_missions_completed", []))

        embed = discord.Embed(
            title=f"{fdata['emoji']} {fdata['name']}",
            description=fdata["lore"],
            color=fdata["color"],
        )
        embed.add_field(name="Leader",        value=fdata["leader"],             inline=True)
        embed.add_field(name="Your Rank",     value=f"**{tier['title']}**",      inline=True)
        embed.add_field(name="Reputation",    value=f"{rep_val} rep",            inline=True)
        embed.add_field(name="Faction Bonus", value=fdata["bonus_summary"],      inline=False)
        embed.add_field(
            name="📜 Mission Progress",
            value=(
                f"{done_count}/{len(all_missions)} complete · "
                f"{len(pending)} available\n"
                "Use `!faction missions` to view them."
            ),
            inline=False,
        )
        embed.set_footer(text="!faction missions · !faction rep · Allegiance is eternal.")
        await ctx.send(embed=embed)

    # ================================================================== #
    #  GUILD COMMANDS
    # ================================================================== #

    # ------------------------------------------------------------------ #
    #  !guilds
    # ------------------------------------------------------------------ #
    @commands.command(name="guilds", brief="List all player guilds")
    async def guilds_list(self, ctx: commands.Context):
        """Show all existing guilds."""
        guilds = load_guilds()
        if not guilds:
            await ctx.send("No guilds exist yet. Use `!guild_create <name>` to found the first one!")
            return
        embed = discord.Embed(
            title="🏰 Player Guilds",
            description=f"{len(guilds)} guild(s) active · `!guild_info <name>` for details",
            color=0xF1C40F,
        )
        for gid, g in guilds.items():
            bs = bonus_summary(GUILD_BONUS_TABLE.get(g.get("level", 1), {}))
            embed.add_field(
                name=f"Lv {g.get('level',1)} · {g['name']}",
                value=(
                    f"👥 {len(g.get('members',[]))} members · "
                    f"🎖 {g.get('war_wins',0)}W/{g.get('war_losses',0)}L\n"
                    f"Bonuses: {bs}"
                ),
                inline=False,
            )
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !guild_create
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_create", brief="Create a new guild")
    async def guild_create(self, ctx: commands.Context, name: str = None, *, description: str = ""):
        """Create a new guild. Example: `!guild_create Vanguard Elite A fierce guild of warriors`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not name:
            await ctx.send("Usage: `!guild_create <name> [description]`")
            return
        guilds = load_guilds()
        existing_gid = get_player_guild_id(ctx.author.id, guilds)
        if existing_gid:
            gname = guilds[existing_gid]["name"]
            await ctx.send(f"❌ You're already in **{gname}**. Use `!guild_leave` first.")
            return
        gid, msg = create_guild(ctx.author.id, name, description, guilds)
        if not gid:
            await ctx.send(f"❌ {msg}")
            return
        player["guild_id"] = gid
        apply_guild_bonus(player, guilds)
        save_guilds(guilds)
        save_game(ctx.author.id, player)
        bs = bonus_summary(GUILD_BONUS_TABLE[1])
        embed = discord.Embed(
            title=msg,
            description=(
                f"Others can join with `!guild_join {name}`.\n\n"
                f"**Starting member bonuses:** {bs}"
            ),
            color=0xF1C40F,
        )
        embed.set_footer(text="Earn guild XP by defeating bosses, clearing dungeons, and winning PvP!")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !guild_join
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_join", brief="Join a guild by name")
    async def guild_join(self, ctx: commands.Context, *, name: str = None):
        """Join an existing guild. Example: `!guild_join Vanguard Elite`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not name:
            await ctx.send("Usage: `!guild_join <guild name>`. See `!guilds` for the list.")
            return
        guilds = load_guilds()
        existing_gid = get_player_guild_id(ctx.author.id, guilds)
        if existing_gid:
            gname = guilds[existing_gid]["name"]
            await ctx.send(f"❌ You're already in **{gname}**. Use `!guild_leave` first.")
            return
        gid, guild = find_guild_by_name(name, guilds)
        if not gid:
            await ctx.send(f"❌ No guild named **{name}**. Check `!guilds` for the list.")
            return
        err = join_guild(ctx.author.id, gid, guilds)
        if err:
            await ctx.send(f"❌ {err}")
            return
        player["guild_id"] = gid
        apply_guild_bonus(player, guilds)
        save_guilds(guilds)
        save_game(ctx.author.id, player)
        bs = bonus_summary(GUILD_BONUS_TABLE[guild["level"]])
        await ctx.send(
            f"✅ Joined **{guild['name']}** (Level {guild['level']})!\n"
            f"Active bonuses: **{bs}**"
        )

    # ------------------------------------------------------------------ #
    #  !guild_leave
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_leave", brief="Leave your current guild")
    async def guild_leave(self, ctx: commands.Context):
        """Leave your current guild."""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        guilds = load_guilds()
        guild_name, err = leave_guild(ctx.author.id, guilds)
        if err:
            await ctx.send(f"❌ {err}")
            return
        remove_guild_bonus(player)
        player["guild_id"] = None
        save_guilds(guilds)
        save_game(ctx.author.id, player)
        await ctx.send(f"✅ You've left **{guild_name}**. Guild stat bonuses have been removed.")

    # ------------------------------------------------------------------ #
    #  !guild_info / !guild
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_info", aliases=["guild"], brief="View guild info")
    async def guild_info(self, ctx: commands.Context, *, name: str = None):
        """View your guild's info, or another guild by name. Example: `!guild_info Vanguard`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        guilds = load_guilds()
        if name:
            gid, guild = find_guild_by_name(name, guilds)
            if not gid:
                await ctx.send(f"❌ No guild named **{name}**.")
                return
        else:
            gid = player.get("guild_id")
            if not gid or gid not in guilds:
                await ctx.send("You're not in a guild. Use `!guilds` to browse or `!guild_create` to start one.")
                return
            guild = guilds[gid]
        lvl = guild.get("level", 1)
        bonuses = GUILD_BONUS_TABLE.get(lvl, {})
        bs = bonus_summary(bonuses)
        xp = guild.get("xp", 0)
        xp_to_next = guild.get("xp_to_next")
        xp_str = f"{xp}/{xp_to_next} XP" if xp_to_next else f"{xp} XP (**Max Level!**)"
        embed = discord.Embed(
            title=f"🏰 {guild['name']}",
            description=guild.get("description", "No description."),
            color=0xF1C40F,
        )
        embed.add_field(name="Level",      value=str(lvl),                                           inline=True)
        embed.add_field(name="Members",    value=str(len(guild.get("members", []))),                 inline=True)
        embed.add_field(name="War Record", value=f"{guild.get('war_wins',0)}W/{guild.get('war_losses',0)}L", inline=True)
        embed.add_field(name="Guild XP",   value=xp_str,                                             inline=True)
        embed.add_field(name="Member Bonuses", value=bs or "None",                                   inline=False)
        embed.set_footer(text=f"Founded {guild.get('created_at','?')[:10]} · !guild_members to see roster")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !guild_members
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_members", brief="List your guild's members")
    async def guild_members(self, ctx: commands.Context):
        """List all members of your guild."""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        guilds = load_guilds()
        gid = player.get("guild_id")
        if not gid or gid not in guilds:
            await ctx.send("You're not in a guild.")
            return
        guild = guilds[gid]
        member_ids = guild.get("members", [])
        owner_id   = guild.get("owner_id", "")
        lines = [
            f"• <@{mid}>{' 👑' if mid == owner_id else ''}"
            for mid in member_ids
        ]
        embed = discord.Embed(
            title=f"👥 {guild['name']} — Roster",
            description="\n".join(lines) or "No members.",
            color=0xF1C40F,
        )
        embed.set_footer(text=f"{len(member_ids)}/25 members · Lv {guild.get('level',1)} guild")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !guild_refresh
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_refresh", brief="Re-apply your guild bonuses")
    async def guild_refresh(self, ctx: commands.Context):
        """Re-apply your guild's current level bonuses to your character stats."""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        guilds = load_guilds()
        gid = player.get("guild_id")
        if not gid or gid not in guilds:
            await ctx.send("You're not in a guild.")
            return
        apply_guild_bonus(player, guilds)
        save_game(ctx.author.id, player)
        bs = bonus_summary(GUILD_BONUS_TABLE[guilds[gid].get("level", 1)])
        await ctx.send(f"✅ Guild bonuses refreshed! Active bonuses: **{bs}**")

    # ------------------------------------------------------------------ #
    #  !guild_war
    # ------------------------------------------------------------------ #
    @commands.command(name="guild_war", brief="Challenge another guild to war")
    async def guild_war(self, ctx: commands.Context, *, target: str = None):
        """Challenge a guild to a simulated war. Example: `!guild_war Shadow Order`"""
        player = ensure_player(ctx.author.id)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if not target:
            await ctx.send("Usage: `!guild_war <guild name>`")
            return
        guilds = load_guilds()
        my_gid = player.get("guild_id")
        if not my_gid or my_gid not in guilds:
            await ctx.send("❌ You must be in a guild to declare war. Use `!guild_join` or `!guild_create`.")
            return
        target_gid, target_guild = find_guild_by_name(target, guilds)
        if not target_gid:
            await ctx.send(f"❌ No guild named **{target}**. Check `!guilds`.")
            return
        if target_gid == my_gid:
            await ctx.send("❌ You can't declare war on your own guild.")
            return
        my_guild = guilds[my_gid]
        await ctx.send(
            f"⚔️ **{my_guild['name']}** declares war on **{target_guild['name']}**!\n"
            f"*Calculating power...*"
        )
        await asyncio.sleep(1.5)
        attacker_won, lvl_msgs = simulate_guild_war(my_gid, target_gid, guilds)
        save_guilds(guilds)
        if attacker_won:
            color = 0x2ECC71
            title = "⚔️ War Result — Victory!"
            desc = (
                f"**{my_guild['name']}** crushes **{target_guild['name']}** in battle!\n"
                f"+150 Guild XP awarded to the victors."
            )
        else:
            color = 0xE74C3C
            title = "⚔️ War Result — Defeat"
            desc = (
                f"**{my_guild['name']}** is repelled by **{target_guild['name']}**!\n"
                f"+75 Guild XP awarded to the defenders."
            )
        embed = discord.Embed(title=title, description=desc, color=color)
        a = guilds.get(my_gid, my_guild)
        d = guilds.get(target_gid, target_guild)
        embed.add_field(name=my_guild["name"],    value=f"Lv {a.get('level',1)} · {len(a.get('members',[]))} members", inline=True)
        embed.add_field(name=target_guild["name"], value=f"Lv {d.get('level',1)} · {len(d.get('members',[]))} members", inline=True)
        await ctx.send(embed=embed)
        for m in lvl_msgs:
            await ctx.send(m)

    # ================================================================== #
    #  WORLD DUNGEON COMMANDS
    # ================================================================== #

    # ------------------------------------------------------------------ #
    #  !spawnworld
    # ------------------------------------------------------------------ #
    @commands.command(name="spawnworld", brief="[Admin] Spawn a World Dungeon event")
    @commands.has_permissions(administrator=True)
    async def spawn_world(self, ctx: commands.Context, *, boss_name: str = None):
        """
        [Admin] Spawn a server-wide World Dungeon boss event.
        Optionally specify the boss: Ancient Terror, Abyssal Wyrm, Void Colossus.
        Players join with `!joinworld`, then use `!startworld` to begin.
        """
        wd = get_world_dungeon()
        if wd["active"]:
            await ctx.send(
                "❌ A World Dungeon is already active! "
                "Use `!worldstatus` to check, or wait for it to end."
            )
            return

        # Match boss name if provided
        matched_key = None
        if boss_name:
            boss_name_lower = boss_name.strip().lower()
            for key in WORLD_BOSS_CONFIGS:
                if key.lower().startswith(boss_name_lower) or boss_name_lower in key.lower():
                    matched_key = key
                    break
            if not matched_key:
                options = " | ".join(WORLD_BOSS_CONFIGS.keys())
                await ctx.send(f"❌ Unknown boss. Choose: `{options}` (or omit for random).")
                return

        state = spawn_world_dungeon(matched_key)
        cfg   = WORLD_BOSS_CONFIGS[state["boss_key"]]

        boss_intro = cfg.get("boss_intro", cfg.get("description", ""))
        embed = discord.Embed(
            title=f"🌍 WORLD DUNGEON OPENS — {cfg['emoji']} {state['boss_key']}",
            description=(
                f"*{boss_intro}*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 Type `!joinworld` to enlist in the battle.\n"
                f"⚔️ Once ready, an admin uses `!startworld` to begin.\n"
                f"📊 Check status at any time with `!worldstatus`."
            ),
            color=0xED4245,
        )
        embed.add_field(
            name="Boss HP",
            value=f"{cfg['base_hp']:,} + {cfg['hp_per_player']:,}/player",
            inline=True,
        )
        embed.add_field(name="XP Reward",   value=f"Up to {cfg['xp_reward']:,}",     inline=True)
        embed.add_field(name="Copper",      value=f"Up to {cfg['copper_reward']:,}c", inline=True)
        embed.set_footer(text="Rewards scale with your damage contribution. MVP gets the best drops!")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !joinworld
    # ------------------------------------------------------------------ #
    @commands.command(name="joinworld", brief="Join the active World Dungeon")
    async def join_world(self, ctx: commands.Context):
        """Join the current World Dungeon event before the fight starts."""
        uid    = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return
        if uid in ACTIVE_COMBATS or uid in ACTIVE_DUNGEONS or uid in ACTIVE_RIFTS or uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("⚠️ Finish your current activity first!")
            return

        success, msg = join_world_dungeon(uid, ctx.author.display_name)
        await ctx.send(msg)

    # ------------------------------------------------------------------ #
    #  !startworld
    # ------------------------------------------------------------------ #
    @commands.command(name="startworld", brief="[Admin] Begin the World Dungeon fight")
    @commands.has_permissions(administrator=True)
    async def start_world(self, ctx: commands.Context):
        """[Admin] Close the join window and scale the boss to player count, then open the fight."""
        wd = get_world_dungeon()
        if not wd["active"]:
            await ctx.send("❌ No World Dungeon is active. Use `!spawnworld` first.")
            return
        if wd["phase"] != "joining":
            await ctx.send("❌ The World Dungeon is not in the joining phase.")
            return
        if not wd["players"]:
            await ctx.send("❌ At least one player must join before starting!")
            return

        start_world_fight()
        wd = get_world_dungeon()
        cfg = WORLD_BOSS_CONFIGS[wd["boss_key"]]
        player_count = len(wd["players"])
        names = ", ".join(p["name"] for p in wd["players"].values())

        embed = discord.Embed(
            title=f"⚔️ THE BATTLE BEGINS — {cfg['emoji']} {wd['boss_key']}",
            description=(
                f"**{player_count} hunter{'s' if player_count != 1 else ''} answer the call!**\n"
                f"*{names}*\n\n"
                f"*\"The ground trembles as the World Boss awakens...\"*\n"
                f"*\"Players unite against the ancient terror!\"*\n\n"
                f"{cfg['emoji']} **{wd['boss_key']}** awakens with **{wd['boss_hp']:,} HP**!\n\n"
                f"⚔️ Use `!worldattack` to strike (30s cooldown per player).\n"
                f"💢 The boss retaliates after every hit — stay alive!\n"
                f"🌋 Every **{cfg['aoe_every']}** attacks triggers an area attack on all heroes."
            ),
            color=0xE74C3C,
        )
        embed.add_field(name="Boss HP",  value=f"{wd['boss_hp']:,}", inline=True)
        embed.add_field(name="Boss ATK", value=str(wd["boss_attack"]), inline=True)
        embed.add_field(name="Boss DEF", value=str(wd["boss_defense"]), inline=True)
        embed.set_footer(text="Damage % determines reward quality. Fight well, Hunters!")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !worldattack
    # ------------------------------------------------------------------ #
    @commands.command(name="worldattack", aliases=["wattack", "wa"], brief="Attack the World Boss")
    async def world_attack(self, ctx: commands.Context):
        """Strike the World Boss. 30-second cooldown. Boss retaliates every hit."""
        uid    = ctx.author.id
        player = ensure_player(uid)
        if not player:
            await ctx.send("Use `!start` first!")
            return

        wd = get_world_dungeon()
        if not wd["active"]:
            await ctx.send("❌ No World Dungeon is currently active.")
            return
        if wd["phase"] != "fighting":
            phase_hint = (
                "Use `!joinworld` to register."
                if wd["phase"] == "joining"
                else "The event has ended."
            )
            await ctx.send(f"❌ The boss fight hasn't started yet! {phase_hint}")
            return
        if uid not in wd["players"]:
            await ctx.send(
                "❌ You didn't join before the fight began! "
                "Watch for the next World Dungeon event with `!worldstatus`."
            )
            return
        if uid in ACTIVE_COMBATS or uid in ACTIVE_DUNGEONS or uid in ACTIVE_RIFTS or uid in ACTIVE_RAND_DUNGEONS:
            await ctx.send("⚠️ Finish your current combat first!")
            return

        boss_hp, msgs, boss_dead, aoe_hits = world_boss_attack(uid, player)
        save_game(uid, player)

        # Apply AoE damage to all other joined players
        if aoe_hits:
            for target_uid, aoe_dmg in aoe_hits:
                if target_uid == uid:
                    continue  # attacker already handled in world_boss_attack
                target_p = ensure_player(target_uid)
                if target_p:
                    target_p["hp"] = max(0, target_p["hp"] - aoe_dmg)
                    save_game(target_uid, target_p)

        for m in msgs:
            await ctx.send(m)

        if not boss_dead:
            return

        # ── Boss defeated ─────────────────────────────────────────────
        cfg     = WORLD_BOSS_CONFIGS[wd["boss_key"]]
        rewards = distribute_world_rewards(wd["boss_key"])

        sorted_r = sorted(rewards, key=lambda x: x[1]["damage"], reverse=True)
        mvp_uid  = sorted_r[0][0] if sorted_r else None

        award_lines: list[str] = []
        for r_uid, r in sorted_r:
            p = ensure_player(r_uid)
            if not p:
                continue
            xp_msgs = add_experience(p, r["xp"])
            add_currency(p, r["copper"])
            if r["drop"]:
                add_to_inventory(p, r["drop"])
            save_game(r_uid, p)
            mvp_tag = " 👑 **MVP!**" if r_uid == mvp_uid else ""
            drop_tag = f" · 🎁 **{r['drop']}**" if r["drop"] else ""
            award_lines.append(
                f"• <@{r_uid}> — **{r['damage']:,} dmg** ({r['pct']*100:.0f}%) "
                f"· +{r['xp']:,} XP · +{r['copper']:,}c{drop_tag}{mvp_tag}"
            )

        victory_lore = cfg.get("victory_msg", "The realm is saved! Hunters stand victorious!")
        embed = discord.Embed(
            title=f"💀 {cfg['emoji']} {wd['boss_key']} HAS FALLEN!",
            description=(
                f"*{victory_lore}*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**🏆 Final Damage Leaderboard:**\n"
                + "\n".join(award_lines)
            ),
            color=0x57F287,
        )
        embed.set_footer(text="Rewards distributed based on damage contribution. Well fought, Hunters.")
        await ctx.send(embed=embed)
        clear_world_dungeon()

    # ------------------------------------------------------------------ #
    #  !worldstatus
    # ------------------------------------------------------------------ #
    @commands.command(name="worldstatus", aliases=["wstatus", "ws"], brief="Check World Dungeon status")
    async def world_status(self, ctx: commands.Context):
        """Show the current World Dungeon boss HP, phase, and damage leaderboard."""
        lines = world_dungeon_status_lines()
        wd    = get_world_dungeon()
        color = 0xED4245 if wd["active"] else 0x99AAB5
        embed = discord.Embed(
            title="🌍 World Dungeon Status",
            description="\n".join(lines),
            color=color,
        )
        if wd["active"] and wd["phase"] == "joining":
            embed.set_footer(text="Join with !joinworld · Admin starts with !startworld")
        elif wd["active"] and wd["phase"] == "fighting":
            embed.set_footer(text="Attack with !worldattack (30s cooldown)")
        await ctx.send(embed=embed)

    # ------------------------------------------------------------------ #
    #  !help
    # ------------------------------------------------------------------ #
    @commands.command(name="help", brief="Show all commands")
    async def help_cmd(self, ctx: commands.Context):
        embed = discord.Embed(title="⚔️ RPG Bot — Commands", description="Prefix: `!`", color=0x5865F2)
        groups = {
            "Getting Started": [
                "`!start` — Begin/resume your adventure",
                "`!save` / `!load` — Save or load progress",
                "`!choose_class` — Pick from 10 classes at Level 10",
                "`!skill` — View your active skill (upgrades at Lv 20 & 30)",
                "`!characters` — List all your character slots",
                "`!newchar <name>` — Create a new character slot",
                "`!switchchar <name>` — Switch active character",
                "`!deletechar <name>` — Delete a character slot",
            ],
            "Exploration": [
                "`!stats` — Full character sheet",
                "`!map` — World map",
                "`!location` — Current area info",
                "`!travel <loc>` — Travel (40% encounter chance)",
                "`!explore` — Explore current area (40% encounter chance)",
                "`!rest` — Recover HP (advances time)",
            ],
            "Combat": [
                "`!fight` — Start an encounter",
                "During combat: `attack` · `flee` · `use <item>` · `skill`",
                "`!pvp @user` — Challenge another player",
            ],
            "Inventory & Gear": [
                "`!inventory` — View items",
                "`!equip <item>` — Equip weapon · armor · accessory",
                "`!unequip <slot>` — Unequip `weapon` · `armor` · `accessory`",
                "`!use <item>` — Use a consumable",
            ],
            "Shop": [
                "`!shop` — Browse (Aetherfall only)",
                "`!buy <item>` / `!sell <item>` — Buy or sell",
            ],
            "Guilds": [
                "`!guilds` — List all guilds",
                "`!guild_create <name> [desc]` — Found a new guild",
                "`!guild_join <name>` — Join an existing guild",
                "`!guild_leave` — Leave your guild",
                "`!guild_info [name]` — View guild details",
                "`!guild_members` — View your guild's roster",
                "`!guild_refresh` — Re-apply guild stat bonuses",
                "`!guild_war <name>` — Challenge a guild to war",
            ],
            "Quests & Events": [
                "`!quests` — Quest log",
                "`!demonking` — *[Admin]* Start server-wide Demon King event",
                "`!spawnworld [boss]` — *[Admin]* Spawn a World Dungeon boss",
                "`!joinworld` — Join the World Dungeon before it starts",
                "`!startworld` — *[Admin]* Begin the World Dungeon fight",
                "`!worldattack` — Strike the World Boss (30s cooldown)",
                "`!worldstatus` — Check boss HP and damage leaderboard",
            ],
        }
        for section, lines in groups.items():
            embed.add_field(name=section, value="\n".join(lines), inline=False)
        embed.set_footer(text="Good luck, Hunter.")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RPG(bot))
