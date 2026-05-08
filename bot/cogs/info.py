import discord
from discord.ext import commands
from discord import app_commands
from datetime import timezone


def format_dt(dt) -> str:
    if dt is None:
        return "Unknown"
    dt_utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return discord.utils.format_dt(dt_utc, style="F")


class Info(commands.Cog, name="Info"):
    """Information commands about users and servers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="Show information about this server")
    @app_commands.guild_only()
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(
            title=guild.name,
            description=guild.description or "",
            color=discord.Color.blurple(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Emojis", value=str(len(guild.emojis)), inline=True)
        embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="Created", value=format_dt(guild.created_at), inline=False)
        embed.set_footer(text=f"Server ID: {guild.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show information about a user")
    @app_commands.describe(member="The member to look up (defaults to yourself)")
    @app_commands.guild_only()
    async def user_info(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        roles = [r.mention for r in member.roles if r != interaction.guild.default_role]
        embed = discord.Embed(
            title=str(member),
            color=member.color if member.color != discord.Color.default() else discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Display Name", value=member.display_name, inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Account Created", value=format_dt(member.created_at), inline=False)
        if member.joined_at:
            embed.add_field(name="Joined Server", value=format_dt(member.joined_at), inline=False)
        if roles:
            embed.add_field(
                name=f"Roles ({len(roles)})",
                value=" ".join(roles[:20]) + (" ..." if len(roles) > 20 else ""),
                inline=False,
            )
        embed.set_footer(text=f"User ID: {member.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Show a user's full-size avatar")
    @app_commands.describe(member="The member whose avatar to show (defaults to yourself)")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=discord.Color.blurple())
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
