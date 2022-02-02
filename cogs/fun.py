"""Cog responsible for random things."""

import json
import discord
from discord.ext import commands
from datetime import datetime
from dateutil.tz import gettz
from bs4 import BeautifulSoup
import requests
from time import strftime
from time import gmtime
import random

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    join_quiz_channel_ids = [
        data_dict["join_quiz_1_id"]]
    admin_user_id = data_dict["kaigen_user_id"]
#############################################################


class Extra(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def say(self, ctx, message):
        "Comando para hablar a través del bot"
        if(ctx.message.author.id == admin_user_id):
            channel = self.bot.get_channel(654363913470738462)
            await channel.send(message)

    @commands.command(aliases=['tiempojapon', 'horajapon', 'japonhora', 'japontiempo'])
    async def japantime(self, ctx):
        "Muestra la hora actual y la de Japón."
        local = datetime.now(gettz('Spain'))
        local_japan = datetime.now(gettz('Japan'))

        def intToMonth(number):
            if number == 1:
                return "Enero"
            if number == 2:
                return "Febrero"
            if number == 3:
                return "Marzo"
            if number == 4:
                return "Abril"
            if number == 5:
                return "Mayo"
            if number == 6:
                return "Junio"
            if number == 7:
                return "Julio"
            if number == 8:
                return "Agosto"
            if number == 9:
                return "Septiembre"
            if number == 10:
                return "Octubre"
            if number == 11:
                return "Noviembre"
            return "Diciembre"

        localtime = strftime("%H:%M", gmtime(
            int(local.hour) * 3600 + int(local.minute) * 60))

        japantime = strftime("%H:%M", gmtime(
            int(local_japan.hour) * 3600 + int(local_japan.minute) * 60))

        await ctx.send(
            f"Hora Local: {localtime} del {local.day} de {intToMonth(local.month)} \
                de {local.year}\nHora Japonesa: {japantime} del {local_japan.day} \
                    de {intToMonth(local_japan.month)} de {local_japan.year}")

    @commands.command(aliases=['canigotojapan', 'quieroirajapon'])
    async def japonabierto(self, ctx):
        "Te dice si las fronteras de Japón están abiertas para el turismo o no"
        url = "https://canigotojapan.com"

        headers = {
            'Access-Control-Allow-Origin': ' * ',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
        }

        # Make a GET request to fetch the raw HTML content
        req = requests.get(url, headers)

        # Parse the html content
        soup = BeautifulSoup(req.content, 'html.parser')

        await ctx.send(soup.find("h2").text)

    @commands.command(aliases=['jpytoeuro', 'yentoeuro', 'jpyaeuro', 'y2e', 'yte', 'yae'])
    async def yenaeuro(self, ctx, yenes):
        "Convierte yenes a euros. Uso: $comando cantidad"
        result = round(int(yenes) * 0.0077, 2)
        await ctx.send(yenes + "¥ equivalen a " + str(result) + "€")

    @commands.command(aliases=['eurotojpy', 'eurotoyen', 'euroajpy', 'e2y', 'ety', 'eay'])
    async def euroayen(self, ctx, euros):
        "Convierte euros a yenes. Uso: $comando cantidad"
        result = int(euros) * 129.8701298701
        await ctx.send(euros + "€ equivalen a " + str(result) + "¥")

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command(aliases=['randomyoji', 'yojialeatorio', 'palabraaleatoria', 'randomword'])
    async def aleatoria(self, ctx):
        "Obtiene un yoji aleatorio de jisho.org (cooldown de 5 min)"

        if ctx.channel.id not in join_quiz_channel_ids:
            await ctx.send(
                "Este comando solo puede ser usado en <#796084920790679612>.")
            return

        page = random.randint(1, 100)
        response = requests.get(
            f"https://jisho.org/api/v1/search/words?keyword=%23yoji&page={page}")
        element = random.randint(0, len(response.json()["data"]) - 1)
        element = response.json()["data"][element]
        kanji = element["japanese"][0]["word"]
        furigana = element["japanese"][0]["reading"]
        meaninggroup = element["senses"][0]["english_definitions"]
        meanings = meaninggroup[0]
        for element in meaninggroup[1:]:
            meanings += ", " + element

        embed = discord.Embed(title="Yoji aleatorio de AJR",
                              description="Recibe un yojijukugo aleatorio de jisho.org", color=0x24b14d)
        embed.set_author(
            name="IniestaBot", icon_url="https://cdn.discordapp.com/avatars/892168738193936424/c08307c917ffb2fe9e4f59b66db66c9e.webp?size=48")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/654351832734498836/6909a6a37d50d4010169c388c56c2746.webp?size=96")
        embed.add_field(name="Palabra", value=kanji, inline=True)
        embed.add_field(name="Lectura", value=furigana, inline=True)
        embed.add_field(
            name="Significados", value=meanings, inline=False)
        embed.set_footer(
            text="Si quieres obtener otra palabra, escribe $randomyoji dentro de 5 minutos.")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Extra(bot))
