import json
import os
import random
import string
import discord
import requests
import youtube_dl
from discord.ext import commands
from pymongo import MongoClient, errors
from helpers.general import send_error_message

from helpers.test import ALL_CATEGORIES, CATEGORIES, LEVELS, NOKEN_LEVELS, TYPES
from quiz.buttonHandler import ButtonHandler
from helpers.youtubedl import YTDLSource


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False
        self.tasks = dict()
        try:
            client = MongoClient(os.getenv("MONGOURL"),
                                 serverSelectionTimeoutMS=10000)
            client.server_info()
            print("Conectado con éxito con mongodb [tests]")
            self.db = client.Migii
        except errors.ServerSelectionTimeoutError:
            print("Ha ocurrido un error intentando conectar con la base de datos.")
            exit(1)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de tests cargado con éxito")

    @discord.slash_command()
    async def test(self, ctx,
                   nivel: discord.Option(str, "Nivel del Noken del que quieres hacer el test", choices=NOKEN_LEVELS, required=True),
                   preguntas: discord.Option(int, "Número de preguntas que quiere", min_value=1, default=10, required=False),
                   categoria: discord.Option(str, "Tipo de preguntas que quieres", choices=ALL_CATEGORIES, required=False),
                   cronometrado: discord.Option(
                       bool, "Si quieres que las preguntas tengan tiempo límite", default=False, required=False)
                   ):
        """Haz un test con los parámetros que prefieras"""
        users = self.db.users
        exercises = self.db.exercises
        questions = []

        # CREA EL TIPO DE TEST QUE EL USUARIO QUIERE
        # El test es sobre un tipo de ejercicio concreto
        if categoria in LEVELS[nivel]["TYPES"]:
            for elem in exercises.aggregate([{"$match": {"type": categoria.lower(), "level": nivel}}, {"$sample": {"size": preguntas}}, {"$project": {"_id": 0}}]):
                questions.append(elem)

        # El test es sobre una categoría entera
        elif categoria in CATEGORIES:
            for elem in exercises.aggregate([{"$match": {"category": categoria.lower(), "level": nivel}}, {"$sample": {"size": preguntas}}, {"$project": {"_id": 0}}]):
                questions.append(elem)

        # Ha puesto un tipo de ejercicio que no existe en ese nivel
        elif categoria in TYPES:
            categories = ""
            for elem in LEVELS[nivel]["TYPES"]:
                categories += elem + ", "
            categories = categories[:-2]
            return await send_error_message(ctx, "Categorías admitidas para el " + nivel + ": " + categories + ".")

        # Es un test de todo
        else:
            for elem in exercises.aggregate([{"$match": {"level": nivel}}, {"$sample": {"size": preguntas}}, {"$project": {"_id": 0}}]):
                questions.append(elem)

        # AÑADE LAS PREGUNTAS A UN ARCHIVO JSON
        with open(f"temp/test-{ctx.author.id}.json", "wb") as json_file:
            json_file.write(json.dumps(
                questions, ensure_ascii=False).encode('utf8'))

        # COMIENZA EL TEST
        view = ButtonHandler()
        embed = discord.Embed(title="Empieza el Quiz")
        await ctx.respond(embed=embed, view=view)

    @discord.slash_command()
    async def testaño(self, ctx,
                      año: discord.Option(int, "Año del JLPT que quieres hacer", min_value=2010, max_value=2021, required=True),
                      mes: discord.Option(str, "Mes del JLPT que quieres hacer", choices=["JULIO", "DICIEMBRE"], required=True)):
        """Haz un test con las preguntas de un examen real (solo N1)"""
        exercises = self.db.exercises
        questions = []
        for elem in exercises.aggregate([{"$match": {"year": año, "period": mes.capitalize()}}, {"$project": {"_id": 0}}]):
            questions.append(elem)

        with open(f"temp/test-{ctx.author.id}.json", "wb") as json_file:
            json_file.write(json.dumps(
                questions, ensure_ascii=False).encode('utf8'))

        view = ButtonHandler()
        embed = discord.Embed(title="Empieza el Quiz")
        await ctx.respond(embed=embed, view=view)

    # @commands.command()
    # async def connect(self, ctx):
    #     """fghsdkjfgsdjk"""
    #     channel = ctx.message.author.voice.channel
    #     await channel.connect()

    # @commands.command()
    # async def play(self, ctx, song, anime):
    #     res = requests.post("https://anisongdb.com/api/search_request",
    #                         json={"song_name_search_filter": {"search": song, "partial_match": True}, "anime_search_filter": {"search": anime, "partial_match": True}}).json()
    #     for elem in res:
    #         print(elem["songName"])
    #     chosen_one = random.choice(res)["audio"]
    #     server: discord.Guild = ctx.message.guild
    #     voice_channel = server.voice_client
    #     async with ctx.typing():
    #         filename = await YTDLSource.from_url(res[14]["audio"], loop=self.bot.loop)
    #         try:
    #             voice_channel.play(discord.FFmpegPCMAudio(
    #                 executable="ffmpeg.exe", source=filename))
    #         except:
    #             voice_channel.stop()
    #             voice_channel.play(discord.FFmpegPCMAudio(
    #                 executable="ffmpeg.exe", source=filename))


# def setup(bot):
#     bot.add_cog(Test(bot))
