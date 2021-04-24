import re
import asyncio
from sys import flags
import typing
from io import StringIO
from datetime import datetime
import re

from rich import inspect

import discord
from discord.channel import DMChannel
from discord.ext import commands
from discord.ext.commands.core import command

from constants import *
from perms import *

Nukable = typing.Union[
    discord.CategoryChannel,
    discord.TextChannel,
    discord.VoiceChannel,
    discord.Message,
    discord.Member,
]

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
            eval(
                msg,
                {
                    "g": ctx.guild,
                    "c": ctx.channel,
                    "print": contained_print,
                },
            )
            await status.edit(content="Evaluated.", delete_after=TMPMSG_DEFAULT)
            await ctx.send(f"Output:\n{out.getvalue() or 'Nothing'}")
        except SyntaxError:
            await ctx.send("Syntax error.")
        except:
            await ctx.send("Something very weird happened.")

    @commands.command(help="Temporarily forward DMs to another channel.")
    @is_admin()
    async def fwd(
        self, ctx: commands.Context, chan: typing.Optional[discord.TextChannel]
    ):
        if not chan:
            chan = ctx.channel
        await ctx.send(f"Forwarding DMs to {chan.name}.")
        while True:
            m = await self.bot.wait_for(
                "message",
                check=lambda m: type(m.channel) is discord.DMChannel
                or (type(m.channel) is discord.DMChannel and m.author == ctx.author),
            )
            if m.author == ctx.author and m.content == "!@stop":
                break
            await chan.send(f"```\n{m.author.name}:\n{m.content}\n```"[:2000])
        await ctx.send(f"Stopped forwarding messages.")

    @commands.command(
        name="dmp",
        help="Dump messages from your current channel to a file on your local machine.",
    )
    @is_admin()
    async def dump_msgs(self, ctx: commands.Context, filename: typing.Optional[str]):
        status = await ctx.send(f"Started downloading chat history...")

        with open(
            (
                filename
                or f"{ctx.channel.name or 'unknown'}-{datetime.utcnow().strftime('%m-%d-%Y-%H-%M')}"
            ),
            "a+",
        ) as outfile:
            count = 0
            outfile.write(
                f"Started new dump on {datetime.utcnow().strftime('%m-%d-%Y-%H-%M')}.\n---\n"
            )
            outfile.write("Author (Creation Date, Edit Date):\nContent\n\n")
            async for m in ctx.history(limit=None):
                outfile.write(
                    f"{m.author} ({m.created_at}, {m.edited_at}):\n{m.content}\n\n"
                )
                count += 1
                await status.edit(content=f"Read {count} messages to {outfile.name}")

    # one-time use invite
    @commands.command(
        help="Generate a one-time use invite to the system messages channel"
    )
    @is_admin()
    async def otp(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel],
        *,
        reason: typing.Optional[str],
    ):
        status = await ctx.send(f"Creating an invite for you...")
        invite = await (channel or ctx.guild.system_channel).create_invite(
            max_age=0,
            max_uses=1,
            reason=reason or f"{ctx.author} asked for a one-time-use invite.",
        )
        await status.edit(
            content=f"{ctx.author.mention} asked for a one-time-use invite:\n\n{invite.url}"
        )
        await ctx.message.delete()

    # destroy an invite
    @commands.command(help="Destroy an invite")
    @is_admin()
    async def rmotp(self, ctx, inv: discord.Invite, *, reason: typing.Optional[str]):
        status = await ctx.send(f"Deleting invite id {inv.id}")
        await inv.delete()
        await ctx.message.delete(delay=TMPMSG_DEFAULT)
        await status.edit(
            content=f"{ctx.author.mention} deleted invite **{inv.id}**.",
            delete_after=TMPMSG_DEFAULT,
        )

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
            preview = "\n".join(users[idx : idx + 10])
            await status.edit(
                content=f"Here's entries {idx} through {idx+10}:\n{preview}"
            )
            await status.add_reaction("⬅️")
            await status.add_reaction("➡️")
            try:
                r, _ = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: u == ctx.author and r.message.id == status.id,
                    timeout=TMPMSG_DEFAULT,
                )
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
    async def infoDump(
        self, ctx, ignore: typing.Optional[typing.List[discord.TextChannel]]
    ):
        for c in filter(lambda c: c not in (ignore or []), ctx.guild.text_channels):
            await ctx.send(
                f"[{c.position}] {c.category.name if c.category else ''}/{c.name}: {c.topic}"
            )

    # count messages
    @commands.command(help="Count messages matching a regex")
    async def count(
        self,
        ctx,
        chan: typing.Optional[discord.TextChannel],
        *,
        pattern: typing.Optional[str],
    ):
        status = await ctx.send(
            f"Counting messages in {chan or ctx.channel} matching pattern `{pattern}`..."
        )
        count = 0
        async for m in (chan or ctx).history(limit=5000):
            if re.search(pattern or ".*", m.content):
                count += 1
        await status.edit(content=f"Found {count} messages matching your query.")

    # create lots of things
    @commands.command(
        help=f"""
Quickly create channels and categories using the provided syntax.

Usage: {CMD_PREFIX}create [categories or channels...]

catName/(.*,)+(.*) = Comma-delimited channel names.
#chan = Text channel visible to your highest current role.
chan = Voice channel visible to your highest current role.
chan+r = Voice channel 'chan' that is visible to everyone with
         role 'r'.

Example:
{CMD_PREFIX}create catName/#chan1,chan2,chan3 catTwo
"""
    )
    async def create(self, ctx, *args):
        # Acquire user's highest ranked role.
        default_perms = ctx.author.roles[-1]

        status = await ctx.send(
            f'New channels will be visible to members with the "{default_perms.name}" role by default.'
        )

        for info in args:
            await status.edit(content=f"Now creating category `{info}`")

            info = info.split("/")
            category_name = "".join(info[:-1])
            channels = [name for name in info[-1].split(",")]

            cat = await ctx.guild.create_category(category_name)
            for name in channels:
                if name.startswith("#"):
                    await cat.create_text_channel(name)
                else:
                    await cat.create_voice_channel(name)

        await status.edit(
            content="Created category and channels.", delete_after=TMPMSG_DEFAULT
        )

    # delete lots of things
    @commands.command(help="Delete a variety of things quickly and without remorse.")
    @is_leo()
    async def nuke(self, ctx, target: Nukable):
        target_type = type(target)

        status = await ctx.send(
            f"Okay, I'll delete `{str(target)}`. It is of type `{target_type}`. You have {TMPMSG_DEFAULT} seconds to confirm."
        )
        await status.add_reaction(NO_EMOJI)
        await status.add_reaction(OK_EMOJI)

        try:
            r, _ = await self.bot.wait_for(
                "reaction_add",
                timeout=TMPMSG_DEFAULT,
                check=lambda r, u: u == ctx.author and r.emoji in INPUT,
            )
        except asyncio.TimeoutError:
            await status.edit(content="Aborted!", delete_after=TMPMSG_DEFAULT)
        else:
            if r.emoji == NO_EMOJI:
                await status.edit(content="Aborted!", delete_after=TMPMSG_DEFAULT)
                return
            if r.emoji == OK_EMOJI:
                await status.edit(content="Aight.")

        if target_type == discord.CategoryChannel:
            for c in target.channels:
                await c.delete(reason=f"Nuked by {ctx.author}.")
            await target.delete(reason=f"Nuked by {ctx.author}.")
        elif target_type == (
            discord.TextChannel or discord.VoiceChannel or discord.Message
        ):
            await target.delete(reason=f"Nuked by {ctx.author}")
        elif target_type == discord.Member:
            await target.kick(reason=f"Nuked by {ctx.author}")

        await status.edit(content="It is done.")
