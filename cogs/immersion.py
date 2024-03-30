import asyncio
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import re
import csv
import calendar
import json
import math
import threading
import numpy as np
import matplotlib.pyplot as plt
import discord
import pandas as pd
import bar_chart_race as bcr
import locale
import random

from dateutil.relativedelta import relativedelta
from discord.ext import commands, tasks
from discord.ext.pages import Paginator
from discord import Member, Option
from copy import copy
from datetime import datetime, timedelta
from termcolor import cprint, COLORS
from asyncio import sleep

from cogs.menus.ranking import ranking_command
from cogs.help import Help
from cogs.menus.mvp import mvp_command
from cogs.menus.logs import logs_command
from cogs.menus.log import LogView
from cogs.menus.backlog import BacklogView
from cogs.menus.me import me_command
from cogs.menus.achievements import logros_command, LogroView
from cogs.menus.manabe import manabe_command
from cogs.menus.progreso import progreso_command
from cogs.menus.league import league_command

from cogs.dialogs.recommend import RecommendModal

from helpers.immersion.graphs import fin_de_mes_graph, fin_de_mes_sync
from helpers.immersion.logs import MEDIA_TYPES, MEDIA_TYPES_ENGLISH, MONTHS, TIMESTAMP_TYPES, add_log, calc_media, check_max_immersion, compute_points, get_all_logs_in_day, get_best_user_of_range, get_last_log, get_log_by_id, get_logs_animation, get_logs_per_day_in_month, get_logs_per_day_in_year, get_media_element, get_media_level, get_param_for_media_level, get_sorted_ranking, get_total_parameter_of_media, get_user_logs, ordenar_logs, remove_last_log, remove_log, update_log
from helpers.immersion.users import check_user, create_user, find_user
from helpers.general import intToMonth, send_error_message, send_response, set_processing
from helpers.immersion.divisions import (
    calculate_promotions_demotions, ascend_users, demote_users, get_user_division, save_division_results, get_current_division_users, get_division_users)

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

process_pool: list[multiprocessing.Process] = []


class Immersion(commands.Cog):
    def __init__(self, bot: discord.bot.Bot):
        self.bot = bot

        self.check_if_first_of_month.start()

    @tasks.loop(minutes=1)
    async def check_if_first_of_month(self):
        # Return if it's not the first minute of the first day of the month
        if datetime.now().day != 1 or datetime.now().hour != 0 or datetime.now().minute != 0:
            return

        print("ACTUALIZANDO RANKINGS")

        # Get ranking of the previous month
        # Get previous month first day
        last_month = datetime.now() - relativedelta(months=1)
        first_day = datetime(last_month.year, last_month.month, 1)

        # Get the last day of the previous month
        last_day = calendar.monthrange(last_month.year, last_month.month)[1]

        period = f"{first_day.strftime('%d/%m/%Y')}-{last_day}/{last_month.strftime('%m/%Y')}"

        last_division_ranking = await get_sorted_ranking(period, "TOTAL", division=2)

        first_division_ranking = await get_sorted_ranking(period, "TOTAL", division=1)

        last_division_ranking = [user for user in last_division_ranking if (user["points"]
                                                                            != 0)]

        total_ranking = first_division_ranking + last_division_ranking

        save_division_results(total_ranking,
                              last_month.month, last_month.year)

        # Calculate promotions and demotions
        promotions, demotions = calculate_promotions_demotions(
            first_division_ranking, last_division_ranking)

        # Ascend users
        ascend_users(promotions)

        # Demote users
        demote_users(demotions)

    @commands.Cog.listener()
    async def on_ready(self):
        cprint("- [✅] Cog de inmersión cargado con éxito",
               random.choice(list(COLORS.keys())))

    @commands.slash_command()
    async def mvp(self, ctx,
                  medio: Option(str, "Medio de inmersión que cubre el ranking", choices=MEDIA_TYPES, required=False, default="TOTAL"),
                  ano: Option(int, "Año que cubre el ranking (el desglose será mensual)", min_value=2019, max_value=datetime.now().year, required=False, default=datetime.now().year)):
        """Imprime un desglose mensual con los usuarios que más han inmersado en cada año desde que hay datos"""
        await set_processing(ctx)

        response = await mvp_command(medio, ano)

        await send_response(ctx, embed=response["embed"], view=response["view"])

    @commands.slash_command()
    async def recomendar(self, ctx):
        modal = RecommendModal(title="Titulo")
        await ctx.send_modal(modal)

    @commands.command(aliases=["halloffame", "salondelafama", "salonfama", "mvp", "hallofame"])
    async def mvpprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.mvp(ctx, "TOTAL", datetime.now().year)

    @commands.command(aliases=["protocolonuevomes"])
    async def avisarclubessugerencias(self, ctx):
        # Si no es admin, no hacer nada
        if ctx.author.id not in admin_users:
            return

        locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

        next_month = datetime.now() + relativedelta(months=1)
        next_month_str = next_month.strftime("%B").capitalize()

        next_year_str = next_month.strftime("%Y")

        timestamp = datetime.now() + relativedelta(days=3)
        timestamp = timestamp.replace(hour=23, minute=59, second=0)

        timestamp_str = f"<t:{int(timestamp.timestamp())}:f>"

        rol_novelas = "1167607765590605905"
        rol_manga = "1167607879667298354"
        rol_anime = "1167607983795085395"
        rol_vn = "1167608243254722580"
        rol_pelis = "1165379985171816478"

        club_novelas = await self.bot.fetch_channel(1142202264208019530)
        club_manga_anime = await self.bot.fetch_channel(756846117567594516)
        club_vn = await self.bot.fetch_channel(1142399071236132944)
        club_pelis = await self.bot.fetch_channel(1165379765046345728)

        # NOVELAS
        msg = await club_novelas.send(f"Se abre el plazo para proponer novelas para el mes de {next_month_str}. El plazo terminará el {timestamp_str}. Podéis escribir vuestras propuestas en el hilo creado a partir de este mensaje. <@&{rol_novelas}>", silent=True)

        await msg.create_thread(name=f"Propuestas novelas {next_month_str} {next_year_str}")

        # MANGA
        msg = await club_manga_anime.send(f"Se abre el plazo para proponer mangas para el mes de {next_month_str}. El plazo terminará el {timestamp_str}. Podéis escribir vuestras propuestas en el hilo creado a partir de este mensaje. <@&{rol_manga}>", silent=True)

        await msg.create_thread(name=f"Propuestas manga {next_month_str} {next_year_str}")

        # ANIME
        msg = await club_manga_anime.send(f"Se abre el plazo para proponer animes para el mes de {next_month_str}. El plazo terminará el {timestamp_str}. Podéis escribir vuestras propuestas en el hilo creado a partir de este mensaje. <@&{rol_anime}>", silent=True)

        await msg.create_thread(name=f"Propuestas anime {next_month_str} {next_year_str}")

        # VN
        msg = await club_vn.send(f"Se abre el plazo para proponer VNs para el mes de {next_month_str}. El plazo terminará el {timestamp_str}. Podéis escribir vuestras propuestas en el hilo creado a partir de este mensaje. <@&{rol_vn}>", silent=True)

        await msg.create_thread(name=f"Propuestas VN {next_month_str} {next_year_str}")

        # PELIS
        msg = await club_pelis.send(f"Se abre el plazo para proponer live actions para el mes de {next_month_str}. El plazo terminará el {timestamp_str}. Podéis escribir vuestras propuestas en el hilo creado a partir de este mensaje. <@&{rol_pelis}>", silent=True)

        await msg.create_thread(name=f"Propuestas live actions {next_month_str} {next_year_str}")

    @discord.slash_command()
    async def podio(self, ctx,
                    division: Option(str, "División del podio", choices=[
                        "Liga 学べ", "Liga 上手", "USUARIO"], required=False, default="USUARIO")
                    ):
        await set_processing(ctx)

        high_div = await get_sorted_ranking("MES", "TOTAL", division=1)
        low_div = await get_sorted_ranking("MES", "TOTAL", division=2)

        low_div = [user for user in low_div if (user["points"]
                                                != 0)]

        if division == "USUARIO":
            # Get user division
            user_division = get_user_division(ctx.author.id)
        elif division == "Liga 学べ":
            user_division = 1
        elif division == "Liga 上手":
            user_division = 2
        else:
            user_division = None

        response = await league_command(user_division, [high_div, low_div])

        if response["type"] == "embed":
            return await send_response(ctx, embed=response["embed"], view=response["view"])

        paginator = Paginator(
            pages=response["pages"], custom_view=response["view"])

        if not ctx.message:
            return await paginator.respond(ctx)
        else:
            return await paginator.send(ctx)

    @commands.command(aliases=["podio", "lb", "leaderboard"])
    async def podio_(self, ctx, division="USUARIO"):
        await self.podio(ctx, division)

    @commands.slash_command()
    async def ranking(self, ctx,
                      periodo: Option(str, "Periodo de tiempo que cubre el ranking", choices=TIMESTAMP_TYPES, required=False, default="MES"),
                      medio: Option(str, "Medio de inmersión que cubre el ranking", choices=MEDIA_TYPES + ["CARACTERES"], required=False, default="TOTAL"),
                      comienzo: Option(str, "Fecha de inicio (DD/MM/YYYY)", required=False),
                      final: Option(
                          str, "Fecha de fin (DD/MM/YYYY)", required=False)):
        """Imprime un ranking de inmersión según los parámetros indicados"""
        if (comienzo and not final) or (final and not comienzo):
            await send_error_message(ctx, "Debes concretar un principio y un final")
            return

        if comienzo and final:
            periodo = comienzo + "-" + final

        await set_processing(ctx)

        if medio == "CARACTERES":
            medio = "TOTAL"

        response = await ranking_command(medio, periodo, medio == "CARACTERES")

        if "embed" in response:
            return await send_response(ctx, embed=response["embed"], view=response["view"])

        paginator = Paginator(
            pages=response["pages"], custom_view=response["view"])

        return await paginator.respond(ctx.interaction)

    @commands.command(aliases=["ranking"])
    async def rankingprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        response = await ranking_command("TOTAL", "MES", False)

        if "embed" in response:
            return await send_response(ctx, embed=response["embed"], view=response["view"])

        paginator = Paginator(
            pages=response["pages"], custom_view=response["view"])

        return await paginator.send(ctx)

    @commands.slash_command()
    async def constancia(self, ctx,
                         month: discord.Option(str, "Mes a mostrar", choices=MONTHS, default=MONTHS[datetime.now().month-1], required=False),
                         year: discord.Option(int, "Año a mostrar", default=datetime.now().year, required=False),
                         totalyear: discord.Option(bool, "Mostrar el total del año", default=False, required=False)):
        """Muestra gráfica del mes seleccionado día por día con los puntos acumulados"""
        await set_processing(ctx)

        if await check_user(int(ctx.author.id)) is False:
            await send_error_message(ctx, "No se han encontrado logs asociados a esa Id.")
            return

        # Get the points of the user in each day of the month in
        mont_index = MONTHS.index(month)+1
        if not totalyear:
            logs = list(await get_logs_per_day_in_month(ctx.author.id, mont_index, year))

            # Create a dictionary with the accumulated points per day of the month, even those without points
            points_per_day = {}
            points = 0
            for day in range(1, calendar.monthrange(year, mont_index)[1]+1):
                # If there is a log with an _id for that day in the month, add it to the points
                for log in logs:
                    if log["_id"] == day:
                        points += log["count"]
                        points_per_day[day] = points
                    else:
                        points_per_day[day] = points

            # Create the graph
            fig, ax = plt.subplots(figsize=(10, 8))
            plt.plot(list(points_per_day.keys()), list(
                points_per_day.values()), label="Puntos acumulados")
            plt.xlabel("Día")
            plt.ylabel("Puntos acumulados")
            plt.title(
                f"Puntos acumulados en el mes de {month} de {year} para el usuario {ctx.author.name}")
        else:
            logs = list(await get_logs_per_day_in_year(ctx.author.id, year))

            # Create a dictionary with the accumulated points per day of the month, even those without points
            points_per_day = {}
            points = 0
            for day in range(1, 366):
                # If there is a log with an _id for that day in the month, add it to the points
                for log in logs:
                    if log["_id"] == day:
                        points += log["count"]
                        points_per_day[day] = points
                    else:
                        points_per_day[day] = points

            # Create the graph
            fig, ax = plt.subplots(figsize=(10, 8))
            # Make the x axis go from january to decembre
            plt.xticks(np.arange(1, 366, 30.5), MONTHS)
            plt.plot(list(points_per_day.keys()), list(
                points_per_day.values()), label="Puntos acumulados")
            plt.xlabel("Día")
            plt.ylabel("Puntos acumulados")
            plt.title(
                f"Puntos acumulados en el año {year} para el usuario {ctx.author.name}")

        plt.legend()
        # Fill the inner part of the line with gray
        plt.fill_between(list(points_per_day.keys()), list(
            points_per_day.values()), color="#24B14D")
        # Change line color
        plt.plot(list(points_per_day.keys()), list(
            points_per_day.values()), color="#24B14D")
        fig.set_facecolor("#2F3136")
        ax.title.set_color('white')
        ax.set_facecolor('#36393f')
        ax.title.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        plt.xticks(rotation=45)
        plt.savefig("temp/image.png")
        plt.close()
        file = discord.File("temp/image.png", filename="image.png")
        await send_response(ctx, file=file)

    @commands.command(aliases=["constancia"])
    async def constanciaprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.constancia(ctx, MONTHS[datetime.now().month-1], datetime.now().year, False)

    @commands.slash_command()
    async def logs(self, ctx,
                   periodo: Option(str, "Periodo de tiempo para ver logs", choices=TIMESTAMP_TYPES, required=False, default="TOTAL"),
                   medio: Option(str, "Medio de inmersión para ver logs", choices=MEDIA_TYPES, required=False, default="TOTAL"),
                   usuario: Option(Member, "Usuario del que quieres ver los logs", required=False)):
        """Muestra lista con todos los logs hechos con los parámetros indicados"""
        await set_processing(ctx)

        if not usuario:
            usuario = ctx.author.id
        else:
            usuario = usuario.id

        response = await logs_command(usuario, periodo, medio)

        paginator = Paginator(
            pages=response["pages"], custom_view=response["view"])

        return await paginator.respond(ctx.interaction)

    @commands.command(aliases=["logs"])
    async def logsprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")

        response = await logs_command(ctx.author.id, "TOTAL", "TOTAL")

        paginator = Paginator(
            pages=response["pages"], custom_view=response["view"])

        return await paginator.send(ctx)

    @commands.slash_command()
    async def export(self, ctx,
                     periodo: Option(
                         str, "Periodo de tiempo para exportar", choices=TIMESTAMP_TYPES, required=False, default="TOTAL")
                     ):
        """Exporta los logs en formato csv"""
        await set_processing(ctx)
        if not await check_user(ctx.author.id):
            await send_error_message(ctx, "No tiene ningún log")
            return

        result = await get_user_logs(ctx.author.id, periodo)
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

    @commands.command(aliases=["export", "exportar"])
    async def exportprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.export(ctx, "TOTAL")

    @commands.slash_command(pass_context=True)
    async def me(self, ctx,
                 periodo: Option(str, "Periodo de tiempo para exportar", choices=TIMESTAMP_TYPES, required=False, default="TOTAL"),
                 gráfica: Option(str, "Gráficos para acompañar los datos", choices=["SECTORES", "BARRAS", "VELOCIDAD", "NINGUNO"], required=False, default="SECTORES"),
                 comienzo: Option(str, "Fecha de inicio (DD/MM/YYYY)", required=False),
                 final: Option(str, "Fecha de fin (DD/MM/YYYY)", required=False),
                 usuario: Option(Member, "Usuario del que quieres ver las stats", required=False)):
        """Muestra pequeño resumen de lo inmersado"""
        await set_processing(ctx)

        if not usuario:
            usuario = ctx.author
        else:
            usuario = usuario

        if not await check_user(usuario.id):
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

        response = await me_command(usuario, periodo, gráfica)

        await send_response(ctx, embed=response["embed"], view=response["view"], file=response["file"])

    @commands.command(aliases=["yo", "me", "resumen"])
    async def meprefix(self, ctx, periodo="TOTAL", grafica="SECTORES"):
        if periodo.upper() in ["SECTORES", "BARRAS"]:
            grafica = periodo
            periodo = "TOTAL"
        await self.me(ctx, periodo.upper(), grafica.upper(), None, None, None)

    @commands.slash_command()
    async def backfill(self, ctx,
                       fecha: Option(str, "Fecha en formato DD/MM/YYYY", required=True),
                       medio: Option(str, "Medio inmersado", choices=MEDIA_TYPES, required=True),
                       cantidad: Option(int, "Cantidad inmersada", required=True, min_value=1, max_value=5000000),
                       descripción: Option(str, "Pequeño resumen de lo inmersado", required=True),
                       tiempo: Option(int, "Tiempo que te ha llevado en minutos", required=False),
                       caracteres: Option(int, "Caracteres leídos (para medios que no sean lectura)", required=False),
                       bonus: Option(bool, "Log de un club mensual de Manabe", required=False)):
        """Loguear inmersión hecha en el pasado"""
        # Check if the user has logs
        await set_processing(ctx)
        if not await check_user(ctx.author.id):
            await create_user(ctx.author.id, ctx.author.name)

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

        bonus = "manabeclub" in descripción.lower() or bonus or "clubmanabe" in descripción.lower(
        ) or "manabe-club" in descripción.lower() or "club-manabe" in descripción.lower()

        compiled = re.compile(re.escape("manabeclub"), re.IGNORECASE)
        compiled_2 = re.compile(re.escape("clubmanabe"), re.IGNORECASE)
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
            ranking = await get_sorted_ranking("MES", "TOTAL")
            for user in ranking:
                if user["username"] == ctx.author.name:
                    position = ranking.index(user)
            logid = await add_log(ctx.author.id, newlog, ctx.author.name)
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
                extra = " (club Manabe)"
                multiplier = " (x1.4)"

            embed = discord.Embed(title=f"Log registrado con éxito{extra}",
                                  description=f"Id Log #{logid} || {strdate.strftime('%d/%m/%Y')}", color=color)
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
            message = await send_response(ctx, embed=embed, view=BacklogView(bonus))
        elif output == 0:
            await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
            return
        elif output == -1:
            await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
            return
        elif output == -2:
            await send_error_message(ctx, "Cantidad de inmersión exagerada")
            return

    @commands.slash_command()
    async def logros(self, ctx,
                     usuario: Option(Member, "Usuario del que quieres ver las stats", required=False)):
        """Obtener tus logros de inmersión"""
        await self.achievements_(ctx, usuario)

    @commands.command(aliases=["achievements", "logros", "level", "nivel"])
    async def achievements_(self, ctx, usuario=None):
        """Obtener tus logros de inmersión"""
        await set_processing(ctx)

        user_id = usuario.id if usuario else ctx.author.id
        user_name = usuario.name if usuario else ctx.author.name

        if user_id:
            try:
                found = await find_user(user_id)
                if found:
                    user_name = found["username"]
                    user_id = int(user_id)
                else:
                    await ctx.message.delete()
                    return
            except:
                await ctx.message.delete()
                return

        logros_embed = await logros_command(user_id, user_name)
        return await send_response(ctx, embed=logros_embed)

    @commands.slash_command()
    async def log(self, ctx,
                  medio: Option(str, "Medio inmersado", choices=MEDIA_TYPES, required=True),
                  cantidad: Option(int, "Cantidad inmersada", required=True, min_value=1, max_value=5000000),
                  descripción: Option(str, "Pequeño resumen de lo inmersado", required=True),
                  tiempo: Option(int, "Tiempo que te ha llevado en minutos", required=False),
                  caracteres: Option(int, "Caracteres leídos (para medios que no sean lectura)", required=False),
                  bonus: Option(
                      bool, "Log de un club mensual de Manabe", required=False)
                  ):
        """Loguear inmersión"""
        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        await set_processing(ctx)
        # Check if the user has logs
        if not await check_user(ctx.author.id):
            await create_user(ctx.author.id, ctx.author.name)

        if not check_max_immersion(int(cantidad), medio.upper()):
            await send_error_message(ctx, "Esa cantidad de inmersión no es posible en un solo día, considera usar el comando /backfill para indicar las fechas con precisión")
            return

        bonus = "manabeclub" in descripción.lower() or bonus or "clubmanabe" in descripción.lower(
        ) or "manabe-club" in descripción.lower() or "club-manabe" in descripción.lower()

        compiled = re.compile(re.escape("manabeclub"), re.IGNORECASE)
        compiled_2 = re.compile(re.escape("clubmanabe"), re.IGNORECASE)
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
            user_division = get_user_division(ctx.author.id)

            ranking = await get_sorted_ranking("MES", "TOTAL", division=user_division)
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

            logid = await add_log(ctx.author.id, newlog, ctx.author.name)

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
                day_logs = await get_all_logs_in_day(ctx.author.id, current_day)
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
                extra = " (club Manabe)"
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
                    name=f"🎉 Has subido en el ranking del mes! ({user_division}ª) 🎉", value=f"**{position+1}º** ---> **{newposition+1}º**", inline=False)

            total_ranking = await get_sorted_ranking("MES", "TOTAL")

            # Check the points of the 10th user
            if len(total_ranking) > 9:
                tenth_user_points = total_ranking[9]["points"]

            if (user_division == 1 and newposition != 0):
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
            elif (user_division == 2 and current_points < tenth_user_points):
                needed_points = round(tenth_user_points - current_points, 1)
                embed.add_field(
                    name=f"🪖 Lucha para subir a primera 🪖",
                    value=f"Necesitas {str(needed_points)} puntos para entrar en puestos de ascenso",
                    inline=False
                )
            embed.set_footer(
                text=f"Id del usuario: {ctx.author.id}")
            message = await send_response(ctx, embed=embed, view=LogView(bonus))
            current_param = await get_total_parameter_of_media(medio.upper(), ctx.author.id)

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
                await send_response(ctx, embed=achievement_embed, view=LogroView(ctx.author))
            await sleep(10)

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
    async def logprefix(self, ctx, medio, cantidad=0):
        if medio.upper() == "HELP":
            return await Help(self.bot).help(ctx, "log")

        if medio.upper() not in MEDIA_TYPES:
            if medio.upper() in MEDIA_TYPES_ENGLISH:
                medio = MEDIA_TYPES_ENGLISH[medio.upper()]
            else:
                return await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
        if not str(cantidad).isnumeric():
            return await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
        if int(cantidad) > 5000000:
            return await send_error_message(ctx, "Cantidad de inmersión exagerada")
        elif int(cantidad) < 1:
            return await send_error_message(ctx, "Cantidad de inmersión demasiado pequeña")

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
    async def editlog(self, ctx,
                      logid: Option(int, "Id del log a editar", required=True),
                      cantidad: Option(int, "Cantidad inmersada", required=False, min_value=1, max_value=5000000),
                      descripción: Option(str, "Pequeño resumen de lo inmersado", required=False),
                      tiempo: Option(int, "Tiempo que te ha llevado en minutos", required=False),
                      caracteres: Option(int, "Caracteres leídos (para medios que no sean lectura)", required=False)):
        """Editar un log"""
        await set_processing(ctx)
        if not await check_user(ctx.author.id):
            return await send_error_message("No tienes ningún log.")

        log = await get_log_by_id(ctx.author.id, logid)

        previous_points = log["puntos"]

        if not log:
            return await send_error_message("No tienes ningún log con ese id.")

        if cantidad and not check_max_immersion(cantidad, log["medio"]):
            await send_error_message(ctx, "Esa cantidad de inmersión no es posible en un solo día, considera usar el comando /backfill para indicar las fechas con precisión")
            return

        # Add keys to log modification only if values are not None
        log_modification = {}
        aux_log = copy(log)
        if not cantidad is None:
            log_modification["parametro"] = cantidad
            aux_log["parametro"] = cantidad
        if descripción:
            log_modification["descripcion"] = descripción
            aux_log["descripcion"] = descripción
        if not tiempo is None:
            log_modification["tiempo"] = tiempo
            aux_log["tiempo"] = tiempo
        if not caracteres is None:
            log_modification["caracteres"] = caracteres
            aux_log["caracteres"] = caracteres

        points = 0

        if not cantidad is None or not tiempo is None or not caracteres is None:
            output = compute_points(
                aux_log, aux_log["bonus"] if "bonus" in aux_log else False)

            if "tiempo" in aux_log and aux_log["tiempo"] and aux_log["tiempo"] > 0:
                aux_log['tiempo'] = math.ceil(aux_log["tiempo"])
                auxlog = copy(aux_log)
                auxlog["medio"] = "TIEMPOLECTURA"
                auxlog["parametro"] = aux_log["tiempo"]
                new_points = compute_points(
                    auxlog, aux_log["bonus"] if "bonus" in aux_log else False)
                if new_points > output:
                    output = new_points
                    aux_log["puntos"] = new_points

            if "caracteres" in aux_log and aux_log["caracteres"] and aux_log["caracteres"] > 0 and aux_log["medio"].upper() not in ["LECTURA", "VN"]:
                aux_log['caracteres'] = math.ceil(aux_log["caracteres"])
                auxlog = copy(aux_log)
                auxlog["medio"] = "LECTURA"
                auxlog["parametro"] = aux_log["caracteres"]
                new_points = compute_points(
                    auxlog, aux_log["bonus"] if "bonus" in aux_log else False)
                if new_points > output:
                    output = new_points
                    aux_log["puntos"] = new_points

            if output > 0.01:
                points = output
            elif output == 0:
                await send_error_message(ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, output, audio y video")
                return
            elif output == -1:
                await send_error_message(ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
                return
            elif output == -2:
                await send_error_message(ctx, "Cantidad de inmersión exagerada")
                return

        if points > 0:
            aux_log["puntos"] = points

        preranking = await get_sorted_ranking("MES", "TOTAL")
        for user in preranking:
            if user["username"] == ctx.author.name:
                position = preranking.index(user)

        update_log(log["_id"], aux_log)

        color = 0x24b14d
        extra = ""
        multiplier = ""

        ranking = await get_sorted_ranking("MES", "TOTAL")

        for user in ranking:
            if user["username"] == ctx.author.name:
                # Busca el indice del usuario en el nuevo ranking
                newposition = ranking.index(user)
                current_points = user["points"]

        next_user = {
            "user": "",
            "difference": 0,
            "outside": False
        }

        if newposition > 9:
            # usuario que va en la posición 10
            next_user_aux = ranking[9]
            next_user["outside"] = True
        elif newposition != 0:
            # usuario que va delante de ti
            next_user_aux = ranking[newposition-1]

        if newposition != 0:
            next_user["user"] = next_user_aux["username"]
            next_user["difference"] = next_user_aux["points"] - \
                current_points

        if "bonus" in aux_log and aux_log["bonus"]:
            color = 0xbf9000
            extra = " (club Manabe)"
            multiplier = " (x1.4)"

        embed = discord.Embed(title=f"Log registrado con éxito{extra}",
                              description=f"Id Log #{logid} || Fecha: {datetime.fromtimestamp(aux_log['timestamp']).strftime('%d/%m/%Y')}", color=color)
        embed.add_field(
            name="Usuario", value=ctx.author.name, inline=True)
        embed.add_field(
            name="Medio", value=aux_log["medio"].upper(), inline=True)
        embed.add_field(
            name=f"Puntos{multiplier}", value=f"{previous_points} -> {round(aux_log['puntos'],2)} (+{round(aux_log['puntos']-previous_points,2)})", inline=True)
        embed.add_field(name="Inmersado",
                        value=get_media_element(aux_log['parametro'], aux_log["medio"].upper()), inline=True)
        embed.add_field(name="Descripción",
                        value=aux_log["descripcion"], inline=False)
        if "tiempo" in aux_log and aux_log["tiempo"] and aux_log["tiempo"] > 0:
            embed.add_field(name="Tiempo invertido",
                            value=get_media_element(aux_log['tiempo'], "VIDEO"), inline=False)
        if "caracteres" in aux_log and aux_log["caracteres"] and aux_log["caracteres"] > 0:
            embed.add_field(name="Caracteres leídos",
                            value=get_media_element(aux_log["caracteres"], "LECTURA"), inline=False)
        if "caracteres" in aux_log and aux_log["caracteres"] and aux_log["caracteres"] > 0 and "tiempo" in aux_log and aux_log["tiempo"] and aux_log["tiempo"] > 0:
            embed.add_field(name="Velocidad media",
                            value=f"{math.floor(int(aux_log['caracteres'])/aux_log['tiempo']*60)}chars/h", inline=False)
        elif (aux_log['medio'].upper() in ["LECTURA", "VN"]) and "tiempo" in aux_log and aux_log['tiempo'] and aux_log['tiempo'] > 0:
            embed.add_field(name="Velocidad media",
                            value=f"{math.floor(int(aux_log['parametro'])/aux_log['tiempo']*60)}chars/h", inline=False)
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
        return await send_response(ctx, embed=embed)

    @commands.slash_command()
    async def puntos(self, ctx,
                     cantidad: Option(int, "Puntos a calcular/cantidad a calcular puntos", min_value=1, required=True),
                     medio: Option(str, "Medio del que calcular los puntos", choices=MEDIA_TYPES, required=False)):
        """Calcular cuanta inmersión se necesita para conseguir x puntos y cuantos puntos da x inmersión"""
        await set_processing(ctx)
        if medio:
            aux = {
                'medio': medio,
                'parametro': cantidad,
            }
            points = compute_points(aux)

            logs = await get_user_logs(ctx.author.id, "MES")
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
        if not await check_user(ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        last_log = await get_last_log(ctx.author.id)

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

    @commands.slash_command()
    async def undo(self, ctx):
        """Borra el último log hecho"""
        # Verify the user has logs
        await set_processing(ctx)
        if not await check_user(ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return
        result, last_log_id = await remove_last_log(ctx.author.id)
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
                     logid: Option(int, "Id del log a borrar", required=True)):
        """Borra un log usando su identificador"""
        # Verify the user has logs
        await set_processing(ctx)
        if not await check_user(ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        if ctx.channel.id not in immersion_logs_channels:
            await send_response(ctx,
                                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        result = await remove_log(ctx.author.id, logid)
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
        if not await check_user(ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        # Verify the user is in the correct channel
        ordenar_logs(ctx.author.id)

        await send_response(ctx, "Tu toc ha sido remediado con éxito.")

    @commands.command(aliases=["ordenarlogs"])
    async def ordenarlogsprefix(self, ctx):
        await self.ordenarlogs(ctx)

    @commands.slash_command()
    async def manabestats(self, ctx,
                          horas: Option(bool, "Mostrar horas en vez de puntos", required=False, default=False)):
        """Estadísticas totales de todo el servidor de Manabe"""

        response = await manabe_command(horas)

        await send_response(ctx, file=response["file"], view=response["view"])

    @ commands.command(aliases=["manabestats"])
    async def manabestatsprefix(self, ctx, horas=False):
        return await self.manabestats(ctx, horas)

    @ commands.slash_command()
    async def progreso(self, ctx,
                       ano: Option(int, "Año que cubre el ranking (el desglose será mensual)", min_value=2019, max_value=datetime.now().year, required=False, default=datetime.now().year),
                       total: Option(bool, "Progreso desde el primer log registrado", required=False, default=False)):
        """Muestra una gráfica temporal con la inmersión segmentada en tipos"""
        await set_processing(ctx)
        if not await check_user(ctx.author.id):
            await send_error_message(ctx, "No tienes ningún log.")
            return
        ano = str(ano)
        if total:
            ano = "TOTAL"

        response = await progreso_command(ctx.author, ano, total)

        await send_response(ctx, embed=response["embed"], file=response["file"], view=response["view"])

    @ commands.command(aliases=["progreso"])
    async def progresoprefix(self, ctx, argument=""):
        if argument != "":
            return await send_error_message(ctx, "Para usar parámetros escribe el comando con / en lugar de .")
        await self.progreso(ctx, datetime.now().year, False)

    @ commands.slash_command()
    async def findemes(self, ctx,
                       mes: Option(int, "Mes que ha finalizado", min_value=1, max_value=12, required=False, default=datetime.now().month - 1),
                       year: Option(int, "Año", required=False, default=datetime.now().year)):
        """Video conmemorativo con ranking interactivo de todo el mes"""
        if ctx.author.id not in admin_users:
            return await send_error_message(ctx, "Vuelve a hacer eso y te mato")

        # Get current divisions in format [{userId:id}]
        current_first_division, current_second_division = get_current_division_users()
        # Get previous divisions in format [{userId:id}]
        previous_first_division, previous_second_division = get_division_users(
            mes, year)

        promotions = []
        demotions = []

        # Calculate demotions, previous_first and current_second are arrays of objects with the format {userId:id}
        for position in previous_first_division:
            for user in current_second_division:
                if position["userId"] == user["userId"]:
                    demotions.append(user)
                    break

        for position in previous_second_division:
            for user in current_first_division:
                if position["userId"] == user["userId"]:
                    promotions.append(user)
                    break

        await set_processing(ctx)
        today = datetime.now()
        next_month = (mes) % 12 + 1
        day = (datetime(year, next_month, 1) - timedelta(days=1)).day
        await ctx.send("Procesando datos del mes, espere por favor...", delete_after=60.0)

        # Add to chosen_ones the ids of the union between the current first division and the previous first division
        chosen_ones = []
        for user in current_first_division:
            chosen_ones.append(user["userId"])
        for user in previous_first_division:
            if user["userId"] not in chosen_ones:
                chosen_ones.append(user["userId"])

        await get_logs_animation(mes, day, year, chosen_ones, previous_first_division)

        # Execute fin_de_mes_graph async function in another thread
        await fin_de_mes_graph(self, ctx, mes, year, promotions, demotions)

    # @ commands.slash_command()
    # async def addanilist(self, ctx,
    #                      anilistuser: Option(str, "Nombre de usuario anilist", required=True),
    #                      fechaminima: Option(str, "Fecha de inicio en formato YYYYMMDD", required=False)):
    #     """Añade logs de anime de anilist"""
    #     if fechaminima and len(fechaminima) != 8:
    #         await send_error_message(ctx, "La fecha debe tener el formato YYYYMMDD")
    #         return

    #     await set_processing(ctx)
    #     user_id = await get_anilist_id(anilistuser)
    #     if user_id == -1:
    #         await send_error_message(ctx, "Esa cuenta de anilist no existe o es privada, cambia tus ajustes de privacidad.")
    #         return
    #     await send_response(ctx, f"Añadiendo los logs de anilist de {anilistuser} a tu cuenta... si esto ha sido un error contacta con el administrador.", delete_after=10.0)
    #     nextPage = True
    #     page = 1
    #     errored = []
    #     total_logs = 0
    #     total_repeated = 0
    #     while nextPage:
    #         logs = await get_anilist_logs(user_id, page, fechaminima)
    #         nextPage = logs["data"]["Page"]["pageInfo"]["hasNextPage"]
    #         for log in logs["data"]["Page"]["mediaList"]:
    #             newlog = {
    #                 'anilistAccount': anilistuser,
    #                 'anilistId': log["id"],
    #                 'timestamp': 0,
    #                 'descripcion': "",
    #                 'medio': "",
    #                 'parametro': ""
    #             }
    #             newlog["descripcion"] = log["media"]["title"]["native"]
    #             if log["media"]["format"] == "MOVIE":
    #                 newlog["medio"] = "VIDEO"
    #                 newlog["parametro"] = str(log["media"]["duration"])
    #             elif log["media"]["duration"] < 19:
    #                 newlog["medio"] = "VIDEO"
    #                 newlog["parametro"] = str(
    #                     log["media"]["duration"] * log["media"]["episodes"])
    #             else:
    #                 newlog["medio"] = "ANIME"
    #                 newlog["parametro"] = str(log["media"]["episodes"])

    #             failed = False
    #             if log["completedAt"]["year"]:
    #                 newlog["timestamp"] = int(datetime(
    #                     log["completedAt"]["year"], log["completedAt"]["month"], log["completedAt"]["day"]).timestamp())
    #             elif log["startedAt"]["year"]:
    #                 newlog["timestamp"] = int(datetime(
    #                     log["startedAt"]["year"], log["startedAt"]["month"], log["startedAt"]["day"]).timestamp())
    #             else:
    #                 errored.append(log["media"]["title"]["native"])
    #                 failed = True

    #             if self.db.logs.find({'anilistId': newlog["anilistId"], "userId": user_id}).count() > 0:
    #                 total_repeated += 1
    #                 failed = True

    #             if not failed:
    #                 total_logs += 1
    #                 output = compute_points(newlog)
    #                 if output > 0:
    #                     logid = await add_log(ctx.author.id, newlog, ctx.author.name)

    #         page += 1
    #     total_errored = ""
    #     total_len = 0
    #     total_size = 0
    #     for elem in errored:
    #         total_errored += elem + "\n"
    #         total_len += 1
    #         total_size += len(elem)
    #     if total_size > 500:
    #         total_errored = "Demasiados logs fallidos para poder representarlo, revisa que tus entradas de anilist tienen fecha de finalización."
    #     embed = discord.Embed(
    #         title=f"Añadido a logs la cuenta de anilist de {anilistuser}", color=0x1302ff, description="-----------------")
    #     embed.add_field(name="Logs introducidos",
    #                     value=total_logs, inline=False)
    #     if total_repeated > 0:
    #         embed.add_field(name="Logs repetidos",
    #                         value=total_repeated, inline=False)
    #     if total_errored != "":
    #         embed.add_field(name="Logs fallidos",
    #                         value=total_len, inline=False)
    #         embed.add_field(name="Lista de fallidos",
    #                         value=total_errored, inline=True)
    #     embed.set_footer(
    #         text="Es recomendable que escribas el comando .ordenarlogs después de hacer un import de anilist.")
    #     await send_response(ctx, embed=embed)
    #     print(errored)

    # @ commands.command(aliases=["addanilist"])
    # async def addanilistprefix(self, ctx, anilistuser, fechaminima=""):
    #     await self.addanilist(ctx, anilistuser, fechaminima)


def setup(bot):
    bot.add_cog(Immersion(bot))
