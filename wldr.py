import os
import datetime as dt
import asyncio
import discord

from anitools import ani
import mgmt
from stream import *

CMD_PREFIX="//"
OK_EMOJI="\U00002705"
BAD_EMOJI="\U0000274C"

MEDIA_TYPES={'a': 'anime', 'm': 'manga'}

ABOUT=r"""
こんにちはー
<@131994985682829312>が作ったボット、ウェルダーと申し上げます！
もっと知りたかったら「**//h**」ってどこでも送って下さいね！
"""

USAGE=r"""
**Commands you'll probably want to use**
```
# NOTE: deletions of messages older than 14 days is
# incredibly slow.
# there is a limit on the number of messages you can
# bulk delete, of 100.
//d 1s                      # delete messages from 1 second ago
//d 2m                      # delete messages from 2 minutes ago
//d 3h                      # delete messages from 3 hours ago
//d 4d                      # delete messages from 4 days ago
//d 5w                      # delete messages from 5 weeks ago

//c                         # current seasonal AniChart

//s {mal, ani} [SEARCH]     # search MyAnimeList or AniList for SEARCH.

//about                     # about the bot.
//help                      # this text.
```
**Commands that exist, but might not see use**
These are mostly permissions. When you add the bot, it initially allows all users to use its commands.
```
# grant yourself or another user the ability to control this bot.
# the server owner can only use this initially.
//permg {me, @USER#TAG}

# remove permissions from another user.
//permr {me, @USER#TAG}
```
"""

client = discord.Client(max_messages=None)
streams = {str: Stream}

# fairly intricate routine used for deletion of messages.
async def delete_mode(channel, args):
    try:
        magnitude = float(args[0][:-1])
    except:
        magnitude = -1

    if magnitude < 0:
        await channel.send('Invalid time magnitude.')
        return

    unit = args[0][-1]

    # switch/case for time unit
    if unit == 's':
        delta = dt.timedelta(seconds=magnitude)
    elif unit == 'm':
        delta = dt.timedelta(minutes=magnitude)
    elif unit == 'h':
        delta = dt.timedelta(hours=magnitude)
    elif unit == 'd':
        delta = dt.timedelta(days=magnitude)
    elif unit == 'w':
        delta = dt.timedelta(weeks=magnitude)

    if delta > dt.timedelta(weeks=52):
        await channel.send('I cannot delete more than six month\'s worth of messages at once!')
        return

    try:
        await mgmt.delete_from(dt.datetime.utcnow() - delta, channel)
    except:
        await channel.send('Failed to delete messages!')
        return
    
    await channel.send('Transaction completed successfully.')

# process user command input
async def process_input(guild = discord.Guild,
                        channel = discord.TextChannel,
                        author = discord.User,
                        prefix = str,
                        args = list):
    print('{0}\t{1}::{2}::{3}\t\t{4}({5})'.format(dt.datetime.utcnow(), guild, channel, author, prefix, args))

    if prefix == 'help' or prefix == 'h':
        await channel.send(USAGE)

    # grant perms
    elif prefix == 'permg' and args is not None:
        if args[0] == 'me' and author == guild.owner:
            await mgmt.mod_perms(1, guild, author)
            await channel.send(u'許可与えました。')

    # revoke perms
    elif prefix == 'permr':
        await mgmt.mod_perms(0, guild, args[0])

    # delete messages
    elif prefix == 'd' and args is not None:
        await delete_mode(channel, args)

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
    elif prefix == 'c':
        await channel.send(ani.seasonal_chart_url())
        
    elif prefix == 'about':
        await channel.send(ABOUT)
    else:
        await channel.send(u'ごめんね！その命令正しくありません')

@client.event
async def on_ready():
    print(u'\"{0}\"としてログインしてきました。'.format(client.user))
    print(u'現在、モニター中ギルド：{0}'.format(client.guilds))

@client.event
async def on_message(message):
    guild = message.guild
    channel = message.channel
    author = message.author
    content = str(message.content)

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
            react, user = await client.wait_for('reaction_add', timeout = 45, check = lambda r, u: u == author and (r.emoji in [OK_EMOJI, BAD_EMOJI]))
        except asyncio.TimeoutError:
            await dest_chan.send('No reaction detected. Bother me with \'//stream\' to turn it on if you want to turn it on later.')
        else:
            print(react, user)
            if react.emoji == OK_EMOJI:
                await dest_chan.send('Turning it on!')
                # start monitoring the stream.
                streams[author.id] = Stream.from_voice_state(author, after)
            else:
                await dest_chan.send('Okay, I won\'t.')

    # otherwise, terminate the prior stream chat.
    if before.self_stream and not after.self_stream:
        if streams.pop(author.id) is not None:
            streams.pop(author.id)
            await dest_chan.send('Stopped monitoring your stream.')

if __name__ == "__main__":
    try:
        client.run(os.environ.get('TOKEN'))
    except:
        print('$TOKEN variable not set')