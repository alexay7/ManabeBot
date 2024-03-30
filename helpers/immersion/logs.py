import calendar
import csv
import json
import math

from datetime import datetime, timedelta
from pymongo import collection
from helpers.mongo import logs_db

MONTHS = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
          "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

MEDIA_TYPES = ["ANIME", "AUDIO", "LECTURA", "LIBRO",
               "MANGA", "OUTPUT", "TIEMPOLECTURA", "VIDEO", "VN"]

MEDIA_TYPES_ENGLISH = {"BOOK": "LIBRO", "READING": "LECTURA",
                       "READTIME": "TIEMPOLECTURA", "LISTENING": "AUDIO"}

TIMESTAMP_TYPES = ["TOTAL", "MES", "SEMANA", "HOY"]


def get_start_end_from_timestamp(timelapse):
    if timelapse in MONTHS:
        year = year if year else datetime.now().year
        month = MONTHS.index(timelapse) + 1
        timelapse = f"{year}/{month}"

    if timelapse == "SEMANA":
        start = int((datetime.today() - timedelta(weeks=1)
                     ).replace(hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())
        # SEVEN-DAY LOGS OF A MEDIA TYPE FROM USER

    elif timelapse == "MES":
        start = int(
            (datetime(datetime.today().year, datetime.today().month, 1)).replace(hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())

    elif timelapse == "HOY":
        start = int(datetime.today().replace(
            hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())
    elif len(timelapse.split("-")) == 1:
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
    else:
        dates = timelapse.split("-")
        start_split = dates[0].split("/")
        end_split = dates[1].split("/")
        try:
            start = int(
                datetime(int(start_split[2]), int(start_split[1]), int(start_split[0])).timestamp())
            end = int(
                datetime(int(end_split[2]), int(end_split[1]), int(end_split[0])).timestamp())
        except:
            return ""
    return start, end


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
    if media in {"TIEMPOLECTURA", "AUDIO", "VIDEO", "OUTPUT"}:
        if int(num) < 60:
            return f"{int(num)%60} minutos"
        elif int(num) < 120:
            return f"1 hora y {int(num)%60} minutos"
        return f"{int(int(num)/60)} horas y {int(num)%60} minutos"
    if media == "CLUB Manabe":
        return f"{int(num)} puntos"


def calc_media(points):
    # Mejor prevenir que curar
    result = {
        "libro": points,
        "manga": points * 5,
        "vn": points * 350,
        "anime": points / 45 * 100 / 24,
        "lectura": points * 350,
        "tiempolectura": points / 45 * 100,
        "output": points/45*100,
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
    elif len(timelapse.split("-")) > 1:
        tiempo = f"desde el {timelapse.split('-')[0]} hasta el {timelapse.split('-')[1]}"
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
    elif media == "CARACTERES":
        medio = "de caracteres"
    return f"{tiempo} {medio}"


async def bonus_log(log_id, user_id):
    logs: collection.Collection = logs_db.logs
    old_log = logs.find_one(
        {"userId": user_id, "id": int(log_id), '$or': [
            {
                'bonus': False
            }, {
                'bonus': {
                    '$exists': False
                }
            }
        ]})

    print(old_log)

    if not old_log:
        return -1

    new_points = old_log["puntos"] * 1.4
    logs.update_one({"userId": user_id, "id": int(log_id)},
                    {"$set": {"bonus": True, "puntos": new_points}})
    return new_points


async def unbonus_log(log_id, user_id):
    logs: collection.Collection = logs_db.logs
    old_log = logs.find_one(
        {"userId": user_id, "id": int(log_id), "bonus": True})

    if not old_log:
        return -1

    new_points = old_log["puntos"] / 1.4
    logs.update_one({"userId": user_id, "id": int(log_id)},
                    {"$set": {"bonus": False, "puntos": new_points}})
    return new_points


async def add_log(userid, log, username):
    logs = logs_db.logs
    users = logs_db.users
    user = users.find_one({'userId': userid})
    log["id"] = user["lastlog"] + 1

    users.update_one(
        {'userId': userid},
        {'$set': {"lastlog": log["id"], "username": username}}
    )

    log["userId"] = userid

    logs.insert_one(log)

    return log["id"]


async def get_user_logs(userid, timelapse, media=None, year=None):
    logs = logs_db.logs
    if timelapse in MONTHS:
        year = year if year else datetime.now().year
        month = MONTHS.index(timelapse) + 1
        timelapse = f"{year}/{month}"

    if timelapse == "TOTAL":
        if media in MEDIA_TYPES:
            # ALL LOGS OF A MEDIA TYPE FROM USER
            result = logs.find({"medio": media, "userId": userid})
            if result:
                return result
        else:
            # ALL LOGS OF ALL MEDIA TYPES FROM USER
            result = logs.find({"userId": userid})
            if result:
                return result
        return ""

    if timelapse == "SEMANA":
        start = int((datetime.today() - timedelta(weeks=1)
                     ).replace(hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())
        # SEVEN-DAY LOGS OF A MEDIA TYPE FROM USER

    elif timelapse == "MES":
        start = int(
            (datetime(datetime.today().year, datetime.today().month, 1)).replace(hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())

    elif timelapse == "HOY":
        start = int(datetime.today().replace(
            hour=0, minute=0, second=0).timestamp())
        end = int(datetime.today().replace(
            hour=23, minute=59, second=59).timestamp())
    elif len(timelapse.split("-")) == 1:
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
    else:
        dates = timelapse.split("-")
        start_split = dates[0].split("/")
        end_split = dates[1].split("/")
        try:
            start = int(
                datetime(int(start_split[2]), int(start_split[1]), int(start_split[0])).timestamp())
            end = int(
                datetime(int(end_split[2]), int(end_split[1]), int(end_split[0])).timestamp())
        except:
            return ""

    query = {"$and": [{"timestamp": {"$gte": start}}, {
        "timestamp": {"$lte": end}}], "userId": userid}

    if media in MEDIA_TYPES:
        query["medio"] = media

    result = logs.find(query)

    if result:
        return result
    return ""


async def get_total_immersion_of_month(timelapse):
    logs = logs_db.logs
    split_time = timelapse.split("/")
    month = int(split_time[1])
    year = int(split_time[0])
    start = int(
        (datetime(int(year), month, 1)).replace(hour=0, minute=0, second=0).timestamp())
    if month + 1 > 12:
        month = 0
        year += 1
    end = int(
        (datetime(int(year), month + 1, 1) - timedelta(days=1)).replace(hour=23, minute=59, second=59).timestamp())

    result = logs.find(
        {"$and": [{"timestamp": {"$gte": start}}, {"timestamp": {"$lte": end}}]})

    total = 0
    if result:
        for log in result:
            # Only one document should be found so no problem returning data
            total += log["puntos"]

    return total


async def get_total_parameter_of_media(media, userid):
    # ALL LOGS OF A MEDIA TYPE FROM USER
    logs = await get_user_logs(userid, "TOTAL")
    total_param = 0
    for log in logs:
        if log["medio"] == media:
            total_param += int(log["parametro"])
    return total_param


async def remove_log(userid, logid):
    logs: collection.Collection = logs_db.logs
    found_log = logs.delete_one({"userId": userid, "id": int(logid)})
    if found_log.deleted_count > 0:
        return 1
    return 0


async def get_all_logs_in_day(userid, day):
    logs = logs_db.logs
    day_logs = logs.count_documents({
        'userId': userid,
        'timestamp': {'$gte': datetime.combine(day, datetime.min.time()).timestamp(),
                      '$lte': datetime.combine(day, datetime.max.time()).timestamp()}
    })
    return day_logs


async def get_logs_per_day_in_month(userid, month, year):
    logs = logs_db.logs
    month_logs = logs.aggregate([
        {
            '$match': {
                'userId': userid,
                'timestamp': {
                    '$gte': datetime(int(year), int(month), 1).timestamp(),
                    '$lte': datetime(int(year), int(month), calendar.monthrange(int(year), int(month))[1]).timestamp()
                }
            }
        }, {
            '$group': {
                '_id': {
                    '$dayOfMonth': {
                        'date': {
                            '$toDate': {
                                '$multiply': ['$timestamp', 1000]
                            }
                        },
                        'timezone': 'Europe/Madrid'
                    }
                },
                'count': {
                    '$sum': "$puntos"
                }
            }
        }
    ])
    return month_logs


async def get_logs_per_day_in_year(userid, year):
    logs = logs_db.logs
    year_logs = logs.aggregate([
        {
            '$match': {
                'userId': userid,
                'timestamp': {
                    '$gte': datetime(int(year), 1, 1).timestamp(),
                    '$lte': datetime(int(year), 12, 31).timestamp()
                }
            }
        }, {
            '$group': {
                '_id': {
                    '$dayOfYear': {
                        'date': {
                            '$toDate': {
                                '$multiply': ['$timestamp', 1000]
                            }
                        },
                        'timezone': 'Europe/Madrid'
                    }
                },
                'count': {
                    '$sum': "$puntos"
                }
            }
        }
    ])
    return year_logs


async def get_last_log(userid):
    logs = logs_db.logs
    newest_log = logs.find({"userId": userid}).sort("_id", -1).limit(1)
    if newest_log:
        return newest_log[0]


async def remove_last_log(userid):
    logs = logs_db.logs
    try:
        newest_log = logs.find({"userId": userid}).sort("_id", -1).limit(1)
        last_log_id = f"{newest_log[0]['id']}"
        if newest_log:
            logs.delete_one({"_id": newest_log[0]["_id"]})
            return 1, last_log_id
    except:
        return 0


async def get_user_data(userid, timelapse, media="TOTAL", chars=False, year=None):
    logs = await get_user_logs(userid, timelapse, media, year)
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
        "TOTAL": 0
    }

    for log in logs:
        log_points = log["puntos"]
        if "bonus" in log and log["bonus"] and media != "TOTAL":
            log_points = log["puntos"]/1.4

        if chars:
            if log["medio"] in ["LECTURA", "VN"]:
                parameters["TOTAL"] += int(log["parametro"])
            else:
                if "caracteres" in log:
                    parameters["TOTAL"] += int(log["caracteres"])
            points[log["medio"]] += log_points
            points["TOTAL"] += log_points
        else:
            points[log["medio"]] += log_points
            parameters[log["medio"]] += int(log["parametro"])
            points["TOTAL"] += log_points

    return points, parameters


async def get_best_user_of_range(media, timelapse):
    aux = None
    # Get users that have logs in that range
    users = await get_users_that_logged_in_range(timelapse)

    points = 0
    tot_parameters = 0
    for user in users:
        userpoints, parameters = await get_user_data(user["userId"], timelapse, media)
        newuser = {
            "id": user["userId"],
            "username": user["username"],
            "points": round(userpoints[media], 2),
            "parameters": parameters[media]
        }
        if media == "TOTAL":
            if newuser["points"] > points:
                points = round(newuser["points"], 2)
                aux = newuser
        else:
            if newuser["parameters"] > tot_parameters:
                tot_parameters = round(newuser["parameters"], 2)
                aux = newuser
    if not (aux is None):
        return aux
    return None


async def get_users_that_logged_in_range(timelapse):
    start, end = get_start_end_from_timestamp(timelapse)

    users = logs_db.logs.aggregate([
        {
            '$match': {
                'timestamp': {
                    '$gte': start,
                    '$lte': end
                },
            }
        }, {
            '$lookup': {
                'from': 'users',
                'localField': 'userId',
                'foreignField': 'userId',
                'as': 'user'
            }
        }, {
            '$unwind': '$user'
        }, {
            '$group': {
                '_id': '$user'
            }
        }, {
            '$project': {
                'userId': '$_id.userId',
                'username': '$_id.username'
            }
        }
    ])

    return users


async def get_sorted_ranking(timelapse, media, caracteres=False, year=None, division=None, user_ids=[]):
    leaderboard = []
    if division:
        users = logs_db.users.aggregate([
            {
                '$lookup': {
                    'from': 'divisions',
                    'localField': 'userId',
                    'foreignField': 'userId',
                    'as': 'userWithDivision'
                }
            }, {
                '$match': {
                    'userWithDivision.division': division
                }
            }
        ])
    elif user_ids:
        users = logs_db.users.find({"userId": {"$in": user_ids}})
    else:
        users = logs_db.users.find({})

    counter = 0
    for user in users:
        points, parameters = await get_user_data(
            user["userId"], timelapse, media, caracteres, year)
        leaderboard.append({
            "username": user["username"],
            "id": user["userId"],
            "points": points["TOTAL"],
            "parameters": parameters[media]})
        if media in MEDIA_TYPES or media == "CARACTERES":
            leaderboard[counter]["param"] = parameters[media]
        counter += 1
    if caracteres or media != "TOTAL":
        return sorted(
            leaderboard, key=lambda x: x["parameters"], reverse=True)
    else:
        return sorted(
            leaderboard, key=lambda x: x["points"], reverse=True)


async def get_logs_animation(month, day, year, users, firsts):
    # Esta función va a tener como parámetro el día, lo pasará a la función get logs y a partir de ahí generará el ranking pertinente
    header = []
    data = []
    header.append("date")

    monthly_ranking = await get_sorted_ranking(MONTHS[int(month) - 1], "TOTAL", False, year, user_ids=users)
    userlist = []
    for elem in monthly_ranking:
        if elem["points"] != 0:
            userlist.append(elem["username"])
    for user in userlist:
        header.append(user)

    aux = [-1 for i in range(len(header))]
    # First value is the name of the previous month
    aux[0] = f"{month}/{1}/{year}"
    for user in monthly_ranking:
        for elem in firsts:
            if elem["userId"] == user["id"]:
                aux[header.index(user["username"])] = 0

    data.append(aux)

    total = dict()
    date = datetime.today()
    # if int(day) > date.day:
    #     day = date.day
    counter = 1
    while counter < int(day) + 1:
        total[str(counter)] = await get_sorted_ranking(
            f"{year}/{month}/{counter}", "TOTAL", user_ids=users)
        aux = [0 for i in range(len(header))]
        aux[0] = f"{month}/{counter}/{year}"
        for user in total[str(counter)]:
            if user["points"] != 0:
                aux[header.index(user["username"])] = user["points"]
        counter += 1
        data.append(aux)
    with open('temp/test.csv', 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)
    return


def compute_points(log, bonus=False):
    # Mejor prevenir que curar
    if log["medio"] not in MEDIA_TYPES:
        return 0
    if int(log["parametro"]) > 9999999:
        return -2
    if log["medio"] == "LIBRO":
        puntos = round(int(log["parametro"]), 4)
    elif log["medio"] == "MANGA":
        puntos = round(int(log["parametro"]) / 5, 4)
    elif log["medio"] == "VN":
        puntos = round(int(log["parametro"]) / 350, 4)
    elif log["medio"] == "ANIME":
        puntos = round(int(log["parametro"]) * 45 / 100 * 24, 4)
    elif log["medio"] == "LECTURA":
        puntos = round(int(log["parametro"]) / 350, 4)
    elif log["medio"] == "TIEMPOLECTURA":
        puntos = round(int(log["parametro"]) * 45 / 100, 4)
    elif log["medio"] == "AUDIO":
        puntos = round(int(log["parametro"]) * 45 / 100, 4)
    elif log["medio"] == "OUTPUT":
        puntos = round(int(log["parametro"]) * 45 / 100, 4)
    elif log["medio"] == "VIDEO":
        puntos = round(int(log["parametro"]) * 45 / 100, 4)

    if bonus:
        puntos = round(puntos * 1.4, 2)

    log["puntos"] = puntos

    return puntos


def get_immersion_level(parameter):
    y = parameter

    nivel = 0
    while y >= 0:
        puntos_nivel_siguiente = 100 * math.log2(nivel + 1) + 100
        if y >= puntos_nivel_siguiente:
            nivel += 1
            y -= puntos_nivel_siguiente
        else:
            break
    if y > 2000:
        y = 2000
    return nivel


def get_param_for_media_level(level, medio):
    with open("config/achievements.json") as json_file:
        levels_dict = json.load(json_file)

    level_points = levels_dict[medio]
    accumulated_points = 0

    for i in range(1, level + 1):
        if i <= 10:
            accumulated_points += level_points[0]
        elif i <= 25:
            accumulated_points += level_points[1]
        elif i <= 50:
            accumulated_points += level_points[2]
        elif i <= 75:
            accumulated_points += level_points[3]
        elif i <= 100:
            accumulated_points += level_points[4]
        else:
            accumulated_points += level_points[5]

    if accumulated_points > 1:
        return accumulated_points
    else:
        return 1


def get_media_level(parametro, medio):
    with open("config/achievements.json") as json_file:
        levels_dict = json.load(json_file)

    required_points = levels_dict[medio]
    total_points = 0
    for i in range(1, 101):
        if i < 11:
            required = required_points[0]
        elif i < 26:
            required = required_points[1]
        elif i < 51:
            required = required_points[2]
        elif i < 76:
            required = required_points[3]
        elif i < 101:
            required = required_points[4]
        else:
            required = required_points[5]

        total_points += required
        if parametro < total_points:
            return i - 1
    return 100


async def get_log_by_id(userid, logid):
    logs = logs_db.logs
    return logs.find_one({"userId": userid, "id": int(logid)})


def check_max_immersion(parameter: int, media: str):
    if media == "LIBRO":
        return 2000 >= parameter
    elif media == "MANGA":
        return 10000 >= parameter
    elif media in ["VN", "LECTURA"]:
        return 720000 >= parameter
    elif media == "ANIME":
        return 60 >= parameter
    elif media in ["TIEMPOLECTURA", "AUDIO", "OUTPUT", "VIDEO"]:
        return 1440 >= parameter
    return


def update_log(logid, log):
    logs = logs_db.logs
    # Only update the parameteres that exist in the new log
    logs.update_one({"_id": logid}, {"$set": log})


def ordenar_logs(user_id):
    logs = logs_db.logs
    found_logs = logs.find({'userId': user_id})
    newlogs = sorted(found_logs, key=lambda d: d['timestamp'])
    counter = 1
    for elem in newlogs:
        logs.update_one({"_id": elem["_id"]}, {"$set": {"id": counter}})
        counter = counter + 1

    users = logs_db.users

    users.update_one({"userId": user_id}, {
        "$set": {"lastlog": len(newlogs)}})
