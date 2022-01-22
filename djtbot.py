"""Main file"""
from discord.ext.commands import CommandNotFound
import os
import discord
import json
from discord.ext import commands
import time

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True
djtbot = commands.Bot(command_prefix='$', intents=intents)
client = discord.Client()

with open(f"cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    trusted_server_ids = data_dict["trusted_server_ids"]


@djtbot.event
async def on_message(message):
    if message.content == "pong":
        await message.channel.send('ping')

    for cog in djtbot.cogs:
        cog = djtbot.get_cog(cog)
        try:
            check = await cog.searchAnilist(message)
        except AttributeError:
            continue
    await djtbot.process_commands(message)


@djtbot.check
def check_guild(ctx):
    try:
        return ctx.guild.id in trusted_server_ids
    except AttributeError:
        return True


for filename in os.listdir('./cogs'):
    if filename.endswith('.py') and not filename.startswith("nocog"):
        djtbot.load_extension(f'cogs.{filename[:-3]}')
        print(f"Loaded cog {filename}")

with open("./token.txt") as token_file:
    bot_token = token_file.read()

djtbot.run(bot_token)
