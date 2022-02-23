"""Cog responsible for sauce."""

import asyncio
import json
from time import sleep
import discord
import os
from discord.ext import commands
from saucenao_api import SauceNao, errors
from discord import Embed
from .logs import send_error_message

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    join_quiz_channel_ids = data_dict["join_quiz_1_id"]
    admin_id = data_dict["kaigen_user_id"]
#############################################################

# BOT'S COMMANDS


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False

    @ commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        # await self.private_admin_channel.send("Connected to db successfully")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot:
            return

        if message.content.startswith('.test') and not self.busy:
            self.busy = True
            questions = [
            ]
            points = 0
            for question in questions:
                qs = question.get("question") + "\n"
                counter = 1
                for elem in question.get("answers"):
                    qs += str(counter) + ") " + elem + "\n"
                    counter += 1
                answer = question.get("correct")
                output = await message.channel.send(qs)
                await output.add_reaction("1️⃣")
                await output.add_reaction("2️⃣")
                await output.add_reaction("3️⃣")
                await output.add_reaction("4️⃣")

                def check(reaction, user):
                    return user == message.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

                try:
                    guess = await self.bot.wait_for('reaction_add', timeout=20.0, check=check)

                except asyncio.TimeoutError:
                    return await message.channel.send('Mensaje de tardar', delete_after=3)

                def checkanswer(reaction, answer):
                    if reaction == "1️⃣" and answer == 1:
                        return True
                    if reaction == "2️⃣" and answer == 2:
                        return True
                    if reaction == "3️⃣" and answer == 3:
                        return True
                    if reaction == "4️⃣" and answer == 4:
                        return True
                    return False

                if checkanswer(guess[0].emoji, answer):
                    await message.channel.send('Mensaje de correcto', delete_after=3)
                    points += 1
                    sleep(3)
                else:
                    await message.channel.send('Mensaje de error', delete_after=3)
                    sleep(3)
            await message.channel.send("Resultado final: " + str(points) + " respuestas correctas.")
            self.busy = False


def setup(bot):
    bot.add_cog(Test(bot))
