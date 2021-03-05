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
import gspread
from dotenv import load_dotenv

load_dotenv(verbose=True)

from constants import *

from util import Util
from bottools import BotTools
from fun import Fun
from points import Points

logging.basicConfig(level=logging.INFO)
cli = commands.Bot(command_prefix=CMD_PREFIX)


@cli.event
async def on_ready():
    print(f"Successfully logged in as {cli.user}.")
    await cli.change_presence(
        status=discord.Status.online,
        activity=discord.Game(
            name=STARTUP_STATUS[int(random.randint(0, len(STARTUP_STATUS) - 1))]
        ),
    )


# Cog setup
cli.add_cog(Util(cli))
cli.add_cog(BotTools(cli))
cli.add_cog(Fun(cli))

if __name__ == "__main__":
    try:
        gc = gspread.service_account(filename=os.environ.get("CREDENTIALS"))
        sheet = gc.open_by_key(os.environ.get("SPREADSHEET")).sheet1
        cli.add_cog(Points(cli, sheet))
    except:
        print(
            "Failed to start Google Drive interface. Points functionality will be disabled."
        )

    try:
        cli.run(os.environ.get("TOKEN"))
    except AttributeError:
        print("An environment variable is not set.")
