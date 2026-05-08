import discord
from discord.ext import commands
from discord import app_commands
import time


class General(commands.Cog, name="General"):
    """General utility commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blurple(),
        )
        sections = {
            "General": [
                "`/help` — Show this help message",
                "`/ping` — Check bot latency",
                "`/invite` — Get the bot invite link",
                "`/botinfo` — Show bot information",
            ],
            "Fun": [
                "`/roll [dice]` — Roll dice (e.g. 2d6)",
                "`/flip` — Flip a coin",
                "`/8ball <question>` — Ask the magic 8-ball",
                "`/choose <options>` — Choose between comma-separated options",
                "`/rps <choice>` — Rock, paper, scissors",
                "`/random [min] [max]` — Random number in a range",
            ],
            "Info": [
                "`/serverinfo` — Show server information",
                "`/userinfo [@user]` — Show user information",
                "`/avatar [@user]` — Show a user's avatar",
            ],
            "Moderation": [
                "`/purge <amount>` — Delete messages (requires Manage Messages)",
                "`/slowmode [seconds]` — Set channel slowmode (requires Manage Channels)",
                "`/kick <user> [reason]` — Kick a member (requires Kick Members)",
                "`/ban <user> [reason]` — Ban a member (requires Ban Members)",
                "`/unban <user_id>` — Unban a user (requires Ban Members)",
                "`/mute <user> [minutes] [reason]` — Timeout a member (requires Moderate Members)",
                "`/unmute <user>` — Remove timeout (requires Moderate Members)",
            ],
        }
        for name, cmds in sections.items():
            embed.add_field(name=name, value="\n".join(cmds), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        ws_latency = self.bot.latency * 1000
        start = time.perf_counter()
        await interaction.response.defer()
        end = time.perf_counter()
        roundtrip = (end - start) * 1000
        embed = discord.Embed(title="Pong!", color=discord.Color.green())
        embed.add_field(name="Roundtrip", value=f"`{roundtrip:.1f} ms`", inline=True)
        embed.add_field(name="WebSocket", value=f"`{ws_latency:.1f} ms`", inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="invite", description="Get a link to invite this bot")
    async def invite(self, interaction: discord.Interaction):
        permissions = discord.Permissions(
            send_messages=True,
            read_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            add_reactions=True,
            manage_messages=True,
            moderate_members=True,
            kick_members=True,
            ban_members=True,
        )
        url = discord.utils.oauth_url(self.bot.user.id, permissions=permissions)
        embed = discord.Embed(
            title="Invite Me!",
            description=f"[Click here to invite me to your server]({url})",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="botinfo", description="Show information about this bot")
    async def botinfo(self, interaction: discord.Interaction):
        app = await self.bot.application_info()
        embed = discord.Embed(
            title=str(self.bot.user),
            description=app.description or "A general-purpose Discord bot.",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Owner", value=str(app.owner), inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Commands", value=str(len(self.bot.tree.get_commands())), inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.1f} ms", inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.set_footer(text=f"Bot ID: {self.bot.user.id}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
