"""Cog responsible for tests."""

import asyncio
import json
from time import sleep, time
import discord
import os
from discord.ext import commands
from discord import Embed
from .logs import send_error_message
from pymongo import MongoClient, errors

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    join_quiz_channel_ids = data_dict["join_quiz_1_id"]
    admin_id = data_dict["kaigen_user_id"]
#############################################################

# BOT'S COMMANDS

CATEGORIES = ["VOCAB", "GRAM"]
TYPES = ["KANJI", "CONTEXTO", "PARAF", "USO", "GRAMFRASE", "ORDENAR"]


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


def question_params(question):
    if question == "kanji":
        name = "Lectura de Kanjis (漢字読み)"
        description = "_____の言葉の読み方として最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 10
    if question == "contexto":
        name = "Contexto (文脈規定)"
        description = "_____に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 20
    if question == "paraf":
        name = "Parafraseo (言い換え類義)"
        description = "_____の言葉に意味が最も近ものを、１・２・３・４から一つ選びなさい。"
        time = 20
    if question == "uso":
        name = "Uso de palabras (用法)"
        description = "次の言葉の使い方として最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 30
    if question == "gramfrase":
        name = "Gramática (文法形式の判断)"
        description = "次の文の_____に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 15
    if question == "ordenar":
        name = "Ordenar frases (文の組み立て)"
        description = "次の文の＿★＿に入れる最も良いものを、１・２・３・４から一つ選びなさい。"
        time = 40
    return name, description, time


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False
        self.tasks = dict()

    @ commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        if(self.myguild):
            try:
                client = MongoClient(os.getenv("MONGOURL"),
                                     serverSelectionTimeoutMS=10000)
                client.server_info()
                print("Obtenida colección de logs de MongoDB")
                self.db = client.Migii
            except errors.ServerSelectionTimeoutError:
                print("Ha ocurrido un error intentando conectar con la base de datos.")
                exit(1)
        # await self.private_admin_channel.send("Connected to db successfully")

    # @commands.Cog.listener()
    # async def on_message(self,message):
    #     if(message.autor==self.bot):
    #         return

    #     if(message.conte)

    @commands.command()
    async def stop(self, ctx):
        try:
            self.tasks[ctx.message.author.id].close()
            embed = discord.Embed(
                title="‼️ El test ha sido detenido.", color=0xffff00)
            await ctx.send(embed=embed)
        except KeyError:
            await send_error_message(self, ctx, "No has iniciado ningún test.")

    @commands.command()
    async def test(self, ctx, param, questionnum=5, timed=False):
        if ctx.message.author == self.bot:
            return

        if(param == "help"):
            embed = discord.Embed(color=0x00e1ff, title="Tipos de quiz",
                                  description="Uso: .test [tipo] [número de preguntas (def: 5)] [modo veloz (def: false)]")
            embed.add_field(
                name="Vocabulario *[.test vocab]*", value="**Lectura de Kanjis** *[.test kanji]*: Debes seleccionar la respuesta con la lectura del kanji entre paréntesis.\n**Contexto** *[.test contexto]*: Debes llenar el hueco en la frase con la palabra más adecuada.\n**Parafrases** *[.test paraf]*: Debes seleccionar la palabra con el significado más parecido a la palabra entre paréntesis dentro de la frase.\n**Uso** *[.test uso]*: Debes seleccionar la frase donde la palabra indicada esté bien utilizada.", inline=False)
            embed.add_field(
                name="Gramática *[.test gram]*", value="**Gramática de frases** *[.test gramfrase]*: Debes seleccionar la forma gramatical más adecuada en el hueco de la frase.\n**Ordenar frases** *[.test ordenar]*: Debes seleccionar la parte de la frase que encaja en el hueco señalado con una estrella.", inline=False)
            embed.add_field(
                name="Modo veloz", value="Activar este modo hará que tengas menos tiempo para responder a las preguntas. (def: 1 min)")
            embed.set_footer(
                text="Puedes ver de nuevo esta información escribiendo [.test help]")
            return await ctx.send(embed=embed)

        exercises = self.db.exercises
        questions = []
        if param.upper() in CATEGORIES:
            for elem in exercises.aggregate([{"$match": {"category": param.lower()}}, {"$sample": {"size": questionnum}}]):
                questions.append(elem)
        elif param.upper() in TYPES:
            for elem in exercises.aggregate([{"$match": {"type": param.lower()}}, {"$sample": {"size": questionnum}}]):
                questions.append(elem)
        else:
            return await send_error_message(self, ctx, "Los tipos de ejercicio admitidos son: GRAM, VOCAB para las categorías y KANJI, CONTEXTO, PARAF, USO y GRAMFRASE, ORDENAR para las subcategorías")

        points = 0
        for question in questions:
            qname, explain, timemax = question_params(question.get("type"))
            if(not timed):
                timemax = 60
            ""
            qs = question.get("question").replace("＿", " ＿ ").replace(
                "*", " ( ", 1).replace("*", ") ", 1).replace("_", "\_") + "\n"
            counter = 1
            anwserArr = ""
            for elem in question.get("answers"):
                anwserArr += str(counter) + ") " + \
                    elem + "\n"
                counter += 1
            answer = question.get("correct")
            # embed = discord.Embed(
            #     title="", color=0x00e1ff, description=qs)
            embed = discord.Embed(color=0x00e1ff, title="(" + qname + ")")
            embed.add_field(
                name="Pregunta", value=qs, inline=True)
            embed.add_field(name="Posibles Respuestas",
                            value=anwserArr, inline=False)
            embed.set_footer(
                text="Enunciado: " + explain)
            output = await ctx.send(embed=embed)
            await output.add_reaction("1️⃣")
            await output.add_reaction("2️⃣")
            await output.add_reaction("3️⃣")
            await output.add_reaction("4️⃣")

            def check(reaction, user):
                return user == ctx.message.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

            timeout = False
            try:
                self.tasks[ctx.message.author.id] = self.bot.wait_for(
                    'reaction_add', timeout=timemax, check=check)
                guess = await self.tasks[ctx.message.author.id]
            except asyncio.TimeoutError:
                await ctx.send('Mensaje de tardar', delete_after=3)
                timeout = True
            except RuntimeError:
                return

            if(not timeout):
                userans = emojiToInt(guess[0].emoji)

            if timeout:
                incorrect = discord.Embed(
                    title="❌ Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".", color=0xff2929)
                await ctx.send(embed=incorrect)
                # await onlyUserReaction(userans)
                sleep(3)
            elif checkanswer(userans, answer):
                correct = discord.Embed(
                    title="✅ Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".", color=0x24b14d)
                await ctx.send(embed=correct)
                points += 1
                # userans = await onlyUserReaction(userans)
                sleep(2)
            else:
                incorrect = discord.Embed(
                    title="❌ Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".", color=0xff2929, description="Tu Respuesta: " + str(userans) + ") " + question.get("answers")[userans - 1] + ".")
                await ctx.send(embed=incorrect)
                # await onlyUserReaction(userans)
                sleep(3)

        if(points == questionnum):
            emoji = "🏆"
        elif(points > questionnum * 0.7):
            emoji = "🎖️"
        elif(points > questionnum * 0.5):
            emoji = "😐"
        else:
            emoji = "⚠️"
        embed = discord.Embed(color=0x3344dd, title="Quiz terminado")
        embed.add_field(
            name=" Preguntas acertadas: ", value=emoji + " " + str(points) + "/" + str(questionnum) + " (" + str(points * 100 / questionnum) + "%)", inline=True)
        output = await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Test(bot))

# Ideas:
# Comando para crear un test de una categoría (vocabulario/gramatica)
# Comando para crear un test de un tipo (kanjis/uso/parafrases/...)
# Argumento para los tests anteriores que defina el tiempo limite
# Argumento para los tests anteriores que defina el numero de preguntas
# Comando para crear un test que imite un examen del N1
# Comando para salir de un test no finalizado
