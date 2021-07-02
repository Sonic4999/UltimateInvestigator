#!/usr/bin/env python3.8
import collections
import logging
import traceback
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands

import common.models as models


def bullet_proper_perms():
    async def predicate(ctx: commands.Context):
        bullet_config = await get_or_create_bullet_config(ctx.guild.id)

        default_perms = False
        if bullet_config.bullet_default_perms_check:
            # checks if author has admin or manage guild perms or is the owner
            permissions = ctx.channel.permissions_for(ctx.author)
            default_perms = permissions.administrator or permissions.manage_guild

        # checks to see if the internal role list for the user has any of the roles specified in the roles specified
        role_perms = any(
            ctx.author._roles.has(r) for r in bullet_config.bullet_custom_perm_roles
        )

        return default_perms or role_perms

    return commands.check(predicate)


def proper_permissions():
    async def predicate(ctx: commands.Context):
        # checks if author has admin or manage guild perms or is the owner
        permissions = ctx.channel.permissions_for(ctx.author)
        return permissions.administrator or permissions.manage_guild

    return commands.check(predicate)


async def error_handle(bot, error, ctx=None):
    # handles errors and sends them to owner
    if isinstance(error, aiohttp.ServerDisconnectedError):
        to_send = "Disconnected from server!"
        split = True
    else:
        error_str = error_format(error)
        logging.getLogger("discord").error(error_str)

        chunks = line_split(error_str)
        for i in range(len(chunks)):
            chunks[i][0] = f"```py\n{chunks[i][0]}"
            chunks[i][len(chunks[i]) - 1] += "\n```"

        final_chunks = ["\n".join(chunk) for chunk in chunks]
        if ctx and hasattr(ctx, "message") and hasattr(ctx.message, "jump_url"):
            final_chunks.insert(0, f"Error on: {ctx.message.jump_url}")

        to_send = final_chunks
        split = False

    await msg_to_owner(bot, to_send, split)

    if ctx:
        if hasattr(ctx, "reply"):
            await ctx.reply(
                "An internal error has occured. The bot owner has been notified."
            )
        else:
            await ctx.channel.send(
                content="An internal error has occured. The bot owner has been notified."
            )


async def msg_to_owner(bot, content, split=True):
    # sends a message to the owner
    owner = bot.owner
    string = str(content)

    str_chunks = string_split(string) if split else content
    for chunk in str_chunks:
        await owner.send(f"{chunk}")


async def get_or_create_guild_config(guild_id):
    defaults = {
        "id": guild_id,
        "prefixes": {"v!"},
        "player_role": 0,
    }
    result, _ = await models.GuildConfig.get_or_create(defaults, guild_id=guild_id)
    return result


async def get_or_create_bullet_config(guild_id):
    defaults = {
        "guild_id": guild_id,
        "bullet_chan_id": 0,
        "ult_detective_role": 0,
        "player_role": 0,
        "bullets_enabled": False,
        "bullet_default_perms_check": True,
        "bullet_custom_perm_roles": set(),
    }
    result, _ = await models.BulletConfig.get_or_create(defaults, guild__id=guild_id)
    return result


def line_split(content: str, split_by=20):
    content_split = content.splitlines()
    return [
        content_split[x : x + split_by] for x in range(0, len(content_split), split_by)
    ]


def embed_check(embed: discord.Embed) -> bool:
    """Checks if an embed is valid, as per Discord's guidelines.
    See https://discord.com/developers/docs/resources/channel#embed-limits for details."""
    if len(embed) > 6000:
        return False

    if embed.title and len(embed.title) > 256:
        return False
    if embed.description and len(embed.description) > 2048:
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
    return discord.AllowedMentions(everyone=False, users=[user], roles=False)


def error_format(error):
    # simple function that formats an exception
    return "".join(
        traceback.format_exception(
            etype=type(error), value=error, tb=error.__traceback__
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


def get_all_extensions(str_path, folder="cogs"):
    # gets all extensions in a folder
    ext_files = collections.deque()
    loc_split = str_path.split("cogs")
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

        if str_path != "cogs.db_handler":
            ext_files.append(str_path)

    return ext_files


def toggle_friendly_str(bool_to_convert):
    if bool_to_convert == True:
        return "on"
    else:
        return "off"


def yesno_friendly_str(bool_to_convert):
    if bool_to_convert == True:
        return "yes"
    else:
        return "no"


def role_check(ctx: commands.Context, role: discord.Role):
    top_role = ctx.guild.me.top_role

    if role > top_role:
        raise CustomCheckFailure(
            "The role provided is a role that is higher than the roles I can edit. "
            + "Please move either that role or my role so that "
            + "my role is higher than the role you want to use."
        )


def error_embed_generate(error_msg):
    return discord.Embed(colour=discord.Colour.red(), description=error_msg)


def add_decimal_value(ori_value, add):
    if not isinstance(add, Decimal):
        return str(Decimal(ori_value) + Decimal(add))
    else:
        return str(Decimal(ori_value) + add)


class CustomCheckFailure(commands.CheckFailure):
    # custom classs for custom prerequisite failures outside of normal command checks
    pass


class ValidChannelConverter(commands.TextChannelConverter):
    """The text channel converter, but we do a few checks to make sure we can do what we need to do in the channel."""

    async def convert(self, ctx: commands.Context, argument: str):
        chan = await super().convert(ctx, argument)
        perms = chan.permissions_for(ctx.guild.me)

        if not perms.read_messages:  # technically pointless, but who knows
            raise commands.BadArgument(f"Cannot read messages in {chan.name}.")
        elif not perms.read_message_history:
            raise commands.BadArgument(f"Cannot read message history in {chan.name}.")
        elif not perms.send_messages:
            raise commands.BadArgument(f"Cannot send messages in {chan.name}.")
        elif not perms.embed_links:
            raise commands.BadArgument(f"Cannot send embeds in {chan.name}.")

        return chan


class DecimalConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> Decimal:
        try:
            return Decimal(argument)
        except InvalidOperation:
            raise commands.BadArgument("This is not a decimal!")


class UsableIDConverter(commands.IDConverter):
    """The internal ID converter, but usable.
    Will be replaced by the ObjectConverter in d.py 2.0."""

    async def convert(self, ctx: commands.Context, argument: str):
        match = self._get_id_match(argument)
        try:
            return int(match.group(1))
        except:
            raise commands.MessageNotFound(argument)
