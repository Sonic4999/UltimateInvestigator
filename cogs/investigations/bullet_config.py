import importlib
import typing

import discord
from discord.ext import commands

import common.models as models
import common.utils as utils


class BulletConfigCMDs(commands.Cog, name="Bullet Config"):
    """Commands for using and modifying Truth Bullet server settings."""

    def __init__(self, bot):
        self.bot = bot

    def truth_bullet_managers(self, bullet_config: models.BulletConfig):
        role_str_builder = []
        if bullet_config.bullet_default_perms_check:
            role_str_builder.append("Members with `Manage Server` permissions")

        for role_id in bullet_config.bullet_custom_perm_roles:
            role_str_builder.append(f"<@&{role_id}>")

        return f"Can Manage Truth Bullets: {', '.join(role_str_builder)}"

    @commands.command(aliases=["bull_config", "bullconfig"])
    @utils.bullet_proper_perms()
    async def bullet_config(self, ctx: commands.Context):
        """Lists out the Truth Bullet configuration settings for the server.
        Requires being able to Manage Truth Bullets."""
        # sourcery skip: merge-list-append
        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)

            str_builder = []
            str_builder.append(
                f"Truth Bullets: {utils.toggle_friendly_str(bullet_config.bullets_enabled)}"
            )
            str_builder.append(
                f"Truth Bullet channel: {f'<#{bullet_config.bullet_chan_id}>' if bullet_config.bullet_chan_id > 0 else 'None'}"
            )
            str_builder.append("")
            str_builder.append(
                f"Player role: {f'<@&{bullet_config.guild.player_role}>' if bullet_config.guild.player_role > 0 else 'None'}"
            )
            str_builder.append(
                f"Best Detective role: {f'<@&{bullet_config.ult_detective_role}>' if bullet_config.ult_detective_role > 0 else 'None'}"
            )

            str_builder.append(self.truth_bullet_managers(bullet_config))

            embed = discord.Embed(
                title=f"Server config for {ctx.guild.name}",
                description="\n".join(str_builder),
                color=self.bot.color,
            )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["set_bull_chan", "set_bullets_channel"])
    @utils.bullet_proper_perms()
    async def set_bullet_channel(
        self, ctx: commands.Context, channel: utils.ValidChannelConverter
    ):
        """Sets where all Truth Bullets are sent to (alongside the channel they were found in).
        The channel could be its mention, its ID, or its name.
        Requires being able to Manage Truth Bullets."""
        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)
            bullet_config.bullet_chan_id = channel.id
            await bullet_config.save()

        await ctx.reply(f"Truth Bullet channel set to {channel.mention}!")

    class CheckForNone(commands.Converter):
        async def convert(self, ctx: commands.Context, argument: str):
            if argument.lower() == "none":
                return discord.Object(
                    0
                )  # little hack so we don't have to do as much instance checking
            raise commands.BadArgument("Not 'none'!")

    @commands.command(
        aliases=[
            "set_ult_detect_role",
            "set_ult_detective_role",
            "set_ult_detect",
            "set_ult_detective",
            "set_ultimate_detective_role",
            "set_best_detect_role",
            "set_best_detect",
        ]
    )
    @utils.bullet_proper_perms()
    async def set_best_detective_role(
        self, ctx: commands.Context, role: typing.Union[discord.Role, CheckForNone]
    ):
        """Sets (or unsets) the Best Detective role.
        The 'Best Detective' is the person who found the most Truth Bullets during an investigation.
        Either specify a role (mention/ID/name in quotes) to set it, or 'none' to unset it.
        The role must be one the bot can edit.
        Requires being able to Manage Truth Bullets."""

        # we do this because union error messages are vague and wouldn't work
        if isinstance(role, discord.Role):
            utils.role_check(ctx, role)

        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)
            bullet_config.ult_detective_role = role.id
            await bullet_config.save()

        if isinstance(role, discord.Role):
            await ctx.reply(
                f"Best Detective role set to {role.mention}!",
                allowed_mentions=utils.deny_mentions(ctx.author),
            )
        else:
            await ctx.reply("Best Detective role unset!")

    @commands.command()
    @utils.bullet_proper_perms()
    async def set_player_role(self, ctx: commands.Context, role: discord.Role):
        """Sets the Player role.
        The Player role can actually find the Truth Bullets themself.
        The role could be its mention, its ID, or its name in quotes.
        Requires being able to Manage Truth Bullets."""

        async with ctx.typing():
            guild_config = await utils.get_or_create_guild_config(ctx.guild.id)
            guild_config.player_role = role.id
            await guild_config.save()

        await ctx.reply(
            f"Player role set to {role.mention}!",
            allowed_mentions=utils.deny_mentions(ctx.author),
        )

    def enable_check(self, config: models.Config):
        if config.player_role <= 0:
            raise utils.CustomCheckFailure(
                "You still need to set the Player role for this server!"
            )
        elif config.bullet_chan_id <= 0:
            raise utils.CustomCheckFailure(
                "You still need to set a Truth Bullets channel!"
            )

    @commands.command(aliases=["toggle_bullet"])
    @utils.bullet_proper_perms()
    async def toggle_bullets(self, ctx: commands.Context):
        """Turns on or off the Truth Bullets, depending on what it was earlier.
        It will turn the Truth Bullets off if they're on, or on if they're off.
        To turn on Truth Bullets, you need to set the Player role and the Truth Bullets channel.
        Requires being able to Manage Truth Bullets."""
        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)

            if (
                not bullet_config.bullets_enabled
            ):  # if truth bullets will be enabled by this
                self.enable_check(bullet_config)
            bullet_config.bullets_enabled = not bullet_config.bullets_enabled
            await bullet_config.save()

        await ctx.reply(
            f"Truth Bullets turned {utils.toggle_friendly_str(bullet_config.bullets_enabled)}!"
        )

    @commands.command(aliases=["enable_bullet"])
    @utils.bullet_proper_perms()
    async def enable_bullets(self, ctx: commands.Context):
        """Turns on the Truth Bullets.
        Kept around to match up with the old YAGPDB system.
        To turn on Truth Bullets, you need to set the Player role and the Truth Bullets channel.
        Requires being able to Manage Truth Bullets."""
        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)

            self.enable_check(bullet_config)
            bullet_config.bullets_enabled = True
            await bullet_config.save()

        await ctx.reply("Truth Bullets enabled!")

    @commands.command(aliases=["disable_bullet"])
    @utils.bullet_proper_perms()
    async def disable_bullets(self, ctx: commands.Context):
        """Turns off the Truth Bullets.
        Kept around to match up with the old YAGPDB system.
        This is automatically done after all Truth Bullets have been found.
        Requires being able to Manage Truth Bullets."""
        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)
            bullet_config.bullets_enabled = False
            await bullet_config.save()

        await ctx.reply("Truth Bullets disabled!")

    @commands.group(
        aliases=["bull_perms", "bullet_perms", "bull_perm", "bullet_perm"],
        invoke_without_command=True,
        ignore_extra=False,
    )
    @utils.proper_permissions()
    async def bullet_permissions(self, ctx: commands.Context):
        """The base command for determining who can Manage Truth Bullets.
        Use the help command on this in order to see your options.
        All commands here require Manage Guild permissions."""

        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)

        await ctx.reply(
            self.truth_bullet_managers(bullet_config),
            allowed_mentions=utils.deny_mentions(ctx.author),
        )

    @bullet_permissions.command()
    @utils.proper_permissions()
    async def default(self, ctx: commands.Context, toggle: bool):
        """Allows you to toggle if people with Manage Guild permissions can Manage Truth Bullets.
        Technically pointless as someone with Manage Guild perms could just toggle this back on, \
        but this will be useful later.
        Requires Manage Guild permissions."""

        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)
            bullet_config.bullet_default_perms_check = toggle
            await bullet_config.save()

        toggle_str = "can" if toggle else "cannot"
        await ctx.reply(
            f"People with Manage Server permissions now {toggle_str} use Truth Bullet commands."
        )

    @bullet_permissions.command()
    @utils.proper_permissions()
    async def add(self, ctx: commands.Context, role: discord.Role):
        """Adds a role to the roles that can Manage Truth Bullets.
        Requires Manage Guild permissions."""

        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)

            if role.id in bullet_config.bullet_custom_perm_roles:
                raise commands.BadArgument(
                    "This role is already allowed to Manage Truth Bullets!"
                )

            bullet_config.bullet_custom_perm_roles.add(role.id)
            await bullet_config.save()

        await ctx.reply(
            f"{role.mention} can now Manage Truth Bullets.",
            allowed_mentions=utils.deny_mentions(ctx.author),
        )

    @bullet_permissions.command()
    @utils.proper_permissions()
    async def remove(self, ctx: commands.Context, role: discord.Role):
        """Removes a role from the roles that can Manage Truth Bullets.
        Requires Manage Guild permissions."""

        async with ctx.typing():
            bullet_config = await utils.get_or_create_bullet_config(ctx.guild.id)

            try:
                bullet_config.bullet_custom_perm_roles.remove(role.id)
                await bullet_config.save()
            except KeyError:
                raise commands.BadArgument(
                    "This role is already not allowed to Manage Truth Bullets!"
                )

        await ctx.reply(
            f"{role.mention} can no longer Manage Truth Bullets.",
            allowed_mentions=utils.deny_mentions(ctx.author),
        )


def setup(bot):
    importlib.reload(utils)
    bot.add_cog(BulletConfigCMDs(bot))
