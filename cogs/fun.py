"""Cog responsible for random things."""

from asyncio import tasks
import json
import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from dateutil.tz import gettz
from bs4 import BeautifulSoup
import requests
from time import strftime, gmtime, sleep
import random
from pymongo import MongoClient, errors

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    join_quiz_channel_ids = data_dict["join_quiz_1_id"]
    admin_user_id = data_dict["kaigen_user_id"]
#############################################################


async def send_error_message(self, ctx, content):
    embed = discord.Embed(color=0xff2929)
    embed.add_field(
        name="❌", value=content, inline=False)
    await ctx.send(embed=embed, delete_after=15.0)


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


def intToWeekday(number):
    if number == 1:
        return "火"
    if number == 2:
        return "水"
    if number == 3:
        return "木"
    if number == 4:
        return "金"
    if number == 5:
        return "土"
    if number == 6:
        return "日"
    return "月"


async def create_user(db, userid, username):
    users = db.madrugar
    newuser = {
        'userId': userid,
        'username': username,
        'currentStreak': 1,
        'lastDay': datetime.utcnow()
    }
    users.insert_one(newuser)


async def check_user(db, userid):
    users = db.madrugar
    return users.find({'userId': int(userid)}).count() > 0


class Extra(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @ commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        if(self.myguild):
            try:
                client = MongoClient(os.getenv("MONGOURL"),
                                     serverSelectionTimeoutMS=10000)
                client.server_info()
                print("Obtenida colección de madrugar de MongoDB")
                self.db = client.ajrlogs
            except errors.ServerSelectionTimeoutError:
                print("Ha ocurrido un error intentando conectar con la base de datos.")
                exit(1)

    @commands.Cog.listener()
    async def on_message(self, message):
        if(message.author.id != 155149108183695360):
            if("media.discordapp.net" in message.content):
                await message.delete()
                newlink = message.content.replace(
                    "media.discordapp.net", "cdn.discordapp.com")
                await message.channel.send(newlink)

    @commands.command()
    async def say(self, ctx, message):
        "Comando para hablar a través del bot"
        if(ctx.message.author.id == admin_user_id):
            channel = self.bot.get_channel(654363913470738462)
            message = ""
            for word in ctx.message.content.split(" ")[1:]:
                message += word + " "
            await channel.send(message)

    @commands.command()
    async def kalise(self, ctx):
        "Para veri, pesao"
        await ctx.send("https://pbs.twimg.com/profile_images/446190654356324352/nFIIKVXx_400x400.jpeg")

    @commands.command(aliases=['tiempojapon', 'horajapon', 'japonhora', 'japontiempo'])
    async def japantime(self, ctx):
        "Muestra la hora actual y la de Japón."
        local = datetime.now(gettz('Spain'))
        local_japan = datetime.now(gettz('Japan'))

        localtime = strftime("%H:%M", gmtime(
            int(local.hour) * 3600 + int(local.minute) * 60))

        japantime = strftime("%H:%M", gmtime(
            int(local_japan.hour) * 3600 + int(local_japan.minute) * 60))

        await ctx.send(
            f"Hora Local: {localtime} del {local.day} de {intToMonth(local.month)} de {local.year}\nHora Japonesa: {japantime} del {local_japan.day} de {intToMonth(local_japan.month)} de {local_japan.year}")

    @commands.command(aliases=['canigotojapan', 'quieroirajapon'])
    async def japonabierto(self, ctx, countdown=False):
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
        if countdown:
            countdown = 5
            message = await ctx.send(f"La respuesta será revelada en {countdown}...")
            while(countdown > 0):
                sleep(1)
                countdown -= 1
                await message.edit(
                    content=f"La respuesta será revelada en {countdown}...")
            sleep(1)
            await message.edit(content=soup.find("h2").text)
        else:
            await ctx.send(soup.find("h2").text)

    @commands.command(aliases=['jpytoeuro', 'yentoeuro', 'jpyaeuro', 'y2e', 'yte', 'yae'])
    async def yenaeuro(self, ctx, yenes):
        "Convierte yenes a euros. Uso: .comando cantidad"
        result = round(int(yenes) * 0.0077, 2)
        await ctx.send(yenes + "¥ equivalen a " + str(result) + "€")

    @commands.command(aliases=['eurotojpy', 'eurotoyen', 'euroajpy', 'e2y', 'ety', 'eay'])
    async def euroayen(self, ctx, euros):
        "Convierte euros a yenes. Uso: .comando cantidad"
        result = int(euros) * 129.8701298701
        await ctx.send(euros + "€ equivalen a " + str(result) + "¥")

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command(aliases=['randomyoji', 'yojialeatorio', 'palabraaleatoria', 'randomword'])
    async def aleatoria(self, ctx):
        "Obtiene un yoji aleatorio de jisho.org (cooldown de 5 min)"

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
            text="Si quieres obtener otra palabra, escribe .randomyoji dentro de 5 minutos.")
        await ctx.send(embed=embed)

    @commands.command()
    async def despierto(self, ctx):
        now = datetime.now()
        users = self.db.madrugar
        if((now.hour == 8 and now.minute < 30) or now.hour == 7):
            if(not await check_user(self.db, ctx.author.id)):
                await create_user(self.db, ctx.author.id, ctx.author.name)
                embed = discord.Embed(
                    title="Que empiece la racha!", description="Gracias por usar el bot para madrugar!", color=0x009411)
                embed.add_field(name="Días consecutivos",
                                value="1", inline=True)
                embed.add_field(name="Hora registrada",
                                value=strftime("%H:%M", gmtime(
                                    int(now.hour) * 3600 + int(now.minute) * 60)), inline=True)
                embed.set_footer(text="Sigue así!")
                return await ctx.send(embed=embed)
            author = users.find_one({'userId': ctx.author.id})
            if(now.replace(hour=0, minute=0, second=0, microsecond=0) == (author["lastDay"] + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)):
                # Sigue la racha
                users.update_one({'userId': ctx.author.id}, {
                    '$inc': {
                        'currentStreak': 1
                    }, '$set': {
                        'lastDay': datetime.now()
                    }})
                embed = discord.Embed(
                    title="La racha sigue!", description="Muy bien! Has conseguido conservar la racha de madrugones!", color=0x009411)
                embed.add_field(name="Días consecutivos", value=str(
                    author["currentStreak"] + 1), inline=True)
                embed.add_field(name="Hora registrada",
                                value=strftime("%H:%M", gmtime(
                                    int(now.hour) * 3600 + int(now.minute) * 60)), inline=True)
                embed.set_footer(text="Sigue así!")
                await ctx.send(embed=embed)
            elif(now.replace(hour=0, minute=0, second=0, microsecond=0) == author["lastDay"].replace(hour=0, minute=0, second=0, microsecond=0)):
                embed = discord.Embed(
                    title="Ya has registrado tu despertar hoy!", color=0x990000)
                await ctx.send(embed=embed)
            else:
                # Racha perdida
                users.update_one({'userId': ctx.author.id}, {
                    '$set': {
                        'lastDay': datetime.now(),
                        'currentStreak': 1
                    }})
                embed = discord.Embed(
                    title="Racha perdida!", description="Parece que no has conseguido aguantar la racha, toca empezar de nuevo!", color=0xff9411)
                embed.add_field(name="Días consecutivos",
                                value="1", inline=True)
                embed.add_field(name="Hora registrada",
                                value=strftime("%H:%M", gmtime(
                                    int(now.hour) * 3600 + int(now.minute) * 60)), inline=True)
                embed.set_footer(text="Animo!")
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Has llegado tarde!!", description="Solo se pueden registrar despertares entre las 8:00 y las 8:30", color=0x990000)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Extra(bot))
