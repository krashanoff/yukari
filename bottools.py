import typing
import discord
from discord.ext import commands

from constants import *
from perms import *

# Bot admin and features
class BotTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # regurgitate some information about the bot.
    @commands.command(help="Info-dump about the bot")
    async def about(self, ctx):
        await ctx.channel.send(ABOUT)

    # regurgitate some information about yourself.
    @commands.command(help="Info-dump about the user and their perms")
    async def whoami(self, ctx):
        if is_leo()(ctx):
            await ctx.send(f"お父さん！")
        else:
            admin = is_admin()(ctx)
            await ctx.send(
                f"You are {ctx.author}. You are {'not ' if not admin else ''}an admin, and are not my dad.",
                delete_after=TMPMSG_DEFAULT,
            )

    # set bot status
    @commands.command(help="Set the bot status")
    @is_leo()
    async def status(self, ctx, *, status: str):
        await self.bot.change_presence(
            status=discord.Status.online, activity=discord.Game(name=status)
        )
        await ctx.send("Updated status.", delete_after=TMPMSG_DEFAULT)

    # say something
    @commands.command(help="Say something on your behalf")
    @is_leo()
    async def say(
        self,
        ctx,
        send_to: typing.Optional[typing.Union[discord.TextChannel, discord.User]],
        *,
        contents: str,
    ):
        if send_to:
            await send_to.send(contents)
        else:
            await ctx.send(contents)

    # keep a conversation
    @commands.command(help="Start a conversation with someone on behalf of the bot")
    @is_leo()
    async def convo(
        self, ctx, user: typing.Optional[discord.User], *, initial_msg: str
    ):
        portal = await ctx.send("```\nOpening the portal...\n```")
        msg = [
            m.content
            async for m in (user.dm_channel or await user.create_dm()).history()
        ]
        await portal.edit(
            content=f"Got some messages: {msg}", delete_after=TMPMSG_DEFAULT
        )
