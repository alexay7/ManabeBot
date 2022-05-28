"""Cog responsible for immersion logs."""

import asyncio
from calendar import month
import math
import os
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from discord.ext import commands
from discord import Embed
import discord.errors
from time import sleep, time

import requests

from .anilist import get_anilist_id, get_anilist_logs
from .fun import intToMonth, intToWeekday, send_error_message
import matplotlib.pyplot as plt
import csv
import bar_chart_race as bcr
import pandas as pd
from pymongo import MongoClient, errors
import numpy as np

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    logs_channel_id = data_dict["logs_channel_id"]
    admin_id = data_dict["kaigen_user_id"]
    mvp_role = data_dict["mvp_role"]
#############################################################

MEDIA_TYPES = {"LIBRO", "MANGA", "VN", "ANIME",
               "LECTURA", "TIEMPOLECTURA", "AUDIO", "VIDEO"}

TIMESTAMP_TYPES = {"TOTAL", "MES", "SEMANA", "HOY"}

MONTHS = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
          "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


# FUNCTIONS FOR SENDING MESSAGES

async def send_message_with_buttons(self, ctx, content):
    pages = len(content)
    cur_page = 1
    message = await ctx.send(f"```\n{content[cur_page-1]}\nPág {cur_page} de {pages}\n```")
    if(pages > 1):
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30)
                if(not user.bot):
                    # waiting for a reaction to be added - times out after x seconds, 60 in this
                    # example

                    if str(reaction.emoji) == "▶️" and cur_page != pages:
                        cur_page += 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")

                    elif str(reaction.emoji) == "◀️" and cur_page > 1:
                        cur_page -= 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")

                    else:
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
            except asyncio.TimeoutError:
                try:
                    await message.delete()
                except discord.errors.Forbidden:
                    await send_error_message(self, ctx, "‼️ Los mensajes con páginas no funcionan bien en DM!")
                break
                # ending the loop if user doesn't react after x seconds

# FUNCTIONS RELATED WITH LOGS


async def remove_log(db, userid, logid):
    users = db.users
    result = users.update_one(
        {"userId": userid}, {"$pull": {"logs": {"id": int(logid)}}})
    return result.modified_count


async def remove_last_log(db, userid):
    users = db.users
    result = users.update_one(
        {"userId": userid}, {"$pop": {"logs": 1}})
    return result.modified_count


async def create_user(db, userid, username):
    users = db.users
    newuser = {
        'userId': userid,
        'username': username,
        'logs': [],
        'lastlog': -1
    }
    users.insert_one(newuser)


async def get_user_logs(db, userid, timelapse, media=None):
    users = db.users

    if timelapse in MONTHS:
        year = datetime.now().year
        month = MONTHS.index(timelapse) + 1
        timelapse = f"{year}/{month}"

    if timelapse == "TOTAL":
        if media in MEDIA_TYPES:
            # ALL LOGS OF A MEDIA TYPE FROM USER
            result = users.aggregate([
                {
                    "$match": {
                        "userId": userid
                    }
                }, {
                    "$project": {
                        "logs": {
                            "$filter": {
                                "input": "$logs",
                                "as": "log",
                                "cond": {"$eq": ["$$log.medio", media]}
                            }
                        }
                    }
                }
            ])
            if result:
                for elem in result:
                    # Only one document should be found so no problem returning data
                    return elem["logs"]
        else:
            # ALL LOGS OF ALL MEDIA TYPES FROM USER
            result = users.find_one({"userId": userid}, {"logs"})
            if result:
                return result["logs"]
        return ""

    if timelapse.upper() == "SEMANA":
        start = int((datetime.today() - timedelta(weeks=1)
                     ).replace(hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())
        # SEVEN-DAY LOGS OF A MEDIA TYPE FROM USER

    elif timelapse.upper() == "MES":
        start = int(
            (datetime(datetime.today().year, datetime.today().month, 1)).replace(hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())

    elif timelapse.upper() == "HOY":
        start = int(datetime.today().replace(
            hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())
    else:
        split_time = timelapse.split("/")
        if len(split_time) == 1:
            # TOTAL VIEW
            start = int(
                (datetime(int(split_time[0]), 1, 1)).replace(hour=0, minute=0, second=0).timestamp())
            end = int(
                (datetime(int(split_time[0]), 12, 31)).replace(hour=23, minute=59, second=59).timestamp())

        elif len(split_time) == 2:
            # MONTHLY VIEW
            month = int(split_time[1])
            year = int(split_time[0])
            start = int(
                (datetime(int(year), month, 1)).replace(hour=0, minute=0, second=0).timestamp())
            if month + 1 > 12:
                month = 0
                year += 1
            end = int(
                (datetime(int(year), month + 1, 1) - timedelta(days=1)).replace(hour=23, minute=59, second=59).timestamp())
        else:
            day = int(split_time[2])
            month = int(split_time[1])
            year = int(split_time[0])
            start = int((datetime(int(year), month, 1)).replace(
                hour=0, minute=0, second=0).timestamp())
            end = int((datetime(int(year), month, day)).replace(
                hour=23, minute=59, second=59).timestamp())
    query = [{"$match": {"userId": userid}},
             {
        "$project": {
            "logs": {
                "$filter": {
                    "input": "$logs",
                    "as": "log",
                    "cond": {"$and": [
                            {"$gte": ["$$log.timestamp", start]},
                            {"$lte": ["$$log.timestamp", end]}
                    ]}
                }
            }
        }
    }]
    if media in MEDIA_TYPES:
        query[1]["$project"]["logs"]["$filter"]["cond"]["$and"].append(
            {"$eq": ["$$log.medio", media]})
    result = users.aggregate(query)
    if result:
        for elem in result:
            # Only one document should be found so no problem returning data
            return elem["logs"]
    return ""


async def get_best_user_of_range(db, media, timelapse):
    aux = None
    users = db.users.find({}, {"userId", "username"})
    points = 0
    parameternum = 0
    for user in users:
        userpoints, parameters = await get_user_data(db, user["userId"], timelapse, media)
        newuser = {
            "id": user["userId"],
            "username": user["username"],
            "points": round(userpoints[media.upper()], 2),
            "parameters": parameters[media.upper()]
        }
        if newuser["points"] > points:
            points = round(newuser["points"], 2)
            parameternum = newuser["parameters"]
            aux = newuser
    if(not(aux is None)):
        return aux
    return None


async def add_log(db, userid, log, username):
    users = db.users
    user = users.find_one({'userId': userid})
    newid = len(user["logs"])
    log["id"] = user["lastlog"] + 1
    users.update_one(
        {'userId': userid},
        {'$push': {"logs": log},
         '$set': {"lastlog": log["id"], "username": username}}
    )
    return log["id"]


async def get_sorted_ranking(db, timelapse, media):
    leaderboard = []
    users = db.users.find({}, {"userId", "username"})
    counter = 0
    for user in users:
        points, parameters = await get_user_data(
            db, user["userId"], timelapse.upper(), media.upper())
        leaderboard.append({
            "username": user["username"],
            "points": points["TOTAL"]})
        if media.upper() in MEDIA_TYPES:
            leaderboard[counter]["param"] = parameters[media.upper()]
        counter += 1
    return sorted(
        leaderboard, key=lambda x: x["points"], reverse=True)

# GENERAL FUNCTIONS


def calc_points(log):
    # Mejor prevenir que curar
    if log["medio"] not in MEDIA_TYPES:
        return 0
    if not log["parametro"].isdecimal():
        return -1
    if int(log["parametro"]) > 9999999:
        return -2
    if log["medio"] == "LIBRO":
        puntos = round(int(log["parametro"]), 2)
    elif log["medio"] == "MANGA":
        puntos = round(int(log["parametro"]) / 5, 2)
    elif log["medio"] == "VN":
        puntos = round(int(log["parametro"]) / 350, 2)
    elif log["medio"] == "ANIME":
        puntos = round(int(log["parametro"]) * 95 / 10, 2)
    elif log["medio"] == "LECTURA":
        puntos = round(int(log["parametro"]) / 350, 2)
    elif log["medio"] == "TIEMPOLECTURA":
        puntos = round(int(log["parametro"]) * 45 / 100, 2)
    elif log["medio"] == "AUDIO":
        puntos = round(int(log["parametro"]) * 45 / 100, 2)
    elif log["medio"] == "VIDEO":
        puntos = round(int(log["parametro"]) * 45 / 100, 2)
    log["puntos"] = puntos
    return puntos


def calc_media(points):
    # Mejor prevenir que curar
    result = {
        "libro": points,
        "manga": points * 5,
        "vn": points * 350,
        "anime": points / 95 * 10,
        "lectura": points * 350,
        "tiempolectura": points / 45 * 100,
        "audio": points / 45 * 100,
        "video": points / 45 * 100
    }
    return result


def get_ranking_title(timelapse, media):
    tiempo = ""
    if timelapse == "MES":
        tiempo = "mensual"
    elif timelapse == "SEMANA":
        tiempo = "semanal"
    elif timelapse == "HOY":
        tiempo = "diario"
    elif timelapse.isnumeric():
        tiempo = "de " + timelapse
    else:
        tiempo = "total"
    medio = ""
    if media in {"MANGA", "ANIME", "AUDIO", "LECTURA", "VIDEO"}:
        medio = "de " + media.lower() + " "
    elif media in {"LIBRO"}:
        medio = "de " + media.lower() + "s "
    elif media in {"LECTURATIEMPO"}:
        medio = "de lectura (tiempo) "
    elif media in {"VN"}:
        medio = "de " + media + " "
    return f"{tiempo} {medio}"


def get_media_element(num, media):
    if media in {"MANGA", "LIBRO"}:
        if int(num) == 1:
            return "1 página"
        return f"{num} páginas"
    if media in {"VN", "LECTURA"}:
        if int(num) == 1:
            return "1 caracter"
        return f"{num} caracteres"
    if media == "ANIME":
        if int(num) == 1:
            return "1 episodio"
        return f"{num} episodios"
    if media in {"TIEMPOLECTURA", "AUDIO", "VIDEO"}:
        if int(num) < 60:
            return f"{int(num)%60} minutos"
        elif int(num) < 120:
            return f"1 hora y {int(num)%60} minutos"
        return f"{int(int(num)/60)} horas y {int(num)%60} minutos"


async def get_user_data(db, userid, timelapse, media="TOTAL"):
    logs = await get_user_logs(db, userid, timelapse.upper(), media.upper())
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
        "VIDEO": 0,
        "TOTAL": 0
    }

    for log in logs:
        points[log["medio"]] += log["puntos"]
        parameters[log["medio"]] += int(log["parametro"])
        points["TOTAL"] += log["puntos"]
    return points, parameters


async def check_user(db, userid):
    users = db.users
    return users.find({'userId': int(userid)}).count() > 0


def generate_graph(points, type, timelapse=None):
    aux = dict(points)
    if(type == "piechart"):
        for elem in list(aux):
            if(aux[elem] == 0):
                aux.pop(elem)
        aux.pop("TOTAL")

        labels = []
        values = []

        for x, y in aux.items():
            labels.append(x),
            values.append(y)

        fig1, ax1 = plt.subplots()
        ax1.pie(values, labels=labels, autopct='%1.1f%%',
                shadow=True, startangle=90, textprops={'color': "w"})
        fig1.set_facecolor("#2F3136")
        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax1.axis('equal')

        plt.savefig("temp/image.png")
        file = discord.File("temp/image.png", filename="image.png")
        return file
    elif type == "progress":
        labels = []
        values = []
        media = {"LIBRO": [], "MANGA": [], "VN": [], "ANIME": [],
                 "LECTURA": [], "TIEMPOLECTURA": [], "AUDIO": [], "VIDEO": []}

        for x, y in aux.items():
            labels.append(x),
            values.append(y)
        fig1, ax = plt.subplots(figsize=(10, 5))
        max = 0

        for elem in values:
            media["LIBRO"].append(elem["LIBRO"])
            media["MANGA"].append(elem["MANGA"])
            media["VN"].append(elem["VN"])
            media["ANIME"].append(elem["ANIME"])
            media["LECTURA"].append(elem["LECTURA"])
            media["TIEMPOLECTURA"].append(elem["TIEMPOLECTURA"])
            media["AUDIO"].append(elem["AUDIO"])
            media["VIDEO"].append(elem["VIDEO"])
            total = elem["LIBRO"] + elem["MANGA"] + elem["VN"] + elem["ANIME"] +  \
                elem["LECTURA"] + elem["TIEMPOLECTURA"] +  \
                elem["AUDIO"] + elem["VIDEO"]
            if total > max:
                max = total

        libro = np.array(media["LIBRO"])
        manga = np.array(media["MANGA"])
        vn = np.array(media["VN"])
        anime = np.array(media["ANIME"])
        lectura = np.array(media["LECTURA"])
        tiempolectura = np.array(media["TIEMPOLECTURA"])
        audio = np.array(media["AUDIO"])
        video = np.array(media["VIDEO"])
        plt.xticks(rotation=45)
        plt.bar(labels, libro, color='#b3554d')
        plt.bar(labels, manga, bottom=libro, color='#4BD0CB')
        plt.bar(labels, vn, bottom=(
            libro + manga), color='#93D04B')
        plt.bar(labels, anime, bottom=libro +
                manga + vn, color='#808bc1')
        plt.bar(labels, lectura,
                bottom=libro + manga + vn + anime, color='#4BD088')
        plt.bar(labels, tiempolectura,
                bottom=libro + manga + vn + anime + lectura, color='#4b92d0')
        plt.bar(labels, audio,
                bottom=libro + manga + vn + anime + lectura + tiempolectura, color='#D04B51')
        plt.bar(labels, video, bottom=libro + manga + vn + anime + lectura +
                tiempolectura + audio, color='#CB4BD0')
        plt.xlabel("FECHA")
        plt.ylabel("PUNTOS")
        print(max)
        plt.ylim(0, max * 1.05)
        plt.legend(["LIBRO", "MANGA", "VN", "ANIME", "LECTURA",
                   "TIEMPOLECTURA", "AUDIO", "VIDEO"], loc='upper center', bbox_to_anchor=(0.5, 1.25),
                   ncol=3, fancybox=True, shadow=True)
        plt.savefig("temp/image.png", bbox_inches="tight")
        file = discord.File("temp/image.png", filename="image.png")
        return file
    else:
        labels = []
        values = []
        if timelapse.upper() == "SEMANA":
            start = datetime.today().replace(hour=0, minute=0, second=0) - timedelta(days=6)
            for x in range(0, 7):
                normaldate = start + timedelta(days=x)
                auxdate = str(normaldate
                              ).replace("-", "/").split(" ")[0]
                labels.append(auxdate + intToWeekday(normaldate.weekday()))
                if auxdate in points:
                    values.append(points[auxdate])
                else:
                    values.append(0)
            plt.rc('font', family='Noto Sans CJK JP')
            fig, ax = plt.subplots()
            ax.bar(labels, values, color='#24B14D')
            ax.set_ylabel('Puntos', color="white")
            ax.tick_params(axis='both', colors='white')
            fig.set_facecolor("#2F3136")
            fig.autofmt_xdate()
            plt.savefig("temp/image.png")
            file = discord.File("temp/image.png", filename="image.png")
            return file


async def get_logs_animation(db, month, day):
    # Esta función va a tener como parámetro el día, lo pasará a la función get logs y a partir de ahí generará el ranking pertinente
    header = []
    data = []
    header.append("date")
    users = db.users.find({}, {"username"})
    for user in users:
        header.append(user["username"])
    total = dict()
    date = datetime.today()
    # if int(day) > date.day:
    #     day = date.day
    counter = 1
    while counter < int(day) + 1:
        total[str(counter)] = await get_sorted_ranking(
            db, f"{date.year}/{month}/{counter}", "TOTAL")
        aux = [0 for i in range(len(header))]
        aux[0] = f"{month}/{counter}/{date.year}"
        for user in total[str(counter)]:
            aux[header.index(user["username"])] = user["points"]
        counter += 1
        data.append(aux)
    with open('temp/test.csv', 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)
    return


# BOT'S COMMANDS
class Logs(commands.Cog):
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
                print("Obtenida colección de logs de MongoDB")
                self.db = client.ajrlogs
            except errors.ServerSelectionTimeoutError:
                print("Ha ocurrido un error intentando conectar con la base de datos.")
                exit(1)

        # await self.private_admin_channel.send("Connected to db successfully")

    @ commands.command(aliases=["halloffame", "salondelafama", "salonfama", "mvp"])
    async def hallofame(self, ctx, timelapse=f"{datetime.today().year}", media="TOTAL"):
        """Uso:: .hallofame <tiempo (semana/mes/año/total)/tipo de inmersión> <tipo de inmersión>"""
        output = ""
        if timelapse.upper() in MEDIA_TYPES:
            media = timelapse.upper()
            timelapse = f"{datetime.today().year}"

        if timelapse.upper() != "TOTAL":
            # Calcular lo que es el start y el end aquí, mandarlos como argumento
            domain = range(1, 13)
            for x in domain:
                winner = await get_best_user_of_range(self.db, media, f"{timelapse}/{x}")
                if(not(winner is None)):
                    output += f"**{intToMonth(x)}:** {winner['username']} - {winner['points']} puntos"
                    if media.upper() in MEDIA_TYPES:
                        output += f" -> {get_media_element(winner['parameters'],media.upper())}\n"
                    else:
                        output += "\n"
            if(timelapse.isnumeric()):
                year = timelapse
            else:
                year = datetime.today().year
            title = f"🏆 Usuarios del mes ({year})"
            if media.upper() in MEDIA_TYPES:
                title += f" [{media.upper()}]"

        else:
            # Iterate from 2020 until current year
            end = datetime.today().year
            domain = range(2020, end + 1)
            for x in domain:
                winner = await get_best_user_of_range(self.db, media, f"{x}")
                if(not(winner is None)):
                    output += f"**{x}:** {winner['username']} - {winner['points']} puntos"
                    if media.upper() in MEDIA_TYPES:
                        output += f" -> {get_media_element(winner['parameters'],media.upper())}\n"
                    else:
                        output += "\n"
            title = f"🏆 Usuarios del año"
            if media.upper() in MEDIA_TYPES:
                title += f" [{media.upper()}]"

        embed = Embed(title=title, color=0xd400ff)
        embed.add_field(name="---------------------",
                        value=output, inline=True)
        await ctx.send(embed=embed)

    @ commands.command(aliases=["ranking", "podio", "lb"])
    async def leaderboard(self, ctx, timelapse="MES", media="TOTAL", extended=False):
        """Uso:: .leaderboard <tiempo (semana/mes/año/total)/tipo de inmersión> <tipo de inmersión>"""
        leaderboard = []
        if timelapse.upper() in MEDIA_TYPES:
            aux = media
            media = timelapse.upper()
            if aux != "TOTAL":
                timelapse = aux.upper()
            else:
                timelapse = "MES"
        if media.isnumeric():
            aux = timelapse
            timelapse = media
            media = aux
        sortedlist = await get_sorted_ranking(self.db, timelapse, media)
        message = ""
        position = 1
        total_users = 10
        if(extended):
            total_users = len(sortedlist)
        for user in sortedlist[0:total_users]:
            if(user["points"] != 0):
                message += f"**{str(position)}º {user['username']}:** {str(round(user['points'],2))} puntos"
                if("param" in user):
                    message += f" -> {get_media_element(user['param'],media.upper())}\n"
                else:
                    message += "\n"
                position += 1
            else:
                sortedlist.remove(user)
        append = ""
        if(extended):
            append = "extendido"
        if len(sortedlist) > 0:
            title = "Ranking " + \
                get_ranking_title(timelapse.upper(), media.upper()) + append
            embed = Embed(color=0x5842ff)
            embed.add_field(name=title, value=message, inline=True)
            await ctx.send(embed=embed)
        else:
            await send_error_message(self, ctx, "Ningún usuario ha inmersado con este medio en el periodo de tiempo indicado")
            return

    @ commands.command()
    async def logs(self, ctx, timelapse="TOTAL", user=None, media="TOTAL"):
        """Uso:: .logs <tiempo (semana/mes/total)/Id usuario> <Id usuario>"""
        if timelapse.isnumeric():
            user = int(timelapse)
            timelapse = "TOTAL"

        if timelapse.upper() in MEDIA_TYPES:
            media = timelapse.upper()
            timelapse = "TOTAL"

        if user is None:
            user = ctx.author.id

        if not isinstance(user, int) and user:
            if user.upper() in MEDIA_TYPES:
                media = user.upper()
                user = None

        errmsg = "No se han encontrado logs asociados a esa Id."

        if(await check_user(self.db, user) is False):
            await send_error_message(self, ctx, errmsg)
            return

        result = await get_user_logs(self.db, int(user), timelapse.upper(), media.upper())
        sorted_res = sorted(result, key=lambda x: x["timestamp"], reverse=True)

        output = [""]
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
            await send_message_with_buttons(self, ctx, output)
        else:
            await send_error_message(self, ctx, errmsg)

    @commands.command()
    async def export(self, ctx, timelapse="TOTAL"):
        """Uso:: .export <tiempo (semana/mes/total)>"""
        if(not await check_user(self.db, ctx.author.id)):
            await send_error_message(self, ctx, "No tiene ningún log")
            return

        result = await get_user_logs(self.db, ctx.author.id, timelapse)
        sorted_res = sorted(result, key=lambda x: x["timestamp"], reverse=True)
        header = ["fecha", "medio", "cantidad", "descripcion", "puntos"]
        data = []
        for log in sorted_res:
            date = datetime.fromtimestamp(log["timestamp"])
            aux = [f"{date.day}/{date.month}/{date.year}", log["medio"],
                   log["parametro"], log["descripcion"][:-1], log["puntos"]]
            data.append(aux)
        with open('temp/user.csv', 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)
        await ctx.send(file=discord.File("temp/user.csv"))

    @ commands.command(aliases=["yo"])
    async def me(self, ctx, timelapse="MES", graph=1):
        """Uso:: .me <tiempo (semana/mes/total)>"""
        if(not await check_user(self.db, ctx.author.id)):
            await send_error_message(self, ctx, "No tienes ningún log")
            return
        if timelapse.isnumeric():
            graph = int(timelapse)
            timelapse = "MES"
        logs = await get_user_logs(self.db, ctx.author.id, timelapse.upper())
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
        ranking = await get_sorted_ranking(self.db, timelapse, "TOTAL")
        for user in ranking:
            if user["username"] == ctx.author.name:
                position = ranking.index(user)

        normal = discord.Embed(
            title=f"Vista {get_ranking_title(timelapse.upper(),'ALL')}", color=0xeeff00)
        normal.add_field(name="Usuario", value=ctx.author.name, inline=True)
        normal.add_field(name="Puntos", value=round(
            points["TOTAL"], 2), inline=True)
        normal.add_field(name="Posición ranking",
                         value=f"{position+1}º", inline=True)
        normal.add_field(name="Medios", value=output, inline=False)
        normal.set_footer(
            text="Escribe este comando seguido de '2' para ver la distribución de tu inmersión o seguido de '0' para ocultar los gráficos.")
        if graph == 2:
            piedoc = generate_graph(points, "piechart")
            normal.set_image(url="attachment://image.png")
            await ctx.send(embed=normal, file=piedoc)
        elif graph == 1:
            bardoc = generate_graph(graphlogs, "bars", timelapse)
            normal.set_image(url="attachment://image.png")
            await ctx.send(embed=normal, file=bardoc)
        else:
            await ctx.send(embed=normal)

    @ commands.command(aliases=["backlog"])
    async def backfill(self, ctx, fecha, medio, cantidad, descripcion):
        """Uso:: .backfill <fecha (dd/mm/yyyy)> <tipo de inmersión> <cantidad inmersada>"""

        # Check if the user has logs
        if(not await check_user(self.db, ctx.author.id)):
            await create_user(self.db, ctx.author.id, ctx.author.name)

        # Verify the user is in the correct channel
        if ctx.channel.id not in logs_channel_id:
            await ctx.send(
                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        date = fecha.split("/")
        if(len(date) < 3):
            await send_error_message(self, ctx, "Formato de fecha no válido")
            return
        try:
            if(int(date[2]) < 2000):
                date[2] = int(date[2]) + 2000
            datets = int(datetime(int(date[2]), int(
                date[1]), int(date[0])).timestamp())
        except ValueError:
            await send_error_message(self, ctx, "Formato de fecha no válido")
            return
        except OSError:
            await send_error_message(self, ctx, "Formato de fecha no válido")
            return

        strdate = datetime.fromtimestamp(datets)
        if(datetime.today().timestamp() - datets < 0):
            await send_error_message(self, ctx, "Prohibido viajar en el tiempo")
            return

        message = ""
        for word in ctx.message.content.split(" ")[4:]:
            message += word + " "

        newlog = {
            'timestamp': datets,
            'descripcion': message,
            'medio': medio.upper(),
            'parametro': cantidad
        }

        output = calc_points(newlog)

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

            embed = Embed(title="Log registrado con éxito",
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
            message = await ctx.send(embed=embed)
            await message.add_reaction("❌")
        elif output == 0:
            await send_error_message(self, ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
            return
        elif output == -1:
            await send_error_message(self, ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
            return
        elif output == -2:
            await send_error_message(self, ctx, "Cantidad de inmersión exagerada")
            return

    @ commands.command()
    async def log(self, ctx, medio, cantidad, descripcion):
        """Uso:: .log <tipo de inmersión> <cantidad inmersada>"""
        # Check if the user has logs
        if(not await check_user(self.db, ctx.author.id)):
            await create_user(self.db, ctx.author.id, ctx.author.name)

        # Verify the user is in the correct channel
        if ctx.channel.id not in logs_channel_id:
            await ctx.send(
                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        message = ""
        for word in ctx.message.content.split(" ")[3:]:
            message += word + " "

        today = datetime.today()

        newlog = {
            'timestamp': int(today.timestamp()),
            'descripcion': message,
            'medio': medio.upper(),
            'parametro': cantidad
        }

        output = calc_points(newlog)

        if output > 0:

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

            embed = Embed(title="Log registrado con éxito",
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
            if newposition < position:
                embed.add_field(
                    name="🎉 Has subido en el ranking del mes! 🎉", value=f"**{position+1}º** ---> **{newposition+1}º**", inline=False)
            embed.set_footer(
                text=ctx.author.id)
            message = await ctx.send(embed=embed)
            await message.add_reaction("❌")
            sleep(10)
            await message.clear_reaction("❌")

        elif output == 0:
            await send_error_message(self, ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
            return
        elif output == -1:
            await send_error_message(self, ctx, "La cantidad de inmersión solo puede expresarse en números enteros")
            return
        elif output == -2:
            await send_error_message(self, ctx, "Cantidad de inmersión exagerada")
            return

    @ commands.command()
    async def puntos(self, ctx, points):
        """Uso:: .log <tipo de inmersión> <cantidad inmersada>"""
        immersion_needed = calc_media(int(points))
        embed = discord.Embed(
            title=f"Para conseguir {points} puntos necesitas inmersar:", color=0x00ccff)
        embed.add_field(name="Libro", value=get_media_element(
            immersion_needed["libro"], "LIBRO"), inline=False)
        embed.add_field(name="Manga", value=get_media_element(
            immersion_needed["manga"], "MANGA") + f" (aprox {math.ceil(int(immersion_needed['manga'])/170)} volúmenes)", inline=False)
        embed.add_field(name="VN", value=get_media_element(
            immersion_needed["vn"], "VN"), inline=False)
        embed.add_field(name="Anime", value=get_media_element(
            math.ceil(immersion_needed["anime"]), "ANIME") + f" (aprox {get_media_element(immersion_needed['anime']*24, 'VIDEO')})", inline=False)
        embed.add_field(name="Lectura", value=get_media_element(
            immersion_needed["lectura"], "LECTURA"), inline=False)
        embed.add_field(name="Tiempo de lectura", value=get_media_element(
            immersion_needed["tiempolectura"], "TIEMPOLECTURA"), inline=False)
        embed.add_field(name="Audio", value=get_media_element(
            immersion_needed["audio"], "AUDIO"), inline=False)
        embed.add_field(name="Video", value=get_media_element(
            immersion_needed["video"], "VIDEO"), inline=False)
        await ctx.send(embed=embed, delete_after=60.0)

    @ commands.command(aliases=["deshacer"])
    async def undo(self, ctx):
        """Uso:: .undo"""
        # Verify the user has logs
        if(not await check_user(self.db, ctx.author.id)):
            await send_error_message(self, ctx, "No tienes ningún log.")
            return

        # Verify the user is in the correct channel
        if ctx.channel.id not in logs_channel_id:
            await ctx.send(
                "Este comando solo puede ser usado en <#950449182043430942>.")
            return
        result = await remove_last_log(self.db, ctx.author.id)
        if(result == 1):
            logdeleted = Embed(color=0x24b14d)
            logdeleted.add_field(
                name="✅", value="Log eliminado con éxito", inline=False)
            await ctx.send(embed=logdeleted, delete_after=10.0)
        else:
            await send_error_message(self, ctx, "Ese log no existe")

    @ commands.command(aliases=["dellog"])
    async def remlog(self, ctx, logid):
        """Uso:: .remlog <Id log a borrar>"""
        # Verify the user has logs
        if(not await check_user(self.db, ctx.author.id)):
            await send_error_message(self, ctx, "No tienes ningún log.")
            return

        # Verify the user is in the correct channel
        if ctx.channel.id not in logs_channel_id:
            await ctx.send(
                "Este comando solo puede ser usado en <#950449182043430942>.")
            return

        result = await remove_log(self.db, ctx.author.id, logid)
        if(result == 1):
            logdeleted = Embed(color=0x24b14d)
            logdeleted.add_field(
                name="✅", value="Log eliminado con éxito", inline=False)
            await ctx.send(embed=logdeleted, delete_after=10.0)
        else:
            await send_error_message(self, ctx, "Ese log no existe")

    @ commands.command()
    async def ordenarlogs(self, ctx):
        if(not await check_user(self.db, ctx.author.id)):
            await send_error_message(self, ctx, "No tienes ningún log.")
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
        await ctx.send("Tu toc ha sido remediado con éxito.")

    @commands.command()
    async def progreso(self, ctx, timelapse=str(datetime.now().year)):
        if(not await check_user(self.db, ctx.author.id)):
            await send_error_message(self, ctx, "No tienes ningún log.")
            return
        results = {}
        if(timelapse.upper() == "TOTAL"):

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
        elif(timelapse.isdigit()):
            if(int(timelapse) < 1000):
                timelapse = "20" + timelapse
            start = datetime(year=int(timelapse), month=1, day=1)
            end = datetime(year=int(timelapse), month=12, day=31)
            steps = 12

            # funcion get logs de mes en mes hasta el día de hoy
            # meter en array ordenado cada mes
            # hacer gráfica con el array ordenado
            # profit
        else:
            return await send_error_message(self, ctx, "Escribe 'TOTAL' para ver el progreso desde tu primer log o concreta un año para ver el progreso en ese año")
        i = 0
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

            for log in logs:
                points[log["medio"]] += log["puntos"]
            results[f"{begin.year}/{begin.month}"] = points

        normal = discord.Embed(
            title=f"Vista {get_ranking_title(timelapse.upper(),'ALL')}", color=0xeeff00)
        normal.add_field(name="Usuario", value=ctx.author.name, inline=True)
        bardoc = generate_graph(results, "progress")
        normal.set_image(url="attachment://image.png")
        await ctx.send(embed=normal, file=bardoc)

    @ commands.command()
    async def findemes(self, ctx, video=False, month=None, day=None):
        if ctx.message.author.id != int(admin_id):
            return await send_error_message(self, ctx, "Vuelve a hacer eso y te mato")
        today = datetime.today()
        if month is None:
            month = today.month
        if day is None:
            day = (datetime(today.year, int(month) + 1, 1) - timedelta(days=1)
                   ).day
        message = await ctx.send("Procesando datos del mes, espere por favor...")
        await get_logs_animation(self.db, month, day)
        # Generate monthly ranking animation
        df = pd.read_csv('temp/test.csv', index_col='date',
                         parse_dates=['date'])
        df.tail()
        plt.rc('font', family='Noto Sans CJK JP')
        plt.rcParams['text.color'] = "#FFFFFF"
        plt.rcParams['axes.labelcolor'] = "#FFFFFF"
        plt.rcParams['xtick.color'] = "#FFFFFF"
        plt.rcParams['ytick.color'] = "#FFFFFF"
        plt.rcParams.update({'figure.autolayout': True})
        fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
        ax.set_title(f"Ranking {intToMonth(int(month))} AJR")
        ax.set_facecolor("#36393F")
        fig.set_facecolor("#36393F")
        ax.set_xlabel('Puntos', color="white")
        ax.tick_params(axis='both', colors='white')
        if video:
            bcr.bar_chart_race(df, 'temp/video.mp4', figsize=(20, 12), fig=fig,
                               period_fmt="%d/%m/%Y", period_length=2000, steps_per_period=75, bar_size=0.7, interpolate_period=True)
            file = discord.File("temp/video.mp4", filename="ranking.mp4")
        await message.delete()
        mvp = await get_best_user_of_range(self.db, "TOTAL", f"{today.year}/{month}")
        newrole = self.myguild.get_role(mvp_role)
        for user in ctx.guild.members:
            if newrole in user.roles:
                await user.remove_roles(newrole)
        mvpuser = ctx.message.guild.get_member(mvp["id"])
        await mvpuser.add_roles(newrole)

        embed = Embed(
            title=f"🎌 AJR mes de {intToMonth(int(month))} 🎌", color=0x1302ff, description="-----------------")
        embed.add_field(name="Usuario del mes",
                        value=mvp["username"], inline=False)
        if mvpuser is not None:
            embed.set_thumbnail(
                url=mvpuser.avatar)
        embed.add_field(name="Puntos conseguidos",
                        value=round(mvp["points"], 2), inline=False)
        message = f"🎉 Felicidades a <@{mvp['id']}> por ser el usuario del mes de {intToMonth(int(month))}!"
        if video:
            await ctx.send(embed=embed, content=message, file=file)
        else:
            await ctx.send(embed=embed, content=message)

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            reaction = discord.utils.get(message.reactions, emoji="❌")
        except discord.errors.NotFound:
            print("todo en orden")

        if(len(message.embeds) > 0 and reaction):
            if(message.embeds[0].title == "Log registrado con éxito" and int(message.embeds[0].footer.text) == payload.user_id):
                # TODO: función para borrar logs dado el id del log y el id del usuario
                await remove_log(self.db, payload.user_id, message.embeds[0].description.split(" ")[1].replace("#", ""))
                await message.delete()

    @commands.command()
    async def calcchars(self, ctx, total_chars, read_pages, total_pages):
        await ctx.message.delete()
        if(total_chars.isnumeric() and read_pages.isnumeric() and total_pages.isnumeric()):
            read_chars = round(int(read_pages) *
                               int(total_chars) / int(total_pages))
            return await ctx.send(f"Has leido un total de {read_chars} carácteres", delete_after=15.0)
        return await send_error_message(self, ctx, "Solo se aceptan números")

    @commands.command()
    async def loganilist(self, ctx, username, date=20000101):
        if len(str(date)) != 8:
            await send_error_message(self, ctx, "La fecha debe tener el formato YYYYMMDD")
            return
        user_id = await get_anilist_id(username)
        if(user_id == -1):
            await send_error_message(self, ctx, "Esa cuenta de anilist no existe o es privada, cambia tus ajustes de privacidad.")
            return
        nextPage = True
        page = 1
        errored = []
        total_logs = 0
        total_repeated = 0
        while nextPage:
            logs = await get_anilist_logs(user_id, page, date)
            print(logs)
            nextPage = logs["data"]["Page"]["pageInfo"]["hasNextPage"]
            for log in logs["data"]["Page"]["mediaList"]:
                newlog = {
                    'anilistAccount': username,
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
                    newlog["parametro"] = str(log["media"]["duration"] *
                                              log["media"]["episodes"])
                else:
                    newlog["medio"] = "ANIME"
                    newlog["parametro"] = str(log["media"]["episodes"])

                failed = False
                if(log["completedAt"]["year"]):
                    newlog["timestamp"] = int(datetime(
                        log["completedAt"]["year"], log["completedAt"]["month"], log["completedAt"]["day"]).timestamp())
                elif(log["startedAt"]["year"]):
                    newlog["timestamp"] = int(datetime(
                        log["startedAt"]["year"], log["startedAt"]["month"], log["startedAt"]["day"]).timestamp())
                else:
                    errored.append(log["media"]["title"]["native"])
                    failed = True

                if(self.db.users.find({'userId': ctx.author.id, 'logs': {'$elemMatch': {'anilistId': newlog["anilistId"]}}}).count() > 0):
                    total_repeated += 1
                    failed = True

                if(not failed):
                    total_logs += 1
                    output = calc_points(newlog)
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
        if(total_size > 500):
            total_errored = "Demasiados logs fallidos para poder representarlo, revisa que tus entradas de anilist tienen fecha de finalización."
        embed = Embed(
            title=f"Añadido a logs la cuenta de anilist de {username}", color=0x1302ff, description="-----------------")
        embed.add_field(name="Logs introducidos",
                        value=total_logs, inline=False)
        if(total_repeated > 0):
            embed.add_field(name="Logs repetidos",
                            value=total_repeated, inline=False)
        if(total_errored != ""):
            embed.add_field(name="Logs fallidos",
                            value=total_len, inline=False)
            embed.add_field(name="Lista de fallidos",
                            value=total_errored, inline=True)
        embed.set_footer(
            text="Es recomendable que escribas el comando .ordenarlogs después de hacer un import de anilist.")
        await ctx.send(embed=embed)
        print(errored)


def setup(bot):
    bot.add_cog(Logs(bot))
