import os
import datetime as dt
import asyncio
import discord
from discord.ext import commands
import logging
import re
import time

import mgmt
from stream import *

CMD_PREFIX="~"

PREVIEW_COUNT=10
MSG_LIMIT=2000
DATETIME_FMT="%m/%d/%y|%H:%M"

OK_EMOJI='\U00002705'
NO_EMOJI='\U0000274C'
REPEAT_EMOJI='\U0001F501'
INPUT=[OK_EMOJI, NO_EMOJI, REPEAT_EMOJI]

ABOUT=r"""
こんにちはー
<@131994985682829312>が作ったボット、ウェルダーと申し上げます！
もっと知りたかったら「**//help**」ってどこでも送って下さいね！
"""

USAGE=r"**Usage message unavailable.**"

logging.basicConfig(level=logging.INFO)
cli = commands.Bot(command_prefix=CMD_PREFIX)

def preview_messages(msgs):
    return str('\n\n').join([f'{m.author}@{m.created_at} in #{m.channel}: {m.content[:50]}...' for m in msgs[:PREVIEW_COUNT]])[:1500]

@cli.event
async def on_ready():
    print(f'Successfully logged in as {cli.user}.')

# quick check for admin perms.
def is_admin():
    async def pred(ctx):
        return len([role for role in ctx.author.roles if role.permissions.administrator]) != 0
    return commands.check(pred)

@cli.command()
async def about(ctx):
    await ctx.channel.send(ABOUT, delete_after=30)

@cli.command(name='d')
@is_admin()
async def query(ctx, *args):
    status_message = await ctx.channel.send('Request received. Standby.')

    before = None            # lower bound on date range
    after = None             # upper bound on date range
    channels = [ctx.channel] # a specific channel to search, if need be
    author = ".*"            # author name regexp
    q = ".*"                 # search expr

    for a in args:
        try:
            separator = a.find('=')
            arg = a[:separator]
            val = a[separator + 1:]
        except:
            return None

        if arg == 'before':
            if val == 'now':
                before = dt.datetime.utcnow()
            else:
                before = dt.datetime.strptime(val, DATETIME_FMT)
        elif arg == 'after':
            after = dt.datetime.strptime(val, DATETIME_FMT)
        # TODO
        elif arg == 'channels':
            if val == 'all':
                channels = ctx.guild.text_channels
        elif arg == 'author':
            author = val
        elif arg == 'q':
            q = val
        
    def pred(m):
        return author == str(m.author) and re.search(q, str(m.content))

    await status_message.edit(content='Querying channel history...')

    msgs = []
    for c in channels:
        [msgs.append(m) async for m in c.history(limit=MSG_LIMIT, before=before, after=after) if pred(m)]
    msgs.reverse()
    if len(msgs) == 0:
        await status_message.edit(content='No results found!', delete_after=5)
        return
    else:
        await status_message.edit(content=f'Query completed successfully. Previewing results:\n```{preview_messages(msgs)}```')

    prompt = await ctx.channel.send('Ready to delete?')
    await prompt.add_reaction(OK_EMOJI)
    await prompt.add_reaction(NO_EMOJI)

    try:
        r, u = await cli.wait_for('reaction_add',
                                  timeout=30,
                                  check=lambda r, u: u == ctx.author and r.emoji in INPUT)
    except asyncio.TimeoutError:
        await prompt.edit(content='No reaction detected. Terminating transaction.', delete_after=5)
    else:
        await prompt.delete()
        if r.emoji == OK_EMOJI:
            await status_message.edit(content='Deleting messages...')
            await mgmt.bulk_delete(channel, msgs)
        else:
            await status_message.edit(content='Terminating transaction.', delete_after=5)
            return

    await status_message.edit(content='Transaction completed successfully.', delete_after=5)

"""TODO: Currently broken.
# handles starting and stopping of stream chats.
@client.event
async def on_voice_state_update(author, before, after):
    if before.channel is not after.channel:
        return

    guild = after.channel.guild
    dest_chan = guild.system_channel
    if dest_chan is None:
        dest_chan = guild.text_channels[0]

    # if they start streaming, then start tracking.
    if not before.self_stream and after.self_stream:
        m = await dest_chan.send('I noticed you\'re streaming! Do you want to turn on spoiler chat for this stream?')
        await m.add_reaction(OK_EMOJI)
        await m.add_reaction(BAD_EMOJI)

        try:
            react, user = await client.wait_for('reaction_add', check=lambda r, u: True, timeout = 15)
            print(react, user)
        except asyncio.TimeoutError:
            await m.delete()
            m = await dest_chan.send('No reaction detected. Bother me with \'//stream\' to turn it on if you want to turn it on later.')
        else:
            await react.message.delete()
            if react.emoji == OK_EMOJI:
                await dest_chan.send('Turning it on!')
                # start monitoring the stream.
                streams[author.id] = Stream.from_voice_state(author, after)
            else:
                await dest_chan.send('Okay, I won\'t.')
            await m.delete()

    # otherwise, terminate the prior stream chat.
    if before.self_stream and not after.self_stream:
        if streams.get(author.id) is not None:
            streams.pop(author.id)
            await dest_chan.send(f'Stopped monitoring <@{author.id}>\'s stream.')
"""

if __name__ == "__main__":
    try:
        cli.run(os.environ.get('TOKEN'))
    except:
        print('$TOKEN variable not set')