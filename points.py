#
# simple points system for users.
#

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
    async def points(self, ctx: commands.Context, chan: discord.TextChannel, kw: str):
        if chan is None:
            await ctx.send(f"Invalid invocation: channel {chan} does not exist.", delete_after=TMPMSG_DEFAULT)
            return

        await ctx.send(f"Listening for points with keyword '{kw}' in channel {chan}. Send `!!{kw}` close points.")
        status = await chan.send(f"Tell me who you want to put your raffle votes in for! Send `!@{kw} Name #` to this channel.")
        
        tallies=[]
        while True:
            m = await self.bot.wait_for("message", check=lambda m: (m.channel == chan or m.channel == ctx.channel) and m.content.startswith(("!@", "!!")))
            if m.author == ctx.author and m.content == f"!!{kw}":
                break
            tallies.append((m.author.name, m.content.split(' ')[1:]))
            await chan.send(f"Recorded!")

        await status.edit(content=f"Points have been collected! Recording now...")
        for t in tallies:
            try:
                cell = self._sheet.find(t[0])
                self._sheet.update_cell(cell.row, cell.col, t[1])
            except:
                self._sheet.update_cell(self._sheet.row_count, self._sheet.col_count, t[1])
                
        await chan.send(f"Stopped listening for points. Recorded {len(tallies)} tallies.")
