import discord

from discord.ext.pages import Paginator
from datetime import datetime
from discord import Interaction
from discord.ui.select import Select

from helpers.immersion.logs import MEDIA_TYPES, get_media_element, get_user_logs
from helpers.immersion.users import check_user
from helpers.views import create_error_embed, select_option


async def logs_command(authorId, periodo, medio):
    if await check_user(int(authorId)) is False:
        return {"embed": create_error_embed("No se han encontrado logs"), "view": LogsView()}

    result = await get_user_logs(int(authorId), periodo, medio)
    sorted_res = sorted(result, key=lambda x: x["timestamp"], reverse=True)

    output = [
        "ID LOG ║ FECHA: MEDIO CANTIDAD -> PUNTOS: DESCRIPCIÓN || TIEMPO || CARACTERES\n═══════════════════════════════════════════════════\n"]
    overflow = 0
    for log in sorted_res:
        extra = ""

        if "bonus" in log and log["bonus"]:
            extra = " (Club AJR)"

        timestring = datetime.fromtimestamp(
            log["timestamp"]).strftime('%d/%m/%Y')
        line = f"#{log['id']} ║ {timestring}: {log['medio']}{extra} {get_media_element(log['parametro'],log['medio'])} -> {log['puntos']} puntos: {log['descripcion']}\n"
        if "tiempo" in log:
            line = line.replace(
                "\n", f" || tiempo: {get_media_element(log['tiempo'],'VIDEO')}\n")
        if "caracteres" in log:
            line = line.replace(
                "\n", f" || caracteres: {get_media_element(log['caracteres'],'LECTURA')}\n")
        if len(output[overflow]) + len(line) < 1000:
            output[overflow] += line
        else:
            overflow += 1
            output.append(line)
    if len(output[0]) > 0:
        pages = []
        for page in output:
            pages.append(f"```{page}```")
        return {"pages": pages, "view": LogsView(medio=medio, userId=authorId, periodo=periodo)}
    else:
        return {"embed": create_error_embed("No se han encontrado logs"), "view": LogsView(medio=medio, userId=authorId, periodo=periodo)}


class LogsView(discord.ui.View):
    def __init__(self, medio="TOTAL", userId=None, periodo="TOTAL"):
        super().__init__()

        self.userId = userId
        self.periodo = periodo

        medio_select = self.get_item("medio")
        select_option(medio_select, medio)

    @discord.ui.select(
        row=1,
        options=[discord.SelectOption(label="TOTAL", value="TOTAL", default=True)]+[discord.SelectOption(
            label=media_type, value=media_type) for media_type in MEDIA_TYPES],
        placeholder="TOTAL",
        custom_id="medio"
    )
    async def select_callback(self, select: Select, interaction: Interaction):
        medio = select.values[0]

        await interaction.response.defer()

        await interaction.delete_original_response()

        response = await logs_command(self.userId, self.periodo, medio)

        select_option(select, medio)

        paginator = Paginator(
            pages=response["pages"], custom_view=self)

        await paginator.respond(interaction)
