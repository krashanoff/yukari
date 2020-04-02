"""mgmt
Management tools.
"""

import datetime as dt
import discord

# intelligently delete messages in bulk.
async def bulk_delete(channel=discord.TextChannel, msgs=[discord.Message]):
    if len(msgs) <= 0:
        return
    
    if len(msgs) == 1:
        await msgs[0].delete()
        return

    bulk_deletable = []
    for m in msgs:
        # can only bulk delete messages that are less than 14 days old.
        if dt.datetime.utcnow() - m.created_at <= dt.timedelta(days=14):
            bulk_deletable.append(m)

            # can delete at most 100 messages
            if len(bulk_deletable) == 100:
                await channel.delete_messages(bulk_deletable)
                bulk_deletable.clear()
        else:
            await m.delete()

    await channel.delete_messages(bulk_deletable)