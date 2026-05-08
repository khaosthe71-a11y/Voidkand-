import discord
from discord.ext import commands
from discord import app_commands
import random


COIN_SIDES = ["Heads", "Tails"]

MAGIC_8_BALL_RESPONSES = [
    "It is certain.",
    "It is decidedly so.",
    "Without a doubt.",
    "Yes, definitely.",
    "You may rely on it.",
    "As I see it, yes.",
    "Most likely.",
    "Outlook good.",
    "Yes.",
    "Signs point to yes.",
    "Reply hazy, try again.",
    "Ask again later.",
    "Better not tell you now.",
    "Cannot predict now.",
    "Concentrate and ask again.",
    "Don't count on it.",
    "My reply is no.",
    "My sources say no.",
    "Outlook not so good.",
    "Very doubtful.",
]

RPS_CHOICES = ["rock", "paper", "scissors"]
RPS_WINS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}


class Fun(commands.Cog, name="Fun"):
    """Fun and game commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll dice using NdN format (e.g. 2d6, 1d20)")
    @app_commands.describe(dice="Dice expression like 2d6 or 1d20 (default: 1d6)")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        try:
            parts = dice.lower().split("d")
            if len(parts) != 2:
                raise ValueError
            num_dice = int(parts[0]) if parts[0] else 1
            sides = int(parts[1])
            if not (1 <= num_dice <= 100 and 2 <= sides <= 1000):
                raise ValueError
        except (ValueError, IndexError):
            await interaction.response.send_message(
                "Invalid format. Use `NdN` like `2d6` or `1d20`.", ephemeral=True
            )
            return

        rolls = [random.randint(1, sides) for _ in range(num_dice)]
        total = sum(rolls)
        embed = discord.Embed(title=f"Dice Roll — {dice}", color=discord.Color.orange())
        if num_dice > 1:
            embed.add_field(name="Rolls", value=", ".join(str(r) for r in rolls), inline=False)
        embed.add_field(name="Total", value=f"**{total}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="flip", description="Flip a coin")
    async def flip(self, interaction: discord.Interaction):
        result = random.choice(COIN_SIDES)
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"**{result}!**",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a yes/no question")
    @app_commands.describe(question="Your yes/no question")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        response = random.choice(MAGIC_8_BALL_RESPONSES)
        embed = discord.Embed(title="Magic 8-Ball 🎱", color=discord.Color.dark_purple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="choose", description="Randomly choose between comma-separated options")
    @app_commands.describe(options="Options separated by commas (e.g. pizza, tacos, sushi)")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [o.strip() for o in options.split(",") if o.strip()]
        if len(choices) < 2:
            await interaction.response.send_message(
                "Please provide at least 2 options separated by commas.", ephemeral=True
            )
            return
        chosen = random.choice(choices)
        embed = discord.Embed(
            title="Random Choice",
            description=f"I choose: **{chosen}**",
            color=discord.Color.teal(),
        )
        embed.set_footer(text=f"From {len(choices)} options")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Play rock, paper, scissors against the bot")
    @app_commands.describe(choice="Your choice: rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock 🪨", value="rock"),
        app_commands.Choice(name="Paper 📄", value="paper"),
        app_commands.Choice(name="Scissors ✂️", value="scissors"),
    ])
    async def rps(self, interaction: discord.Interaction, choice: str):
        bot_choice = random.choice(RPS_CHOICES)
        if choice == bot_choice:
            result = "It's a tie!"
            color = discord.Color.yellow()
        elif RPS_WINS[choice] == bot_choice:
            result = "You win!"
            color = discord.Color.green()
        else:
            result = "You lose!"
            color = discord.Color.red()
        embed = discord.Embed(title="Rock, Paper, Scissors", color=color)
        embed.add_field(name="You", value=f"{RPS_EMOJI[choice]} {choice.capitalize()}", inline=True)
        embed.add_field(name="Bot", value=f"{RPS_EMOJI[bot_choice]} {bot_choice.capitalize()}", inline=True)
        embed.add_field(name="Result", value=f"**{result}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="random", description="Generate a random number between two values")
    @app_commands.describe(minimum="Lower bound (default: 1)", maximum="Upper bound (default: 100)")
    async def random_number(self, interaction: discord.Interaction, minimum: int = 1, maximum: int = 100):
        if minimum >= maximum:
            await interaction.response.send_message(
                "The minimum must be less than the maximum.", ephemeral=True
            )
            return
        result = random.randint(minimum, maximum)
        embed = discord.Embed(
            title="Random Number",
            description=f"**{result}**",
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Range: {minimum} – {maximum}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
