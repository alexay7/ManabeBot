import re
from asyncio import sleep
import csv
import calendar
from copy import copy
from datetime import datetime, timedelta
import itertools
import json
import math
import numpy as np
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
from helpers.inmersion import (MEDIA_TYPES, MEDIA_TYPES_ENGLISH, MONTHS, TIMESTAMP_TYPES,
                               get_media_level, get_param_for_media_level, get_immersion_level, add_log, calc_media,
                               check_user, compute_points, create_user, generate_graph, generate_linear_graph,
                               get_best_user_of_range, get_logs_animation, get_media_element, get_ranking_title,
                               get_sorted_ranking, get_total_immersion_of_month, get_total_parameter_of_media,
                               get_user_logs, remove_last_log, remove_log, send_message_with_buttons, get_all_logs_in_day,
                               get_last_log, check_max_immersion, bonus_log, unbonus_log)

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

            if len(message.embeds) > 0:
                if "Log registrado con éxito" in message.embeds[0].title and int(message.embeds[0].footer.text.replace("Id del usuario: ", "")) == payload.user_id:
                    log_id = message.embeds[0].description.split(" ")[
                        2].replace("#", "")
                    if str(payload.emoji) == "❌":
                        await remove_log(self.db, payload.user_id, log_id)
                        logdeleted = discord.Embed(color=0x24b14d)
                        logdeleted.add_field(
                            name="✅", value=f"Log {message.embeds[0].description.split(' ')[2]} eliminado con éxito", inline=False)
                        await channel.send(embed=logdeleted, delete_after=10.0)
                        await message.delete()
                    elif str(payload.emoji) == "🟢":
                        old_embed = message.embeds[0]

                        if "AJR" in old_embed.title:
                            await send_error_message(channel, "Este log ya está marcado como bonus")
                            return

                        new_points_aux = await bonus_log(self.db, log_id, payload.user_id)

                        if new_points_aux < 0:
                            await send_error_message(channel, "Este log ya está marcado como bonus")
                            return

                        old_points = float(
                            old_embed.fields[2].value.split(" ")[0])
                        old_points_added = float(old_embed.fields[2].value.split(" ")[
                            1].replace("(+", "").replace(")", ""))
                        new_points = old_points-old_points_added+new_points_aux

                        old_embed.remove_field(2)
                        old_embed.insert_field_at(
                            index=2, name="Puntos (x1.4)", value=f"{round(new_points,2)} (+{round(new_points_aux,2)})", inline=True)
                        old_embed.title = old_embed.title+" (club AJR)"
                        old_embed.color = 0xbf9000
                        await message.edit(embed=old_embed)
                        await message.clear_reaction("🟢")
                    elif str(payload.emoji == "🔴"):
                        old_embed = message.embeds[0]

                        if "AJR" not in old_embed.title:
                            await send_error_message(channel, "Este log no está marcado como bonus")
                            return

                        new_points_aux = await unbonus_log(self.db, log_id, payload.user_id)

                        if new_points_aux < 0:
                            await send_error_message(channel, "Este log no está marcado como bonus")
                            return

                        old_points = float(
                            old_embed.fields[2].value.split(" ")[0])
                        old_points_added = float(old_embed.fields[2].value.split(" ")[
                            1].replace("(+", "").replace(")", ""))
                        new_points = old_points-old_points_added+new_points_aux

                        old_embed.remove_field(2)
                        old_embed.insert_field_at(
                            index=2, name="Puntos", value=f"{round(new_points,2)} (+{round(new_points_aux,2)})", inline=True)
                        old_embed.title = old_embed.title.replace(
                            " (club AJR)", "")
                        old_embed.color = 0x24b14d
                        await message.edit(embed=old_embed)
                        await message.clear_reaction("🔴")

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
                    medio: discord.Option(str, "Medio de inmersión que cubre el ranking", choices=MEDIA_TYPES.union(["CARACTERES"]), required=False, default="TOTAL"),
                    comienzo: discord.Option(str, "Fecha de inicio (DD/MM/YYYY)", required=False),
                    final: discord.Option(str, "Fecha de fin (DD/MM/YYYY)", required=False),
                    extendido: discord.Option(
                        bool, "Muestra el ranking completo", required=False)
                    ):
        """Imprime un ranking de inmersión según los parámetros indicados"""
        if (comienzo and not final) or (final and not comienzo):
            await send_error_message(ctx, "Debes concretar un principio y un final")
            return

        if comienzo and final:
            periodo = comienzo + "-" + final

        await set_processing(ctx)

        chars = medio == "CARACTERES"
        if chars:
            medio = "TOTAL"

        sortedlist = await get_sorted_ranking(self.db, periodo, medio, chars)
        message = ""
        position = 1
        total_users = 10
        if extendido:
            total_users = len(sortedlist)
        for user in sortedlist[0:total_users]:
            if user["points"] != 0:
                if chars:
                    if user["parameters"] != 0:
                        message += f"**{str(position)}º {user['username']}:** {str(round(user['parameters'],2))} caracteres"
                else:
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
        await self.podio(ctx, "MES", "TOTAL", None, None, None)

    @commands.slash_command()
    async def logs(self, ctx,
                   periodo: discord.Option(str, "Periodo de tiempo para ver logs", choices=TIMESTAMP_TYPES, required=False, default="TOTAL"),
                   medio: discord.Option(str, "Medio de inmersión para ver logs", choices=MEDIA_TYPES, required=False, default="TOTAL"),
                   usuario: discord.Option(str, "ID DEL Usuario del que quieres ver los logs", required=False)):
        """Muestra lista con todos los logs hechos con los parámetros indicados"""
        await set_processing(ctx)

        if not usuario:
            usuario = ctx.author.id
        else:
            if not usuario.isnumeric():
                await send_error_message(ctx, "Debes poner el ID del usuario del que quieras saber los logs! (Lo puedes ver al final de los logs que haya hecho)")
                return

        if await check_user(self.db, int(usuario)) is False:
            await send_error_message(ctx, "No se han encontrado logs asociados a esa Id.")
            return

        result = await get_user_logs(self.db, int(usuario), periodo, medio)
        sorted_res = sorted(result, key=lambda x: x["timestamp"], reverse=True)

        output = [
            "LOGID | FECHA: MEDIO CANTIDAD -> PUNTOS: DESCRIPCIÓN\n------------------------------------\n"]
        overflow = 0
        for log in sorted_res:
            extra = ""

            if "bonus" in log and log["bonus"]:
                extra = " (Club AJR)"

            timestring = datetime.fromtimestamp(
                log["timestamp"]).strftime('%d/%m/%Y')
            line = f"#{log['id']} | {timestring}: {log['medio']}{extra} {get_media_element(log['parametro'],log['medio'])} -> {log['puntos']} puntos: {log['descripcion']}\n"
            if "tiempo" in log:
                line = line.replace(
                    "\n", f" | tiempo: {get_media_element(log['tiempo'],'VIDEO')}\n")
            if "caracteres" in log:
                line = line.replace(
                    "\n", f" | caracteres: {get_media_element(log['caracteres'],'LECTURA')}\n")
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
                 gráfica: discord.Option(str, "Gráficos para acompañar los datos", choices=["SECTORES", "BARRAS", "VELOCIDAD", "NINGUNO"], required=False, default="SECTORES"),
                 comienzo: discord.Option(str, "Fecha de inicio (DD/MM/YYYY)", required=False),
                 final: discord.Option(str, "Fecha de fin (DD/MM/YYYY)", required=False)):
        """Muestra pequeño resumen de lo inmersado"""
        await set_processing(ctx)
        if not await check_user(self.db, ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log")
            return

        if (comienzo and not final) or (final and not comienzo):
            await send_error_message(ctx, "Debes concretar un principio y un final")
            return

        if comienzo and final:
            periodo = comienzo + "-" + final
        else:
            if gráfica == "BARRAS":
                periodo = "SEMANA"

        logs = await get_user_logs(self.db, ctx.author.id, periodo)
        if logs == "":
            await send_error_message("Algo ha salido mal, revisa el comando")
            return
        points = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "OUTPUT": 0,
            "AUDIO": 0,
            "VIDEO": 0,
            "TOTAL": 0,
            "CLUB AJR": 0
        }
        parameters = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "OUTPUT": 0,
            "AUDIO": 0,
            "VIDEO": 0
        }

        graphlogs = {}

        output = ""
        for log in logs:
            log_points = log["puntos"]
            bonus_points = 0

            if "bonus" in log and log["bonus"]:
                log_points = log["puntos"]/1.4
                bonus_points = log["puntos"]-log_points
                points["CLUB AJR"] += bonus_points

            points[log["medio"]] += log_points
            parameters[log["medio"]] += int(log["parametro"])
            points["TOTAL"] += log["puntos"]
            logdate = str(datetime.fromtimestamp(
                log["timestamp"])).replace("-", "/").split(" ")[0]

            if logdate in graphlogs:
                graphlogs[logdate] += log_points
            else:
                graphlogs[logdate] = log_points

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
            if points["OUTPUT"] > 0:
                output += f"**OUTPUT:** {get_media_element(parameters['OUTPUT'],'OUTPUT')} -> {round(points['OUTPUT'],2)} pts\n"
            if points["AUDIO"] > 0:
                output += f"**AUDIO:** {get_media_element(parameters['AUDIO'],'AUDIO')} -> {round(points['AUDIO'],2)} pts\n"
            if points["VIDEO"] > 0:
                output += f"**VIDEO:** {get_media_element(parameters['VIDEO'],'VIDEO')} -> {round(points['VIDEO'],2)} pts\n"
            if points["CLUB AJR"] > 0 and periodo != "TOTAL":
                output += f"**CLUB AJR:** {round(points['CLUB AJR'],2)} puntos\n"
        ranking = await get_sorted_ranking(self.db, periodo, "TOTAL")
        for user in ranking:
            if user["username"] == ctx.author.name:
                position = ranking.index(user)

        days = 0

        if periodo == "SEMANA":
            days = 7
        elif periodo == "MES":
            days = datetime.today().day

        normal = discord.Embed(
            title=f"Vista {get_ranking_title(periodo,'ALL')}", color=0xeeff00)
        normal.add_field(name="Usuario", value=ctx.author.name, inline=True)
        normal.add_field(name="Puntos", value=round(
            points["TOTAL"], 2), inline=True)
        normal.add_field(name="Posición ranking",
                         value=f"{position+1}º", inline=True)
        normal.add_field(name="Horas de inmersión",
                         value=math.ceil((points["TOTAL"]-points["CLUB AJR"]) / 27), inline=True)
        if days > 0:
            normal.add_field(
                name="Media diaria", value=f"{round(points['TOTAL']/days,2)}", inline=True)
        normal.add_field(name="Medios", value=output, inline=False)

        if gráfica == "SECTORES":
            piedoc = generate_graph(points, "piechart", total_points=round(
                points["TOTAL"], 2), position=f"{position+1}º")
            normal.set_image(url="attachment://image.png")
            await send_response(ctx, embed=normal, file=piedoc)
        elif gráfica == "BARRAS":
            bardoc = generate_graph(graphlogs, "bars", periodo)
            normal.set_image(url="attachment://image.png")
            await send_response(ctx, embed=normal, file=bardoc)
        elif gráfica == "VELOCIDAD":
            # Obtener los logs del usuario
            manga_logs = await get_user_logs(self.db, ctx.author.id, "TOTAL", "MANGA")
            read_logs = await get_user_logs(self.db, ctx.author.id, "TOTAL", "LECTURA")
            logs = itertools.chain(manga_logs, read_logs)

            # Crear un conjunto de todos los meses para los que hay registros en cualquiera de los dos medios
            months = set()
            logs_by_medium_and_month = {"MANGA": {}, "LECTURA": {}}
            for log in logs:
                if "tiempo" in log:
                    date = datetime.fromtimestamp(log["timestamp"])
                    month = date.strftime("%Y-%m")
                    months.add(month)
                    medium = log["medio"]
                    if month not in logs_by_medium_and_month[medium]:
                        logs_by_medium_and_month[medium][month] = []
                    logs_by_medium_and_month[medium][month].append(log)

            months = sorted(months)

            # Calcular la velocidad media por mes para cada medio
            speeds_by_medium_and_month = {"MANGA": {}, "LECTURA": {}}
            for medium, logs_by_month in logs_by_medium_and_month.items():
                for month in months:
                    if month not in logs_by_month:
                        logs_by_month[month] = []
                    month_logs = logs_by_month[month]
                    speeds = []
                    for log in month_logs:
                        if log["tiempo"] > 0:
                            if medium == "MANGA" and "caracteres" in log.keys():
                                speed = int(log["caracteres"]) / \
                                    log["tiempo"]*60
                                speeds.append(speed)
                            elif medium == "LECTURA":
                                speed = (
                                    int(log["parametro"])) / log["tiempo"]*60
                                speeds.append(speed)
                    if speeds:
                        speeds_by_medium_and_month[medium][month] = sum(
                            speeds) / len(speeds)
                    else:
                        speeds_by_medium_and_month[medium][month] = 0

            x_values_manga = list(speeds_by_medium_and_month["MANGA"].keys())
            y_values_manga = list(speeds_by_medium_and_month["MANGA"].values())

            x_values_lectura = list(
                speeds_by_medium_and_month["LECTURA"].keys())
            y_values_lectura = list(
                speeds_by_medium_and_month["LECTURA"].values())

            for i in range(1, len(y_values_manga)):
                if y_values_manga[i] == 0:
                    y_values_manga[i] = y_values_manga[i - 1]

            for i in range(1, len(y_values_lectura)):
                if y_values_lectura[i] == 0:
                    y_values_lectura[i] = y_values_lectura[i - 1]

            # Crear la gráfica
            if speeds_by_medium_and_month["MANGA"] and speeds_by_medium_and_month["LECTURA"]:
                plt.figure(figsize=(10, 8))
                plt.plot(x_values_manga, y_values_manga, label="MANGA")
                plt.plot(x_values_lectura, y_values_lectura, label="LECTURA")
                plt.xlabel("Mes")
                plt.ylabel("Caracters leidos por hora")
                plt.title(
                    "Velocidad de lectura mensual para el usuario {}".format(ctx.author.name))
                plt.legend()
                plt.xticks(rotation=45)
                plt.savefig("temp/image.png")
                plt.close()
                file = discord.File("temp/image.png", filename="image.png")
                normal.set_image(url="attachment://image.png")
                await send_response(ctx, embed=normal, file=file)
        else:
            await send_response(ctx, embed=normal)

    @commands.command(aliases=["yo", "me", "resumen"])
    async def meprefix(self, ctx, periodo="TOTAL", grafica="SECTORES"):
        if periodo.upper() in ["SECTORES", "BARRAS"]:
            grafica = periodo
            periodo = "TOTAL"
        await self.me(ctx, periodo.upper(), grafica.upper(), None, None)

    @commands.slash_command()
    async def backfill(self, ctx,
                       fecha: discord.Option(str, "Fecha en formato DD/MM/YYYY", required=True),
                       medio: discord.Option(str, "Medio inmersado", choices=MEDIA_TYPES, required=True),
                       cantidad: discord.Option(int, "Cantidad inmersada", required=True, min_value=1, max_value=5000000),
                       descripción: discord.Option(str, "Pequeño resumen de lo inmersado", required=True),
                       tiempo: discord.Option(int, "Tiempo que te ha llevado en minutos", required=False),
                       caracteres: discord.Option(int, "Caracteres leídos (para medios que no sean lectura)", required=False),
                       bonus: discord.Option(bool, "Log de un club mensual de AJR", required=False)):
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

        if not check_max_immersion(cantidad, medio.upper()):
            await send_error_message(ctx, "Esa cantidad de inmersión no es posible en un solo día, considera usar el comando /backfill para indicar las fechas con precisión")
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

        bonus = "ajrclub" in descripción.lower() or bonus or "clubajr" in descripción.lower(
        ) or "ajr-club" in descripción.lower() or "club-ajr" in descripción.lower()

        compiled = re.compile(re.escape("ajrclub"), re.IGNORECASE)
        compiled_2 = re.compile(re.escape("clubajr"), re.IGNORECASE)
        message_aux = compiled.sub("", descripción).strip()
        message = compiled_2.sub("", message_aux).strip()

        newlog = {
            'timestamp': datets,
            'descripcion': message,
            'medio': medio.upper(),
            'parametro': cantidad
        }

        output = compute_points(newlog)

        if tiempo and tiempo > 0:
            newlog['tiempo'] = math.ceil(tiempo)
            auxlog = copy(newlog)
            auxlog["medio"] = "TIEMPOLECTURA"
            auxlog["parametro"] = tiempo
            new_points = compute_points(auxlog)
            if new_points > output:
                output = new_points

        if caracteres and caracteres > 0 and medio.upper() not in ["LECTURA", "VN"]:
            newlog['caracteres'] = math.ceil(caracteres)
            auxlog = copy(newlog)
            auxlog["medio"] = "LECTURA"
            auxlog["parametro"] = caracteres
            new_points = compute_points(auxlog, bonus)
            if new_points > output:
                output = new_points
                newlog["puntos"] = new_points

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

            color = 0x24b14d
            extra = ""
            multiplier = ""

            if bonus:
                color = 0xbf9000
                extra = " (club AJR)"
                multiplier = " (x1.4)"

            embed = discord.Embed(title=f"Log registrado con éxito{extra}",
                                  description=f"Log #{logid} || {strdate.strftime('%d/%m/%Y')}", color=color)
            embed.add_field(
                name="Usuario", value=ctx.author.name, inline=True)
            embed.add_field(name="Medio", value=medio.upper(), inline=True)
            embed.add_field(
                name=f"Puntos{multiplier}", value=f"{round(current_points,2)} (+{output})", inline=True)
            embed.add_field(name="Inmersado",
                            value=get_media_element(cantidad, medio.upper()), inline=True)
            embed.add_field(name="Inmersión",
                            value=message, inline=False)
            if tiempo and tiempo > 0:
                embed.add_field(name="Tiempo invertido:",
                                value=get_media_element(tiempo, "VIDEO"), inline=False)
            if caracteres and caracteres > 0:
                embed.add_field(name="Caracteres leídos",
                                value=get_media_element(caracteres, "LECTURA"), inline=False)
            if newposition < position:
                embed.add_field(
                    name="🎉 Has subido en el ranking del mes! 🎉", value=f"**{position+1}º** ---> **{newposition+1}º**", inline=False)
            embed.set_footer(
                text=ctx.author.id)
            message = await send_response(ctx, embed=embed)
            await message.add_reaction("❌")
        elif output == 0:
            await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
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

    @commands.slash_command()
    async def logros(self, ctx, userid: discord.Option(str, "Usuario del que quieres ver los logs", required=False)):
        """Obtener tus logros de inmersión"""
        await self.achievements_(ctx, userid)

    @commands.command(aliases=["achievements", "logros", "level", "nivel"])
    async def achievements_(self, ctx, userId=None):
        """Obtener tus logros de inmersión"""
        await set_processing(ctx)

        user_id = ctx.author.id
        user_name = ctx.author.name

        if userId:
            try:
                users = self.db.users
                found = users.find_one({"userId": int(userId)})
                if found:
                    user_name = found["username"]
                    user_id = int(userId)
                else:
                    await ctx.message.delete()
                    return
            except:
                await ctx.message.delete()
                return

        logs = await get_user_logs(self.db, user_id, "TOTAL")
        points = {
            "LIBRO": 0,
            "MANGA": 0,
            "ANIME": 0,
            "VN": 0,
            "LECTURA": 0,
            "TIEMPOLECTURA": 0,
            "OUTPUT": 0,
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
            "OUTPUT": 0,
            "AUDIO": 0,
            "VIDEO": 0,
            "CLUB AJR": 0
        }

        graphlogs = {}

        for log in logs:
            log_points = log["puntos"]
            if "bonus" in log and log["bonus"]:
                log_points = log["puntos"]/1.4
                bonus_points = log["puntos"]-log_points
                parameters["CLUB AJR"] += bonus_points

            points[log["medio"]] += log_points
            parameters[log["medio"]] += int(log["parametro"])
            points["TOTAL"] += log_points
            logdate = str(datetime.fromtimestamp(
                log["timestamp"])).replace("-", "/").split(" ")[0]

            if logdate in graphlogs:
                graphlogs[logdate] += log_points
            else:
                graphlogs[logdate] = log_points

        output = "```"
        for key, value in parameters.items():
            current_level = get_media_level(value, key)
            if value > 0:
                output += f"-> Eres nivel {current_level+1} en {key} con un total de {get_media_element(value,key)}\n"

        title = f"🎌 Tus logros de inmersión 🎌"

        if userId:
            title = f"🎌 Logros de inmersión de {user_name} 🎌"

        normal = discord.Embed(
            title=title, color=0xeeff00)
        normal.add_field(
            name="Usuario", value=f"{user_name} **[Lvl: {get_immersion_level(points['TOTAL'])}]**", inline=True)
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
                  tiempo: discord.Option(int, "Tiempo que te ha llevado en minutos", required=False),
                  caracteres: discord.Option(int, "Caracteres leídos (para medios que no sean lectura)", required=False),
                  bonus: discord.Option(
                      bool, "Log de un club mensual de AJR", required=False)
                  ):
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

        if not check_max_immersion(int(cantidad), medio.upper()):
            await send_error_message(ctx, "Esa cantidad de inmersión no es posible en un solo día, considera usar el comando /backfill para indicar las fechas con precisión")
            return

        bonus = "ajrclub" in descripción.lower() or bonus or "clubajr" in descripción.lower(
        ) or "ajr-club" in descripción.lower() or "club-ajr" in descripción.lower()

        compiled = re.compile(re.escape("ajrclub"), re.IGNORECASE)
        compiled_2 = re.compile(re.escape("clubajr"), re.IGNORECASE)
        message_aux = compiled.sub("", descripción).strip()
        message = compiled_2.sub("", message_aux).strip()

        today = datetime.today()

        newlog = {
            'timestamp': int(today.timestamp()),
            'descripcion': message,
            'medio': medio.upper(),
            'parametro': cantidad,
            "bonus": bonus
        }
        output = compute_points(newlog, bonus)

        if tiempo and tiempo > 0:
            newlog['tiempo'] = math.ceil(tiempo)
            auxlog = copy(newlog)
            auxlog["medio"] = "TIEMPOLECTURA"
            auxlog["parametro"] = tiempo
            new_points = compute_points(auxlog, bonus)
            if new_points > output:
                output = new_points
                newlog["puntos"] = new_points

        if caracteres and caracteres > 0 and medio.upper() not in ["LECTURA", "VN"]:
            newlog['caracteres'] = math.ceil(caracteres)
            auxlog = copy(newlog)
            auxlog["medio"] = "LECTURA"
            auxlog["parametro"] = caracteres
            new_points = compute_points(auxlog, bonus)
            if new_points > output:
                output = new_points
                newlog["puntos"] = new_points

        if output > 0.01:
            # Obtiene el ranking previo al log del usuario
            ranking = await get_sorted_ranking(self.db, "MES", "TOTAL")
            newranking = ranking

            for user in ranking:
                if user["username"] == ctx.author.name:
                    position = ranking.index(user)

                    ranking[position]["points"] += output

                    # Obtiene el ranking actualizado con los nuevos puntos del usuario
                    newranking = sorted(
                        ranking, key=lambda x: x["points"], reverse=True)

            for user in newranking:
                if user["username"] == ctx.author.name:
                    # Busca el indice del usuario en el nuevo ranking
                    newposition = newranking.index(user)
                    # Obtiene el número de puntos del usuario tras el log
                    current_points = user["points"]

            logid = await add_log(self.db, ctx.author.id, newlog, ctx.author.name)

            next_user = {
                "user": "",
                "difference": 0,
                "outside": False
            }

            if newposition > 9:
                # usuario que va en la posición 10
                next_user_aux = newranking[9]
                next_user["outside"] = True
            elif newposition != 0:
                # usuario que va delante de ti
                next_user_aux = newranking[newposition-1]

            if newposition != 0:
                next_user["user"] = next_user_aux["username"]
                next_user["difference"] = next_user_aux["points"] - \
                    current_points

            # Get streak
            current_streak = 0
            current_day = today

            while True:
                day_logs = await get_all_logs_in_day(self.db, ctx.author.id, current_day)
                if day_logs > 0:
                    current_streak += 1
                    current_day -= timedelta(days=1)
                else:
                    break

            color = 0x24b14d
            extra = ""
            multiplier = ""

            if bonus:
                color = 0xbf9000
                extra = " (club AJR)"
                multiplier = " (x1.4)"

            embed = discord.Embed(title=f"Log registrado con éxito{extra}",
                                  description=f"Id Log #{logid} || Fecha: {today.strftime('%d/%m/%Y')}", color=color)
            embed.add_field(
                name="Usuario", value=ctx.author.name, inline=True)
            embed.add_field(name="Medio", value=medio.upper(), inline=True)
            embed.add_field(
                name=f"Puntos{multiplier}", value=f"{round(current_points,2)} (+{output})", inline=True)
            embed.add_field(name="Inmersado",
                            value=get_media_element(cantidad, medio.upper()), inline=True)
            embed.add_field(name="Descripción",
                            value=message, inline=False)
            if tiempo and tiempo > 0:
                embed.add_field(name="Tiempo invertido",
                                value=get_media_element(tiempo, "VIDEO"), inline=False)
            if caracteres and int(caracteres) > 0:
                embed.add_field(name="Caracteres leídos",
                                value=get_media_element(caracteres, "LECTURA"), inline=False)
            if (caracteres and caracteres > 0) and tiempo and tiempo > 0:
                embed.add_field(name="Velocidad media",
                                value=f"{math.floor(int(caracteres)/tiempo*60)}chars/h", inline=False)
            elif (medio.upper() in ["LECTURA", "VN"]) and tiempo and tiempo > 0:
                embed.add_field(name="Velocidad media",
                                value=f"{math.floor(int(cantidad)/tiempo*60)}chars/h", inline=False)
            if current_streak > 1:
                embed.add_field(name="⚡ Racha actual de logueo ⚡ ",
                                value=f"{current_streak} días", inline=False)
            if newposition < position:
                embed.add_field(
                    name="🎉 Has subido en el ranking del mes! 🎉", value=f"**{position+1}º** ---> **{newposition+1}º**", inline=False)
            if newposition != 0:
                aux_title = f"el {newposition}º puesto"
                if newposition == 1 or newposition == 3:
                    aux_title = f"el {newposition}er puesto"
                if next_user["outside"]:
                    aux_title = "entrar al podio"
                embed.add_field(
                    name=f"⚔️ Lucha por {aux_title} ⚔️",
                    value=f"Tienes a {next_user['user']} a {round(next_user['difference'],2)} puntos. ¡Animo!",
                    inline=False
                )
            embed.set_footer(
                text=f"Id del usuario: {ctx.author.id}")
            message = await send_response(ctx, embed=embed)
            await message.add_reaction("❌")
            current_param = await get_total_parameter_of_media(self.db, medio.upper(), ctx.author.id)

            param_before = current_param - int(cantidad)

            level_before = get_media_level(
                current_param - int(cantidad), medio.upper())
            level_after = get_media_level(current_param, medio.upper())

            if level_after > level_before and level_after % 5 == 0:
                if medio.upper() in ["ANIME", "VN", "LECTURA"]:
                    verbo = "inmersados"
                else:
                    verbo = "inmersadas"
                achievement_embed = discord.Embed(title=f"¡Nuevo logro de {ctx.author.name}!",
                                                  description="¡Sigue así!", color=0x0095ff)
                achievement_embed.set_thumbnail(url=ctx.author.avatar)
                achievement_embed.add_field(
                    name="Logro conseguido", value=f"{get_media_element(math.floor(get_param_for_media_level(level_after,medio.upper())),medio.upper())} de {medio.lower()} {verbo}")
                await send_response(ctx, embed=achievement_embed)
            await sleep(10)
            try:
                await message.clear_reaction("❌")
            except discord.errors.NotFound:
                pass

        elif output == 0:
            await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
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
    async def logprefix(self, ctx, medio, cantidad):
        if medio.upper() not in MEDIA_TYPES:
            if medio.upper() in MEDIA_TYPES_ENGLISH:
                medio = MEDIA_TYPES_ENGLISH[medio.upper()]
            else:
                return await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
        if not str(cantidad).isnumeric():
            return await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
        if int(cantidad) > 5000000:
            return await send_error_message(ctx, "Cantidad de inmersión exagerada")

        fields_num = len(ctx.message.content.split(" "))

        if fields_num < 4:
            return await send_error_message(ctx, "Faltan parametros para realizar el log, recuerda que el formato debe ser\n**.log <tipo> <parametro> <descripción>;<tiempo\*>&<caracteres\*>**\n\* Opcionales")

        time = "0"
        characters = "0"
        descripcion = " ".join(ctx.message.content.split(" ")[3:])

        if ";" in descripcion:
            split_desc = descripcion.split(";")
            message = split_desc[0]
            time = split_desc[1]
            extras = True
        else:
            message = descripcion
        # puede haber un & pegado al mensaje o al tiempo

        if "&" in message:
            split_desc = message.split("&")
            message = split_desc[0]
            characters = split_desc[1]

        if "&" in time:
            split_desc = time.split("&")
            time = split_desc[0]
            characters = split_desc[1]

        await self.log(ctx, medio, cantidad, message, int(time), int(characters), False)

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
                title="Previsión de puntos", color=0x8d205f, description=f"Si inmersaras {get_media_element(cantidad,medio)} de {medio}:"
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
                return await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
            else:
                await self.puntos(ctx, cantidad, medio.upper())
        else:
            await self.puntos(ctx, cantidad, None)

    @commands.command(aliases=["ultimolog"])
    async def lastlog(self, ctx):
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

        last_log = await get_last_log(self.db, ctx.author.id)

        today = datetime.utcfromtimestamp(last_log["timestamp"])

        embed = discord.Embed(title="Log registrado con éxito",
                              description=f"Id Log #{last_log['id']} || Fecha: {today.strftime('%d/%m/%Y')}", color=0x24b14d)
        embed.add_field(
            name="Usuario", value=ctx.author.name, inline=True)
        embed.add_field(
            name="Medio", value=last_log["medio"].upper(), inline=True)
        embed.add_field(
            name="Puntos", value=f"{round(last_log['puntos'],2)}", inline=True)
        embed.add_field(name="Inmersado",
                        value=get_media_element(int(last_log["parametro"]), last_log["medio"].upper()), inline=True)
        embed.add_field(name="Descripción",
                        value=last_log["descripcion"], inline=False)
        embed.set_footer(
            text=f"Id del usuario: {ctx.author.id}")
        await send_response(ctx, embed=embed, delete_after=10.0)
        await ctx.message.delete()

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
        result, last_log_id = await remove_last_log(self.db, ctx.author.id)
        if result == 1:
            logdeleted = discord.Embed(color=0x24b14d)
            logdeleted.add_field(
                name="✅", value=f"Log #{last_log_id} eliminado con éxito", inline=False)
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
        print(result)
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
        logs = self.db.logs
        found_logs = logs.find({'userId': ctx.author.id})
        newlogs = sorted(found_logs, key=lambda d: d['timestamp'])
        counter = 1
        for elem in newlogs:
            logs.update_one({"_id": elem["_id"]}, {"$set": {"id": counter}})
            counter = counter + 1
        await send_response(ctx, "Tu toc ha sido remediado con éxito.")

    @commands.command(aliases=["ordenarlogs"])
    async def ordenarlogsprefix(self, ctx):
        await self.ordenarlogs(ctx)

    @commands.slash_command()
    async def ajrstats(self, ctx,
                       horas: discord.Option(bool, "Mostrar horas en vez de puntos", required=False, default=False)):
        """Estadísticas totales de todo el servidor de AJR"""
        pipeline = [
            {"$match": {
                "timestamp": {
                    "$gte": int(datetime(2022, 1, 1, 0, 0, 0).timestamp()),
                }
            }},
            {
                '$group': {
                    '_id': {
                        'userId': '$userId',
                        'year': {'$year': {'$toDate': {'$multiply': ['$timestamp', 1000]}}},
                        'month': {'$month': {'$toDate': {'$multiply': ['$timestamp', 1000]}}}
                    },
                    'totalPuntos': {'$sum': '$puntos'},
                    'totalBonusPuntos': {
                        '$sum': {
                            '$cond': {
                                'if': {'$eq': ['$bonus', True]},
                                'then': {'$divide': ['$puntos', 1.4]},
                                'else': '$puntos'
                            }
                        }
                    }
                }
            },
            {
                '$sort': {'_id.year': 1, '_id.month': 1}
            }, {
                '$lookup': {
                    'from': 'users',
                    'localField': '_id.userId',
                    'foreignField': 'userId',
                    'as': 'userInfo'
                }
            }, {
                '$unwind': {
                    'path': '$userInfo'
                }
            }, {
                '$project': {
                    '_id.month': 1,
                    '_id.year': 1,
                    '_id.userId': '$userInfo.username',
                    'puntos': {
                        '$cond': {
                            'if': {'$eq': ['$bonus', True]},
                            'then': '$totalBonusPuntos',
                            'else': '$totalPuntos'
                        }
                    }
                }
            }
        ]

        # Run the pipeline and get the results
        results = list(self.db.logs.aggregate(pipeline))

        # Create a dictionary to store the data for each user
        user_data = {}
        max_points = 0
        max_month = None

        # Loop through the results and group the data by user
        for result in results:
            user_id = result['_id']['userId'].replace("_", "")
            year = result['_id']['year']
            month = result['_id']['month']
            month_name = calendar.month_name[month]
            puntos = result['puntos']

            # Check if the user data exists in the dictionary, and add it if it doesn't
            if user_id not in user_data:
                user_data[user_id] = {'x': [], 'y': [], 'label': user_id}

            # Add the data point to the user's data
            user_data[user_id]['x'].append(f"{year}/{str(month).zfill(2)}")
            if horas:
                user_data[user_id]['y'].append(puntos / 27)
            else:
                user_data[user_id]['y'].append(puntos)

        # Find the common set of x-axis labels and sort them by year and month
        x_labels = list(
            set([x_val for user_id, data in user_data.items() for x_val in data['x']]))
        x_labels.sort()

        # Create a dictionary to hold the filled-in data
        filled_data = {}

        # Loop through each user's data and fill in missing data with zeros
        for user_id, data in user_data.items():
            filled_data[user_id] = {'x': x_labels, 'y': []}
            for x_label in x_labels:
                if x_label in data['x']:
                    filled_data[user_id]['y'].append(
                        data['y'][data['x'].index(x_label)])
                else:
                    filled_data[user_id]['y'].append(0)
            # Copy the label from the user_data dictionary to the filled_data dictionary
            filled_data[user_id]['label'] = data['label']

        month_points = {}
        for x_label in x_labels:
            total_points = sum([data['y'][idx] for user_id, data in filled_data.items(
            ) for idx, x_val in enumerate(data['x']) if x_val == x_label])
            month_points[x_label] = total_points

        # Find the month with the highest points
        for month, points in month_points.items():
            if points > max_points:
                max_month = month
                max_points = points
            if (month == f"{datetime.now().year}/{str(datetime.now().month).zfill(2)}"):
                current_month = month
                current_month_points = points

        colors = ["#000", "#556b2f", "#7f0000", "#191970", "#5f9ea0", "#9acd32", "#ff0000", "#ff8c00", "#ffd700",
                  "#0000cd", "#ba55d3", "#00fa9a", "#00ffff", "#f08080", "#ff00ff", "#1e90ff", "#dda0dd",
                  "#ff1493", "#f5deb3"]

        # Create a stacked area chart using Matplotlib
        fig, ax = plt.subplots(figsize=(15, 10))

        # Combine the y values for each user and plot them together as a stacked area chart
        stacked_y = [filled_data[user_id]['y']
                     for user_id, data in filled_data.items()]
        stack_coll = ax.stackplot(x_labels, stacked_y, labels=[
            data['label'] for user_id, data in filled_data.items()])

        for i in range(len(stack_coll)):  # Itera sobre las partes del stackplot
            # Asigna un hatch diferente a cada parte
            stack_coll[i].set_color(
                colors[(i - 1) % len(colors)])

        bbox_props = dict(boxstyle="round,pad=0.3",
                          edgecolor="black", facecolor="white")

        ax.text(max_month, max_points,
                f"{math.ceil(max_points)}", ha='center', va='bottom', fontsize=12, bbox=bbox_props, color="black")

        if max_month != month:
            # Add text annotation for current month points
            ax.text(current_month, current_month_points,
                    f"{math.ceil(current_month_points)}", ha='center', va='center', bbox=bbox_props, color="black")

        # Set the x-axis label
        ax.set_xlabel('Meses')

        # Set the y-axis label
        if horas:
            ax.set_ylabel('Horas')
        else:
            ax.set_ylabel('Puntos')

        # Set the title
        ax.set_title('Inmersión en AJR')

        # Create the legend outside the plot
        ax.legend([filled_data[user_id]['label'] for user_id, data in filled_data.items(
        )], loc='upper left', bbox_to_anchor=(1.02, 1), fontsize='large')

        handles, labels = ax.get_legend_handles_labels()
        legend = ax.legend(reversed(handles), reversed(labels),
                           title='Usuarios', loc='upper left')

        ax.set_facecolor('#36393f')  # Color de fondo similar al de Discord
        fig.set_facecolor('#36393f')

        ax.title.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')  # Change tick labels color
        ax.tick_params(axis='y', colors='white')  # Change tick labels color

        for text in legend.get_texts():
            text.set_color("black")

        plt.rcParams.update(
            {'text.color': 'white', 'axes.labelcolor': 'white'})

        plt.xticks(rotation=45)
        plt.savefig("temp/image.png", bbox_inches="tight")
        plt.close()
        file = discord.File("temp/image.png", filename="image.png")
        await send_response(ctx, file=file)

    @ commands.command(aliases=["ajrstats"])
    async def ajrstatsprefix(self, ctx, horas=False):
        return await self.ajrstats(ctx, horas)

    @ commands.slash_command()
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
            data = self.db.logs.find(
                {"userId": ctx.author.id}).sort("timestamp", 1).limit(1)
            firstlog = data[0]
            start = datetime.fromtimestamp(
                firstlog['timestamp']).replace(day=1)
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
                "OUTPUT": 0,
                "AUDIO": 0,
                "VIDEO": 0,
            }
            local_total = 0
            for log in logs:

                log_points = log["puntos"]
                if "bonus" in log and log["bonus"]:
                    log_points = log["puntos"]/1.4

                points[log["medio"]] += log_points
                local_total += log_points
                total += log_points

            if local_total == 0:
                real_months -= 1
            if local_total > best_month["points"]:
                best_month["month"] = begin.month
                best_month["year"] = begin.year
                best_month["points"] = local_total
            results[f"{begin.year}/{begin.month}"] = points
        if real_months > 0:
            media = total / real_months
            normal = discord.Embed(
                title=f"Vista {get_ranking_title(año,'ALL')}", color=0xeeff00)
            normal.add_field(
                name="Usuario", value=ctx.author.name, inline=False)
            normal.add_field(name="Media en el periodo",
                             value=f"{round(media, 2)} puntos", inline=True)
            normal.add_field(
                name="Mejor mes", value=f"{MONTHS[best_month['month']-1].capitalize()} del {best_month['year']} con {round(best_month['points'],2)} puntos", inline=True)
            bardoc = generate_graph(results, "progress")
            normal.set_image(url="attachment://image.png")
            await send_response(ctx, embed=normal, file=bardoc)

    @ commands.command(aliases=["progreso"])
    async def progresoprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.progreso(ctx, datetime.now().year, False)

    @ commands.slash_command()
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

    @ commands.slash_command()
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

                if self.db.logs.find({'anilistId': newlog["anilistId"], "userId": user_id}).count() > 0:
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

    @ commands.command(aliases=["addanilist"])
    async def addanilistprefix(self, ctx, anilistuser, fechaminima=""):
        await self.addanilist(ctx, anilistuser, fechaminima)


def setup(bot):
    bot.add_cog(Immersion(bot))
