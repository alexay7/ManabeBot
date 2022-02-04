"""Cog responsible for immersion logs."""

import asyncio
from turtle import color
from pymongo import MongoClient, errors
import os
import json
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Embed
import discord.errors
from time import sleep
from .fun import intToMonth
import matplotlib.pyplot as plt

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
#############################################################

MEDIA_TYPES = {"LIBRO", "MANGA", "VN", "ANIME",
               "LECTURA", "TIEMPOLECTURA", "AUDIO", "VIDEO"}

TIMESTAMP_TYPES = {"TOTAL", "MES", "SEMANA"}


# FUNCTIONS FOR SENDING MESSAGES


async def send_message_with_buttons(self, ctx, content):
    pages = len(content)
    cur_page = 1
    message = await ctx.send(f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
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
                            await ctx.send("‼️ Los mensajes con páginas no funcionan bien en DM!")

                    elif str(reaction.emoji) == "◀️" and cur_page > 1:
                        cur_page -= 1
                        await message.edit(content=f"```{content[cur_page-1]}\nPág {cur_page} de {pages}```")
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await ctx.send("‼️ Los mensajes con páginas no funcionan bien en DM!")

                    else:
                        try:
                            await message.remove_reaction(reaction, user)
                        except discord.errors.Forbidden:
                            await ctx.send("‼️ Los mensajes con páginas no funcionan bien en DM!")
                        # removes reactions if the user tries to go forward on the last page or
                        # backwards on the first page
            except asyncio.TimeoutError:
                try:
                    await message.delete()
                except discord.errors.Forbidden:
                    await ctx.send("‼️ Los mensajes con páginas no funcionan bien en DM!")
                break
                # ending the loop if user doesn't react after x seconds


async def send_error_message(self, ctx, content):
    embed = Embed(color=0xff2929)
    embed.add_field(
        name="❌", value=content, inline=False)
    await ctx.send(embed=embed, delete_after=10.0)

# FUNCTIONS RELATED WITH LOGS


async def remove_log(db, userid, logid):
    users = db.users
    result = users.update_one(
        {"userId": userid}, {"$pull": {"logs": {"id": int(logid)}}})
    return result.modified_count


async def create_user(db, userid, username):
    users = db.users
    newuser = {
        'userId': userid,
        'username': username,
        'logs': []
    }
    users.insert_one(newuser)


async def get_user_logs(db, userid, timelapse, media=None):
    users = db.users

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

    elif timelapse == "SEMANA":
        start = int((datetime.today() - timedelta(weeks=1)).timestamp())
        end = int(datetime.today().timestamp())
        if media in MEDIA_TYPES:
            # SEVEN-DAY LOGS OF A MEDIA TYPE FROM USER
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
                                "cond": {"$and": [
                                    {"$gte": ["$$log.timestamp", start]},
                                    {"$lte": ["$$log.timestamp", end]},
                                    {"$eq": ["$$log.medio", media]}
                                ]}
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
            # SEVEN-DAY LOGS OF ALL MEDIA TYPES FROM USER
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
                                "cond": {"$and": [
                                    {"$gte": ["$$log.timestamp", start]},
                                    {"$lte": ["$$log.timestamp", end]}
                                ]}
                            }
                        }
                    }
                }
            ])
            if result:
                for elem in result:
                    # Only one document should be found so no problem returning data
                    return elem["logs"]
    elif timelapse == "MES":
        start = int(
            (datetime(datetime.today().year, datetime.today().month, 1)).timestamp())
        end = int(datetime.today().timestamp())
        if media in MEDIA_TYPES:
            # MONTHLY LOGS OF A MEDIA TYPE FROM USER
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
                                "cond": {"$and": [
                                    {"$gte": ["$$log.timestamp", start]},
                                    {"$lte": ["$$log.timestamp", end]},
                                    {"$eq": ["$$log.medio", media]}
                                ]}
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
            # MONTHLY LOGS OF ALL MEDIA TYPES FROM USER
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
                                "cond": {"$and": [
                                    {"$gte": ["$$log.timestamp", start]},
                                    {"$lte": ["$$log.timestamp", end]}
                                ]}
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
        split_time = timelapse.split("/")
        if len(split_time) == 1:
            # TOTAL VIEW
            start = int(
                (datetime(int(split_time[0]), 1, 1)).timestamp())
            end = int(
                (datetime(int(split_time[0]), 12, 31)).timestamp())

        else:
            # MONTHLY VIEW
            month = int(split_time[1])
            year = int(split_time[0])
            start = int(
                (datetime(int(year), month, 1)).timestamp())
            if month+1 > 12:
                month = 0
                year += 1
            end = int(
                (datetime(int(year), month+1, 1)-timedelta(days=1)).timestamp())
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
            "username": user["username"],
            "points": userpoints[media.upper()],
            "parameters": parameters[media.upper()]
        }
        if newuser["points"] > points:
            points = newuser["points"]
            parameternum = newuser["parameters"]
            aux = newuser
    if(not(aux is None)):
        return aux
    return None


async def add_log(db, userid, log):
    users = db.users
    user = users.find_one({'userId': userid})
    newid = len(user["logs"])
    log["id"] = newid
    users.update_one(
        {'userId': userid},
        {'$push': {"logs": log}}
    )
    return newid

# GENERAL FUNCTIONS


def calc_points(log):
    # Mejor prevenir que curar
    if log["medio"] not in MEDIA_TYPES:
        return 0
    if not log["parametro"].isnumeric():
        return -1
    if int(log["parametro"]) > 9999999:
        return -2
    if log["medio"] == "LIBRO":
        puntos = round(int(log["parametro"]), 1)
    elif log["medio"] == "MANGA":
        puntos = round(int(log["parametro"]) / 5, 1)
    elif log["medio"] == "VN":
        puntos = round(int(log["parametro"]) / 350, 1)
    elif log["medio"] == "ANIME":
        puntos = round(int(log["parametro"]) * 95 / 10, 1)
    elif log["medio"] == "LECTURA":
        puntos = round(int(log["parametro"]) / 350, 1)
    elif log["medio"] == "TIEMPOLECTURA":
        puntos = round(int(log["parametro"]) * 45 / 100, 1)
    elif log["medio"] == "AUDIO":
        puntos = round(int(log["parametro"]) * 45 / 100, 1)
    elif log["medio"] == "VIDEO":
        puntos = round(int(log["parametro"]) * 45 / 100, 1)
    log["puntos"] = puntos
    return puntos


def get_ranking_title(timelapse, media):
    tiempo = ""
    if timelapse == "MES":
        tiempo = "mensual"
    elif timelapse == "SEMANA":
        tiempo = "semanal"
    else:
        tiempo = "total"
    medio = ""
    if media in {"MANGA", "ANIME", "AUDIO", "LECTURA", "VIDEO"}:
        medio = "de " + media.lower()
    elif media in {"LIBRO"}:
        medio = "de " + media.lower() + "s"
    elif media in {"LECTURATIEMPO"}:
        medio = "de lectura (tiempo)"
    elif media in {"VN"}:
        medio = "de " + media
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
    return users.find({'userId': userid}).count() > 0


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
    else:
        labels = []
        values = []
        if timelapse.upper() == "SEMANA":
            start = datetime.today()-timedelta(days=7)
            for x in range(0, 7):
                auxdate = str(start+timedelta(days=x)
                              ).replace("-", "/").split(" ")[0]
                labels.append(auxdate)
                if auxdate in points:
                    values.append(points[auxdate])
                else:
                    values.append(0)
            fig, ax = plt.subplots()
            ax.bar(labels, values, color='#24B14D')
            ax.set_ylabel('Puntos', color="white")
            ax.tick_params(axis='both', colors='white')
            fig.set_facecolor("#2F3136")
            fig.autofmt_xdate()
            plt.savefig("temp/image.png")
            file = discord.File("temp/image.png", filename="image.png")
            return file


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
                                     serverSelectionTimeoutMS=1000)
                client.server_info()
            except errors.ServerSelectionTimeoutError:
                print("Ha ocurrido un error intentando conectar con la base de datos.")
                exit(1)
            print("Conexión con base de datos ha sido un éxito.")
            self.db = client.ajrlogs

        # await self.private_admin_channel.send("Connected to db successfully")

    @ commands.command(aliases=["halloffame", "salondelafama", "salonfama", "mvp"])
    async def hallofame(self, ctx, timelapse=f"{datetime.today().year}", media="TOTAL"):
        """Uso:: $hallofame <tiempo (week/month/all)/tipo de inmersión> <tipo de inmersión>"""
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
            title = f"🏆 Usuarios del mes ({datetime.today().year})"
            if media.upper() in MEDIA_TYPES:
                title += f" [{media.upper()}]"

        else:
            # Iterate from 2020 until current year
            end = datetime.today().year
            domain = range(2020, end+1)
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

    @ commands.command(aliases=["ranking", "podio"])
    async def leaderboard(self, ctx, timelapse="MES", media="TOTAL"):
        """Uso:: $leaderboard <tiempo (week/month/all)/tipo de inmersión> <tipo de inmersión>"""
        leaderboard = []
        if timelapse.upper() in MEDIA_TYPES:
            media = timelapse
            timelapse = "MES"
        users = self.db.users.find({}, {"userId", "username"})
        counter = 0
        for user in users:
            points, parameters = await get_user_data(
                self.db, user["userId"], timelapse.upper(), media.upper())
            leaderboard.append({
                "username": user["username"],
                "points": points["TOTAL"]})
            if media.upper() in MEDIA_TYPES:
                leaderboard[counter]["param"] = parameters[media.upper()]
            counter += 1

        sortedlist = sorted(
            leaderboard, key=lambda x: x["points"], reverse=True)
        message = ""
        position = 1
        for user in sortedlist[0:10]:
            if(user["points"] != 0):
                message += f"**{str(position)}º {user['username']}:** {str(round(user['points'],2))} puntos"
                if("param" in user):
                    message += f" -> {get_media_element(user['param'],media.upper())}\n"
                else:
                    message += "\n"
                position += 1
            else:
                sortedlist.remove(user)
        if len(sortedlist) > 0:
            title = "Ranking " + \
                get_ranking_title(timelapse.upper(), media.upper())
            embed = Embed(color=0x5842ff)
            embed.add_field(name=title, value=message, inline=True)
            await ctx.send(embed=embed)
        else:
            await send_error_message(self, ctx, "Ningún usuario ha inmersado con este medio en el periodo de tiempo indicado")
            return

    @ commands.command()
    async def logs(self, ctx, timelapse="TOTAL", user=None):
        """Uso:: $logs <tiempo (week/month/all)/Id usuario> <Id usuario>"""
        if timelapse.isnumeric():
            user = int(timelapse)
            timelapse = "TOTAL"

        errmsg = "No se han encontrado logs asociados a esa Id."
        if user is None:
            errmsg = "No has registrado ningún log"
            user = ctx.author.id

        if(not await check_user(self.db, user)):
            await send_error_message(self, ctx, errmsg)
            return

        result = await get_user_logs(self.db, user, timelapse)
        sorted_res = sorted(result, key=lambda x: x["timestamp"])

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

    @ commands.command(aliases=["yo"])
    async def me(self, ctx, timelapse="MES", graph=0):
        """Uso:: $me <tiempo (semana/mes/all)>"""
        if(not await check_user(self.db, ctx.author.id)):
            await ctx.send("No tienes ningún log.")
            return
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
                graphlogs[logdate] = 1

        if points["TOTAL"] == 0:
            output = "No se han encontrado logs"
        else:
            if points["LIBRO"] > 0:
                output += f"**LIBROS:** {get_media_element(parameters['LIBRO'],'LIBRO')} -> {points['LIBRO']} pts\n"
            if points["MANGA"] > 0:
                output += f"**MANGA:** {get_media_element(parameters['MANGA'],'MANGA')} -> {points['MANGA']} pts\n"
            if points["ANIME"] > 0:
                output += f"**ANIME:** {get_media_element(parameters['ANIME'],'ANIME')} -> {points['ANIME']} pts\n"
            if points["VN"] > 0:
                output += f"**VN:** {get_media_element(parameters['VN'],'VN')} -> {points['VN']} pts\n"
            if points["LECTURA"] > 0:
                output += f"**LECTURA:** {get_media_element(parameters['LECTURA'],'LECTURA')} -> {points['LECTURA']} pts\n"
            if points["TIEMPOLECTURA"] > 0:
                output += f"**LECTURA:** {get_media_element(parameters['TIEMPOLECTURA'],'TIEMPOLECTURA')} -> {points['TIEMPOLECTURA']} pts\n"
            if points["AUDIO"] > 0:
                output += f"**AUDIO:** {get_media_element(parameters['AUDIO'],'AUDIO')} -> {points['AUDIO']} pts\n"
            if points["VIDEO"] > 0:
                output += f"**VIDEO:** {get_media_element(parameters['VIDEO'],'VIDEO')} -> {points['VIDEO']} pts\n"

        normal = discord.Embed(
            title=f"Vista {get_ranking_title(timelapse.upper(),'ALL')}", color=0xeeff00)
        normal.add_field(name="Usuario", value=ctx.author.name, inline=True)
        normal.add_field(name="Puntos", value=round(
            points["TOTAL"], 2), inline=True)
        normal.add_field(name="Medios", value=output, inline=False)
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
        """Uso:: $backfill <fecha (dd/mm/yyyy)> <tipo de inmersión> <cantidad inmersada>"""
        if(not await check_user(self.db, ctx.author.id)):
            await create_user(self.db, ctx.author.id, ctx.author.name)

        date = fecha.split("/")
        if(len(date) < 3):
            await send_error_message(self, ctx, "Formato de fecha no válido")
            return
        try:
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
            logid = await add_log(self.db, ctx.author.id, newlog)

            embed = Embed(title="Log registrado con éxito",
                          description=f"Log #{logid} || {strdate.strftime('%d/%m/%Y')}", color=0x24b14d)
            embed.add_field(
                name="Usuario", value=ctx.author.name, inline=True)
            embed.add_field(name="Medio", value=medio.upper(), inline=True)
            embed.add_field(name="Puntos", value=output, inline=True)
            embed.add_field(name="Inmersado",
                            value=get_media_element(cantidad, medio.upper()), inline=True)
            embed.add_field(name="Inmersión",
                            value=message, inline=False)
            embed.set_footer(
                text=ctx.author.id)
            message = await ctx.send(embed=embed)
            await message.add_reaction("❌")
        elif output == 0:
            await send_error_message(self, ctx, "Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura, audio y video")
            return
        elif output == -1:
            await send_error_message(self, ctx, "La cantidad de inmersión solo puede expresarse en números")
            return
        elif output == -2:
            await send_error_message(self, ctx, "Cantidad de inmersión exagerada")
            return

    @ commands.command()
    async def log(self, ctx, medio, cantidad, descripcion):
        """Uso:: $log <tipo de inmersión> <cantidad inmersada>"""
        if(not await check_user(self.db, ctx.author.id)):
            await create_user(self.db, ctx.author.id, ctx.author.name)

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
            logid = await add_log(self.db, ctx.author.id, newlog)

            embed = Embed(title="Log registrado con éxito",
                          description=f"Log #{logid} || {today.strftime('%d/%m/%Y')}", color=0x24b14d)
            embed.add_field(
                name="Usuario", value=ctx.author.name, inline=True)
            embed.add_field(name="Medio", value=medio.upper(), inline=True)
            embed.add_field(name="Puntos", value=output, inline=True)
            embed.add_field(name="Inmersado",
                            value=get_media_element(cantidad, medio.upper()), inline=True)
            embed.add_field(name="Inmersión",
                            value=message, inline=False)
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
            await send_error_message(self, ctx, "La cantidad de inmersión solo puede expresarse en números")
            return
        elif output == -2:
            await send_error_message(self, ctx, "Cantidad de inmersión exagerada")
            return

    @ commands.command(aliases=["dellog"])
    async def remlog(self, ctx, logid):
        """Uso:: $remlog <Id log a borrar>"""
        if(not await check_user(self.db, ctx.author.id)):
            await ctx.send("No tienes ningún log.")
            return
        result = await remove_log(self.db, ctx.author.id, logid)
        if(result == 1):
            logdeleted = Embed(color=0x24b14d)
            logdeleted.add_field(
                name="✅", value="Log eliminado con éxito", inline=False)
            await ctx.send(embed=logdeleted, delete_after=10.0)
        else:
            await send_error_message(self, ctx, "Ese log no existe")

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            print("todo en orden")

        if(len(message.embeds) > 0):
            if(message.embeds[0].title == "Log registrado con éxito" and int(message.embeds[0].footer.text) == payload.user_id):
                # TODO: función para borrar logs dado el id del log y el id del usuario
                await remove_log(self.db, payload.user_id, message.embeds[0].description.split(" ")[1].replace("#", ""))
                await message.delete()


def setup(bot):
    bot.add_cog(Logs(bot))
