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
from query import *

CMD_PREFIX="//"
CMD_SEPARATOR="="
PREVIEW_COUNT=10

OPS=['d', 's']

ABOUT=r"""
こんにちはー
<@131994985682829312>が作ったボット、ウェルダーと申し上げます！
もっと知りたかったら「**//help**」ってどこでも送って下さいね！
"""

USAGE=r"**Usage message unavailable.**"

logging.basicConfig(level=logging.INFO)
cli = commands.Bot(command_prefix=CMD_PREFIX)

async def pretty_print_msg(message=discord.Message):
    return f'{message.author}@{message.created_at}: {message.content[:50]}...'

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

@cli.command(name='s')
@is_admin()
async def sed(ctx: commands.Context, *args):
    await ctx.channel.send(Query.from_args(args))

# sed-like edit of messages within a query.
async def sed_mode(operation=str,
                       channel=discord.TextChannel,
                       user=discord.User,
                       before=dt.datetime,
                       after=dt.datetime,
                       authors=str,
                       search_exp=str,
                       replace_exp=None):
    m, msgs = await start_query(channel,
                                before,
                                after,
                                lambda m: re.search(search_exp, m.content) and re.match(authors, str(m.author)))

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
            cmd_select = await cli.wait_for('message', timeout=30, check=lambda m: m.author == user and m.content in OPS)
        except asyncio.TimeoutError:
            await input_msg.delete()
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
        # handle replacement.
        if replace_exp is None:
            input_msg = await channel.send(f'What is your replacement regex? For reference, your search expression is: \"{search_exp}\"')
            try:
                search_exp = await cli.wait_for('message', timeout=30, check=lambda m: m.author == user)
            except asyncio.TimeoutError:
                m.edit(content='No input detected.', delete_after=5)
                return
            else:
                search_exp = str(search_exp.content)

        await m.edit(content=f'Editing messages to match provided regexp: {replace_exp}')
        # TODO: replacement.

    await m.edit(content='Transaction completed successfully.', delete_after=5)

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