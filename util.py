import re
import asyncio
import typing
import random
from io import StringIO

import discord
from discord.channel import DMChannel
from discord.ext import commands
from discord.ext.commands.core import command

from constants import *
from perms import *

# General server maintenance.
class Util(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # the god command. evaluate python code.
    @commands.command(help="Evaluate arbitrary Python code.")
    @is_leo()
    async def sudo(self, ctx, *, msg: str):
        status = await ctx.send(f"Evaluating...")

        out = StringIO("")
        def contained_print(m):
            print(m, file=out)

        try:
            eval(msg,
            {
                'g': ctx.guild,
                'c': ctx.channel,
                'print': contained_print,
            })
            await status.edit(content="Evaluated.", delete_after=TMPMSG_DEFAULT)
            await ctx.send(f"Output:\n{out.getvalue() or 'Nothing'}")
        except SyntaxError:
            await ctx.send("Syntax error.")
        except:
            await ctx.send("Something very weird happened.")

    @commands.command(help="Temporarily forward DMs to another channel.")
    @is_admin()
    async def fwd(self, ctx: commands.Context, chan: typing.Optional[discord.TextChannel]):
        if not chan:
            chan = ctx.channel
        await ctx.send(f"Forwarding DMs to {chan.name}. Send `!@stop` to stop.")
        while True:
            m = await self.bot.wait_for("message", check=lambda m: type(m.channel) is discord.DMChannel or (type(m.channel) is discord.DMChannel and m.author == ctx.author))
            if m.author == ctx.author and m.content == "!@stop":
                break
            await chan.send(f"```\n{m.author.name}:\n{m.content[:1500]}\n```")
        await ctx.send(f"Stopped forwarding messages.")
    
    # x-post something to another channel.
    @commands.command(help="Crosspost the given message to some other channel.")
    @is_officer()
    async def pin_it(self, ctx: commands.Context, id: typing.Optional[str]):
        if not msg:
            msg = (await ctx.channel.history(limit=1).flatten())[0]
        else:
            msg = await ctx.fetch_message(id)

    # one-time use invite
    @commands.command(help="Generate a one-time use invite to the system messages channel")
    @is_admin()
    async def otp(self, ctx, channel: typing.Optional[discord.TextChannel], *, reason: typing.Optional[str]):
        status = await ctx.send(f"Creating an invite for you...")
        invite = await (channel or ctx.guild.system_channel).create_invite(max_age=0, max_uses=1, reason=reason or f"{ctx.author} asked for a one-time-use invite.")
        await status.edit(content=f"{ctx.author.mention} asked for a one-time-use invite:\n\n{invite.url}")
        await ctx.message.delete()

    # destroy an invite
    @commands.command(help="Destroy an invite")
    @is_admin()
    async def rmotp(self, ctx, inv: discord.Invite, *, reason: typing.Optional[str]):
        status = await ctx.send(f"Deleting invite id {inv.id}")
        await inv.delete()
        await ctx.message.delete(delay=TMPMSG_DEFAULT)
        await status.edit(content=f"{ctx.author.mention} deleted invite **{inv.id}**.", delete_after=TMPMSG_DEFAULT)

    # list all users in a role
    @commands.command(help="List all the users with a given (set of) role(s)")
    @is_admin()
    async def lsrole(self, ctx, *, pattern: str):
        status = await ctx.send(f"Gathering users")
        users = []
        for u in ctx.guild.members:
            for r in u.roles:
                if r.guild == ctx.guild and re.match(pattern, r.name):
                    users.append(f"{u.name}#{u.discriminator}")
                    break
        found = len(users)
        idx = 0
        print(found)

        while True:
            print(idx)
            preview = '\n'.join(users[idx:idx+10])
            await status.edit(content=f"Here's entries {idx} through {idx+10}:\n{preview}")
            await status.add_reaction("⬅️")
            await status.add_reaction("➡️")
            try:
                r, _ = await self.bot.wait_for("reaction_add", check=lambda r, u: u == ctx.author and r.message.id == status.id, timeout=TMPMSG_DEFAULT)
            except asyncio.TimeoutError:
                break
            else:
                if r.emoji == "⬅️":
                    idx -= 10
                if r.emoji == "➡️":
                    idx += 10
                if idx >= found or idx <= 0:
                    idx = 0
                await status.clear_reaction("⬅️")
                await status.clear_reaction("➡️")

    # short info dump about a server
    @commands.command(help="Info dump about the server")
    @is_admin()
    async def infoDump(self, ctx):
        for c in ctx.guild.text_channels:
            await ctx.send(f"[{c.position}] {c.category.name if c.category else ''}/{c.name}: {c.topic}")

    # count messages
    @commands.command(help="Count messages matching a regex")
    async def count(self, ctx, chan: typing.Optional[discord.TextChannel], *, pattern: typing.Optional[str]):
        status = await ctx.send(f"Counting messages in {chan or ctx.channel} matching pattern `{pattern}`...")
        count = 0
        async for m in (chan or ctx).history(limit=5000):
            if re.search(pattern or ".*", m.content):
                count += 1
        await status.edit(content=f"Found {count} messages matching your query.")

    # bulk deletion tool
    @commands.command(name="d", help="Delete messages")
    @is_admin()
    async def delete(self, ctx, *args):
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
                r, _ = await self.bot.wait_for("reaction_add",
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