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
                 pred):
        self.channel = channel
        self.before = before
        self.after = after
        self.author = author
        self.pred = pred
        self.results = None

    def __repr__(self):
        return f's({self.before}-{self.after}\t{self.pred})'
        
    @staticmethod
    def from_args(channel, args):
        before = None            # lower bound on date range
        after = None             # upper bound on date range
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
                # TODO: Parse datetime in slightly more clean manner.
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
    async def run(self):
        msgs = [m async for m in self.channel.history(limit=MSG_LIMIT, before=self.before, after=self.after) if self.pred(m)]
        return msgs