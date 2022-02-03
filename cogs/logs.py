"""Cog responsible for immersion logs."""

from pymongo import MongoClient, errors
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Embed
from time import sleep

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

TIMESTAMP_TYPES = {"ALL", "MONTH", "WEEK"}


async def create_user(db, userid, username):
    users = db.users
    newuser = {
        'userId': userid,
        'username': username,
        'logs': []
    }
    users.insert_one(newuser)


async def get_user_points(db, userid, timelapse, media="ALL"):
    logs = await get_user_logs(db, userid, timelapse, media)
    total = 0
    for log in logs:
        total += log["puntos"]
    return total


async def get_user_logs(db, userid, timelapse, media=None):
    users = db.users

    if timelapse == "ALL":
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
            for elem in result:
                # Only one document should be found so no problem returning data
                return elem["logs"]
        else:
            # ALL LOGS OF ALL MEDIA TYPES FROM USER
            result = users.find_one({"userId": userid}, {"logs"})
            return result["logs"]

    elif timelapse == "WEEK":
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
            for elem in result:
                # Only one document should be found so no problem returning data
                return elem["logs"]


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
    print(media)
    tiempo = ""
    if timelapse == "MONTH":
        tiempo = "mensual"
    elif timelapse == "WEEK":
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
    return f"Ranking {tiempo} {medio}"

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

    @commands.command()
    async def test(self, ctx, timelapse="MONTH", media="ALL"):
        print(ctx.author.name)

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

    @commands.command()
    async def leaderboard(self, ctx, timelapse="MONTH", media="ALL"):
        leaderboard = []
        if timelapse.upper() in MEDIA_TYPES:
            media = timelapse
            timelapse = "MONTH"
        users = self.db.users.find({}, {"userId", "username"})
        for user in users:
            points = await get_user_points(self.db, user["userId"], timelapse.upper(), media.upper())
            leaderboard.append({
                "username": user["username"],
                "points": points})
        sortedlist = sorted(leaderboard, key=lambda x: x["points"], reverse=True)
        message = ""
        position = 1
        for user in sortedlist[0:10]:
            if(user["points"] != 0):
                message += f"**{str(position)}º {user['username']}:** {str(user['points'])} puntos\n"
                position += 1

        title = get_ranking_title(timelapse.upper(), media.upper())
        embed = Embed(color=0x5842ff)
        embed.add_field(name=title, value=message, inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def logs(self, ctx, timelapse="ALL", user=None):
        if not user:
            user = ctx.author.id

        if timelapse.isnumeric():
            user = int(timelapse)
            timelapse = "ALL"

        result = await get_user_logs(self.db, user, timelapse)
        sorted_res = sorted(result, key=lambda x: x["timestamp"])

        output = ""
        overflow = 0
        for log in sorted_res:
            timestring = datetime.fromtimestamp(log["timestamp"]).strftime('%d/%m/%Y')
            line = f"#{log['id']} | {timestring}: {log['medio']} {get_media_element(log['parametro'],log['medio'])} -> {log['puntos']} puntos: {log['descripcion']}\n"
            if len(output) + len(line) < 1000:
                output += line
            else:
                overflow += 1
        if(overflow > 0):
            output += f"y {overflow} logs más..."

        await ctx.send("```" + output + "```")

    @ commands.command()
    async def backfill(self, ctx, fecha, medio, cantidad, desc):
        if ctx.author.id == admin_user_id or True:
            if(not await check_user(self.db, ctx.author.id)):
                await create_user(self.db, ctx.author.id, ctx.author.name)

            date = fecha.split("/")
            datets = int(datetime(int(date[2]), int(
                date[1]), int(date[0])).timestamp())
            strdate = datetime.fromtimestamp(datets)
            if(datetime.today().timestamp() - datets < 0):
                await ctx.send("No puedes inmersar en el futuro.")

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
                await ctx.send("LIBRO" + "MANGA" + "VN" + "ANIME" + "LECTURA" + "TIEMPOLECTURA" + "AUDIO")
            elif output == -1:
                await ctx.send("Solo números por favor.")
            elif output == -2:
                await ctx.send("Me temo que esa cantidad de inmersión no es humana así que no puedo registrarla.")

    @ commands.command()
    async def me(self, ctx, timelapse="MONTH"):
        if ctx.author.id == admin_user_id or True:
            if(not await check_user(self.db, ctx.author.id)):
                ctx.send("No tienes ningún log.")
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
            for log in logs:
                if log["medio"] == "LIBRO":
                    points["book"] += log["puntos"]
                elif log["medio"] == "MANGA":
                    points["manga"] += log["puntos"]
                elif log["medio"] == "ANIME":
                    points["anime"] += log["puntos"]
                elif log["medio"] == "VN":
                    points["vn"] += log["puntos"]
                elif log["medio"] == "LECTURA":
                    points["read"] += log["puntos"]
                elif log["medio"] == "TIEMPOLECTURA":
                    points["readtime"] += log["puntos"]
                elif log["medio"] == "AUDIO":
                    points["listentim"] += log["puntos"]
                points["total"] += log["puntos"]
            await ctx.send(points)

    @ commands.command()
    async def log(self, ctx, medio, cantidad, desc):
        if ctx.author.id == admin_user_id or True:
            if(not await check_user(self.db, ctx.author.id)):
                await create_user(self.db, ctx.author.id, "alexay7")

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
                await ctx.send("LIBRO" + "MANGA" + "VN" + "ANIME" + "LECTURA" + "TIEMPOLECTURA" + "AUDIO")
            elif output == -1:
                await ctx.send("Eres tonto o que te pasa? No ves que aquí solo puede ir un número.")
            elif output == -2:
                await ctx.send("Me temo que esa cantidad de inmersión no es humana así que no puedo registrarla.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if(len(message.embeds) > 0):
            if(message.embeds[0].title == "Log registrado con éxito" and int(message.embeds[0].footer.text) == payload.user_id):
                # TODO: función para borrar logs dado el id del log y el id del usuario
                ...


def setup(bot):
    bot.add_cog(Logs(bot))
