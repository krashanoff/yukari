#! env/bin/python
#
# yukari
#

import asyncio
import datetime as dt
import logging
import os
import re
import time
import typing

import random
random.seed()

import discord
from discord.ext import commands


"""
All the constants and config.
"""

CMD_PREFIX="~"
STARTUP_STATUS=[    # dangerous activities
    "with fire",
    "with snakes"
]

TMPMSG_DEFAULT=30

MSG_LIMIT=10                    # tight limit at the moment since incomplete feature.

OK_EMOJI="\U00002705"
NO_EMOJI="\U0000274C"
REPEAT_EMOJI="\U0001F501"
INPUT={OK_EMOJI, NO_EMOJI, REPEAT_EMOJI}

ABOUT=f"""
レオの長女、紫と申し上げます。
もっと知りたかったら、あたしのギットハブをチェックして下さい。
"""

logging.basicConfig(level=logging.INFO)
cli = commands.Bot(command_prefix=CMD_PREFIX)

# you may be an admin...
def is_admin():
    return commands.check(lambda ctx: [role for role in ctx.author.roles if role.permissions.administrator])

# ...but are you me?
def is_leo():
    return commands.check(lambda ctx: str(ctx.author) == os.getenv('OWNER'))


"""
Events
"""

@cli.event
async def on_ready():
    print(f"Successfully logged in as {cli.user}.")
    await cli.change_presence(status=discord.Status.online,
                              activity=discord.Game(name=STARTUP_STATUS[int(random.randint(0, len(STARTUP_STATUS) - 1))]))


"""
Commands
"""

# regurgitate some information about the bot.
@cli.command(help="Info-dump about the bot")
async def about(ctx):
    await ctx.channel.send(ABOUT)

# regurgitate some information about yourself.
@cli.command(help="Info-dump about the user and their perms")
async def whoami(ctx):
    if is_leo()(ctx):
        await ctx.send(f"お父さん！")
    else:
        admin = is_admin()(ctx)
        await ctx.send(f"You are {ctx.author}. You are {'not ' if not admin else ''}an admin, and are not my dad.", delete_after=TMPMSG_DEFAULT)

# set bot status
@cli.command(help="Set the bot status")
@is_leo()
async def status(ctx, *, status: str):
    await cli.change_presence(status=discord.Status.online, activity=discord.Game(name=status))
    await ctx.send("Updated status.", delete_after=TMPMSG_DEFAULT)

# say something
@cli.command(help="Say something on your behalf")
@is_leo()
async def say(ctx, chan: typing.Optional[discord.TextChannel], user: typing.Optional[discord.User], *, contents: str):
    if chan:
        await chan.send(contents)
    elif user == cli.user:
        await ctx.send(f"I can't send a DM to myself, silly.", delete_after=TMPMSG_DEFAULT)
    elif user:
        try:
            await user.send(contents)
        except AttributeError:
            await ctx.send(f"I couldn't send the DM to the user, sorry. (つ﹏<)･ﾟ｡", delete_after=TMPMSG_DEFAULT)
        else:
            await ctx.send(f"Something unexpected happened.", delete_after=TMPMSG_DEFAULT)
    else:
        await ctx.send(contents)

# keep a conversation
@cli.command(help="Start a conversation with someone on behalf of the bot")
@is_leo()
async def convo(ctx, user: typing.Optional[discord.User], *, initial_msg: str):
    portal = await ctx.send("```\nOpening the portal...\n```")
    await portal.edit("Just kidding, Leo hasn't implemented this yet.", delete_after=TMPMSG_DEFAULT)

# one-time use invite
@cli.command(help="Generate a one-time use invite to the system messages channel")
@is_leo()
async def otp(ctx, channel: typing.Optional[discord.TextChannel], *, reason: str):
    status = await ctx.send(f"Creating an invite for you...")
    invite = await (channel or ctx.guild.system_channel).create_invite(max_age=0, max_uses=1, reason=reason or f"{ctx.author} asked for a one-time-use invite.")
    await status.edit(content=f"Here's your invite:\n{invite.url}")

# destroy an invite
@cli.command(help="Destroy an invite")
@is_leo()
async def rmotp(ctx, inv: discord.Invite, *, reason: str):
    status = await ctx.send(f"Deleting invite id {inv.id}")
    await inv.delete()
    await status.edit(content=f"Deleted invite id {inv.id}.", delete_after=TMPMSG_DEFAULT)

# bulk deletion tool
@cli.command(name="d", help="Delete messages")
@is_admin()
async def delete(ctx, *args):
    status = await ctx.send("Standby...")
    
    channels = [ctx.channel]
    before   = None
    after    = None

    while True:
        msg = "Welcome to the bulk-deletion tool.\n"
        if channels != [ctx.channel]:
            msg += f"Channels: {[ c.name for c in channels ]}\n"
        if before:
            msg += f"Before: {before}\n"
        if after:
            msg += f"After: {after}\n"
        msg += f"React with {OK_EMOJI} to execute, {NO_EMOJI} to cancel.\n"

        await status.edit(content=msg)
        await status.add_reaction(NO_EMOJI)
        await status.add_reaction(OK_EMOJI)

        try:
            r, _ = await cli.wait_for("reaction_add",
                                      timeout=TMPMSG_DEFAULT,
                                      check=lambda r, u: u == ctx.author and r.emoji in INPUT)
        except asyncio.TimeoutError:
            await status.edit(content="Aborted!", delete_after=TMPMSG_DEFAULT)
            return
        else:
            if r.emoji == OK_EMOJI:
                await status.edit(content="Starting deletion...")
                break
            if r.emoji == NO_EMOJI:
                await status.edit(content="Aborted!", delete_after=TMPMSG_DEFAULT)
                return

    for c in channels:
        await status.edit(content=f"Deleting messages found in {c.name}")

        history = [ m async for m in c.history(limit=MSG_LIMIT) if m.id != status.id ]
        tasks = [ asyncio.gather(*[m.delete() for m in history[i:i+100]]) for i in range(0, len(history), 100) ]
        count = len(tasks)

        await status.edit(content=f"Found {count} batches of ~100 messages. Executing.")
        for i, t in enumerate(tasks):
            await t
            await status.edit(content=f"Completed batch {i+1}/{count}.")

        await status.edit(content=f"Done.")

    await status.edit(content="Transaction completed successfully.", delete_after=TMPMSG_DEFAULT)

if __name__ == "__main__":
    try:
        cli.run(os.environ.get("TOKEN"))
    except AttributeError:
        print("An environment variable is not set.")