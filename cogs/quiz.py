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


def checkanswer(reaction, answer):
    return reaction == answer


def emojiToInt(reaction):
    if reaction == "1️⃣":
        return 1
    if reaction == "2️⃣":
        return 2
    if reaction == "3️⃣":
        return 3
    if reaction == "4️⃣":
        return 4
    return 0


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
            questions = [{
                "_id": {
                    "$oid": "6214f6ac43dc570f7b9e2c47"
                },
                "question": "酒を__醸す__蔵を建てる予定です。",
                "answers": ["ひかす", "かもす", "かかす", "わかす"],
                "correct": 2,
                "category": "vocab",
                "type": "kanji",
                "template": 4
            }, {
                "_id": {
                    "$oid": "6214f6ac43dc570f7b9e2c47"
                },
                "question": "酒を__醸す__蔵を建てる予定です。",
                "answers": ["ひかす", "かもす", "かかす", "わかす"],
                "correct": 2,
                "category": "vocab",
                "type": "kanji",
                "template": 4
            }, {
                "_id": {
                    "$oid": "6214f6ac43dc570f7b9e2c47"
                },
                "question": "酒を__醸す__蔵を建てる予定です。",
                "answers": ["ひかす", "かもす", "かかす", "わかす"],
                "correct": 2,
                "category": "vocab",
                "type": "kanji",
                "template": 4
            }
            ]

            tipos = {"文字・語彙": [
                {"name": "漢字読み (kanjis)",
                 "desc": "_____の言葉の読み方として最も良いものを、１・２・３・４から一つ選びなさい。"},
                "文脈規定 (contexto)",
                "言い換え類義 (parafrases)",
                "用法 (uso)"
            ], "文法": [
                "文法形式の判断 (gramática)",
                "文の組み立て (ordenar)",
                "文章の文法 (texto)"
            ]}

            points = 0
            for question in questions:
                qs = question.get("question") + "\n"
                counter = 1
                anwserArr = ""
                for elem in question.get("answers"):
                    anwserArr += str(counter) + ") " + elem + "\n"
                    counter += 1
                answer = question.get("correct")
                embed = discord.Embed(
                    title="文字・語彙", description="\_\_\_\_\_の言葉の読み方として最も良いものを、１・２・３・４から一つ選びなさい。", color=0x00e1ff)
                embed.set_author(name="N1 Quiz")
                embed.add_field(
                    name="Pregunta", value=qs, inline=True)
                embed.add_field(name="Posibles Respuestas",
                                value=anwserArr, inline=False)
                embed.set_footer(
                    text="Reacciona con la respuesta que creas más adecuada")
                output = await message.channel.send(embed=embed)
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

                userans = emojiToInt(guess[0].emoji)
                if checkanswer(userans, answer):
                    correct = discord.Embed(
                        title="✅ Respuesta Correcta: "+str(answer)+") " + question.get("answers")[answer-1]+".", color=0x24b14d)
                    await message.channel.send(embed=correct)
                    points += 1
                    # userans = await onlyUserReaction(userans)
                    sleep(3)
                else:
                    incorrect = discord.Embed(
                        title="❌ Respuesta Correcta: "+str(answer)+") " + question.get("answers")[answer-1]+".", color=0xff2929, description="Tu Respuesta: "+str(userans)+") " + question.get("answers")[userans-1]+".")
                    await message.channel.send(embed=incorrect)
                    # await onlyUserReaction(userans)
                    sleep(5)

            await message.channel.send("Resultado final: " + str(points) + " respuestas correctas.")
            self.busy = False


def setup(bot):
    bot.add_cog(Test(bot))

# Ideas:
# Comando para crear un test de una categoría (vocabulario/gramatica)
# Comando para crear un test de un tipo (kanjis/uso/parafrases/...)
# Argumento para los tests anteriores que defina el tiempo limite
# Argumento para los tests anteriores que defina el numero de preguntas
# Comando para crear un test que imite un examen del N1
# Comando para salir de un test no finalizado
