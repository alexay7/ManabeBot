import itertools
import discord
import math

from datetime import datetime
from discord import Interaction
from discord.ui.select import Select
from matplotlib import pyplot as plt

from helpers.views import prepare_response, select_option
from helpers.immersion.graphs import generate_graph
from helpers.immersion.logs import TIMESTAMP_TYPES, get_media_element, get_ranking_title, get_sorted_ranking, get_user_logs


async def me_command(usuario, periodo, graph):
    logs = await get_user_logs(usuario.id, periodo)

    if logs == "":
        return

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
        "TOTAL": 0,
        "CLUB AJR": 0
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
        "VIDEO": 0
    }

    graphlogs = {}

    output = ""
    hours = 0
    estimated_hours = 0
    for log in logs:
        log_points = log["puntos"]
        bonus_points = 0

        if "bonus" in log and log["bonus"]:
            log_points = log["puntos"]/1.4
            bonus_points = log["puntos"]-log_points
            points["CLUB AJR"] += bonus_points

        points[log["medio"]] += log_points
        parameters[log["medio"]] += int(log["parametro"])
        points["TOTAL"] += log["puntos"]
        logdate = str(datetime.fromtimestamp(
            log["timestamp"])).replace("-", "/").split(" ")[0]

        if logdate in graphlogs:
            graphlogs[logdate] += log_points
        else:
            graphlogs[logdate] = log_points

        if log["medio"] in ["VIDEO", "AUDIO", "TIEMPOLECTURA", "OUTPUT"]:
            hours += int(log["parametro"])/60
        elif "tiempo" in log:
            hours += log["tiempo"]/60
        elif log["medio"] == "ANIME":
            hours += int(log["parametro"])*24/60
        else:
            hours += log_points/27
            estimated_hours += log_points/27

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
        if points["OUTPUT"] > 0:
            output += f"**OUTPUT:** {get_media_element(parameters['OUTPUT'],'OUTPUT')} -> {round(points['OUTPUT'],2)} pts\n"
        if points["AUDIO"] > 0:
            output += f"**AUDIO:** {get_media_element(parameters['AUDIO'],'AUDIO')} -> {round(points['AUDIO'],2)} pts\n"
        if points["VIDEO"] > 0:
            output += f"**VIDEO:** {get_media_element(parameters['VIDEO'],'VIDEO')} -> {round(points['VIDEO'],2)} pts\n"
        if points["CLUB AJR"] > 0 and periodo != "TOTAL":
            output += f"**CLUB AJR:** {round(points['CLUB AJR'],2)} puntos\n"
    ranking = await get_sorted_ranking(periodo, "TOTAL")
    for user in ranking:
        if user["username"] == usuario.name:
            position = ranking.index(user)

    days = 0

    if periodo == "SEMANA":
        days = 7
    elif periodo == "MES":
        days = datetime.today().day

    normal = discord.Embed(
        title=f"Vista {get_ranking_title(periodo,'ALL')}", color=0xeeff00)
    normal.add_field(name="Usuario", value=usuario.name, inline=True)
    normal.add_field(name="Puntos", value=round(
        points["TOTAL"], 2), inline=True)
    normal.add_field(name="Posición ranking",
                     value=f"{position+1}º", inline=True)
    if estimated_hours > 0:
        value_text = f"{math.ceil(hours)} horas (de las cuales {math.ceil(estimated_hours)} son estimadas)"
    else:
        value_text = f"{math.ceil(hours)} horas"

    normal.add_field(name="Horas de inmersión",
                     value=value_text, inline=True)
    if days > 0:
        normal.add_field(
            name="Media diaria", value=f"{round(points['TOTAL']/days,2)}", inline=True)
    normal.add_field(name="Medios", value=output, inline=False)

    if graph == "SECTORES":
        piedoc = generate_graph(points, "piechart", total_points=round(
            points["TOTAL"], 2), position=f"{position+1}º")
        normal.set_image(url="attachment://image.png")

        # GRÁFICA DE SECTORES
        return {"embed": normal, "view": MeView(user=usuario, graph=graph, periodo=periodo), "file": piedoc}
    elif graph == "BARRAS":
        bardoc = generate_graph(graphlogs, "bars", periodo)
        normal.set_image(url="attachment://image.png")

        # GRÁFICA DE BARRAS
        return {"embed": normal, "view": MeView(user=usuario, graph=graph, periodo=periodo), "file": bardoc}
    elif graph == "VELOCIDAD":
        # Obtener los logs del usuario
        manga_logs = await get_user_logs(usuario.id, "TOTAL", "MANGA")
        read_logs = await get_user_logs(usuario.id, "TOTAL", "LECTURA")
        vn_logs = await get_user_logs(usuario.id, "TOTAL", "VN")
        logs = itertools.chain(manga_logs, read_logs, vn_logs)

        # Crear un conjunto de todos los meses para los que hay registros en cualquiera de los dos medios
        months = set()
        logs_by_medium_and_month = {"MANGA": {}, "LECTURA": {}, "VN": {}}
        for log in logs:
            if "tiempo" in log:
                date = datetime.fromtimestamp(log["timestamp"])
                month = date.strftime("%Y-%m")
                months.add(month)
                medium = log["medio"]
                if month not in logs_by_medium_and_month[medium]:
                    logs_by_medium_and_month[medium][month] = []
                logs_by_medium_and_month[medium][month].append(log)

        months = sorted(months)

        # Calcular la velocidad media por mes para cada medio
        speeds_by_medium_and_month = {"MANGA": {}, "LECTURA": {}, "VN": {}}
        for medium, logs_by_month in logs_by_medium_and_month.items():
            for month in months:
                if month not in logs_by_month:
                    logs_by_month[month] = []
                month_logs = logs_by_month[month]
                speeds = []
                for log in month_logs:
                    if log["tiempo"] > 0:
                        if medium == "MANGA" and "caracteres" in log.keys():
                            speed = int(log["caracteres"]) / \
                                log["tiempo"]*60
                            speeds.append(speed)
                        elif medium in ["LECTURA", "VN"]:
                            speed = (
                                int(log["parametro"])) / log["tiempo"]*60
                            speeds.append(speed)
                if speeds:
                    speeds_by_medium_and_month[medium][month] = sum(
                        speeds) / len(speeds)
                else:
                    speeds_by_medium_and_month[medium][month] = 0

        x_values_manga = list(speeds_by_medium_and_month["MANGA"].keys())
        y_values_manga = list(speeds_by_medium_and_month["MANGA"].values())

        x_values_lectura = list(
            speeds_by_medium_and_month["LECTURA"].keys())
        y_values_lectura = list(
            speeds_by_medium_and_month["LECTURA"].values())

        x_values_vn = list(speeds_by_medium_and_month["VN"].keys())
        y_values_vn = list(speeds_by_medium_and_month["VN"].values())

        for i in range(1, len(y_values_manga)):
            if y_values_manga[i] == 0:
                y_values_manga[i] = y_values_manga[i - 1]

        for i in range(1, len(y_values_lectura)):
            if y_values_lectura[i] == 0:
                y_values_lectura[i] = y_values_lectura[i - 1]

        for i in range(1, len(y_values_vn)):
            if y_values_vn[i] == 0:
                y_values_vn[i] = y_values_vn[i - 1]

        # Crear la gráfica
        if speeds_by_medium_and_month["MANGA"] and speeds_by_medium_and_month["LECTURA"]:
            fig, ax = plt.subplots(figsize=(10, 8))
            plt.plot(x_values_manga, y_values_manga, label="MANGA")
            plt.plot(x_values_lectura, y_values_lectura, label="LECTURA")
            plt.plot(x_values_vn, y_values_vn, label="VN")
            plt.xlabel("Mes")
            plt.ylabel("Caracters leidos por hora")
            plt.title(
                "Velocidad de lectura mensual para el usuario {}".format(usuario.name))
            plt.legend()
            fig.set_facecolor("#2F3136")
            ax.title.set_color('white')
            ax.set_facecolor('#36393f')
            ax.title.set_color('white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            plt.xticks(rotation=45)
            plt.savefig("temp/image.png")
            plt.close()
            file = discord.File("temp/image.png", filename="image.png")
            normal.set_image(url="attachment://image.png")

            # GRÁFICA DE VELOCIDAD
            return {"embed": normal, "view": MeView(user=usuario, graph=graph, periodo=periodo), "file": file}
    else:
        # SIN GRÁFICA
        return {"embed": normal, "view": MeView(user=usuario, graph=graph, periodo=periodo)}


class MeView(discord.ui.View):
    def __init__(self, user, graph, periodo):
        super().__init__()

        if graph == "SECTORES":
            self.get_item("SECTORES").disabled = True
        elif graph == "BARRAS":
            self.get_item("BARRAS").disabled = True
        elif graph == "VELOCIDAD":
            self.get_item("VELOCIDAD").disabled = True
        else:
            self.get_item("NONE").disabled = True

        self.graph = graph
        self.periodo = periodo
        self.user = user

    @discord.ui.button(label="🍰", style=discord.ButtonStyle.blurple, custom_id="SECTORES")
    async def pie_callbar(self, button: discord.Button, interaction: Interaction):
        self.graph = "SECTORES"

        message = await prepare_response(interaction, self)

        response = await me_command(self.user, self.periodo, "SECTORES")

        self.enable_all_items()

        button.disabled = True

        await message.edit(embed=response["embed"], files=[response["file"]], view=self)

    @discord.ui.button(label="📊", style=discord.ButtonStyle.blurple, custom_id="BARRAS")
    async def bars_callback(self, button: discord.Button, interaction: Interaction):
        self.graph = "BARRAS"

        message = await prepare_response(interaction, self)

        response = await me_command(self.user, self.periodo, "BARRAS")

        self.enable_all_items()

        button.disabled = True

        await message.edit(embed=response["embed"], files=[response["file"]], view=self)

    @discord.ui.button(label="📈", style=discord.ButtonStyle.blurple, custom_id="VELOCIDAD")
    async def speed_callback(self, button: discord.Button, interaction: Interaction):
        self.graph = "VELOCIDAD"

        message = await prepare_response(interaction, self)

        response = await me_command(self.user, self.periodo, "VELOCIDAD")

        self.enable_all_items()

        button.disabled = True

        await message.edit(embed=response["embed"], files=[response["file"]], view=self)

    # Botón para ninguna gráfica
    @discord.ui.button(label="🚫", style=discord.ButtonStyle.blurple, custom_id="NONE")
    async def none_callback(self, button: discord.Button, interaction: Interaction):
        self.graph = "NONE"

        message = await prepare_response(interaction, self)

        response = await me_command(self.user, self.periodo, "NONE")

        self.enable_all_items()

        button.disabled = True

        await message.edit(embed=response["embed"], view=self)

    @discord.ui.select(
        row=1,
        options=[discord.SelectOption(
            label=periodo, value=periodo) for periodo in TIMESTAMP_TYPES],
        placeholder="Selecciona un periodo"
    )
    async def select_callback(self, select: Select, interaction: Interaction):
        periodo = select.values[0]

        self.periodo = periodo

        message = await prepare_response(interaction, self)

        response = await me_command(self.user, periodo, self.graph)

        self.enable_all_items()

        select.disabled = False

        if self.graph == "SECTORES":
            self.get_item("SECTORES").disabled = True
        elif self.graph == "BARRAS":
            self.get_item("BARRAS").disabled = True
        elif self.graph == "VELOCIDAD":
            self.get_item("VELOCIDAD").disabled = True
        else:
            self.get_item("NONE").disabled = True

        select_option(select, periodo)

        await message.edit(embed=response["embed"], files=[response["file"]] if "file" in response else [], view=self)
