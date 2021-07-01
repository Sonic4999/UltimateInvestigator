import asyncio
import os
import re

import aiohttp
import discord
import humanize
from discord.ext import commands

# http://urlregex.com/
URL_REGEX = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


async def type_from_url(url):
    # gets type of data from url
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            data = await resp.content.read(12)
            tup_data = tuple(data)

            # first 7 bytes of most pngs
            png_list = (0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
            if tup_data[:8] == png_list:
                return "png"

            # fmt: off
            # first 12 bytes of most jp(e)gs. EXIF is a bit wierd, and so some manipulating has to be done
            jfif_list = (0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
                0x49, 0x46, 0x00, 0x01)
            # fmt: on
            exif_lists = (
                (0xFF, 0xD8, 0xFF, 0xE1),
                (0x45, 0x78, 0x69, 0x66, 0x00, 0x00),
            )

            if tup_data == jfif_list or (
                tup_data[:4] == exif_lists[0] and tup_data[6:] == exif_lists[1]
            ):
                return "jpg"

            # first 3 bytes of some jp(e)gs.
            weird_jpeg_list = (0xFF, 0xD8, 0xFF)
            if tup_data[0:3] == weird_jpeg_list:
                return "jpg"

            # copied from d.py's _get_mime_type_for_image
            if tup_data[0:3] == b"\xff\xd8\xff" or tup_data[6:10] in (b"JFIF", b"Exif"):
                return "jpg"

            # first 6 bytes of most gifs. last two can be different, so we have to handle that
            gif_lists = ((0x47, 0x49, 0x46, 0x38), ((0x37, 0x61), (0x39, 0x61)))
            if tup_data[:4] == gif_lists[0] and tup_data[4:6] in gif_lists[1]:
                return "gif"

            # first 12 bytes of most webps. middle four are file size, so we ignore that
            webp_lists = ((0x52, 0x49, 0x46, 0x46), (0x57, 0x45, 0x42, 0x50))
            if tup_data[:4] == webp_lists[0] and tup_data[8:] == webp_lists[1]:
                return "webp"

    return None


async def tenor_handle(url: str):
    # handles getting gifs from tenor links
    dash_split = url.split("-")

    params = {
        "ids": dash_split[-1],
        "key": os.environ.get("TENOR_KEY"),
        "media_filter": "minimal",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.tenor.com/v1/gifs", params=params) as resp:
            resp_json = await resp.json()

            try:
                return resp_json["results"][0]["media"][0]["gif"]["url"]
            except KeyError:
                return None
            except IndexError:
                return None


async def get_image_url(url: str):
    # handles getting true image url from a url

    if "https://tenor.com/view" in url or "http://tenor.com/view" in url:
        gif_url = await tenor_handle(url)
        if gif_url != None:
            return gif_url

    else:
        try:
            file_type = await type_from_url(url)
        except aiohttp.InvalidURL:
            return None

        image_endings = ("jpg", "jpeg", "png", "gif", "webp")
        image_extensions = tuple(image_endings)  # no idea why I have to do this

        if file_type in image_extensions:
            return url

    return None


async def get_file_bytes(url: str, limit: int, equal_to=True):
    # gets a file as long as it's under the limit (in bytes)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise commands.BadArgument("I can't get this file/URL!")

            try:
                if equal_to:
                    await resp.content.readexactly(
                        limit + 1
                    )  # we want this to error out even if the file is exactly the limit
                    raise commands.BadArgument(
                        f"The file/URL given is over {humanize.naturalsize(limit, binary=True)}!"
                    )
                else:
                    await resp.content.readexactly(limit)
                    raise commands.BadArgument(
                        f"The file/URL given is at or over {humanize.naturalsize(limit, binary=True)}!"
                    )

            except asyncio.IncompleteReadError as e:
                # essentially, we're exploting the fact that readexactly will error out if
                # the url given is less than the limit
                return e.partial


def image_from_ctx(ctx: commands.Context):
    """To be used with URLToImage. Gets image from context, via an embed or via its attachments."""
    if not ctx.message.attachments:
        raise commands.BadArgument("No URL or image given!")

    if ctx.message.attachments[0].proxy_url.lower().endswith(ctx.bot.image_extensions):
        return ctx.message.attachments[0].proxy_url
    else:
        raise commands.BadArgument("Attachment provided is not a valid image.")


class ImageTypeChecker(commands.Converter):
    # given image type to convert, checks to see if image type speciified is valid.

    async def convert(self, ctx, argument: str):
        img_type = argument.replace(".", "").replace("-", "").lower()
        img_type = "jpeg" if img_type == "jpg" else img_type

        if img_type in ctx.bot.image_extensions:
            return img_type
        else:
            raise commands.BadArgument(
                f"Argument {argument} is not a valid image extension."
            )


class URLChecker(commands.Converter):
    # just checks if the argument give is a URL

    async def convert(self, ctx: commands.Context, argument: str):
        urls = URL_REGEX.findall(argument)
        if urls:
            return urls[0]

        raise commands.BadArgument(f"Argument {argument} is not an image url.")


class URLToImage(commands.Converter):
    # gets either the URL or the image from an argument

    async def convert(self, ctx: commands.Context, argument: str):
        urls = URL_REGEX.findall(argument)
        if urls:
            first_url = urls[0]

            possible_url = await get_image_url(first_url)
            if possible_url:
                return possible_url
            elif (
                ctx.message.embeds != []
                and ctx.message.embeds[0].type == "image"
                and ctx.message.embeds[0].thumbnail.url != discord.Embed.Empty
            ):
                return ctx.message.embeds[
                    0
                ].thumbnail.url  # gotta get that imgur support
            else:
                raise commands.BadArgument(f"Argument {argument} is not an image url.")

        raise commands.BadArgument(f"Argument {argument} is not an image url.")
