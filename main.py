import json
import os
import discord

from dotenv import load_dotenv
from discord.ext import commands
from helpers.general import send_error_message

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    trusted_guilds = general_config["trusted_guilds"]

with open("config/immersion.json") as json_file:
    immersion_config = json.load(json_file)
    immersion_logs_channels = immersion_config["immersion_logs_channels"]
# ====================================================

load_dotenv(".env")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name="Cosas japonesas| .help"))
    print(f"{bot.user} está activo")


@bot.event
async def on_message(message: discord.Message):
    if message.channel.id in immersion_logs_channels and message.author.get_role(865660735761678386):
        if not message.content.startswith(".log"):
            ctx = await bot.get_context(message)
            await send_error_message(ctx, "No puedes enviar mensajes mientras tengas activado el modo inmersión")
            await message.delete()
    if not message.guild or message.guild.id in trusted_guilds:
        await bot.process_commands(message)

for filename in os.listdir('./cogs'):
    if filename.endswith('.py') and not filename.startswith("nocog"):
        bot.load_extension(f'cogs.{filename[:-3]}')

bot.run(os.getenv('BOT_TOKEN'))
