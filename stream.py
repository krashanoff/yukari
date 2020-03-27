import datetime as dt
import discord

class Stream:
    def __init__(self,
                 host = discord.User,
                 channel = discord.VoiceChannel,
                 viewership = {discord.User: [dt.datetime]},
                 start_time = dt.datetime.utcnow(),
                 end_time = None,
                 spoiler_chat = False):
        self.host = host
        self.channel = channel

        # list of 2-element tuples of viewing
        # start time and end times associated
        # a particular user, whose id is the
        # key to the list.
        self.viewership = viewership

        self.start_time = start_time
        self.end_time = end_time
        self.spoiler_chat = spoiler_chat

    # is the stream still on?
    def ongoing(self):
        return self.end_time is not None

    # TODO:
    # update if necessary.
    def update(self, user = discord.User, update = discord.VoiceState):
        # check if the update is negligible or if the stream is over.
        if (update.channel != self.channel) or (user != self.host) or self.end_time is not None:
            return

        log = self.viewership[user.id]
        final_timestamp = log[-1][1]

        # if we are updating the status of our streamer,
        # then check if the stream is ending.
        if user == self.host and self_stream is False:
            self.end_time == dt.datetime.utcnow()
            for v in viewership.values():
                if v[-1][1] is None:
                    v[-1][1] = self.end_time
            return

        # if the user has left the voice channel,
        # update their log
        if update.channel is None:
            log[-1][1] = dt.datetime.utcnow()
        # otherwise, the user has joined the voice channel.
        else:
            log.append((dt.datetime.utcnow(), None))

    # create a Stream instance from a voice state update.
    @staticmethod
    def from_voice_state(host = discord.User, update = discord.VoiceState):
        # acquire viewership from the server.
        viewership = {}

        for user in update.channel.members:
            viewership[user.id] = [(dt.datetime.utcnow(), None)]

        return Stream(host, viewership)

async def get_streamers(channel = discord.VoiceChannel):
    return [state for state in channel.voice_states.values() if state.self_stream]