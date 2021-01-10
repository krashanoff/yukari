#
# simple points system for users.
#

import asyncio
import re
import random
from collections import defaultdict

import discord
from discord.ext import commands

from perms import *
from constants import *

DEPOSIT_PREFIX="!@"
CLOSE_PREFIX="!!"

class Points(commands.Cog):
    def __init__(self, bot, sheet):
        self.bot = bot
        self._sheet = sheet

    @commands.command(help="List available cups.")
    async def cups(self, ctx: commands.Context):
        await ctx.send(f"The cups you are able to deposit into (case-sensitive) are: {self._sheet.row_values(1)}")

    @commands.command(name="pickWinner", help="Pick a random winner for the given 'cup'!")
    @is_officer()
    async def pick(self, ctx: commands.Context, cup: str):
        # tranpose list of rows to dictionary mapping header
        # to column values.
        sheet = self._sheet.get_all_values()
        d = { name: [ row[index] for row in sheet[1:] if row[index] != "" ] for index, name in enumerate(sheet[0]) }
        if cup not in d:
            await ctx.send(f"Cup '{cup}' doesn't exist.")
        elif len(d[cup]) == 0:
            await ctx.send(f"Selected cup '{cup}' has no votes.")
        else:
            status = await ctx.send(f"Here we go!")
            await asyncio.sleep(0.5)
            for i in range(5, 0, -1):
                await status.edit(content=f"Picking your random winner in {i}...")
                await asyncio.sleep(1)
            await status.edit(content=f"**YOUR WINNER FOR THE {cup.upper()} CUP IS...**\n{random.choice(d[cup])}!")

    @commands.command(help="Manually deposit some amount of tickets for an user.")
    @is_officer()
    async def deposit(self, ctx: commands.Context, user: discord.User, cup: str, amount: int):
        cups = self._sheet.row_values(1)
        status = await ctx.send(f"Found {cups} cups for deposit...")
        if cup in cups:
            await status.edit(content=f"Making a deposit of {amount} tickets for {user} into cup {cup}.")
            position = cups.index(cup)
            for _ in range(amount):
                deposit_record = [ '' for _ in range(len(cups)) ]
                deposit_record[position] = f"{user.name}#{user.discriminator}"
                self._sheet.append_row(deposit_record)
            await status.edit(content=f"Wrote a deposit of {amount} tickets for {user} into cup {cup}.")
        else:
            await status.edit(content=f"Cup {cup} does not exist!")
    
    @commands.command(help="Open ticket tracking for the server.")
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
Send `{CLOSE_PREFIX}{secret}` to this channel to close points.")

        # Get possible "cups".
        await chan.send(f"Tell me whose cup you want to put your raffle \
tickets in! Send `{DEPOSIT_PREFIX}{secret} # Name` to this channel.\n\n\
You each have **{amount} tickets** to put in any of the following cups (case-sensitive): {', '.join(cups)}.")
        
        # Collect deposits.
        # TODO: Limit amount depositable.
        tallies = { name: [] for name in cups }
        tallies_left = defaultdict(lambda: amount)
        while True:
            m = await self.bot.wait_for("message", check=lambda m: m.channel in [chan, ctx.channel] and m.content.startswith((DEPOSIT_PREFIX, CLOSE_PREFIX)))

            # Break the loop if the author stops collection.
            if m.author == ctx.author and m.channel == ctx.channel and m.content == f"{CLOSE_PREFIX}{secret}":
                break
                
            # Ignore stop commands.
            if m.content.startswith(CLOSE_PREFIX):
                continue

            # Otherwise, parse the content for vote information.
            try:
                author = f"{m.author.name}#{m.author.discriminator}"
                arr = m.content.split(' ')
                cup = ' '.join(arr[2:])
                amt = int(arr[1])
            except:
                continue

            if cup not in tallies:
                await chan.send(f"{m.author.mention}, please use one of the following cups: {cups}")
            else:
                deposited = 0

                # Check that the user has some tickets to spare.
                if tallies_left[author] <= 0:
                    await chan.send(f"{m.author.mention}: You have no tickets left to use!")
                elif tallies_left[author] < amt:
                    await chan.send(f"{m.author.mention}: You only had {tallies_left[author]} ticket(s) left, so I will just put the rest in.")
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
        await status.edit(content=f"**I have stopped listening for deposits. Your deposits have been recorded.**")
        await chan.send(f"Stopped listening. Wrote back records.")
