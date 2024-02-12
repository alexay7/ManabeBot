import discord
import helpers.mongo as mongo

from dateutil.relativedelta import relativedelta
from datetime import datetime

from helpers.views import prepare_response, select_option
from helpers.immersion.graphs import generate_graph
from helpers.immersion.logs import MONTHS, get_ranking_title, get_user_logs


async def progreso_command(user, ano, total):
    results = {}
    if ano == "TOTAL":
        data = mongo.db.logs.find(
            {"userId": user.id}).sort("timestamp", 1).limit(1)
        firstlog = data[0]
        start = datetime.fromtimestamp(
            firstlog['timestamp']).replace(day=1)
        end = datetime.now().replace()
        steps = (end.year - start.year) * 12 + end.month - start.month + 1
        real_months = steps
    else:
        if int(ano) < 1000:
            ano = "20" + ano
        start = datetime(year=int(ano), month=1, day=1)
        end = datetime(year=int(ano), month=12, day=31)
        steps = 12
    i = 0
    total = 0
    real_months = steps
    best_month = {
        'month': 0,
        'year': 0,
        'points': 0
    }
    while i < steps:
        begin = (start + relativedelta(months=i)).replace(day=1)
        logs = await get_user_logs(mongo.db, user.id, f"{begin.year}/{begin.month}")
        i += 1

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
        }
        local_total = 0
        for log in logs:

            log_points = log["puntos"]
            if "bonus" in log and log["bonus"]:
                log_points = log["puntos"]/1.4

            points[log["medio"]] += log_points
            local_total += log_points
            total += log_points

        if local_total == 0:
            real_months -= 1
        if local_total > best_month["points"]:
            best_month["month"] = begin.month
            best_month["year"] = begin.year
            best_month["points"] = local_total
        results[f"{begin.year}/{begin.month}"] = points
    if real_months > 0:
        media = total / real_months
        normal = discord.Embed(
            title=f"Vista {get_ranking_title(ano,'ALL')}", color=0xeeff00)
        normal.add_field(
            name="Usuario", value=user.name, inline=False)
        normal.add_field(name="Media en el periodo",
                         value=f"{round(media, 2)} puntos", inline=True)
        normal.add_field(
            name="Mejor mes", value=f"{MONTHS[best_month['month']-1].capitalize()} del {best_month['year']} con {round(best_month['points'],2)} puntos", inline=True)
        bardoc = generate_graph(results, "progress")
        normal.set_image(url="attachment://image.png")
        return {"embed": normal, "file": bardoc, "view": ProgresoView(user, ano, total)}


class ProgresoView(discord.ui.View):
    def __init__(self, user, ano, total):
        super().__init__()

        self.user = user
        self.ano = "TOTAL" if total else ano

        # Make default the year selected in the first select
        year_select = self.get_item("year_select")

        year_options = year_select.options

        # Remove all default options
        for option in year_options:
            if option.label == str(ano) or (option.label == "TOTAL" and ano == "TOTAL"):
                option.default = True
            else:
                option.default = False

    @discord.ui.select(
        row=0,
        options=[discord.SelectOption(label="TOTAL", value="TOTAL")]+[discord.SelectOption(
            label=str(x), value=str(x)) for x in range(2020, datetime.now().year+1)],
        placeholder="Selecciona un año",
        custom_id="year_select"
    )
    async def select_ano(self, select, interaction):
        ano = select.values[0]

        self.ano = ano

        message = await prepare_response(interaction, self)

        response = await progreso_command(self.user, self.ano, True if ano == "TOTAL" else False)

        self.enable_all_items()

        select_option(select, ano)

        await message.edit(embed=response["embed"], files=[response["file"]], view=self)
