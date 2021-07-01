import importlib
import os
import time

import discord
from discord.ext import commands

import common.utils as utils


class OtherCMDs(commands.Cog, name="Other"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Pings the bot. Great way of finding out if the bot’s working correctly, but otherwise has no real use."""

        start_time = time.perf_counter()
        ping_discord = round((self.bot.latency * 1000), 2)

        mes = await ctx.reply(
            f"Pong!\n`{ping_discord}` ms from Discord.\nCalculating personal ping..."
        )

        end_time = time.perf_counter()
        ping_personal = round(((end_time - start_time) * 1000), 2)

        await mes.edit(
            content=f"Pong!\n`{ping_discord}` ms from Discord.\n`{ping_personal}` ms personally."
        )

    @commands.command()
    async def support(self, ctx):
        """Gives an invite link to the support server."""
        await ctx.reply("Support server:\nhttps://discord.gg/NSdetwGjpK")

    @commands.command()
    async def invite(self, ctx):
        """Gives an invite link to invite the bot... or not.
        It's a private bot. I can't let this thing grow exponentially."""
        await ctx.reply("Contact Sonic49 in order to invite me.")

    @commands.command()
    async def about(self, ctx):
        """Gives information about the bot."""

        msg_list = [
            "Hi! I'm the Ultimate Helper, a bot meant to help out with Danganronpa KG RPs.",
            "Niche use, I know, but it has a demand.",
            "",
            "Right now, this bot handles auto announcements, cards, Truth Bullets, and voting.",
            "Unlike a certain other bot, you can use what you want and ignore the rest.",
            "I don't intend on making this bloated.",
            ""
            "If you wish to invite me, contact Sonic49 and he'll talk to you about it.",
            "If you need support for me, maybe take a look at the support server here:\nhttps://discord.gg/NSdetwGjpK",
            "",
            "Bot made by Sonic49#7171.",
        ]

        about_embed = discord.Embed(
            title="About", colour=self.bot.color, description="\n".join(msg_list),
        )
        about_embed.set_author(
            name=f"{self.bot.user.name}",
            icon_url=f"{str(ctx.guild.me.avatar_url_as(format=None,static_format='png', size=128))}",
        )

        source_list = [
            "My source code is [here!](https://github.com/Sonic4999/UltimateInvestigator)",
            "This code might not be the best code out there, but you may have some use for it.",
            "Note that much of it was based off my other bot, Seraphim.",
        ]

        about_embed.add_field(
            name="Source Code", value="\n".join(source_list), inline=False
        )

        await ctx.reply(embed=about_embed)

    @commands.group(invoke_without_command=True, aliases=["prefix"], ignore_extra=False)
    async def prefixes(self, ctx):
        """A way of getting all of the prefixes for this server. You can also add and remove prefixes via this command."""

        async with ctx.typing():
            guild_config = await utils.create_and_or_get(ctx.guild.id)
            prefixes = tuple(f"`{p}`" for p in guild_config.prefixes)

        if prefixes:
            await ctx.reply(
                f"My prefixes for this server are: `{', '.join(prefixes)}`, but you can also mention me."
            )
        else:
            await ctx.reply(
                "I have no prefixes on this server, but you can mention me to run a command."
            )

    @prefixes.command(ignore_extra=False)
    @utils.proper_permissions()
    async def add(self, ctx, prefix: str):
        """Addes the prefix to the bot for the server this command is used in, allowing it to be used for commands of the bot.
        If it's more than one word or has a space at the end, surround the prefix with quotes so it doesn't get lost.
        Requires Manage Guild permissions."""

        if not prefix:
            raise commands.BadArgument("This is an empty string! I cannot use this.")

        async with ctx.typing():
            guild_config = await utils.create_and_or_get(ctx.guild.id)
            if len(guild_config.prefixes) >= 10:
                raise utils.CustomCheckFailure(
                    "You have too many prefixes! You can only have up to 10 prefixes."
                )

            if prefix in guild_config.prefixes:
                raise commands.BadArgument("The server already has this prefix!")

            guild_config.prefixes.add(prefix)
            await guild_config.save()

        await ctx.reply(f"Added `{prefix}`!")

    @prefixes.command(ignore_extra=False, aliases=["delete"])
    @utils.proper_permissions()
    async def remove(self, ctx, prefix):
        """Deletes a prefix from the bot from the server this command is used in. The prefix must have existed in the first place.
        If it's more than one word or has a space at the end, surround the prefix with quotes so it doesn't get lost.
        Requires Manage Guild permissions."""

        async with ctx.typing():
            try:
                guild_config = await utils.create_and_or_get(ctx.guild.id)
                guild_config.prefixes.remove(prefix)
                await guild_config.save()

            except KeyError:
                raise commands.BadArgument(
                    "The server doesn't have that prefix, so I can't delete it!"
                )

        await ctx.reply(f"Removed `{prefix}`!")


def setup(bot):
    importlib.reload(utils)
    bot.add_cog(OtherCMDs(bot))
