import os
import datetime as dt
import discord

import mgmt
import mal
import ani

CMD_PREFIX="//"

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
async def process_input(guild, channel, author, prefix, args):
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

    # search MAL or AniList
    elif prefix == 's' and args is not None and len(args) > 1:
        if args[0].upper() == 'MAL':
            q = str(' ').join(args[1:])
            r = mal.search(q)
            await channel.send(str(r)[:1500])
        elif args[0].upper() == 'AL':
            pass # TODO: finish anilist queries
            q = str(' ').join(args[1:])
            r = await anilist.search_anime(q)
            await channel.send(r)
    
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

if __name__ == "__main__":
    try:
        client.run(os.environ.get('TOKEN'))
    except:
        print('$TOKEN variable not set')