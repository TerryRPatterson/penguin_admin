#! /usr/bin/env python3
"""This is a simple text editor."""


import asyncio

import discord

from api_secrets import bot_token


client = discord.Client()

prefix = "~"


@client.event
async def on_ready():
    """Handle client first connect."""
    print('Logged in as')
    print(client.user.name)
    print('------')

# @client.event
# async def on_message


async def test(message):
    """Test bot functionality."""
    print("Test triggered.")
    counter = 0
    tmp = await client.send_message(message.channel,
                                    'Calculating messages...')
    async for log in client.logs_from(message.channel, limit=100):
        if log.author == message.author:
            counter += 1

    await client.edit_message(tmp, 'You have {} messages.'.format(counter))


async def sleep(message):
    """Show sleep functionality."""
    await asyncio.sleep(5)
    await client.send_message(message.channel, 'Done sleeping')


commands = {
    f"{prefix}test": test,
    f"{prefix}sleep": sleep,
}


@client.event
async def on_message(message):
    """Handle messages."""
    print(message.content, message.author)
    print(message.id)
    for command_name in commands:
        if message.content.startswith(command_name):
            return await commands[command_name](message)


client.run(bot_token)
