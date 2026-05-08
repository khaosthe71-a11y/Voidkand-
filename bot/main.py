import discord
from discord.ext import commands
import os
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

COGS = [
    "bot.cogs.rpg",
]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing, name="an RPG | !start"
        )
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`. Use `!help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument. Use `!help` for usage.")
    else:
        logger.error(f"Error in '{ctx.command}': {error}")


async def load_cogs():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)


async def main():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")
    async with bot:
        await load_cogs()
        await bot.start(token)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
