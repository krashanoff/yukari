import discord
import datetime as dt

DATETIME_FMT="%m/%d/%y|%H:%M"
MSG_LIMIT=2000

class Query:
    def __init__(self,
                 channel,
                 before,
                 after,
                 author,
                 search_exp):
        self.channel = channel
        self.before = before
        self.after = after
        self.author = author
        self.search_exp = search_exp

    def __repr__(self):
        return f's({self.before}-{self.after}\t{self.search_exp})'
        
    @staticmethod
    def from_args(channel, args):
        before = None            # lower bound on date range
        after = None             # upper bound on date range
        author = ".*"            # author name regexp
        q = ".*"                 # search expr

        for a in args:
            try:
                separator = a.find(CMD_SEPARATOR)
                arg = a[1:separator]
                val = a[separator + 1:]
            except:
                return None

            if arg == 'before':
                before = dt.datetime.strptime(val, DATETIME_FMT)
            elif arg == 'after':
                after = dt.datetime.strptime(val, DATETIME_FMT)
            elif arg == 'author':
                author = val
            elif arg == 'q':
                q = val
        
        return Query(channel, before, after, author, q)

    # get a filtered history of the messages in accordance to a regular expression.
    # returns the message sent when searching and the list of results.
    async def start_query(self):
        status_message = await self.channel.send('Querying channel history...')
        msgs = [m async for m in self.channel.history(limit=MSG_LIMIT, before=before, after=after) if pred(m)]
        return (status_message, msgs)