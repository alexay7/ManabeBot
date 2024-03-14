import discord

from datetime import datetime
from discord import Interaction

from helpers.immersion.logs import get_immersion_level, get_media_element, get_media_level, get_user_logs


async def logros_command(user_id, user_name):
    logs = await get_user_logs(user_id, "TOTAL")
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
        "CLUB Manabe": 0
    }

    graphlogs = {}

    for log in logs:
        log_points = log["puntos"]
        if "bonus" in log and log["bonus"]:
            log_points = log["puntos"]/1.4
            bonus_points = log["puntos"]-log_points
            parameters["CLUB Manabe"] += bonus_points

        points[log["medio"]] += log_points
        parameters[log["medio"]] += int(log["parametro"])
        points["TOTAL"] += log_points
        logdate = str(datetime.fromtimestamp(
            log["timestamp"])).replace("-", "/").split(" ")[0]

        if logdate in graphlogs:
            graphlogs[logdate] += log_points
        else:
            graphlogs[logdate] = log_points

    output = "```"
    for key, value in parameters.items():
        current_level = get_media_level(value, key)
        if value > 0:
            output += f"-> Eres nivel {current_level+1} en {key} con un total de {get_media_element(value,key)}\n"

    title = f"🎌 Logros de inmersión de {user_name} 🎌"

    normal = discord.Embed(
        title=title, color=0xeeff00)
    normal.add_field(
        name="Usuario", value=f"{user_name} **[Lvl: {get_immersion_level(points['TOTAL'])}]**", inline=True)
    normal.add_field(name="Puntos Totales", value=round(
        points["TOTAL"], 2), inline=True)
    normal.add_field(name="Nivel por categorías",
                     value=f"{output}```", inline=False)

    return normal


class LogroView(discord.ui.View):
    def __init__(self, user):
        super().__init__()

        self.user = user

    @discord.ui.button(label="🏅 Ver tus logros", style=discord.ButtonStyle.primary)
    async def logros(self, button: discord.ui.Button, interaction: Interaction):
        embed = await logros_command(self.user.id, self.user.name)

        self.clear_items()

        await interaction.response.send_message(embed=embed, view=self)
