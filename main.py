import json
import os
import random
import discord

from discord.ext import bridge, tasks
from helpers.general import send_error_message
from time import sleep

from cogs.menus.log import LogView
from cogs.menus.backlog import BacklogView

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    trusted_guilds = general_config["trusted_guilds"]

with open("config/immersion.json") as json_file:
    immersion_config = json.load(json_file)
    immersion_logs_channels = immersion_config["immersion_logs_channels"]
# ====================================================


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = bridge.Bot(command_prefix=".", intents=intents, help_command=None)


@bot.event
async def on_ready():
    bot.add_view(LogView())
    bot.add_view(BacklogView())

    update_presence.start()


@bot.event
async def on_message(message: discord.Message):
    if message.channel.id in immersion_logs_channels and message.author.get_role(865660735761678386):
        ctx = await bot.get_context(message)
        await send_error_message(ctx, "No puedes enviar mensajes mientras tengas activado el modo inmersión")
        sleep(1)
        await message.delete()
    if not message.guild or message.guild.id in trusted_guilds:
        await bot.process_commands(message)

print("\n================ CARGANDO COGS ================\n")
for filename in os.listdir('./cogs'):
    if filename.endswith('.py') and not filename.startswith("nocog"):
        bot.load_extension(f'cogs.{filename[:-3]}')


@tasks.loop(minutes=5)
async def update_presence():
    presences = [
        discord.Activity(type=discord.ActivityType.competing,
                         name="El ranking del servidor", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.listening,
                         name="Canciones de anime", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.watching,
                         name="Anime de temporada", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.playing,
                         name="Todo tipo de eroges", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.watching,
                         name="Vtubers jugando al tetris", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.competing,
                         name="Mejorar mi pitch accent", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.playing,
                         name="Tests del kotoba", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.streaming,
                         name="Discusión sobre métodos", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.playing,
                         name="Anki a última hora", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.playing,
                         name="Aprender kanjis", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.watching,
                         name="Videos y haciendo shadowing", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.competing,
                         name="Ejercicios de gramática", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.competing,
                         name="El JLPT", state="Si necesitas ayuda utiliza .help o /help 🤖"),
        discord.Activity(type=discord.ActivityType.watching,
                         name="Vuelos a Japón", state="Si necesitas ayuda utiliza .help o /help 🤖"),
    ]

    # Random presence
    presence = presences[random.randint(0, len(presences)-1)]

    await bot.change_presence(activity=presence)

bot.run(os.getenv('BOT_TOKEN'))
