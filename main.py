#! /usr/bin/env python3
"""This is a simple text editor."""


import argparse
import asyncio
from shlex import split

import discord
from api_secrets import bot_token

client = discord.Client()

prefix = "~"

admin_channels = {}
admin_roles = {}
created_channels = {}


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        help_message = self.print_help()
        help_message += f"{self.prog}: error: {message}\n"
        raise SyntaxError(help_message)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                return message
            file.write(message)

    def print_help(self, file=None):
        return self._print_message(self.format_help(), file)

@client.event
async def on_ready():
    """Handle client first connect."""
    print("Logged in as")
    print(client.user.name)
    print("------")
    for server in client.servers:
        id = server.id
        created_channels[id] = []
        for channel in server.channels:
            if channel.name == "admins":
                admin_channels[id] = channel
        for role in server.roles:
            if role.name == "admins":
                admin_roles[id] = role


async def count(message, parsed_args):
    """Test bot functionality."""
    counter = 0
    tmp = await client.send_message(message.channel,
                                    "Calculating messages...")
    async for log in client.logs_from(message.channel, limit=100):
        if log.author == message.author:
            counter += 1

    await client.edit_message(tmp, "You have {} messages.".format(counter))


async def sleep(message, parsed_args):
    """Show sleep functionality."""
    if parsed_args.time is not None:
        time = parsed_args.time
    else:
        time = 5

    await asyncio.sleep(time)
    await client.send_message(message.channel, "Done sleeping")


async def summon(message, parsed_args):
    """Create a mirrored channel pair."""
    server = message.server
    everyone_role = server.default_role
    server_id = server.id
    admin_role = admin_roles[server_id]
    author = message.author
    channel_name = f"{author.name} talking to admins."

    everyone_perms = discord.PermissionOverwrite(read_messages=False)
    allowed_perms = discord.PermissionOverwrite(read_messages=True)

    everyone = discord.ChannelPermissions(target=everyone_role,
                                          overwrite=everyone_perms)
    admin = discord.ChannelPermissions(target=admin_role,
                                       overwrite=allowed_perms)
    user = discord.ChannelPermissions(target=author,
                                      overwrite=allowed_perms)

    new_channel = await client.create_channel(server, channel_name, everyone,
                                              admin, user)
    created_channels[server_id].append(new_channel)
    await client.delete_message(message)
    creation_content = f"{author.mention} {admin_role.mention}"
    await client.send_message(new_channel, creation_content)
    return True


async def resolve(message, parsed_args):
    """Resolve an issue channel."""
    server_id = message.server.id
    channel = message.channel

    if channel in created_channels[server_id]:
        await client.delete_channel(channel)


async def admin(message_object, parsed_args):
    """Send a message to the admins."""
    author_mention = message_object.author.mention
    channel_mention = message_object.channel.mention
    destination_id = message_object.server.id
    destination = admin_channels[destination_id]
    if len(parsed_args.message) >= 1:
        message_content = f"{author_mention} in {channel_mention} said: "
        for message_piece in parsed_args.message:
            message_content += message_piece + " "
    else:
        message_content = (f"{author_mention} mentioned admins in "
                           f"{channel_mention}")
    await client.send_message(destination, message_content)


commands = {
    "count": count,
    "sleep": sleep,
    "admin": admin,
    "summon": summon,
    "resolve": resolve
}


def create_parser():
    """Create the parser for message."""
    parser = ArgumentParser(prog="Admin bot discord.", allow_abbrev=True,
                            add_help=False)
    sub_parsers = parser.add_subparsers(dest="command")

    count_parser = sub_parsers.add_parser("count", help="Count messages.")

    sleep_parser = sub_parsers.add_parser("sleep", help="Sleep bot.")

    summon_parser = sub_parsers.add_parser("summon")

    resolve_parser = sub_parsers.add_parser("resolve")

    sleep_parser.add_argument("time", help="The time the bot should sleep.",
                              nargs="?",  type=int)

    admin_parser = sub_parsers.add_parser("admin", help="Talk to admins"
                                                        " in private channel.")
    admin_parser.add_argument("message", nargs="*")

    return parser


@client.event
async def on_message(message):
    """Handle messages."""
    if message.content.startswith(prefix):
        try:
            message_no_prefix = message.content.lstrip(prefix)
            message_seperated = split(message_no_prefix)
            list_arguments = list(message_seperated)
            parser = create_parser()
            parsed_args = parser.parse_args(args=list_arguments)
            command = parsed_args.command
            await commands[command](message, parsed_args)
        except SyntaxError as error_message:
            user = message.author
            await client.send_message(user, error_message)
            await client.delete_message(message)


client.run(bot_token)
