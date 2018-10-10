#! /usr/bin/env python3
"""This is a simple text editor."""


import argparse
import asyncio
from collections import namedtuple
from shlex import split

import discord
from api_secrets import bot_token

bot = discord.Client()

prefix = "~"

servers = {}


class ArgumentParser(argparse.ArgumentParser):
    """Argument Parser override to allow for help handling."""

    def error(self, message):
        """Handle bad arguments."""
        help_message = self.print_help()
        help_message += f"{self.prog}: error: {message}\n"
        raise SyntaxError(help_message)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                return message
            file.write(message)

    def print_help(self, file=None):
        """Return help for the parser."""
        return self._print_message(self.format_help(), file)


@bot.event
async def on_ready():
    """Handle bot first connect."""
    print("Logged in as")
    print(bot.user.name)
    print("------")
    for server in bot.servers:
        id = server.id
        servers[id] = {
            "admin_channel": None,
            "admin_role": None,
            "created_channels": []
        }
        for channel in server.channels:
            if channel.name == "admins":
                servers[id]["admin_channels"] = channel

        for role in server.roles:
            if role.permissions.administrator and not role.managed:
                print(role.name)
                servers[id]["admin_role"] = role


async def count(message, parsed_args):
    """Test bot functionality."""
    counter = 0
    tmp = await bot.send_message(message.channel,
                                 "Calculating messages...")
    async for log in bot.logs_from(message.channel, limit=100):
        if log.author == message.author:
            counter += 1

    await bot.edit_message(tmp, "You have {} messages.".format(counter))


async def sleep(message, parsed_args):
    """Show sleep functionality."""
    if parsed_args.time is not None:
        time = parsed_args.time
    else:
        time = 5

    await asyncio.sleep(time)
    await bot.send_message(message.channel, "Done sleeping")


async def summon(message, parsed_args):
    """Create a mirrored channel pair."""
    private_channel_tuple = namedtuple("private_channel_pair",
                                       ["user_channel", "admin_channel"])

    server = message.server
    everyone_role = server.default_role
    server_id = server.id
    admin_role = servers[server_id]["admin_role"]
    author = message.author
    channel_name = f"{author.name}-Talking to admins"
    channel_name_admin = channel_name + "-Admin only side"

    denied_perms = discord.PermissionOverwrite(read_messages=False)
    allowed_perms = discord.PermissionOverwrite(read_messages=True)

    everyone = discord.ChannelPermissions(target=everyone_role,
                                          overwrite=denied_perms)
    admin = discord.ChannelPermissions(target=admin_role,
                                       overwrite=allowed_perms)
    admin_no = discord.ChannelPermissions(target=admin_role,
                                          overwrite=denied_perms)
    user = discord.ChannelPermissions(target=author,
                                      overwrite=allowed_perms)
    bot_perms = discord.ChannelPermissions(target=bot.user,
                                           overwrite=denied_perms)

    new_user_channel = await bot.create_channel(server, channel_name,
                                                everyone, admin_no, user,
                                                bot_perms)
    new_admin_channel = await bot.create_channel(server, channel_name_admin,
                                                 everyone, admin, bot_perms)
    new_channels = private_channel_tuple(new_user_channel, new_admin_channel)
    servers[server_id]["created_channels"].append(new_channels)
    await bot.delete_message(message)
    user_message = f"{author.mention} you can talk to the admins here."
    admin_message = (f"{author.mention} has opened a private channel with the "
                     "admins")
    await bot.send_message(new_user_channel, user_message)
    await bot.send_message(new_admin_channel, admin_message)
    return True


async def admin(message_object, parsed_args):
    """Send a message to the admins."""
    author_mention = message_object.author.mention
    channel_mention = message_object.channel.mention
    destination_id = message_object.server.id
    destination = servers[destination_id]
    if len(parsed_args.message) >= 1:
        message_content = f"{author_mention} in {channel_mention} said: "
        for message_piece in parsed_args.message:
            message_content += message_piece + " "
    else:
        message_content = (f"{author_mention} mentioned admins in "
                           f"{channel_mention}")
    await bot.send_message(destination, message_content)
    await bot.delete_message(message_object)


commands = {
    "count": count,
    "sleep": sleep,
    "admin": admin,
    "summon": summon,
}


def create_parser():
    """Create the parser for message."""
    parser = ArgumentParser(prog="Admin bot discord.", allow_abbrev=True,
                            add_help=False)
    sub_parsers = parser.add_subparsers(dest="command")

    count_parser = sub_parsers.add_parser("count", help="Count messages.")

    sleep_parser = sub_parsers.add_parser("sleep", help="Sleep bot.")

    summon_parser = sub_parsers.add_parser("summon")

    sleep_parser.add_argument("time", help="The time the bot should sleep.",
                              nargs="?",  type=int)

    admin_parser = sub_parsers.add_parser("admin", help="Talk to admins"
                                                        " in private channel.")
    admin_parser.add_argument("message", nargs="*")

    return parser


async def check_controlled_channels(message):
    """Check if a message is in a controlled channel."""
    channel = message.channel
    id = message.server.id
    found = False
    for private_channel_pair in servers[id]["created_channels"]:
        user_channel = private_channel_pair.user_channel
        admin_channel = private_channel_pair.admin_channel
        if channel.id == user_channel.id:
            author = message.author.mention
            mirror_message = f"{author}: {message.content}"
            await bot.send_message(admin_channel, mirror_message)
            found = True
        if channel.id == admin_channel.id:
            if message.content.startswith(prefix):
                message_no_prefix = message.content.lstrip(prefix)
                if message_no_prefix.startswith("resolve"):
                    await bot.delete_channel(user_channel)
                    await bot.delete_channel(admin_channel)
                else:
                    admin_message = f"Admins: {message_no_prefix}"
                    await bot.send_message(user_channel, admin_message)
            found = True
    return found


@bot.event
async def on_message(message):
    """Handle messages."""
    if not message.author == bot.user:
        controlled_message = await check_controlled_channels(message)
        if message.content.startswith(prefix):
            try:
                message_no_prefix = message.content.lstrip(prefix)
                message_seperated = split(message_no_prefix)
                list_arguments = list(message_seperated)
                if not controlled_message:
                    parser = create_parser()
                    parsed_args = parser.parse_args(args=list_arguments)
                    command = parsed_args.command
                    await commands[command](message, parsed_args)
            except SyntaxError as error_message:
                user = message.author
                await bot.send_message(user, error_message)


bot.run(bot_token)
