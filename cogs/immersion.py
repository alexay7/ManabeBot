from asyncio import sleep
import csv
from datetime import datetime, timedelta
import json
import math
import os
import matplotlib.pyplot as plt
import discord
import pandas as pd
import bar_chart_race as bcr
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from discord.ext.pages import Paginator
from pymongo import MongoClient, errors

from helpers.anilist import get_anilist_id, get_anilist_logs
from helpers.general import intToMonth, send_error_message, send_response, set_processing
from helpers.inmersion import MEDIA_TYPES, MEDIA_TYPES_ENGLISH, MONTHS, TIMESTAMP_TYPES, add_log, calc_media, check_user, compute_points, create_user, generate_graph, generate_linear_graph, get_best_user_of_range, get_logs_animation, get_media_element, get_ranking_title, get_sorted_ranking, get_total_immersion_of_month, get_total_parameter_of_media, get_user_logs, remove_last_log, remove_log, send_message_with_buttons

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    admin_users = general_config["admin_users"]
    main_guild = general_config["trusted_guilds"][0]

with open("config/immersion.json") as json_file:
    immersion_config = json.load(json_file)
    immersion_logs_channels = immersion_config["immersion_logs_channels"]
    immersion_mvp_role = immersion_config["immersion_mvp_role"]
    announces_channel = immersion_config["announces_channel"]

with open("config/achievements.json") as json_file:
    levels = json.load(json_file)
# ====================================================


class Immersion(commands.Cog):
    def __init__(self, bot: discord.bot.Bot):
        self.bot = bot
        try:
            client = MongoClient(os.getenv("MONGOURL"),
                                 serverSelectionTimeoutMS=10000)
            client.server_info()
            self.db = client.ajrlogs
            print("Conectado con éxito con mongodb [logs]")
        except errors.ServerSelectionTimeoutError:
            print("Ha ocurrido un error intentando conectar con la base de datos")
            exit(1)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de inmersión cargado con éxito")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id in immersion_logs_channels:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            reaction = discord.utils.get(message.reactions, emoji="❌")

            if len(message.embeds) > 0 and reaction:
                if message.embeds[0].title == "Log registrado con éxito" and int(message.embeds[0].footer.text) == payload.user_id:
                    await remove_log(self.db, payload.user_id, message.embeds[0].description.split(" ")[1].replace("#", ""))
                    await message.delete()

    @commands.slash_command()
    async def mvp(self, ctx,
                  medio: discord.Option(str, "Medio de inmersión que cubre el ranking", choices=MEDIA_TYPES, required=False, default="TOTAL"),
                  año: discord.Option(int, "Año que cubre el ranking (el desglose será mensual)", min_value=2019, max_value=datetime.now().year, required=False, default=datetime.now().year)):
        """Imprime un desglose mensual con los usuarios que más han inmersado en cada año desde que hay datos"""
        output = ""
        await set_processing(ctx)
        if año != "TOTAL":
            domain = range(1, 13)
            for x in domain:
                winner = await get_best_user_of_range(self.db, medio, f"{año}/{x}")
                if not (winner is None):
                    output += f"**{intToMonth(x)}:** {winner['username']} - {winner['points']} puntos"
                    if medio.upper() in MEDIA_TYPES:
                        output += f" -> {get_media_element(winner['parameters'],medio.upper())}\n"
                    else:
                        output += "\n"
            title = f"🏆 Usuarios del mes ({año})"
            if medio.upper() in MEDIA_TYPES:
                title += f" [{medio.upper()}]"
        else:
            # Iterate from 2020 until current year
            end = datetime.today().year
            domain = range(2020, end + 1)
            for x in domain:
                winner = await get_best_user_of_range(self.db, medio, f"{x}")
                if not (winner is None):
                    output += f"**{x}:** {winner['username']} - {winner['points']} puntos"
                    if medio.upper() in MEDIA_TYPES:
                        output += f" -> {get_media_element(winner['parameters'],medio.upper())}\n"
                    else:
                        output += "\n"
            title = f"🏆 Usuarios del año"
            if medio.upper() in MEDIA_TYPES:
                title += f" [{medio.upper()}]"
        if output:
            embed = discord.Embed(title=title, color=0xd400ff)
            embed.add_field(name="---------------------",
                            value=output, inline=True)
            await send_response(ctx, embed=embed)
        else:
            await send_error_message(ctx, "No existen datos")

    @commands.command(aliases=["halloffame", "salondelafama", "salonfama", "mvp", "hallofame"])
    async def mvpprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.mvp(ctx, "TOTAL", datetime.now().year)

    @commands.slash_command()
    async def podio(self, ctx,
                    periodo: discord.Option(str, "Periodo de tiempo que cubre el ranking", choices=TIMESTAMP_TYPES, required=False, default="MES"),
                    medio: discord.Option(str, "Medio de inmersión que cubre el ranking", choices=MEDIA_TYPES, required=False, default="TOTAL"),
                    año: discord.Option(int, "Año que cubre el ranking", min_value=2019, max_value=datetime.now().year, required=False),
                    extendido: discord.Option(
                        bool, "Muestra el ranking completo", required=False)
                    ):
        """Imprime un ranking de inmersión según los parámetros indicados"""
        if año:
            periodo = str(año)
        await set_processing(ctx)
        sortedlist = await get_sorted_ranking(self.db, periodo, medio)
        message = ""
        position = 1
        total_users = 10
        if extendido:
            total_users = len(sortedlist)
        for user in sortedlist[0:total_users]:
            if user["points"] != 0:
                message += f"**{str(position)}º {user['username']}:** {str(round(user['points'],2))} puntos"
                if "param" in user:
                    message += f" -> {get_media_element(user['param'],medio)}\n"
                else:
                    message += "\n"
                position += 1
            else:
                sortedlist.remove(user)
        append = ""
        if extendido:
            append = "extendido"
        if len(sortedlist) > 0:
            title = "Ranking " + \
                get_ranking_title(periodo, medio) + append
            embed = discord.Embed(color=0x5842ff)
            embed.add_field(name=title, value=message, inline=True)
            await send_response(ctx, embed=embed)
        else:
            await send_error_message(ctx, "Ningún usuario ha inmersado con este medio en el periodo de tiempo indicado")
            return

    @commands.command(aliases=["ranking", "podio", "lb", "leaderboard"])
    async def podioprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.podio(ctx, "MES", "TOTAL", None, None)

    @commands.slash_command()
    async def logs(self, ctx,
                   periodo: discord.Option(str, "Periodo de tiempo para ver logs", choices=TIMESTAMP_TYPES, required=False, default="TOTAL"),
                   medio: discord.Option(str, "Medio de inmersión para ver logs", choices=MEDIA_TYPES, required=False, default="TOTAL"),
                   usuario: discord.Option(str, "Usuario del que quieres ver los logs", required=False)):
        """Muestra lista con todos los logs hechos con los parámetros indicados"""
        await set_processing(ctx)
        if not usuario:
            usuario = ctx.author.id

        if await check_user(self.db, int(usuario)) is False:
            await send_error_message(ctx, "No se han encontrado logs asociados a esa Id.")
            return

        result = await get_user_logs(self.db, int(usuario), periodo, medio)
        sorted_res = sorted(result, key=lambda x: x["timestamp"], reverse=True)

        output = [
            "LOGID | FECHA: MEDIO CANTIDAD -> PUNTOS: DESCRIPCIÓN\n------------------------------------\n"]
        overflow = 0
        for log in sorted_res:
            timestring = datetime.fromtimestamp(
                log["timestamp"]).strftime('%d/%m/%Y')
            line = f"#{log['id']} | {timestring}: {log['medio']} {get_media_element(log['parametro'],log['medio'])} -> {log['puntos']} puntos: {log['descripcion']}\n"
            if len(output[overflow]) + len(line) < 1000:
                output[overflow] += line
            else:
                overflow += 1
                output.append(line)
        if len(output[0]) > 0:
            if ctx.message:
                await send_message_with_buttons(self, ctx, output)
            else:
                pages = []
                for page in output:
                    pages.append(f"```{page}```")
                paginator = Paginator(pages=pages,)
                await paginator.respond(ctx.interaction, ephemeral=True)
        else:
            await send_error_message(ctx, "No se han encontrado logs asociados a esa Id.")

    @commands.command(aliases=["logs"])
    async def logsprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.logs(ctx, "TOTAL", "TOTAL", None)

    @commands.slash_command()
    async def export(self, ctx,
                     periodo: discord.Option(
                         str, "Periodo de tiempo para exportar", choices=TIMESTAMP_TYPES, required=False, default="TOTAL")
                     ):
        """Exporta los logs en formato csv"""
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tiene ningún log")
            return

        result = await get_user_logs(self.db, ctx.author.id, periodo)
        sorted_res = sorted(result, key=lambda x: x["timestamp"], reverse=True)
        header = ["fecha", "medio", "cantidad", "descripcion", "puntos"]
        data = []
        for log in sorted_res:
            date = datetime.fromtimestamp(log["timestamp"])
            aux = [f"{date.day}/{date.month}/{date.year}", log["medio"],
                   log["parametro"], log["descripcion"].strip(), log["puntos"]]
            data.append(aux)
        with open('temp/user.csv', 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)
        await send_response(ctx, file=discord.File("temp/user.csv"), ephemeral=True)

    @commands.command(aliases=["export"])
    async def exportprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.export(ctx, "TOTAL")

    @commands.slash_command(pass_context=True)
    async def me(self, ctx,
                 periodo: discord.Option(str, "Periodo de tiempo para exportar", choices=TIMESTAMP_TYPES, required=False, default="TOTAL"),
                 gráfica: discord.Option(str, "Gráficos para acompañar los datos", choices=["SECTORES", "BARRAS", "NINGUNO"], required=False, default="SECTORES")):
        """Muestra pequeño resumen de lo inmersado"""
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log")
            return

        if gráfica == "BARRAS":
            periodo = "SEMANA"

        logs = await get_user_logs(self.db, ctx.author.id, periodo)
        points = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "AUDIO": 0,
            "VIDEO": 0,
            "TOTAL": 0
        }
        parameters = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "AUDIO": 0,
            "VIDEO": 0
        }

        graphlogs = {}

        output = ""
        for log in logs:
            points[log["medio"]] += log["puntos"]
            parameters[log["medio"]] += int(log["parametro"])
            points["TOTAL"] += log["puntos"]
            logdate = str(datetime.fromtimestamp(
                log["timestamp"])).replace("-", "/").split(" ")[0]

            if logdate in graphlogs:
                graphlogs[logdate] += log["puntos"]
            else:
                graphlogs[logdate] = log["puntos"]

        if points["TOTAL"] == 0:
            output = "No se han encontrado logs"
        else:
            if points["LIBRO"] > 0:
                output += f"**LIBROS:** {get_media_element(parameters['LIBRO'],'LIBRO')} -> {round(points['LIBRO'],2)} pts\n"
            if points["MANGA"] > 0:
                output += f"**MANGA:** {get_media_element(parameters['MANGA'],'MANGA')} -> {round(points['MANGA'],2)} pts\n"
            if points["ANIME"] > 0:
                output += f"**ANIME:** {get_media_element(parameters['ANIME'],'ANIME')} -> {round(points['ANIME'],2)} pts\n"
            if points["VN"] > 0:
                output += f"**VN:** {get_media_element(parameters['VN'],'VN')} -> {round(points['VN'],2)} pts\n"
            if points["LECTURA"] > 0:
                output += f"**LECTURA:** {get_media_element(parameters['LECTURA'],'LECTURA')} -> {round(points['LECTURA'],2)} pts\n"
            if points["TIEMPOLECTURA"] > 0:
                output += f"**LECTURA:** {get_media_element(parameters['TIEMPOLECTURA'],'TIEMPOLECTURA')} -> {round(points['TIEMPOLECTURA'],2)} pts\n"
            if points["AUDIO"] > 0:
                output += f"**AUDIO:** {get_media_element(parameters['AUDIO'],'AUDIO')} -> {round(points['AUDIO'],2)} pts\n"
            if points["VIDEO"] > 0:
                output += f"**VIDEO:** {get_media_element(parameters['VIDEO'],'VIDEO')} -> {round(points['VIDEO'],2)} pts\n"
        ranking = await get_sorted_ranking(self.db, periodo, "TOTAL")
        for user in ranking:
            if user["username"] == ctx.author.name:
                position = ranking.index(user)

        normal = discord.Embed(
            title=f"Vista {get_ranking_title(periodo,'ALL')}", color=0xeeff00)
        normal.add_field(name="Usuario", value=ctx.author.name, inline=True)
        normal.add_field(name="Puntos", value=round(
            points["TOTAL"], 2), inline=True)
        normal.add_field(name="Posición ranking",
                         value=f"{position+1}º", inline=True)
        normal.add_field(name="Medios", value=output, inline=False)

        if gráfica == "SECTORES":
            piedoc = generate_graph(points, "piechart")
            normal.set_image(url="attachment://image.png")
            await send_response(ctx, embed=normal, file=piedoc)
        elif gráfica == "BARRAS":
            bardoc = generate_graph(graphlogs, "bars", periodo)
            normal.set_image(url="attachment://image.png")
            await send_response(ctx, embed=normal, file=bardoc)
        else:
            await send_response(ctx, embed=normal)

    @commands.command(aliases=["yo", "me", "resumen"])
    async def meprefix(self, ctx, periodo="TOTAL", grafica="SECTORES"):
        if periodo.upper() in ["SECTORES", "BARRAS"]:
            grafica = periodo
            periodo = "TOTAL"
        await self.me(ctx, periodo.upper(), grafica.upper())

    @commands.slash_command()
    async def backfill(self, ctx,
                       fecha: discord.Option(str, "Fecha en formato DD/MM/YYYY", required=True),
                       medio: discord.Option(str, "Medio inmersado", choices=MEDIA_TYPES, required=True),
                       cantidad: discord.Option(int, "Cantidad inmersada", required=True, min_value=1, max_value=5000000),
                       descripción: discord.Option(str, "Pequeño resumen de lo inmersado", required=True)):
        """Loguear inmersión hecha en el pasado"""
        # Check if the user has logs
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await create_user(self.db, ctx.author.id, ctx.author.name)

        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                f"Este comando solo puede ser usado en <#{immersion_logs_channels[0]}>.")
            return

        date = fecha.split("/")
        if len(date) < 3:
            await send_error_message(ctx, "Formato de fecha no válido")
            return
        try:
            if int(date[2]) < 2000:
                date[2] = int(date[2]) + 2000
            datets = int(datetime(int(date[2]), int(
                date[1]), int(date[0])).timestamp())
        except ValueError:
            await send_error_message(ctx, "Formato de fecha no válido")
            return
        except OSError:
            await send_error_message(ctx, "Formato de fecha no válido")
            return

        strdate = datetime.fromtimestamp(datets)
        if datetime.today().timestamp() - datets < 0:
            await send_error_message(ctx, "Prohibido viajar en el tiempo")
            return

        message = descripción

        newlog = {
            'timestamp': datets,
            'descripcion': message,
            'medio': medio.upper(),
            'parametro': cantidad
        }

        output = compute_points(newlog)

        if output > 0:
            ranking = await get_sorted_ranking(self.db, "MES", "TOTAL")
            for user in ranking:
                if user["username"] == ctx.author.name:
                    position = ranking.index(user)
            logid = await add_log(self.db, ctx.author.id, newlog, ctx.author.name)
            ranking[position]["points"] += output

            newranking = sorted(
                ranking, key=lambda x: x["points"], reverse=True)

            for user in newranking:
                if user["username"] == ctx.author.name:
                    newposition = newranking.index(user)
                    current_points = user["points"]

            embed = discord.Embed(title="Log registrado con éxito",
                                  description=f"Log #{logid} || {strdate.strftime('%d/%m/%Y')}", color=0x24b14d)
            embed.add_field(
                name="Usuario", value=ctx.author.name, inline=True)
            embed.add_field(name="Medio", value=medio.upper(), inline=True)
            embed.add_field(
                name="Puntos", value=f"{round(current_points,2)} (+{output})", inline=True)
            embed.add_field(name="Inmersado",
                            value=get_media_element(cantidad, medio.upper()), inline=True)
            embed.add_field(name="Inmersión",
                            value=message, inline=False)
            if newposition < position:
                embed.add_field(
                    name="🎉 Has subido en el ranking del mes! 🎉", value=f"**{position+1}º** ---> **{newposition+1}º**", inline=False)
            embed.set_footer(
                text=ctx.author.id)
            message = await send_response(ctx, embed=embed)
            await message.add_reaction("❌")
        elif output == 0:
            await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
            return
        elif output == -1:
            await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
            return
        elif output == -2:
            await send_error_message(ctx, "Cantidad de inmersión exagerada")
            return
        await sleep(10)
        try:
            await message.clear_reaction("❌")
        except discord.errors.NotFound:
            pass

    @commands.command(aliases=["backlog", "backfill"])
    async def backfillprefix(self, ctx, fecha, medio, cantidad, descripcion):
        if medio.upper() not in MEDIA_TYPES:
            return await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
        if not str(cantidad).isnumeric():
            return await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
        if int(cantidad) > 5000000:
            return await send_error_message(ctx, "Cantidad de inmersión exagerada")
        message = ""
        for word in ctx.message.content.split(" ")[3:]:
            message += word + " "
        await self.backfill(ctx, fecha, medio, cantidad, message)

    @commands.slash_command()
    async def logros(self, ctx):
        """Obtener tus logros de inmersión"""
        await self.achievements_(ctx)

    @commands.command(aliases=["achievements", "logros", "level", "nivel"])
    async def achievements_(self, ctx):
        """Obtener tus logros de inmersión"""
        await set_processing(ctx)

        logs = await get_user_logs(self.db, ctx.author.id, "TOTAL")
        points = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "AUDIO": 0,
            "VIDEO": 0,
            "TOTAL": 0
        }
        parameters = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "AUDIO": 0,
            "VIDEO": 0
        }

        graphlogs = {}

        for log in logs:
            points[log["medio"]] += log["puntos"]
            parameters[log["medio"]] += int(log["parametro"])
            points["TOTAL"] += log["puntos"]
            logdate = str(datetime.fromtimestamp(
                log["timestamp"])).replace("-", "/").split(" ")[0]

            if logdate in graphlogs:
                graphlogs[logdate] += log["puntos"]
            else:
                graphlogs[logdate] = log["puntos"]

        output = "```"
        for key, value in parameters.items():
            current_level = math.floor(value / levels[key.upper()])
            if value > 0:
                output += f"-> Eres nivel {current_level+1} en {key} con un total de {get_media_element(value,key)}\n"

        normal = discord.Embed(
            title=f"🎌 Tus logros de inmersión 🎌", color=0xeeff00)
        normal.add_field(
            name="Usuario", value=f"{ctx.author.name} **[Lvl: {math.floor(points['TOTAL'] / 2000) + 1}]**", inline=True)
        normal.add_field(name="Puntos Totales", value=round(
            points["TOTAL"], 2), inline=True)
        normal.add_field(name="Nivel por categorías",
                         value=f"{output}```", inline=False)
        await send_response(ctx, embed=normal)
        return

    @commands.slash_command()
    async def log(self, ctx,
                  medio: discord.Option(str, "Medio inmersado", choices=MEDIA_TYPES, required=True),
                  cantidad: discord.Option(int, "Cantidad inmersada", required=True, min_value=1, max_value=5000000),
                  descripción: discord.Option(str, "Pequeño resumen de lo inmersado", required=True),
                  tiempo: discord.Option(int, "Tiempo que te ha llevado en minutos", required=False)):
        """Loguear inmersión"""
        await set_processing(ctx)
        # Check if the user has logs
        if not await check_user(self.db, ctx.author.id):
            await create_user(self.db, ctx.author.id, ctx.author.name)

        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        message = descripción

        today = datetime.today()

        newlog = {
            'timestamp': int(today.timestamp()),
            'descripcion': message,
            'medio': medio.upper(),
            'parametro': cantidad
        }
        output = compute_points(newlog)

        if tiempo and tiempo > 0:
            newlog['tiempo'] = math.ceil(tiempo)

        if output > 0.01:
            ranking = await get_sorted_ranking(self.db, "MES", "TOTAL")
            newranking = ranking
            for user in ranking:
                if user["username"] == ctx.author.name:
                    position = ranking.index(user)

                    ranking[position]["points"] += output

                    newranking = sorted(
                        ranking, key=lambda x: x["points"], reverse=True)
            for user in newranking:
                if user["username"] == ctx.author.name:
                    newposition = newranking.index(user)
                    current_points = user["points"]

            logid = await add_log(self.db, ctx.author.id, newlog, ctx.author.name)

            embed = discord.Embed(title="Log registrado con éxito",
                                  description=f"Log #{logid} || {today.strftime('%d/%m/%Y')}", color=0x24b14d)
            embed.add_field(
                name="Usuario", value=ctx.author.name, inline=True)
            embed.add_field(name="Medio", value=medio.upper(), inline=True)
            embed.add_field(
                name="Puntos", value=f"{round(current_points,2)} (+{output})", inline=True)
            embed.add_field(name="Inmersado",
                            value=get_media_element(cantidad, medio.upper()), inline=True)
            embed.add_field(name="Inmersión",
                            value=message, inline=False)
            if tiempo and tiempo > 0:
                embed.add_field(name="Tiempo invertido:",
                                value=get_media_element(tiempo, "VIDEO"), inline=False)
            if newposition < position:
                embed.add_field(
                    name="🎉 Has subido en el ranking del mes! 🎉", value=f"**{position+1}º** ---> **{newposition+1}º**", inline=False)
            embed.set_footer(
                text=ctx.author.id)
            message = await send_response(ctx, embed=embed)
            await message.add_reaction("❌")
            current_param = await get_total_parameter_of_media(self.db, medio.upper(), ctx.author.id)
            param_before = current_param - int(cantidad)

            if math.floor(param_before / levels[medio.upper()]) != math.floor(current_param / levels[medio.upper()]):
                if medio.upper() in ["ANIME", "VN", "LECTURA"]:
                    verbo = "inmersados"
                else:
                    verbo = "inmersadas"
                achievement_embed = discord.Embed(title=f"¡Nuevo logro de {ctx.author.name}!",
                                                  description="¡Sigue así!", color=0x0095ff)
                achievement_embed.set_thumbnail(url=ctx.author.avatar)
                achievement_embed.add_field(
                    name="Logro conseguido", value=f"{get_media_element(math.floor(current_param / levels[medio.upper()])*levels[medio.upper()],medio.upper())} de {medio.lower()} {verbo}")
                await send_response(ctx, embed=achievement_embed)
            await sleep(10)
            try:
                await message.clear_reaction("❌")
            except discord.errors.NotFound:
                pass

        elif output == 0:
            await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
            return
        elif output == -1:
            await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
            return
        elif output == -2:
            await send_error_message(ctx, "Cantidad de inmersión exagerada")
            return
        else:
            await send_error_message(ctx, "Cantidad de inmersión demasiado pequeña")
            return

    @commands.command(aliases=["log"])
    async def logprefix(self, ctx, medio, cantidad, descripcion):
        if medio.upper() not in MEDIA_TYPES:
            if medio.upper() in MEDIA_TYPES_ENGLISH:
                medio = MEDIA_TYPES_ENGLISH[medio.upper()]
            else:
                return await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
        if not str(cantidad).isnumeric():
            return await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
        if int(cantidad) > 5000000:
            return await send_error_message(ctx, "Cantidad de inmersión exagerada")
        message = ""
        description = ctx.message.content.split(" ")[3].split(";")
        if len(description) > 1:
            await self.log(ctx, medio, cantidad, description[0], int(description[1]))
        else:
            await self.log(ctx, medio, cantidad, description[0], 0)

    @commands.slash_command()
    async def puntos(self, ctx,
                     cantidad: discord.Option(int, "Puntos a calcular/cantidad a calcular puntos", min_value=1, required=True),
                     medio: discord.Option(str, "Medio del que calcular los puntos", choices=MEDIA_TYPES, required=False)):
        """Calcular cuanta inmersión se necesita para conseguir x puntos y cuantos puntos da x inmersión"""
        await set_processing(ctx)
        if medio:
            aux = {
                'medio': medio,
                'parametro': cantidad,
            }
            points = compute_points(aux)

            logs = await get_user_logs(self.db, ctx.author.id, "MES")
            user_points = 0
            for log in logs:
                user_points += log["puntos"]

            embed = discord.Embed(
                title="Preivisión de puntos", color=0x8d205f, description=f"Si inmersaras {get_media_element(cantidad,medio)} de {medio}:"
            )
            embed.add_field(name="Puntos otorgados", value=points)
            embed.add_field(name="Puntos mensuales",
                            value=user_points + points)
            await send_response(ctx, embed=embed, delete_after=30.0)
        else:
            immersion_needed = calc_media(int(cantidad))
            embed = discord.Embed(
                title=f"Para conseguir {cantidad} puntos necesitas inmersar:", color=0x8d205f)
            embed.add_field(name="Libro", value=get_media_element(
                immersion_needed["libro"], "LIBRO"), inline=False)
            embed.add_field(name="Manga", value=get_media_element(
                immersion_needed["manga"], "MANGA") + f" (aprox {math.ceil(int(immersion_needed['manga'])/170)} volúmenes)", inline=False)
            embed.add_field(name="Lectura / VN", value=get_media_element(
                immersion_needed["vn"], "VN"), inline=False)
            embed.add_field(name="Anime", value=get_media_element(
                math.ceil(immersion_needed["anime"]), "ANIME") + f" (aprox {get_media_element(immersion_needed['anime']*24, 'VIDEO')})", inline=False)
            embed.add_field(name="Audio / Video / Tiempo de lectura", value=get_media_element(
                immersion_needed["audio"], "AUDIO"), inline=False)
            await send_response(ctx, embed=embed, delete_after=60.0)

    @commands.command(aliases=["calcpuntos", 'calcularpuntos', 'puntos', 'calpoints'])
    async def puntosprefix(self, ctx, cantidad, medio=""):
        if not str(cantidad).isnumeric():
            if not str(cantidad).isnumeric():
                return await send_error_message(ctx, "Los puntos deben ser un número entero")
        if medio != "":
            if medio.upper() not in MEDIA_TYPES:
                return await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
            else:
                await self.puntos(ctx, cantidad, medio.upper())
        else:
            await self.puntos(ctx, cantidad, None)

    @commands.slash_command()
    async def undo(self, ctx):
        """Borra el último log hecho"""
        # Verify the user has logs
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return
        result = await remove_last_log(self.db, ctx.author.id)
        if result == 1:
            logdeleted = discord.Embed(color=0x24b14d)
            logdeleted.add_field(
                name="✅", value="Log eliminado con éxito", inline=False)
            await send_response(ctx, embed=logdeleted, delete_after=10.0)
        else:
            await send_error_message(ctx, "No quedan logs por borrar")

    @commands.command(aliases=["undo", "deshacer"])
    async def undoprefix(self, ctx):
        await self.undo(ctx)

    @commands.slash_command()
    async def remlog(self, ctx,
                     logid: discord.Option(int, "Id del log a borrar", required=True)):
        """Borra un log usando su identificador"""
        # Verify the user has logs
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        result = await remove_log(self.db, ctx.author.id, logid)
        if result == 1:
            logdeleted = discord.Embed(color=0x24b14d)
            logdeleted.add_field(
                name="✅", value="Log eliminado con éxito", inline=False)
            await send_response(ctx, embed=logdeleted, delete_after=10.0)
        else:
            await send_error_message(ctx, "Ese log no existe")

    @commands.command(aliases=["remlog", "dellog"])
    async def remlogprefix(self, ctx, logid):
        if not str(logid).isnumeric():
            return await send_error_message("El id del log debe ser un valor numérico")
        await self.remlog(ctx, logid)

    @commands.slash_command()
    async def ordenarlogs(self, ctx):
        """Rellena los huecos causados por logs borrados"""
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        users = self.db.users
        logs = users.find_one({'userId': ctx.author.id}, {'logs'})["logs"]
        newlogs = sorted(logs, key=lambda d: d['timestamp'])
        counter = 1
        for elem in newlogs:
            elem["id"] = counter
            counter = counter + 1
        users.update_one({'userId': ctx.author.id}, {'$set': {
                         'logs': newlogs, 'lastlog': len(newlogs)}})
        await send_response(ctx, "Tu toc ha sido remediado con éxito.")

    @commands.command(aliases=["ordenarlogs"])
    async def ordenarlogsprefix(self, ctx):
        await self.ordenarlogs(ctx)

    @commands.slash_command()
    async def ajrstats(self, ctx,
                       horas: discord.Option(bool, "Mostrar horas en vez de puntos", required=False, default=False)):
        """Estadísticas totales de todo el servidor de AJR"""
        results = {}

        rigth_now = datetime.today()
        start = datetime(year=2022, month=1, day=1)

        while start.year != rigth_now.year or start.month != (rigth_now + relativedelta(months=1)).month:
            divisor = 1
            if horas:
                divisor = 27
            results[f"{start.year}/{start.month}"] = math.ceil(await get_total_immersion_of_month(self.db, f"{start.year}/{start.month}") / divisor)

            start = start + relativedelta(months=1)

        graph = generate_linear_graph(results, horas)
        return await send_response(ctx, file=graph)

    @commands.command(aliases=["ajrstats"])
    async def ajrstatsprefix(self, ctx):
        return await self.ajrstats(ctx)

    @commands.slash_command()
    async def progreso(self, ctx,
                       año: discord.Option(int, "Año que cubre el ranking (el desglose será mensual)", min_value=2019, max_value=datetime.now().year, required=False, default=datetime.now().year),
                       total: discord.Option(bool, "Progreso desde el primer log registrado", required=False, default=False)):
        """Muestra una gráfica temporal con la inmersión segmentada en tipos"""
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        año = str(año)
        if total:
            año = "TOTAL"
        results = {}
        if año == "TOTAL":
            data = self.db.users.aggregate([
                {"$match": {"userId": ctx.author.id}},
                {"$project":
                 {"item": 1,
                  "firstElem": {"$arrayElemAt": ["$logs", 0]}
                  }
                 }
            ])
            firstlog = data.next()
            start = datetime.fromtimestamp(
                firstlog['firstElem']['timestamp']).replace(day=1)
            end = datetime.now().replace()
            steps = (end.year - start.year) * 12 + end.month - start.month + 1
            real_months = steps
        else:
            if int(año) < 1000:
                año = "20" + año
            start = datetime(year=int(año), month=1, day=1)
            end = datetime(year=int(año), month=12, day=31)
            steps = 12
        i = 0
        total = 0
        real_months = steps
        best_month = {
            'month': 0,
            'year': 0,
            'points': 0
        }
        while i < steps:
            begin = (start + relativedelta(months=i)).replace(day=1)
            logs = await get_user_logs(self.db, ctx.author.id, f"{begin.year}/{begin.month}")
            i += 1

            points = {
                "LIBRO": 0,
                "MANGA": 0,
                "ANIME": 0,
                "VN": 0,
                "LECTURA": 0,
                "TIEMPOLECTURA": 0,
                "AUDIO": 0,
                "VIDEO": 0,
            }
            local_total = 0
            for log in logs:
                points[log["medio"]] += log["puntos"]
                local_total += log["puntos"]
                total += log["puntos"]
            if local_total == 0:
                real_months -= 1
            if local_total > best_month["points"]:
                best_month["month"] = begin.month
                best_month["year"] = begin.year
                best_month["points"] = local_total
            results[f"{begin.year}/{begin.month}"] = points
        media = total / real_months
        normal = discord.Embed(
            title=f"Vista {get_ranking_title(año,'ALL')}", color=0xeeff00)
        normal.add_field(name="Usuario", value=ctx.author.name, inline=False)
        normal.add_field(name="Media en el periodo",
                         value=f"{round(media, 2)} puntos", inline=True)
        normal.add_field(
            name="Mejor mes", value=f"{MONTHS[best_month['month']-1].capitalize()} del {best_month['year']} con {round(best_month['points'],2)} puntos", inline=True)
        bardoc = generate_graph(results, "progress")
        normal.set_image(url="attachment://image.png")
        await send_response(ctx, embed=normal, file=bardoc)

    @commands.command(aliases=["progreso"])
    async def progresoprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.progreso(ctx, datetime.now().year, False)

    @commands.slash_command()
    async def findemes(self, ctx,
                       mes: discord.Option(int, "Mes que ha finalizado", min_value=1, max_value=12, required=False, default=datetime.now().month - 1),
                       video: discord.Option(bool, "Video o no", required=False, default=True)):
        """Video conmemorativo con ranking interactivo de todo el mes"""
        if ctx.author.id not in admin_users:
            return await send_error_message(ctx, "Vuelve a hacer eso y te mato")
        await set_processing(ctx)
        today = datetime.now()
        next_month = (mes) % 12 + 1
        day = (datetime(today.year, next_month, 1) - timedelta(days=1)).day
        await ctx.send("Procesando datos del mes, espere por favor...", delete_after=60.0)
        await get_logs_animation(self.db, mes, day)
        # Generate monthly ranking animation
        df = pd.read_csv('temp/test.csv', index_col='date',
                         parse_dates=['date'])
        df.tail()
        plt.rc('font', family='Noto Sans JP')
        plt.rcParams['text.color'] = "#FFFFFF"
        plt.rcParams['axes.labelcolor'] = "#FFFFFF"
        plt.rcParams['xtick.color'] = "#FFFFFF"
        plt.rcParams['ytick.color'] = "#FFFFFF"
        plt.rcParams.update({'figure.autolayout': True})
        fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
        ax.set_title(f"Ranking {intToMonth(mes)} AJR")
        ax.set_facecolor("#36393F")
        fig.set_facecolor("#36393F")
        ax.set_xlabel('Puntos', color="white")
        ax.tick_params(axis='both', colors='white')
        if video:
            bcr.bar_chart_race(df, 'temp/video.mp4', figsize=(20, 12), fig=fig,
                               period_fmt="%d/%m/%Y", period_length=2000, steps_per_period=75, bar_size=0.7, interpolate_period=True)
            file = discord.File("temp/video.mp4", filename="ranking.mp4")
        mvp = await get_best_user_of_range(self.db, "TOTAL", f"{today.year}/{mes}")
        newrole = discord.utils.get(ctx.guild.roles, name="先輩")
        for user in ctx.guild.members:
            if newrole in user.roles:
                await user.remove_roles(newrole)
        mvpuser = ctx.guild.get_member(mvp["id"])
        await mvpuser.add_roles(newrole)

        embed = discord.Embed(
            title=f"🎌 AJR mes de {intToMonth(mes)} 🎌", color=0x1302ff, description="-----------------")
        embed.add_field(name="Usuario del mes",
                        value=mvp["username"], inline=False)
        if mvpuser is not None:
            embed.set_thumbnail(
                url=mvpuser.avatar)
        embed.add_field(name="Puntos conseguidos",
                        value=round(mvp["points"], 2), inline=False)
        message = f"🎉 Felicidades a <@{mvp['id']}> por ser el usuario del mes de {intToMonth(mes)}!"
        channel = await self.bot.fetch_channel(announces_channel)
        if video:
            await channel.send(embed=embed, content=message, file=file)
        else:
            await channel.send(embed=embed, content=message)
        await send_response(ctx, "Gráfico generado con éxito")

    @commands.slash_command()
    async def addanilist(self, ctx,
                         anilistuser: discord.Option(str, "Nombre de usuario anilist", required=True),
                         fechaminima: discord.Option(str, "Fecha de inicio en formato YYYYMMDD", required=False)):
        """Añade logs de anime de anilist"""
        if fechaminima and len(fechaminima) != 8:
            await send_error_message(ctx, "La fecha debe tener el formato YYYYMMDD")
            return

        await set_processing(ctx)
        user_id = await get_anilist_id(anilistuser)
        if user_id == -1:
            await send_error_message(ctx, "Esa cuenta de anilist no existe o es privada, cambia tus ajustes de privacidad.")
            return
        await send_response(ctx, f"Añadiendo los logs de anilist de {anilistuser} a tu cuenta... si esto ha sido un error contacta con el administrador.", delete_after=10.0)
        nextPage = True
        page = 1
        errored = []
        total_logs = 0
        total_repeated = 0
        while nextPage:
            logs = await get_anilist_logs(user_id, page, fechaminima)
            nextPage = logs["data"]["Page"]["pageInfo"]["hasNextPage"]
            for log in logs["data"]["Page"]["mediaList"]:
                newlog = {
                    'anilistAccount': anilistuser,
                    'anilistId': log["id"],
                    'timestamp': 0,
                    'descripcion': "",
                    'medio': "",
                    'parametro': ""
                }
                newlog["descripcion"] = log["media"]["title"]["native"]
                if log["media"]["format"] == "MOVIE":
                    newlog["medio"] = "VIDEO"
                    newlog["parametro"] = str(log["media"]["duration"])
                elif log["media"]["duration"] < 19:
                    newlog["medio"] = "VIDEO"
                    newlog["parametro"] = str(
                        log["media"]["duration"] * log["media"]["episodes"])
                else:
                    newlog["medio"] = "ANIME"
                    newlog["parametro"] = str(log["media"]["episodes"])

                failed = False
                if log["completedAt"]["year"]:
                    newlog["timestamp"] = int(datetime(
                        log["completedAt"]["year"], log["completedAt"]["month"], log["completedAt"]["day"]).timestamp())
                elif log["startedAt"]["year"]:
                    newlog["timestamp"] = int(datetime(
                        log["startedAt"]["year"], log["startedAt"]["month"], log["startedAt"]["day"]).timestamp())
                else:
                    errored.append(log["media"]["title"]["native"])
                    failed = True

                if self.db.users.find({'userId': ctx.author.id, 'logs': {'$elemMatch': {'anilistId': newlog["anilistId"]}}}).count() > 0:
                    total_repeated += 1
                    failed = True

                if not failed:
                    total_logs += 1
                    output = compute_points(newlog)
                    if output > 0:
                        logid = await add_log(self.db, ctx.author.id, newlog, ctx.author.name)

            page += 1
        total_errored = ""
        total_len = 0
        total_size = 0
        for elem in errored:
            total_errored += elem + "\n"
            total_len += 1
            total_size += len(elem)
        if total_size > 500:
            total_errored = "Demasiados logs fallidos para poder representarlo, revisa que tus entradas de anilist tienen fecha de finalización."
        embed = discord.Embed(
            title=f"Añadido a logs la cuenta de anilist de {anilistuser}", color=0x1302ff, description="-----------------")
        embed.add_field(name="Logs introducidos",
                        value=total_logs, inline=False)
        if total_repeated > 0:
            embed.add_field(name="Logs repetidos",
                            value=total_repeated, inline=False)
        if total_errored != "":
            embed.add_field(name="Logs fallidos",
                            value=total_len, inline=False)
            embed.add_field(name="Lista de fallidos",
                            value=total_errored, inline=True)
        embed.set_footer(
            text="Es recomendable que escribas el comando .ordenarlogs después de hacer un import de anilist.")
        await send_response(ctx, embed=embed)
        print(errored)

    @commands.command(aliases=["addanilist"])
    async def addanilistprefix(self, ctx, anilistuser, fechaminima=""):
        await self.addanilist(ctx, anilistuser, fechaminima)


def setup(bot):
    bot.add_cog(Immersion(bot))
