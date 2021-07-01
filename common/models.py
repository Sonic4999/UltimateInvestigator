import datetime
import os
import typing
from enum import Enum

import discord
import ujson
from tortoise import fields
from tortoise.models import Model

from common.utils import yesno_friendly_str


class Status(Enum):
    ALIVE = discord.Color(3062497)
    DEAD = discord.Color.red()
    ESCAPED = discord.Color.lighter_gray()
    HOST = discord.Color.darker_gray()


class SetField(fields.BinaryField, set):
    """A very exploity way of using a binary field to store a set."""

    def json_dumps(self, value):
        return bytes(ujson.dumps(value), "utf-8")

    def json_loads(self, value: str):
        return ujson.loads(value)

    def to_python_value(self, value):
        if value is not None and isinstance(value, self.field_type):  # if its bytes
            value = set(self.json_loads(value))  # loading it would return a list, so...
        return value or set()  # empty bytes value go brr

    def to_db_value(self, value, instance):
        if value is not None and not isinstance(
            value, self.field_type
        ):  # if its not bytes
            if isinstance(value, set):  # this is a dumb fix
                value = self.json_dumps(list(value))  # returns a bytes value
            else:
                value = self.json_dumps(value)
            # the reason why i chose using BinaryField over JSONField
            # was because orjson returns bytes, and orjson's fast
        return value


class StatusEnumField(fields.IntField, Status):
    """An extension to CharField that allows storing Statuses."""

    def __init__(self, **kwargs):
        super().__init__(False, **kwargs)
        self._enum_type = Status

    def to_db_value(self, value: typing.Type[Status], instance) -> int:
        return value.value.value  # get the enum value, then get the value of the color

    def to_python_value(self, value: int) -> typing.Type[Status]:
        try:
            return self._enum_type(discord.Color(value))
        except Exception:
            raise ValueError(
                "Database value {} does not exist on Enum {}.".format(
                    value, self._enum_type
                )
            )


class TruthBullet(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    aliases = SetField()
    description = fields.TextField()
    channel_id = fields.BigIntField()
    guild_id = fields.BigIntField()
    found = fields.BooleanField()
    finder = fields.BigIntField()

    def chan_mention(self):
        return f"<#{self.channel_id}>"

    def __str__(self):  # sourcery skip: merge-list-append
        str_list = []
        str_list.append(f"`{self.name}` - in {self.chan_mention()}")
        str_list.append(f"Aliases: {', '.join(f'`{a}`' for a in self.aliases)}")
        str_list.append(f"Found: {yesno_friendly_str(self.found)}")
        str_list.append(f"Finder: {f'<@{self.finder}>' if self.finder > 0 else 'N/A'}")
        str_list.append("")
        str_list.append(f"Description: {self.description}")

        return "\n".join(str_list)

    def found_embed(self, username):
        embed = discord.Embed(
            title="Truth Bullet Discovered",
            timestamp=datetime.datetime.utcnow(),
            color=discord.Color(int(os.environ.get("BOT_COLOR"))),
        )
        embed.description = (
            f"`{self.name}` - from {self.chan_mention()}\n\n{self.description}"
        )

        footer = "To be found as of" if self.finder is None else f"Found by {username}"
        embed.set_footer(text=footer)

        return embed


class Card(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
    oc_name = fields.CharField(max_length=100)
    oc_talent = fields.CharField(max_length=100)
    card_url = fields.TextField()
    _status = StatusEnumField()

    @property
    def mention(self):
        return f"<@{self.user_id}>"

    @property
    def title_name(self):
        return f"{self.oc_name}, the Ultimate {self.oc_talent}"

    @property
    def status(self):
        return self._status.name if self._status != Status.HOST else "ALIVE"

    async def as_embed(self, bot: discord.Client):
        member = await bot.fetch_user(
            self.user_id
        )  # we're assuming this will never fail because i double check everything
        embed = discord.Embed(
            title=self.title_name,
            description=f"By: {member.mention} ({str(member)})\nStatus: **{self.status}**",
        )
        embed.set_image(url=self.card_url)
        embed.color = self._status.value

        return embed


class UserInteraction(Model):
    id: int = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
    interactions = fields.DecimalField(4, 1)


class Config(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    bullet_chan_id = fields.BigIntField()
    ult_detective_role = fields.BigIntField()
    player_role = fields.BigIntField()
    bullets_enabled = fields.BooleanField(default=False)
    prefixes = SetField()
    bullet_default_perms_check = fields.BooleanField(default=True)
    bullet_custom_perm_roles = SetField()
