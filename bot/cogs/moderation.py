import discord
from discord.ext import commands
from discord import app_commands
import datetime


class Moderation(commands.Cog, name="Moderation"):
    """Moderation commands for managing your server."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member == interaction.user:
            await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("You cannot kick someone with an equal or higher role.", ephemeral=True)
            return
        try:
            await member.send(f"You have been kicked from **{interaction.guild.name}**. Reason: {reason}")
        except discord.Forbidden:
            pass
        await member.kick(reason=f"{interaction.user}: {reason}")
        embed = discord.Embed(title="Member Kicked", color=discord.Color.orange())
        embed.add_field(name="Member", value=str(member), inline=True)
        embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member == interaction.user:
            await interaction.response.send_message("You cannot ban yourself.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("You cannot ban someone with an equal or higher role.", ephemeral=True)
            return
        try:
            await member.send(f"You have been banned from **{interaction.guild.name}**. Reason: {reason}")
        except discord.Forbidden:
            pass
        await member.ban(reason=f"{interaction.user}: {reason}")
        embed = discord.Embed(title="Member Banned", color=discord.Color.red())
        embed.add_field(name="Member", value=str(member), inline=True)
        embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unban", description="Unban a user by their Discord ID")
    @app_commands.describe(user_id="The Discord user ID to unban")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            uid = int(user_id.strip())
        except ValueError:
            await interaction.response.send_message("Please provide a valid user ID (numbers only).", ephemeral=True)
            return
        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user)
            embed = discord.Embed(title="User Unbanned", color=discord.Color.green())
            embed.add_field(name="User", value=str(user), inline=True)
            embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message("That user is not banned or does not exist.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to unban users.", ephemeral=True)

    @app_commands.command(name="purge", description="Delete a number of messages from this channel")
    @app_commands.describe(amount="Number of messages to delete (1–100)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if not 1 <= amount <= 100:
            await interaction.response.send_message("Please provide a number between 1 and 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} message(s).", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set the slowmode delay for this channel")
    @app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int = 0):
        if not 0 <= seconds <= 21600:
            await interaction.response.send_message("Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("Slowmode disabled.")
        else:
            await interaction.response.send_message(f"Slowmode set to {seconds} second(s).")

    @app_commands.command(name="mute", description="Timeout (mute) a member for a set number of minutes")
    @app_commands.describe(member="The member to timeout", minutes="Duration in minutes (1–40320)", reason="Reason for the timeout")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
        if not 1 <= minutes <= 40320:
            await interaction.response.send_message("Duration must be between 1 and 40320 minutes.", ephemeral=True)
            return
        if member == interaction.user:
            await interaction.response.send_message("You cannot mute yourself.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("You cannot mute someone with an equal or higher role.", ephemeral=True)
            return
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{interaction.user}: {reason}")
        embed = discord.Embed(title="Member Timed Out", color=discord.Color.dark_orange())
        embed.add_field(name="Member", value=str(member), inline=True)
        embed.add_field(name="Duration", value=f"{minutes} minute(s)", inline=True)
        embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Remove a member's timeout")
    @app_commands.describe(member="The member to remove the timeout from")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        embed = discord.Embed(title="Timeout Removed", color=discord.Color.green())
        embed.add_field(name="Member", value=str(member), inline=True)
        embed.add_field(name="Moderator", value=str(interaction.user), inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
