import re
import asyncio
from datetime import datetime, timezone
import json
import random
from time import gmtime, strftime
from dateutil.tz import gettz
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter
from discord.raw_models import RawReactionActionEvent
from discord import Member, Guild
from translate import Translator
from time import gmtime

from helpers.general import intToMonth, send_error_message, send_message_for_other, send_response, set_processing, get_clock_emoji

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    admin_users = general_config["admin_users"]
    main_guild = general_config["trusted_guilds"][1]

with open("config/roles.json", encoding="utf-8") as roles_file:
    roles_config = json.load(roles_file)
# ====================================================


class Extra(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.bot.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de cosas random cargado con éxito")
        self.update_clock.start()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        message_id = str(payload.message_id)
        if message_id in roles_config.keys():
            guild: Guild = await self.bot.fetch_guild(654351832734498836)
            user: Member = await guild.fetch_member(payload.user_id)
            role_config = roles_config[message_id]
            if str(payload.emoji) == role_config["emoji"]:
                newrole = discord.utils.get(
                    guild.roles, id=int(role_config["role"]))
                await user.add_roles(newrole)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        message_id = str(payload.message_id)
        if message_id in roles_config.keys():
            guild: Guild = await self.bot.fetch_guild(654351832734498836)
            user: Member = await guild.fetch_member(payload.user_id)
            role_config = roles_config[message_id]
            if str(payload.emoji) == role_config["emoji"]:
                newrole = discord.utils.get(
                    guild.roles, id=int(role_config["role"]))
                await user.remove_roles(newrole)

    @commands.slash_command(guild_ids=[main_guild])
    async def say(self, ctx,
                  message: discord.Option(str, "Mensaje a enviar", required=True),
                  channel: discord.Option(str, "Canal a enviar", required=True)):
        "Comando para hablar a través del bot"

        if ctx.author.id == 615896601554190346:
            channel = self.bot.get_channel(int(channel))
            await channel.send(message)
            await ctx.respond("Enviado")

    @tasks.loop(minutes=10)
    async def update_clock(self):
        channel = self.bot.get_channel(1160718763965022258)
        now = datetime.now()

        emoji = await get_clock_emoji(now.hour, now.minute)

        await channel.edit(name=f"{emoji} {now.strftime('%H:%M Hora 🇪🇸')}")

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

    # @commands.command()
    # async def anunciar(self, ctx):
    #     channel = self.bot.get_channel(1167606735360503859)
    #     embed = discord.Embed(title="🎮 ¡Club de VN y juegs🎮
    #                           description="Reacciona a este mensaje con 🎮 para recibir notificaciones sobre el club de VN y juegos", color=discord.Color.from_rgb(230, 126, 34), url="https://discord.com/channels/654351832734498836/1142399071236132944")
    #     embed.set_footer(
    #         text="Al recibir el rol entiendes que podrás recibir varias notificaciones en relación a la participación en las actividades del mes")

    #     await channel.send(embed=embed)

    @commands.slash_command()
    async def grammar(self, ctx, clave: discord.Option(str, "Id de la lección", required=False), forma_gramatical: discord.Option(str, "Punto gramatical que te interesa", required=False)):
        """Comando para obtener información de diferentes puntos gramaticales"""
        with open("config/grammar.json", "r", encoding="utf-8") as file:
            grammar = json.load(file)

        if clave:
            resultado = None

            for elemento in grammar:
                if elemento['id'] == clave:
                    resultado = elemento
                    break

            embed = discord.Embed(title=resultado["titulo"])

            embed.add_field(
                name=f"📕 {resultado['subtitulo']} 📕", value=f" ")

            resultado = resultado["texto"].split("\nç\n")
            for elem in resultado:
                embed.add_field(name=" ",
                                value=elem, inline=False)
                embed.set_footer(
                    text="Explicación cortesía de http://www.guidetojapanese.org/spanish/")
            return await send_response(ctx, embed=embed)

        elif forma_gramatical:
            resultados = []
            for elemento in grammar:
                if "formas" in elemento and isinstance(elemento["formas"], list):
                    for forma in elemento["formas"]:
                        if forma_gramatical == forma:
                            resultados.append(elemento)
                            break

            if len(resultados) > 1:
                embed = discord.Embed(color=0x442255,
                                      title="Se han encontrado varios resultados con esa forma", description="```Para ver el contenido usa el comando /grammar rellenando el campo \"Clave\" con la clave debajo de cada entrada gramatical```")

                for result in resultados:
                    embed.add_field(
                        value=f"Clave: **__{result['id']}__**", name=f"{result['titulo']} || {result['subtitulo']}", inline=False)
                await send_response(ctx, embed=embed, delete_after=30.0)
            elif len(resultados) == 0:
                return await send_error_message(ctx, "No se ha encontrado esa forma gramatical")
            else:
                embed = discord.Embed(
                    title=resultados[0]["titulo"], color=0x11abad)

                embed.add_field(
                    name=f"📕 {resultados[0]['subtitulo']} 📕", value=f" ")

                resultado = resultados[0]["texto"].split("\nç\n")
                for elem in resultado:
                    embed.add_field(name=" ",
                                    value=elem, inline=False)
                embed.set_footer(
                    text="Explicación cortesía de http://www.guidetojapanese.org/spanish/")
                return await send_response(ctx, embed=embed)

        else:
            await send_error_message(ctx, "Debes rellenar la forma gramatical a buscar o la clave del elemento!")


def setup(bot):
    bot.add_cog(Extra(bot))
