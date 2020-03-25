"""mgmt
Management tools. Perms, etc.
"""

import datetime as dt
import discord

# add/remove, guild, user.
async def mod_perms(ar, guild, user):
    if ar <= 0:
        # TODO: remove perms
        pass
    else:
        # TODO: add perms
        pass

# delete messages from a particular date onwards.
async def delete_from(date, channel, filter = lambda message: message, limit = 200):
    to_delete = [filter(m) async for m in channel.history(limit=limit, after=date)]

    if dt.timedelta(days=14) <= (dt.datetime.utcnow() - date):
        # if it is beyond 14 days, we have to delete one-by-one.
        for m in to_delete:
            await m.delete()
    else:
        # otherwise, we are okay to delete in bulk.
        await channel.delete_messages(to_delete)