#! /usr/bin/env python3
"""This is a simple text editor."""


import argparse
import asyncio
from shlex import split

import discord
from api_secrets import bot_token

client = discord.Client()

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


@client.event
async def on_ready():
    """Handle client first connect."""
    print("Logged in as")
    print(client.user.name)
    print("------")
    for server in client.servers:
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
    admin_role = servers[server_id]["admin_role"]
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
    servers[server_id]["created_channels"].append(new_channel)
    await client.delete_message(message)
    creation_content = f"{author.mention} {admin_role.mention}"
    await client.send_message(new_channel, creation_content)
    return True


async def resolve(message, parsed_args):
    """Resolve an issue channel."""
    server_id = message.server.id
    channel = message.channel
    author = message.author

    if channel in servers[server_id]["created_channels"]:
        if author.permissions_in(channel).administrator:
            await client.delete_channel(channel)
        else:
            failure_message = (f"{author.mention} you do not have permission "
                               "to close the channel.")
            await client.send_message(channel, failure_message)


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
    await client.send_message(destination, message_content)
    await client.delete_message(message_object)


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


client.run(bot_token)
