from helpers.mongo import logs_db


def calculate_promotions_demotions(high_div, low_div):
    # The parameter high_div contains all the users from the first division and their points sorted
    # The parameter low_div contains all the users from the second division and their points sorted

    # This function will compare the first user from the last division with the last user from the first division, and if the first user has more points than the last user, it will promote the first user and demote the last user. This will continue until the first user has less points than the last user, or until there are no more users in the first division.

    # The function will return the users that have been promoted and demoted

    promotions = []
    demotions = []

    for user in low_div:
        if (len(promotions) == 10):
            break
        if len(high_div) == 0 or user["points"] > high_div[-1]["points"]:
            promotions.append(user)
            if len(high_div):
                demotions.append(high_div[-1])
                high_div.pop(-1)
        else:
            break

    return promotions, demotions


def ascend_users(users):
    divisions = logs_db.divisions
    for user in users:
        user_division = divisions.find_one({"userId": user["id"]})
        if user_division == 1:
            return

        divisions.update_one({"userId": user["id"]}, {
                             "$set": {"division": user_division["division"] - 1}})


def demote_users(users):
    divisions = logs_db.divisions
    for user in users:
        user_division = divisions.find_one({"userId": user["id"]})
        if user_division == 5:
            return

        divisions.update_one({"userId": user["id"]}, {
                             "$set": {"division": user_division["division"] + 1}})


def get_user_division(userId):
    divisions = logs_db.divisions
    user_division = divisions.find_one({"userId": userId})
    return user_division["division"]


def save_division_results(ranking, month, year):
    historic = logs_db.historic

    current_division_data = []
    for user in ranking:
        user_division = get_user_division(user["id"])
        current_division_data.append({
            "userId": user["id"],
            "points": user["points"],
            "division": user_division
        })

    historic.insert_one({
        "month": month,
        "year": year,
        "division": current_division_data
    })
