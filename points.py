#
# simple points system for users.
#

import re
from collections import defaultdict

import discord
from discord.ext import commands

from perms import *
from constants import *

class Points(commands.Cog):
    def __init__(self, bot, sheet):
        self.bot = bot
        self._sheet = sheet
    
    @commands.command(help="Open points tracking for the server.")
    @is_admin()
    async def points(self, ctx: commands.Context, chan: discord.TextChannel, amount: int, secret: str):
        if chan is None:
            await ctx.send(f"Invalid invocation: channel {chan} does not exist.", delete_after=TMPMSG_DEFAULT)
            return

        cups = self._sheet.row_values(1)
        await ctx.send(f"\
You have allowed people in {chan} to use up to {amount} tickets. \
According to the spreadsheet, people can choose to put their tickets \
in the following cups: {', '.join(cups)}.\n\n\
Send `!!{secret}` to this channel to close points.")

        # Get possible "cups".
        await chan.send(f"Tell me whose cup you want to put your raffle \
tickets in! Send `!@{secret} # Name` to this channel.\n\n\
You each have **{amount} tickets** to put in any of the following cups (case-sensitive): {', '.join(cups)}.")
        
        # Collect deposits.
        # TODO: Limit amount depositable.
        tallies = { name: [] for name in cups }
        tallies_left = defaultdict(lambda: amount)
        while True:
            m = await self.bot.wait_for("message", check=lambda m: m.channel in [chan, ctx.channel] and m.content.startswith(("!@", "!!")))

            # Break the loop if the author stops collection.
            if m.author == ctx.author and m.channel == ctx.channel and m.content == f"!!{secret}":
                break

            # Otherwise, parse the content for vote information.
            author = f"{m.author.name}#{m.author.discriminator}"
            arr = m.content.split(' ')
            cup = ' '.join(arr[2:])
            amt = int(arr[1])

            if cup not in tallies:
                await chan.send(f"{m.author.mention}, please use one of the following cups: {cups}")
            else:
                deposited = 0

                # Check that the user has some tickets to spare.
                if tallies_left[author] <= 0:
                    await chan.send(f"{m.author.mention}: You have no tickets left to use!")
                elif tallies_left[author] < amt:
                    await chan.send(f"{m.author.mention}: You only had {tallies_left[author]} tickets left, so I will just put the rest in.")
                    deposited = tallies_left[author]
                    tallies_left[author] = 0
                else:
                    await chan.send(f"{m.author.mention}: Recorded your deposit of {amt} tickets for {cup}.")
                    deposited = amt
                    tallies_left[author] -= amt

                for _ in range(deposited):
                    tallies[cup].append(author)

        # Write deposits.
        # TODO: efficiency.
        status = await chan.send(content=f"Collection period has ended! Writing results now...")
        update = [ [] for _ in range(max([ len(tallies[k]) for k in tallies ])) ]
        for i in range(len(update)):
            for k in tallies:
                if i < len(tallies[k]):
                    update[i].append(tallies[k][i])
                else:
                    update[i].append("")
        print(update)
        self._sheet.append_rows(update)
        await status.edit(content=f"Wrote tally records.")
