#!/usr/bin/env python3.8
import collections
import functools
import logging
import traceback
import typing
from pathlib import Path

import aiohttp
import interactions as ipy
import tansy
from interactions.ext import prefixed_commands as prefixed

import common.models as models


@functools.wraps(tansy.slash_command)
def manage_guild_slash_cmd(
    name: str,
    description: ipy.Absent[str] = ipy.MISSING,
):
    return tansy.slash_command(
        name=name,
        description=description,
        default_member_permissions=ipy.Permissions.MANAGE_GUILD,
    )


def error_embed_generate(error_msg: str):
    return ipy.Embed(color=ipy.RoleColors.RED, description=error_msg)


async def error_handle(
    bot: ipy.Client, error: Exception, ctx: ipy.BaseContext | None = None
):
    # handles errors and sends them to owner
    if isinstance(error, aiohttp.ServerDisconnectedError):
        to_send = "Disconnected from server!"
    else:
        error_str = error_format(error)
        logging.getLogger("uibot").error(error_str)

        chunks = line_split(error_str, split_by=40)
        for i in range(len(chunks)):
            chunks[i][0] = f"```py\n{chunks[i][0]}"
            chunks[i][-1] += "\n```"

        final_chunks: list[str | ipy.Embed] = [
            error_embed_generate("\n".join(chunk)) for chunk in chunks
        ]
        if ctx and hasattr(ctx, "message") and hasattr(ctx.message, "jump_url"):
            final_chunks.insert(0, f"Error on: {ctx.message.jump_url}")

        to_send = final_chunks

    await msg_to_owner(bot, to_send)

    if ctx and hasattr(ctx, "send"):
        if isinstance(ctx, prefixed.PrefixedContext):
            await ctx.reply(
                "An internal error has occured. The bot owner has been notified."
            )
        elif isinstance(ctx, ipy.InteractionContext):
            await ctx.send(
                content=(
                    "An internal error has occured. The bot owner has been notified."
                ),
                ephemeral=True,
            )
        else:
            await ctx.send(
                "An internal error has occured. The bot owner has been notified."
            )


async def msg_to_owner(
    bot: "UIBase",
    chunks: list[str] | list[ipy.Embed] | list[str | ipy.Embed] | str | ipy.Embed,
):
    if not isinstance(chunks, list):
        chunks = [chunks]

    # sends a message to the owner
    for chunk in chunks:
        if isinstance(chunk, ipy.Embed):
            await bot.owner.send(embeds=chunk)
        else:
            await bot.owner.send(chunk)


def line_split(content: str, split_by=20):
    content_split = content.splitlines()
    return [
        content_split[x : x + split_by] for x in range(0, len(content_split), split_by)
    ]


def embed_check(embed: ipy.Embed) -> bool:
    """
    Checks if an embed is valid, as per Discord's guidelines.
    See https://discord.com/developers/docs/resources/channel#embed-limits for details.
    """
    if len(embed) > 6000:
        return False

    if embed.title and len(embed.title) > 256:
        return False
    if embed.description and len(embed.description) > 4096:
        return False
    if embed.author and embed.author.name and len(embed.author.name) > 256:
        return False
    if embed.footer and embed.footer.text and len(embed.footer.text) > 2048:
        return False
    if embed.fields:
        if len(embed.fields) > 25:
            return False
        for field in embed.fields:
            if field.name and len(field.name) > 1024:
                return False
            if field.value and len(field.value) > 2048:
                return False

    return True


def deny_mentions(user):
    # generates an AllowedMentions object that only pings the user specified
    return ipy.AllowedMentions(users=[user])


def error_format(error: Exception):
    # simple function that formats an exception
    return "".join(
        traceback.format_exception(  # type: ignore
            type(error), value=error, tb=error.__traceback__
        )
    )


def string_split(string):
    # simple function that splits a string into 1950-character parts
    return [string[i : i + 1950] for i in range(0, len(string), 1950)]


def file_to_ext(str_path, base_path):
    # changes a file to an import-like string
    str_path = str_path.replace(base_path, "")
    str_path = str_path.replace("/", ".")
    return str_path.replace(".py", "")


def get_all_extensions(str_path, folder="exts"):
    # gets all extensions in a folder
    ext_files = collections.deque()
    loc_split = str_path.split(folder)
    base_path = loc_split[0]

    if base_path == str_path:
        base_path = base_path.replace("main.py", "")
    base_path = base_path.replace("\\", "/")

    if base_path[-1] != "/":
        base_path += "/"

    pathlist = Path(f"{base_path}/{folder}").glob("**/*.py")
    for path in pathlist:
        str_path = str(path.as_posix())
        str_path = file_to_ext(str_path, base_path)

        if str_path != "exts.db_handler":
            ext_files.append(str_path)

    return ext_files


def toggle_friendly_str(bool_to_convert):
    return "on" if bool_to_convert == True else "off"


def yesno_friendly_str(bool_to_convert):
    return "yes" if bool_to_convert == True else "no"


def role_check(ctx: ipy.BaseContext, role: ipy.Role):
    top_role = ctx.guild.me.top_role

    if role > top_role:
        raise CustomCheckFailure(
            "The role provided is a role that is higher than the roles I can edit. "
            + "Please move either that role or my role so that "
            + "my role is higher than the role you want to use."
        )

    return role


class ValidRoleConverter(ipy.Converter):
    async def convert(self, context: ipy.InteractionContext, argument: ipy.Role):
        return role_check(context, argument)


class CustomCheckFailure(ipy.errors.BadArgument):
    # custom classs for custom prerequisite failures outside of normal command checks
    pass


class GuildMessageable(ipy.GuildChannel, ipy.MessageableMixin):
    pass


def valid_channel_check(
    channel: ipy.GuildChannel, perms: ipy.Permissions
) -> GuildMessageable:
    if not isinstance(channel, ipy.MessageableMixin):
        raise ipy.errors.BadArgument(f"Cannot send messages in {channel.name}.")

    if not perms:
        raise ipy.errors.BadArgument(f"Cannot resolve permissions for {channel.name}.")

    if (
        ipy.Permissions.VIEW_CHANNEL not in perms
    ):  # technically pointless, but who knows
        raise ipy.errors.BadArgument(f"Cannot read messages in {channel.name}.")
    elif ipy.Permissions.READ_MESSAGE_HISTORY not in perms:
        raise ipy.errors.BadArgument(f"Cannot read message history in {channel.name}.")
    elif ipy.Permissions.SEND_MESSAGES not in perms:
        raise ipy.errors.BadArgument(f"Cannot send messages in {channel.name}.")
    elif ipy.Permissions.EMBED_LINKS not in perms:
        raise ipy.errors.BadArgument(f"Cannot send embeds in {channel.name}.")

    return channel  # type: ignore


class ValidChannelConverter(ipy.Converter):
    async def convert(self, ctx: ipy.InteractionContext, argument: ipy.GuildText):
        return valid_channel_check(argument, ctx.app_permissions)


async def _global_checks(ctx: ipy.BaseContext):
    return bool(ctx.guild) if ctx.bot.is_ready else False


class Extension(ipy.Extension):
    def __new__(cls, bot: ipy.Client, *args, **kwargs):
        new_cls = super().__new__(cls, bot, *args, **kwargs)
        new_cls.add_ext_check(_global_checks)
        return new_cls


if typing.TYPE_CHECKING:
    from interactions.ext.prefixed_commands import PrefixedInjectedClient
    from .help_tools import MiniCommand, PermissionsResolver

    class UIBase(PrefixedInjectedClient):
        owner: ipy.User
        color: ipy.Color
        slash_perms_cache: collections.defaultdict[int, dict[int, PermissionsResolver]]
        mini_commands_per_scope: dict[int, dict[str, MiniCommand]]

else:

    class UIBase(ipy.Client):
        pass


class UIContextMixin:
    guild_config: typing.Optional[models.Config]

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.guild_config = None
        super().__init__(*args, **kwargs)

    @property
    def guild(self) -> ipy.Guild:
        return self.client.cache.get_guild(self.guild_id)  # type: ignore

    @property
    def bot(self) -> "UIBase":
        """A reference to the bot instance."""
        return self.client  # type: ignore

    async def fetch_config(self) -> models.Config:
        """
        Gets the configuration for the context's guild.

        Returns:
            GuildConfig: The guild config.
        """
        if self.guild_config:
            return self.guild_config

        config, _ = await models.Config.get_or_create(guild_id=self.guild_id)

        self.guild_config = config
        return config


class UIInteractionContext(UIContextMixin, ipy.InteractionContext):
    pass


class UISlashContext(UIContextMixin, ipy.SlashContext):
    pass
