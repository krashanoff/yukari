import discord
import sqlite3
from discord.ext import commands

from constants import *
from perms import *


class Board(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
