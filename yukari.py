#! env/bin/python
#
# yukari
#

import asyncio
import datetime as dt
import logging
import os
import re
import socket
import time
import typing

import random
random.seed()

import discord
from discord.ext import commands

from constants import *

from util import Util
from bottools import BotTools

logging.basicConfig(level=logging.INFO)
cli = commands.Bot(command_prefix=CMD_PREFIX)

@cli.event
async def on_ready():
    print(f"Successfully logged in as {cli.user}.")
    await cli.change_presence(status=discord.Status.online,
                              activity=discord.Game(name=STARTUP_STATUS[int(random.randint(0, len(STARTUP_STATUS) - 1))]))

# cog setup
cli.add_cog(Util(cli))
cli.add_cog(BotTools(cli))

if __name__ == "__main__":
    # bind for Heroku
    port = int(os.environ.get("PORT") or 8080)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", port))
    sock.listen(1)
    print(f"Bound to port {port}")

    try:
        cli.run(os.environ.get("TOKEN"))
    except AttributeError:
        print("An environment variable is not set.")