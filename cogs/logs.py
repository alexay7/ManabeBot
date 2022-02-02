"""Cog responsible for immersion logs."""

from pymongo import MongoClient,errors
import os
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
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

async def get_user_points(db,userid,timelapse):
    logs = await get_user_logs(db,userid,timelapse)
    total=0
    for log in logs:
        total+=log["puntos"]
    return total

async def get_user_logs(db,userid,timelapse):
    users = db.users
    if timelapse=="ALL":
        # Get all the logs from the user and compute the points
        result = users.find_one({"userId":userid},{"logs"})
        return result["logs"]
        
    elif timelapse=="WEEK":
        # Get the logs from 7 days ago until today
        start = int((datetime.today()-timedelta(weeks=1)).timestamp())
        end = int(datetime.today().timestamp())
        result = users.aggregate([
            {
                "$match":{
                "userId":userid
            }
            },{
                "$project": {
                    "logs": {
                        "$filter": {
                            "input": "$logs",
                            "as": "log",
                            "cond": {"$and": [
                                {"$gte": ["$$log.timestamp", start]},
                                {"$lte": ["$$log.timestamp", end]},
                                {"userId":userid}
                            ]}
                        }
                    }
                }
            }
        ])
        for elem in result:
            print(elem)
            # Only one document should be found so no problem returning data
            return elem["logs"]
    else:
        # Get the logs from the current month
        start = int((datetime(datetime.today().year,datetime.today().month,1)).timestamp())
        end = int(datetime.today().timestamp())
        result = users.aggregate([
            {
                "$match":{
                "userId":userid
            }
            },{
                "$project": {
                    "logs": {
                        "$filter": {
                            "input": "$logs",
                            "as": "log",
                            "cond": {"$and": [
                                {"$gte": ["$$log.timestamp", start]},
                                {"$lte": ["$$log.timestamp", end]},
                                {"userId":userid}
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
    users.update_one(
        {'userId': userid},
        {'$push': {"logs": log}}
    )

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

    @commands.command()
    async def leaderboard(self,ctx,timelapse):
        leaderboard=[]
        users = self.db.users.find({},{"userId","username"})
        for user in users:
            leaderboard.append({
                "username":user["username"],
                "points":await get_user_points(self.db,user["userId"],timelapse.upper())
            })
            print(sorted(leaderboard,key=lambda x: x["points"],reverse=True))

    @ commands.command()
    async def backfill(self, ctx, fecha, medio, cantidad, desc):
        if ctx.author.id==admin_user_id or True:
            if(not await check_user(self.db, ctx.author.id)):
                await create_user(self.db, ctx.author.id, "alexay7")

            date = fecha.split("/")
            datets=int(datetime(int(date[2]), int(date[1]), int(date[0])).timestamp())
            if(datetime.today().timestamp()-datets<0):
                await ctx.send("No puedes inmersar en el futuro.")
            newlog = {
                'timestamp': datets,
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

    @commands.command()
    async def me(self,ctx,timelapse):
        if ctx.author.id==admin_user_id or True:
            if(not await check_user(self.db, ctx.author.id)):
                ctx.send("No tienes ningún log.")
                return
            logs = await get_user_logs(self.db,ctx.author.id,timelapse.upper())
            points={
                "book":0,
                "manga":0,
                "anime":0,
                "vn":0,
                "read":0,
                "readtime":0,
                "listentime":0,
                "total":0
            }
            for log in logs:
                if log["medio"]=="LIBRO":
                    points["book"]+=log["puntos"]
                elif log["medio"]=="MANGA":
                    points["manga"]+=log["puntos"]
                elif log["medio"]=="ANIME":
                    points["anime"]+=log["puntos"]
                elif log["medio"]=="VN":
                    points["vn"]+=log["puntos"]
                elif log["medio"]=="LECTURA":
                    points["read"]+=log["puntos"]
                elif log["medio"]=="TIEMPOLECTURA":
                    points["readtime"]+=log["puntos"]
                elif log["medio"]=="ESCUCHA":
                    points["listentim"]+=log["puntos"]
                points["total"]+=log["puntos"]
            await ctx.send(points)


    @commands.command()
    async def log(self, ctx, medio, cantidad, desc):
        if ctx.author.id==admin_user_id or True:
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
