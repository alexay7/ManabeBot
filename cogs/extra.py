import re
import asyncio
from datetime import datetime
import json
import random
from time import gmtime, strftime
from dateutil.tz import gettz
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter
from translate import Translator
from helpers.chatgpt import send_prompt

from helpers.general import intToMonth, send_error_message, send_message_for_other, send_response, set_processing

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    admin_users = general_config["admin_users"]
    main_guild = general_config["trusted_guilds"][1]
# ====================================================


class Extra(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de cosas random cargado con éxito")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        ctx = await self.bot.get_context(message)
        if ctx.message.channel.id == 1082024432182243461 and message.author.id != 1003719195877445642:
            is_japanese = bool(
                re.search("[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF]", message.content))

            if not is_japanese:
                return

            await message.add_reaction("✅")
            await set_processing(ctx)
            await send_prompt(ctx, message.content, "1ab72f53-7a91-494b-a063-89a6f6aa36e2")

    @commands.slash_command(guild_ids=[main_guild])
    async def say(self, ctx,
                  message: discord.Option(str, "Mensaje a enviar", required=True)):
        "Comando para hablar a través del bot"
        if ctx.message.author.id in admin_users:
            channel = self.bot.get_channel(654363913470738462)
            message = ""
            for word in ctx.message.content.split(" ")[1:]:
                message += word + " "
            await channel.respond(message)

    @commands.slash_command()
    async def kalise(self, ctx):
        "Comprobar si el bot está online"
        photos = ["https://www.alimarket.es/media/images/2014/detalle_art/152964/32612_preview.jpg", "https://pbs.twimg.com/profile_images/446190654356324352/nFIIKVXx_400x400.jpeg",
                  "https://s03.s3c.es/imag/_v0/225x250/d/4/e/kalise-iniesta.jpg", "https://static.abc.es/Media/201303/27/iniesta-kalise--644x362.jpg", "https://img.europapress.es/fotoweb/fotonoticia_20110407192259_1200.jpg"]
        await send_response(ctx, random.choice(photos))

    @commands.command(aliases=["kalise"])
    async def kaliseprefix(self, ctx):
        await self.kalise(ctx)

    @commands.slash_command()
    async def japonabierto(self, ctx):
        "Informa sobre si las fronteras de japón están abiertas al turismo"

        translator = Translator(to_lang="es", from_lang="en")
        await set_processing(ctx)
        url = "https://isjapanopen.com"

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
        answer = soup.find("h1").text
        if answer == "Yes":
            color = 0x00ff00
        elif answer == "Yes*":
            color = 0xff8800
        else:
            color = 0xff0000
        embed = discord.Embed(
            title=":flag_jp: ¿Está japón abierto a turistas? :flag_jp:", color=color)
        embed.add_field(name="Respuesta",
                        value=translator.translate(soup.find("h1").text), inline=False)
        embed.add_field(
            name="Condiciones", value=f"\n```{translator.translate(' '.join(soup.find('h3').text.split()))}```")
        await send_response(ctx, embed=embed)

    @ commands.slash_command()
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

    @ commands.command(aliases=['tiempojapon', 'horajapon', 'japonhora', 'japontiempo', 'japantime'])
    async def japantimeprefix(self, ctx):
        await self.japantime(ctx)

    @ commands.command(aliases=['canigotojapan', 'quieroirajapon', 'japonabierto'])
    async def japonabiertoprefix(self, ctx):
        await self.japonabierto(ctx)

    @ commands.slash_command()
    async def yenaeuro(self, ctx,
                       yenes: discord.Option(int, "Cantidad de yenes a convertir", required=True)):
        "Convierte yenes a euros"
        await set_processing(ctx)
        c = CurrencyConverter()
        result = round(c.convert(yenes, "JPY", "EUR"), 2)
        await send_response(ctx, str(yenes) + "¥ equivalen a " + str(result) + "€")

    @ commands.command(aliases=['jpytoeur', 'yentoeuro', 'jpyaeur', "yenaeuro"])
    async def yenaeuroprefix(self, ctx, yenes=0):
        if yenes == 0:
            return await send_error_message(ctx, "Debes indicar una cantidad de yenes")
        await self.yenaeuro(ctx, yenes)

    @ commands.slash_command()
    async def euroayen(self, ctx,
                       euros: discord.Option(int, "Cantidad de euros a convertir", required=True)):
        "Convierte euros a yenes"
        await set_processing(ctx)
        c = CurrencyConverter()
        result = round(c.convert(euros, "EUR", "JPY"))
        await send_response(ctx, str(euros) + "€ equivalen a " + str(result) + "¥")

    @ commands.command(aliases=['eurtojpy', 'eurotoyen', 'eurajpy', 'euroayen'])
    async def euroayenprefix(self, ctx, euros=0):
        if euros == 0:
            return await send_error_message(ctx, "Debes indicar una cantidad de yenes")
        await self.euroayen(ctx, euros)

    @ commands.slash_command()
    @ commands.cooldown(1, 300, commands.BucketType.user)
    async def aleatorio(self, ctx):
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
        await send_response(ctx, embed=embed)

    @ commands.cooldown(1, 300, commands.BucketType.user)
    @ commands.command(aliases=['randomyoji', 'yojialeatorio', 'palabraaleatoria', 'randomword', 'aleatorio', 'aleatoria'])
    async def aleatorioprefix(self, ctx):
        await self.aleatorio(ctx)

    @commands.slash_command()
    @commands.max_concurrency(10)
    async def chatgpt(self, ctx, message=discord.Option(str, "Prompt para chatpgt", required=True)):
        """Envía una prompt a ChatGPT3"""
        if not ctx.guild:
            return await send_error_message(ctx, "No se puede usar ChatGPT en mensajes privados.")

        is_japanese = bool(
            re.search("[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF]", message))

        if not is_japanese:
            return await send_error_message(ctx, "En este servidor solo puedes hablar con ChatGPT en japonés.")

        await set_processing(ctx)
        asyncio.create_task(send_prompt(ctx, message))

    @commands.command("chatgpt")
    async def chatgptprefix(self, ctx):
        message = ""
        full = ctx.message.content.split(" ")[1:]
        for word in full:
            message += word + " "
        await self.chatgpt(ctx, message)


def setup(bot):
    bot.add_cog(Extra(bot))
