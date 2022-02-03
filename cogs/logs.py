"""Cog responsible for immersion logs."""

from pymongo import MongoClient, errors
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Embed
from time import sleep
import re
import discord.errors

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    admin_user_id = data_dict["kaigen_user_id"]
    quizranks = data_dict["quizranks"]
    mycommands = data_dict["mycommands"]
    mycommands = {int(key): value for key, value in mycommands.items()}
    myrankstructure = data_dict["rank_structure"]
#############################################################

MEDIA_TYPES = {"LIBRO", "MANGA", "VN", "ANIME",
               "LECTURA", "TIEMPOLECTURA", "AUDIO"}

TIMESTAMP_TYPES = {"TOTAL", "MES", "SEMANA"}


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
        "total": 0
    }
    parameters = {
        "LIBRO": 0,
        "MANGA": 0,
        "ANIME": 0,
        "VN": 0,
        "LECTURA": 0,
        "TIEMPOLECTURA": 0,
        "AUDIO": 0
    }

    for log in logs:
        if log["medio"] == "LIBRO":
            points["LIBRO"] += log["puntos"]
            parameters["LIBRO"] += int(log["parametro"])
        elif log["medio"] == "MANGA":
            points["MANGA"] += log["puntos"]
            parameters["MANGA"] += int(log["parametro"])
        elif log["medio"] == "ANIME":
            points["ANIME"] += log["puntos"]
            parameters["ANIME"] += int(log["parametro"])
        elif log["medio"] == "VN":
            points["VN"] += log["puntos"]
            parameters["VN"] += int(log["parametro"])
        elif log["medio"] == "LECTURA":
            points["LECTURA"] += log["puntos"]
            parameters["LECTURA"] += int(log["parametro"])
        elif log["medio"] == "TIEMPOLECTURA":
            points["TIEMPOLECTURA"] += log["puntos"]
            parameters["TIEMPOLECTURA"] += int(log["parametro"])
        elif log["medio"] == "AUDIO":
            points["AUDIO"] += log["puntos"]
            parameters["AUDIO"] += int(log["parametro"])
        points["total"] += log["puntos"]
    return points, parameters


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
    else:
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
    return ""


async def check_user(db, userid):
    users = db.users
    return users.find({'userId': userid}).count() > 0


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
        log["puntos"] = puntos
        return puntos
    elif log["medio"] == "MANGA":
        puntos = round(int(log["parametro"]) / 5, 1)
        log["puntos"] = puntos
        return puntos
    elif log["medio"] == "VN":
        puntos = round(int(log["parametro"]) / 350, 1)
        log["puntos"] = puntos
        return puntos
    elif log["medio"] == "ANIME":
        puntos = round(int(log["parametro"]) * 95 / 10, 1)
        log["puntos"] = puntos
        return puntos
    elif log["medio"] == "LECTURA":
        puntos = round(int(log["parametro"]) / 350, 1)
        log["puntos"] = puntos
        return puntos
    elif log["medio"] == "TIEMPOLECTURA":
        puntos = round(int(log["parametro"]) * 45 / 100, 1)
        log["puntos"] = puntos
        return puntos
    elif log["medio"] == "AUDIO":
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
    if media in {"MANGA", "ANIME", "AUDIO", "LECTURA"}:
        medio = "de " + media.lower()
    elif media in {"LIBRO"}:
        medio = "de " + media.lower() + "s"
    elif media in {"LECTURATIEMPO"}:
        medio = "de lectura (tiempo)"
    elif media in {"VN"}:
        medio = "de " + media
    return f"{tiempo} {medio}"


def get_media_element(num, media):
    if media == "MANGA" or media == "LIBRO":
        if num == 1:
            return "1 página"
        return f"{num} páginas"
    if media == "VN" or media == "LECTURA":
        if num == 1:
            return "1 caracter"
        return f"{num} caracteres"
    if media == "ANIME":
        if num == 1:
            return "1 episodio"
        return f"{num} episodios"
    if media == "TIEMPOLECTURA" or media == "AUDIO":
        if int(num) < 60:
            return f"{int(num)%60} minutos"
        elif int(num) < 120:
            return f"1 hora y {int(num)%60} minutos"
        return f"{int(int(num)/60)} horas y {int(num)%60} minutos"


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

    @commands.command(aliases=["ranking", "podio"])
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
                "points": points["total"]})
            if media.upper() in MEDIA_TYPES:
                leaderboard[counter]["param"] = parameters[media.upper()]
            counter += 1

        sortedlist = sorted(
            leaderboard, key=lambda x: x["points"], reverse=True)
        message = ""
        position = 1
        for user in sortedlist[0:10]:
            if(user["points"] != 0):
                message += f"**{str(position)}º {user['username']}:** {str(user['points'])} puntos"
                if("param" in user):
                    message += f" -> {get_media_element(user['param'],media.upper())}\n"
                else:
                    message += "\n"
                position += 1

        title = "Ranking " + \
            get_ranking_title(timelapse.upper(), media.upper())
        embed = Embed(color=0x5842ff)
        embed.add_field(name=title, value=message, inline=True)
        await ctx.send(embed=embed)

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
            logdeleted = Embed(color=0xff2929)
            logdeleted.add_field(
                name="❌", value=errmsg, inline=False)
            await ctx.send(embed=logdeleted, delete_after=10.0)
            return

        result = await get_user_logs(self.db, user, timelapse)
        sorted_res = sorted(result, key=lambda x: x["timestamp"])

        output = ""
        overflow = 0
        for log in sorted_res:
            timestring = datetime.fromtimestamp(
                log["timestamp"]).strftime('%d/%m/%Y')
            line = f"#{log['id']} | {timestring}: {log['medio']} {get_media_element(log['parametro'],log['medio'])} -> {log['puntos']} puntos: {log['descripcion']}\n"
            if len(output) + len(line) < 1000:
                output += line
            else:
                overflow += 1
        if(overflow > 0):
            output += f"y {overflow} logs más..."
        if len(output) > 0:
            await ctx.send("```" + output + "```")
        else:
            logdeleted = Embed(color=0xff2929)
            logdeleted.add_field(
                name="❌", value=errmsg, inline=False)
            await ctx.send(embed=logdeleted, delete_after=10.0)

    @ commands.command(aliases=["yo"])
    async def me(self, ctx, timelapse="MES"):
        """Uso:: $me <tiempo (semana/mes/all)>"""
        if(not await check_user(self.db, ctx.author.id)):
            await ctx.send("No tienes ningún log.")
            return
        logs = await get_user_logs(self.db, ctx.author.id, timelapse.upper())
        points = {
            "book": 0,
            "manga": 0,
            "anime": 0,
            "vn": 0,
            "read": 0,
            "readtime": 0,
            "listentime": 0,
            "total": 0
        }
        parameters = {
            "book": 0,
            "manga": 0,
            "anime": 0,
            "vn": 0,
            "read": 0,
            "readtime": 0,
            "listentime": 0
        }

        output = ""
        for log in logs:
            if log["medio"] == "LIBRO":
                points["book"] += log["puntos"]
                parameters["book"] += int(log["parametro"])
            elif log["medio"] == "MANGA":
                points["manga"] += log["puntos"]
                parameters["manga"] += int(log["parametro"])
            elif log["medio"] == "ANIME":
                points["anime"] += log["puntos"]
                parameters["anime"] += int(log["parametro"])
            elif log["medio"] == "VN":
                points["vn"] += log["puntos"]
                parameters["vn"] += int(log["parametro"])
            elif log["medio"] == "LECTURA":
                points["read"] += log["puntos"]
                parameters["read"] += int(log["parametro"])
            elif log["medio"] == "TIEMPOLECTURA":
                points["readtime"] += log["puntos"]
                parameters["readtime"] += int(log["parametro"])
            elif log["medio"] == "AUDIO":
                points["listentime"] += log["puntos"]
                parameters["listentime"] += int(log["parametro"])
            points["total"] += log["puntos"]

        if points["total"] == 0:
            output = "No se han encontrado logs"
        else:
            if points["book"] > 0:
                output += f"**LIBROS:** {get_media_element(parameters['book'],'LIBRO')} -> {points['book']} pts\n"
            if points["manga"] > 0:
                output += f"**MANGA:** {get_media_element(parameters['manga'],'MANGA')} -> {points['manga']} pts\n"
            if points["anime"] > 0:
                output += f"**ANIME:** {get_media_element(parameters['anime'],'ANIME')} -> {points['anime']} pts\n"
            if points["vn"] > 0:
                output += f"**VN:** {get_media_element(parameters['vn'],'VN')} -> {points['vn']} pts\n"
            if points["read"] > 0:
                output += f"**LECTURA:** {get_media_element(parameters['read'],'LECTURA')} -> {points['read']} pts\n"
            if points["readtime"] > 0:
                output += f"**LECTURA:** {get_media_element(parameters['readtime'],'TIEMPOLECTURA')} -> {points['readtime']} pts\n"
            if points["listentime"] > 0:
                output += f"**AUDIO:** {get_media_element(parameters['listentime'],'AUDIO')} -> {points['listentime']} pts\n"

        embed = discord.Embed(
            title=f"Vista {get_ranking_title(timelapse.upper(),'ALL')}")
        embed.add_field(name="Usuario", value=ctx.author.name, inline=True)
        embed.add_field(name="Puntos", value=points["total"], inline=True)
        embed.add_field(name="Medios", value=output, inline=False)
        await ctx.send(embed=embed)

    @ commands.command(aliases=["backlog"])
    async def backfill(self, ctx, fecha, medio, cantidad):
        """Uso:: $backfill <fecha (dd/mm/yyyy)> <tipo de inmersión> <cantidad inmersada>"""
        if(not await check_user(self.db, ctx.author.id)):
            await create_user(self.db, ctx.author.id, ctx.author.name)

        date = fecha.split("/")
        if(len(date) < 3):
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Formato de fecha no válido", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
            return
        try:
            datets = int(datetime(int(date[2]), int(
                date[1]), int(date[0])).timestamp())
        except ValueError:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Formato de fecha no válido", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
            return
        except OSError:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Formato de fecha no válido", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
            return
        strdate = datetime.fromtimestamp(datets)
        if(datetime.today().timestamp() - datets < 0):
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Prohibido viajar en el tiempo", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
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
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura y audio", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
        elif output == -1:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="La cantidad de inmersión solo puede expresarse en números", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
        elif output == -2:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Cantidad de inmersión exagerada", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)

    @ commands.command()
    async def log(self, ctx, medio, cantidad):
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

        elif output == 0:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Los medios admitidos son: libro, manga, anime, vn, lectura, tiempolectura y audio", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
        elif output == -1:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="La cantidad de inmersión solo puede expresarse en números", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)
        elif output == -2:
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Cantidad de inmersión exagerada", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)

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
            somethingbad = Embed(color=0xff2929)
            somethingbad.add_field(
                name="❌", value="Ese log no existe", inline=False)
            await ctx.send(embed=somethingbad, delete_after=10.0)

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
