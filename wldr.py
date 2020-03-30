import os
import datetime as dt
import asyncio
import discord
import logging
import re
import time

from anitools import ani
import mgmt
from stream import *

CMD_PREFIX="//"
MSG_LIMIT=1000

REACTION_CMD={
                'd': '\N{fire}',
                'e': '\N{comet}'
                #['l', 'log']: '\N{memo}'
             }

MEDIA_TYPES={'a': 'anime', 'm': 'manga'}
DATETIME_FMT=r"%m/%d/%y|%H:%M"

ABOUT=r"""
こんにちはー
<@131994985682829312>が作ったボット、ウェルダーと申し上げます！
もっと知りたかったら「**//h**」ってどこでも送って下さいね！
"""

USAGE=r"**Still working on this. Bear with it**"

logging.basicConfig(level=logging.INFO)
client = discord.Client(max_messages=None)
streams = {str: Stream}

# command line supporting mass deletion, editing of
# messages.
async def command_mode(channel, args):
    issue_time = dt.datetime.utcnow()
    from_time = dt.datetime.utcnow()
    to_time = dt.datetime.utcnow()
    regexp1 = ".*"
    regexp2 = None
    action = None

    for a in args:
        try:
            separator = a.find(':')
            cmd = a[1:separator]
            val = a[separator + 1:]
        except:
            await channel.send('Improperly structured argument.')
            return

        if cmd == 'from':
            from_time = dt.datetime.strptime(val, DATETIME_FMT)
        elif cmd == 'to':
            to_time = dt.datetime.strptime(val, DATETIME_FMT)
        elif cmd == 'r1':
            regexp1 = val
        elif cmd == 'r2':
            regexp2 = val
        elif cmd == 'a':
            action = val

    msgs = [m async for m in channel.history(limit=MSG_LIMIT, before=to_time, after=from_time) if re.match(regexp1, m.content)]
    replace_complete = False if ((action == 'r' or action == 'replace') and regexp2 is None) else True

    # handle previews query for incomplete replace or action.
    if action is None or not replace_complete:
        count = len(msgs) if len(msgs) < 3 else 3
        preview_text = str('\n').join([m.content for m in msgs[:count]])
        m1 = await channel.send(f'Query incomplete. Previewing results:\n{preview_text}')

        if replace_complete:
            m2 = await channel.send('Please provide a replacement regexp for your action.')
            # TODO
        else:
            m2 = await channel.send('What is your desired operation?')
            await m2.reaction_add(REACTION_CMD)

    # we strike.
    if action == 'd' or action == 'delete':
        m = await channel.send('Deleting messsages.')
    if action == 'e' or action == 'edit':
        m = await channel.send('Editing messages in accordance to ')

    m = await channel.send('Transaction completed successfully.')
    time.sleep(5)
    await m.delete()

# process user command input
async def process_input(guild = discord.Guild,
                        channel = discord.TextChannel,
                        author = discord.User,
                        prefix = str,
                        args = list):
    print('{0}\t{1}::{2}::{3}\t\t{4}({5})'.format(dt.datetime.utcnow(), guild, channel, author, prefix, args))

    if prefix == 'help' or prefix == 'h':
        await channel.send(USAGE)

    # delete messages
    elif prefix == 'c' and args is not None:
        await command_mode(channel, args)

    # search MAL or AniList, defaulting to MAL.
    elif prefix[0] == 's' and len(prefix) <= 2 and args is not None:
        media_type = 'anime'

        await channel.trigger_typing()

        # search for manga only if explicitly specified.
        if len(prefix) == 2:
            if prefix[-1] not in MEDIA_TYPES:
                await channel.send('invalid media type')
                return
            else:
                media_type = MEDIA_TYPES[prefix[-1]]

        # searches using AniList's API.
        name = str(' ').join(args[0:])
        search_result = await ani.search(media_type, name)

        # uses AniList results by default.
        if search_result is not None:
            await channel.send(search_result)
        else:
            await channel.send('search failed!')
    
    # fetch seasonal chart
    elif prefix == 'chart':
        await channel.send(ani.seasonal_chart_url())
        
    elif prefix == 'about':
        await channel.send(ABOUT)
    else:
        await channel.send(u'ごめんね！その命令正しくありません')

@client.event
async def on_ready():
    print(u'\"{0}\"としてログインしてきました。準備完了。'.format(client.user))

@client.event
async def on_message(message):
    guild = message.guild
    channel = message.channel
    author = message.author
    content = str(message.content)

    # if the author isn't an admin on the server, then don't let them use the bot.
    if len([role for role in author.roles if role.permissions.administrator]) == 0:
        return

    # parse command
    if content[:2] == CMD_PREFIX:
        try:
            arg_start = content.index(' ')
            cmd = content[2:arg_start]
            args = content[arg_start + 1:].split(' ')
        except:
            arg_start = None
            cmd = content[2:]
            args = None

        await process_input(guild, channel, author, cmd, args)

"""
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

        # TODO: Currently broken.
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
        client.run(os.environ.get('TOKEN'))
    except:
        print('$TOKEN variable not set')