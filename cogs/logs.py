"""Cog responsible for immersion logs."""

from pymongo import MongoClient,errors
import os
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from discord.ext import commands

#############################################################
# Variables (Temporary)
with open(f"cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    admin_user_id = data_dict["kaigen_user_id"]
    quizranks = data_dict["quizranks"]
    mycommands = data_dict["mycommands"]
    mycommands = {int(key): value for key, value in mycommands.items()}
    myrankstructure = data_dict["rank_structure"]
#############################################################


async def create_user(db, userid, username):
    users = db.users
    newuser = {
        'userId': userid,
        'username': username,
        'logs': []
    }
    users.insert_one(newuser)


async def check_user(db, userid):
    users = db.users
    return users.find({'userId': userid}).count() > 0


async def add_log(db, userid, log):
    users = db.users
    users.update_one(
        {'userId': userid},
        {'$push': {"logs": log}}
    )


async def test(db):
    start = int(datetime(2021, 9, 24).timestamp())
    end = int(datetime.today().timestamp())
    print(start)
    users = db.users
    result = users.aggregate([
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
        }
    ])

    for doc in result:
        print(doc)


def calc_points(log):
    # Mejor prevenir que curar
    media_types = {"LIBRO", "MANGA", "VN", "ANIME",
                   "LECTURA", "TIEMPOLECTURA", "ESCUCHA"}
    if log["medio"] not in media_types:
        return 0
    if not log["parametro"].isnumeric():
        return -1
    if int(log["parametro"]) > 9999999:
        return -2
    if log["medio"] == "LIBRO":
        log["puntos"] = int(log["parametro"])
        return 1
    elif log["medio"] == "MANGA":
        log["puntos"] = int(log["parametro"])/5
        return 1
    elif log["medio"] == "VN":
        log["puntos"] = int(log["parametro"])/350
        return 1
    elif log["medio"] == "ANIME":
        log["puntos"] = int(log["parametro"])*95/10
        return 1
    elif log["medio"] == "LECTURA":
        log["puntos"] = int(log["parametro"])/350
        return 1
    elif log["medio"] == "TIEMPOLECTURA":
        log["puntos"] = int(log["parametro"])*45/100
        return 1
    elif log["medio"] == "ESCUCHA":
        log["puntos"] = int(log["parametro"])*45/100
        return 1


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @ commands.Cog.listener()
    async def on_ready(self):
        load_dotenv()
        self.myguild = self.bot.get_guild(guild_id)
        if(self.myguild):
            try:
                client = MongoClient(os.getenv("MONGOURL"),
                                 serverSelectionTimeoutMS=1000)
                client.server_info()
            except errors.ServerSelectionTimeoutError as err:
                print("Ha ocurrido un error intentando conectar con la base de datos.")
                exit(1)
            print("Conexión con base de datos ha sido un éxito.")
            self.db = client.ajrlogs

        # await self.private_admin_channel.send("Connected to db successfully")

    @ commands.command()
    async def test(self, ctx):
        if ctx.author.id==admin_user_id:
            await test(self.db)

    @ commands.command()
    async def backfill(self, ctx, fecha, medio, cantidad, desc):
        if ctx.author.id==admin_user_id:
            if(not await check_user(self.db, ctx.author.id)):
                await create_user(self.db, ctx.author.id, "alexay7")

            date = fecha.split("/")

            newlog = {
                'timestamp': int(datetime(int(date[2]), int(date[1]), int(date[0])).timestamp()),
                'descripcion': desc,
                'medio': medio.upper(),
                'parametro': cantidad
            }

            if calc_points(newlog) == 1:
                await add_log(self.db, ctx.author.id, newlog)
            elif calc_points(newlog) == 0:
                await ctx.send("LIBRO" + "MANGA" + "VN" + "ANIME" +
                            "LECTURA" + "TIEMPOLECTURA" + "ESCUCHA")
            elif calc_points(newlog) == -1:
                await ctx.send("Solo números por favor.")
            elif calc_points(newlog) == -2:
                await ctx.send("Me temo que esa cantidad de inmersión no es humana así que no puedo registrarla.")

    @ commands.command()
    async def log(self, ctx, medio, cantidad, desc):
        if ctx.author.id==admin_user_id:
            if(not await check_user(self.db, ctx.author.id)):
                await create_user(self.db, ctx.author.id, "alexay7")

            newlog = {
                'timestamp': int(datetime.today().timestamp()),
                'descripcion': desc,
                'medio': medio.upper(),
                'parametro': cantidad
            }

            if calc_points(newlog) == 1:
                await add_log(self.db, ctx.author.id, newlog)
            elif calc_points(newlog) == 0:
                await ctx.send("LIBRO" + "MANGA" + "VN" + "ANIME" +
                            "LECTURA" + "TIEMPOLECTURA" + "ESCUCHA")
            elif calc_points(newlog) == -1:
                await ctx.send("Eres tonto o que te pasa? No ves que aquí solo puede ir un número.")
            elif calc_points(newlog) == -2:
                await ctx.send("Me temo que esa cantidad de inmersión no es humana así que no puedo registrarla.")


def setup(bot):
    bot.add_cog(Logs(bot))
