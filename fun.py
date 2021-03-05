import re
import asyncio
import typing
import discord
from discord.ext import commands
import random

from constants import *
from perms import *

# Chaos
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # shuffle users among a category of voice channels
    # TODO: opt-in shuffle
    @commands.command(help="Shuffle users about a category")
    @is_admin()
    async def shuf(self, ctx, *, chan: discord.CategoryChannel):
        status = await ctx.send(f"Okay, I'll shuffle users amongst {chan.name}.")
        random.seed()
        while True:
            await status.edit(content="Waiting for your reaction...")
            await status.add_reaction(OK_EMOJI)
            await status.add_reaction(NO_EMOJI)
            r, _ = await self.bot.wait_for(
                "reaction_add", check=lambda r, u: u == ctx.author
            )
            if r.emoji == NO_EMOJI:
                break

            await status.edit(content="Shuffling...")

            # shuffle the lads
            for m in [m for c in chan.voice_channels for m in c.members]:
                await m.move_to(random.choice(chan.voice_channels))

            await status.edit(content="Shuffled!")
            await status.clear_reaction(OK_EMOJI)
        await status.edit(content="Aborted.", delete_after=TMPMSG_DEFAULT)

    @commands.command(
        help="Select randomly from a list of users, role, or voice channel."
    )
    @is_admin()
    async def pick(
        self,
        ctx,
        *,
        ref: typing.Optional[
            typing.Union[
                discord.CategoryChannel, discord.VoiceChannel, discord.Role, str
            ]
        ],
    ):

        src = []
        if type(ref) is discord.CategoryChannel:
            src = [v.members for v in ref.voice_channels]
        elif type(ref) is discord.VoiceChannel:
            src = ref.members
        elif type(ref) is discord.Role:
            src = ref.members

        if type(ref) is str:
            await ctx.send(f"Chose '{random.choice(ref.split(','))}'!")
        elif src:
            await ctx.send(f"Chose {random.choice(src).mention}!")
        else:
            await ctx.send(
                f"Improper input. Use a nonempty category name, voice channel, role, or CSV,list,of,strings."
            )
