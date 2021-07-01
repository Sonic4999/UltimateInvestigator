import asyncio
import collections
import importlib
import typing

import discord
from discord.ext import commands

import common.models as models
import common.utils as utils


class BulletCheck(commands.Cog, name="Bullet Check"):
    """The cog that checks for the Truth Bullets."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def check_for_finish(
        self,
        guild: discord.Guild,
        bullet_chan: discord.TextChannel,
        guild_config: models.Config,
    ):
        do_not_find = await models.TruthBullet.filter(
            guild_id=guild.id, found=False
        ).first()  # kind of an exploit, but oh well
        if do_not_find:
            return

        counter = collections.Counter()

        async for bullet in models.TruthBullet.filter(guild_id=guild.id):
            counter[bullet.finder] += 1

        most_found = counter.most_common(None)
        most_found_num = most_found[0][
            1
        ]  # number of truth bullets found by highest person
        # the next is just fancy code to check for ties and make a list for the top people
        most_found_people = tuple(p[0] for p in most_found if p[1] == most_found_num)

        if guild_config.ult_detective_role > 0:  # if the role had been specified
            ult_detect_role_obj = guild.get_role(guild_config.ult_detective_role)

            if (
                ult_detect_role_obj
            ):  # if it doesnt exist, lets not waste api calls on it
                for person_id in most_found_people:
                    try:  # use an internal method to save on an http request
                        # we get to skip out on asking for the member, which was... well
                        # who cares, anyways?
                        # but dont do this unless you're me
                        await self.bot._connection.http.add_role(
                            guild.id, person_id, ult_detect_role_obj.id
                        )
                        await asyncio.sleep(1)  # we don't want to trigger ratelimits
                    except discord.HTTPException:
                        continue

        str_builder = collections.deque()
        str_builder.append("**All Truth Bullets have been found.**")
        str_builder.append("")
        str_builder.append(f"Best Detective(s) (found {most_found_num} Truth Bullets):")
        str_builder.extend(f"<@{person_id}>" for person_id in most_found_people)

        await bullet_chan.send("\n".join(str_builder))

        guild_config.bullets_enabled = False
        await guild_config.save()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # if the message is from a bot, from discord, not from a guild, not a default message or a reply, or is empty
        if (
            message.author.bot
            or message.author.system
            or not message.guild
            or message.type != discord.MessageType.default
            or message.content == ""
        ):
            return

        guild_config = await utils.create_and_or_get(message.guild.id)
        if not (
            guild_config.bullets_enabled
            # internal list that has list of ids, faster than using roles property
            and message.author._roles.has(guild_config.player_role)
        ):
            return

        bullet_found: typing.Optional[models.TruthBullet] = None

        async for bullet in models.TruthBullet.filter(channel_id=message.channel.id):
            if (
                bullet.name.lower() in message.content.lower()
                or any(a.lower() in message.content.lower() for a in bullet.aliases)
            ) and not bullet.found:
                bullet_found = bullet
                break

        if not bullet_found or bullet_found.found:
            return

        embed = bullet_found.found_embed(str(message.author))

        bullet_chan = self.bot.get_channel(guild_config.bullet_chan_id)
        if not bullet_chan:
            raise utils.CustomCheckFailure(
                "For some reason, I tried getting a channel I can't see. The owner of the bot should be able to fix this soon."
            )

        await message.channel.send(embed=embed)
        await bullet_chan.send(embed=embed)

        bullet_found.found = True
        bullet_found.finder = message.author.id
        await bullet_found.save()

        await self.check_for_finish(message.guild, bullet_chan, guild_config)


def setup(bot):
    importlib.reload(utils)
    bot.add_cog(BulletCheck(bot))
