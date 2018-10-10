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


@client.event
async def on_ready():
    """Handle client first connect."""
    print("Logged in as")
    print(client.user.name)
    print("------")
    for server in client.servers:
        id = server.id
        for channel in server.channels:
            if channel.name == "admins":
                admin_channels[id] = channel


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
}


def create_parser():
    """Create the parser for message."""
    parser = argparse.ArgumentParser(prog="Admin bot discord.",
                                     allow_abbrev=True)
    sub_parsers = parser.add_subparsers(dest="command")

    count_parser = sub_parsers.add_parser("count", help="Count messages.")

    sleep_parser = sub_parsers.add_parser("sleep", help="Sleep bot.")
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
        message_no_prefix = message.content.lstrip(prefix)
        message_seperated = split(message_no_prefix)
        list_arguments = list(message_seperated)
        parser = create_parser()
        parsed_args = parser.parse_args(args=list_arguments)
        command = parsed_args.command
        await commands[command](message, parsed_args)


client.run(bot_token)
