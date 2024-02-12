from helpers.mongo import logs_db


async def check_user(userid):
    users = logs_db.users
    return users.count_documents({'userId': userid}) > 0


async def create_user(userid, username):
    users = logs_db.users
    newuser = {
        'userId': userid,
        'username': username,
        'lastlog': -1
    }
    users.insert_one(newuser)

    divisions = logs_db.divisions
    newdivision = {
        'userId': userid,
        'division': 1
    }
    divisions.insert_one(newdivision)


async def find_user(id):
    users = logs_db.users
    return users.find_one({"userId": int(id)})
