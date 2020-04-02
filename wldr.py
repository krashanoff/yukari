import os
import datetime as dt
import asyncio
import discord
import logging
import re
import time

import mgmt
from stream import *

CMD_PREFIX="//"
CMD_SEPARATOR="="
PREVIEW_COUNT=10
DATETIME_FMT="%m/%d/%y|%H:%M"
MSG_LIMIT=1000

OPS=['d', 's']

ABOUT=r"""
こんにちはー
<@131994985682829312>が作ったボット、ウェルダーと申し上げます！
もっと知りたかったら「**//help**」ってどこでも送って下さいね！
"""

USAGE=r"**Usage message unavailable.**"

logging.basicConfig(level=logging.INFO)
client = discord.Client(max_messages=None)

async def pretty_print_msg(message=discord.Message):
    return f'{message.author}@{message.created_at}: {message.content[:50]}...'

# get a filtered history of the messages in accordance to a regular expression.
# returns the message sent when searching and the list of results.
async def start_query(channel=discord.TextChannel,
                      before=dt.datetime,
                      after=dt.datetime,
                      pred=lambda m: True):
    status_message = await channel.send('Querying channel history...')
    msgs = [m async for m in channel.history(limit=MSG_LIMIT, before=before, after=after) if pred(m)]
    return (status_message, msgs)

# sed-like edit of messages within a query.
async def sed_mode(operation=str,
                       channel=discord.TextChannel,
                       user=discord.User,
                       before=dt.datetime,
                       after=dt.datetime,
                       authors=str,
                       search_exp=str,
                       replace_exp=None):
    m, msgs = await start_query(channel, before, after, lambda m: re.search(search_exp, m.content))

    # fail if no results.
    if len(msgs) == 0:
        await m.edit(content='No results found!', delete_after=5)
        return

    # handle preview of query.
    if operation == 'q' or operation == 'query':
        count = len(msgs) if len(msgs) < PREVIEW_COUNT else PREVIEW_COUNT
        msgs.reverse()
        preview_text = str('\n\n').join([await pretty_print_msg(m) for m in msgs[:count]])[:1500]
        await m.edit(content=f'Preview of results for query [{after}, {before}], matching `{search_exp}`:\n```{preview_text}\n...```')
        input_msg = await channel.send(f'What is your desired operation (from {OPS})?')

        try:
            cmd_select = await client.wait_for('message', timeout=30, check=lambda m: m.author == user and m.content in OPS)
        except asyncio.TimeoutError:
            await m.edit(content='No input detected.', delete_after=5)
            return
        else:
            operation = cmd_select.content

        await channel.delete_messages([input_msg, cmd_select])

    # execute the transaction.
    if operation == 'd' or operation == 'delete':
        await m.edit(content='Deleting messsages.')
        await mgmt.bulk_delete(channel, msgs)
    elif operation == 's' or operation == 'replace':
        await m.edit(content=f'Editing messages to match provided regexp: {replace_exp}')
        # TODO: replacement regex.

    await m.edit(content='Transaction completed successfully.', delete_after=5)

# handles parsing of command and passing control to
# command_mode.
async def issue_cmd(guild = discord.Guild,
                    channel = discord.TextChannel,
                    author = discord.User,
                    prefix = str,
                    args = list):
    print('{0}\t{1}::{2}::{3}\t\t{4}({5})'.format(dt.datetime.utcnow(), guild, channel, author, prefix, args))

    if prefix == 'help':
        await channel.send(USAGE)
        return
    if prefix == 'about':
        await channel.send(ABOUT)
        return
    if args is None:
        await channel.send('Not enough arguments!')
        return

    before = dt.datetime.utcnow()           # lower bound on date range
    after = dt.datetime.utcnow()            # upper bound on date range
    authors = ".*"                          # author name regexp
    regexp1 = ".*"                          # search expr
    regexp2 = None                          # replacement expr

    for a in args:
        try:
            separator = a.find(CMD_SEPARATOR)
            arg = a[1:separator]
            val = a[separator + 1:]
        except:
            await channel.send('Improperly structured argument.')
            return

        if arg == 'before':
            before = dt.datetime.strptime(val, DATETIME_FMT)
        elif arg == 'after':
            after = dt.datetime.strptime(val, DATETIME_FMT)
        elif arg == 'author':
            authors = val
        elif arg == 'r1':
            regexp1 = val
        elif arg == 'r2':
            regexp2 = val
    await sed_mode(prefix,
                   channel,
                   author,
                   before,
                   after,
                   authors,
                   regexp1,
                   regexp2)

@client.event
async def on_ready():
    print(f'Successfully logged in as {client.user}.')

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

        await issue_cmd(guild, channel, author, cmd, args)

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
        client.run(os.environ.get('TOKEN'))
    except:
        print('$TOKEN variable not set')