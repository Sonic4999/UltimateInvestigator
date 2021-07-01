import datetime
import os

import discord
import ujson
from tortoise import fields
from tortoise.models import Model

# yes, this is a copy from common.utils
# but circular imports are a thing
def yesno_friendly_str(bool_to_convert):
    if bool_to_convert == True:
        return "yes"
    else:
        return "no"


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
