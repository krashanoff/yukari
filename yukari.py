#! env/bin/python
#
# yukari
#

import asyncio
import datetime as dt
import logging
import os
import re
import socket
import time
import typing
import random
import argparse

import discord
from discord.ext import commands

CMD_PREFIX="$ "
STARTUP_STATUS=[    # dangerous activities
    "with fire",
    "with snakes",
    "with scripts",
    "rm -rf /",
    "LEGO™: Ninjago with dad",
    "Apex Legends and stream sniping dad"
]
SCRIPT_CHNAME = "！／ゆかり"
SCRIPT_PFX = "```sh\n#!/yukari/"
SCRIPT_SFX = "```"
TMPMSG_DURATION = 30
SUPPORTED={ f for cog in dir() for f in cog }

SUCCESS=0
FAILURE=1

logging.basicConfig(level=logging.INFO)
cli = commands.Bot(CMD_PREFIX)

# what all yukari functions take as an
# argument.
# side-effects, such as user confirmation,
# are enabled only if interactive.
class Context:
    def __init__(self,
                 guild: discord.Guild,
                 chan: discord.TextChannel,
                 author: discord.User,
                 cmd_msg: discord.Message,
                 msg: str,
                 interactive: bool):    # why did this break it?
        self.guild = guild
        self.chan = chan
        self.author = author
        self.cmd_msg = cmd_msg
        self.msg = msg
        self.interactive = interactive
        self.args = False

    # sends a message~
    async def send(self, msg: str) -> discord.Message:
        if not self.interactive:
            return
        return await self.chan.send(msg)

    # confirm with the user that they want to perform some
    # action. Only sends if interactive.
    async def confirm(self, msg: str) -> bool:
        if not self.interactive:
            return True
        status = await self.chan.send(msg)
        await status.add_reaction("❌")
        await status.add_reaction("✅")
        try:
            await status.wait_for('reaction_add', lambda r, u: u == self.author and r.emoji in {"❌", "✅"})
        except asyncio.TimeoutError:
            await status.edit(content="Aborting!", delete_after=TMPMSG_DURATION)
            return False
        return True

# what all yukari functions return.
# chain together for __slick__ piping.
class Result:
    def __init__(self,
                 code: int,
                 stdout: str,
                 stderr: str):
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self) -> str:
        return f"<Result code:{self.code} stdout:'{self.stdout[:500]}' stderr:'{self.stderr[:500]}'"
    
    def __and__(self, other) -> bool:
        return self.code and other.code
    
    def __or__(self, other) -> bool:
        return self.code or other.code
    
    def __gt__(self, other):
        other.stdout += self.stdout
        return other
    
# makes a function a yukari command.
# handles parsing arguments and context
# delivery.
#
# cargs: map name of arg to (dest, type, nargs, help)
#
# can only decorate a function taking a single Context argument.
def cmd(desc: str, cargs: typing.Dict[str, dict]):
    def w(f):
        def inner(ctx: Context):
            parser = argparse.ArgumentParser(f.__name__, description=desc)
            print(ctx.msg)
            for k in cargs.keys():
                parser.add_argument(k, **(cargs[k]))
            try:
                ctx.args = parser.parse_args(ctx.msg.split(' ')[1:])     # put parsed args in the context
            except:
                return None
            return f(ctx)
        return inner
    return w

# create a one-time-use invite.
async def otp(ctx: Context) -> Result:
    inv = ctx.args.id
    reason = ctx.args.reason
    
    status = await ctx.send(f"Creating an invite for you...")
    invite = await (ctx.chan or ctx.guild.system_channel).create_invite(max_age=0, max_uses=1, reason=ctx.stdin or f"{ctx.author} asked for a one-time-use invite.")
    await status.edit(content=f"{ctx.author.mention} asked for a one-time-use invite:\n\n{invite.url}")

# delete an invite.
async def rminv(ctx: Context, inv: discord.Invite, *, reason: typing.Optional[str]) -> Result:
    status = await ctx.send(f"Deleting invite id {inv.id}")
    await inv.delete()
    await ctx.msg.delete(delay=60)
    await status.edit(content=f"{ctx.author.mention} deleted invite **{inv.id}**.", delete_after=60)

# count messages.
async def count(ctx: Context, chan: typing.Optional[discord.TextChannel], *, pattern: typing.Optional[str]) -> Result:
    status = await ctx.send(f"Counting messages in {chan or ctx.channel} matching pattern `{pattern}`...")
    count = 0
    async for m in (chan or ctx).history(limit=5000):
        if re.search(pattern or ".*", m.content):
            count += 1
    await status.edit(content=f"Found {count} messages matching your query.")

# count words in stdin.
@cmd(desc="Count words, bytes, or lines!",
     cargs={
         "-b": {
             "dest": "b",
             "action": "store_true",
             "help": "Count bytes"
         },
         "-l": {
             "dest": "l",
             "action": "store_true",
             "help": "Count lines"
         },
         "input": {
             "type": str,
             "metavar": "IN",
             "nargs": "*",
             "help": "Your input."
         }
     })
async def wc(ctx: Context) -> Result:
    words = len(ctx.args.input)
    phrase = ' '.join(ctx.args.input)
    byte_count = len(phrase)
    line_count = len(phrase.split('\n'))

    if ctx.args.b:
        return Result(SUCCESS, f"{byte_count}", "")
    elif ctx.args.l:
        return Result(SUCCESS, f"{line_count}", "")
    return Result(SUCCESS, f"{words}", "")

# echo your output.
@cmd(desc="Echo something to stdout",
     cargs={
         "-n": {
            "dest": "nonewline",
            "action": "store_true",
            "help": "Remove trailing newline from output (pretty pointless)."
         },
         "rest": {
            "type": str,
            "metavar": "IN",
            "nargs": "*",
            "help": "Input text."
         }
     })
async def echo(ctx: Context) -> Result:
    print(ctx)
    out = ' '.join(ctx.args.rest)
    if ctx.args.nonewline:
        out = out.rstrip('\n')

    await ctx.send(out)
    return Result(SUCCESS, out, "")

async def cat(ctx, args) -> Result:
    pass

async def helpcmd(ctx: Context) -> Result:
    pass

@cli.event
async def on_ready():
    print(f"Successfully logged in as {cli.user}.")
    random.seed()
    await cli.change_presence(status=discord.Status.online,
                              activity=discord.Game(name=STARTUP_STATUS[int(random.randint(0, len(STARTUP_STATUS) - 1))]))

async def run_script(msg: discord.Message):
    # check our scripts for the server.
    scripts_ch = [ c for c in msg.guild.text_channels if c.name == SCRIPT_CHNAME ][0] or None
    print(f"found scripts channel in guild {msg.guild}")
    scripts = [ s.rstrip(SCRIPT_SFX) async for m in scripts_ch.history(limit=20) if (s := m.content.lstrip(SCRIPT_PFX)) != m.content ]
    for s in scripts:
        name, *parts = s.split('\n')
        print(f"Found a script with name {name}!")

        # if we found a match, then run it.
        # if msg.content.startswith(name):
        #     return run_script(name, parts)

# cmd parser
@cli.event
async def on_message(msg: discord.Message):
    if msg.author == cli.user or not msg.content.startswith(CMD_PREFIX) or not msg.channel.permissions_for(msg.author).administrator:
        return
    content = msg.content.lstrip(CMD_PREFIX)

    # construct our context
    c = Context(msg.guild, msg.channel, msg.author, msg, content, True)
    wcr = await wc(c)
    await msg.channel.send(f"Counted {wcr.stdout}")
    print(await echo(c))

    # check our coreutils.
    cmds = { c[0]: c[1:] for s in msg.content.lstrip(CMD_PREFIX).split(' | ') if (c := s.split(' ', 1))[0] in SUPPORTED }
    print(cmds)
    for cmd, args in cmds:
        print(cmd)

    # if not in coreutils, then try a script.
    if (result := await run_script(msg)):
        await msg.channel.send(f"Terminated successfully.\n{result.stdout}")

if __name__ == "__main__":
    try:
        cli.run(os.environ.get("TOKEN"))
    except AttributeError:
        print("An environment variable is not set.")