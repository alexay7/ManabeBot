import discord

from datetime import datetime
from discord import Interaction
from discord.ui.select import Select

from helpers.general import intToMonth
from helpers.views import prepare_response, select_option, create_error_embed
from helpers.immersion.logs import MEDIA_TYPES, get_best_user_of_range, get_media_element


async def mvp_command(medio, ano):
    output = ""
    if ano != "TOTAL":
        current_month = datetime.today().month
        domain = range(1, current_month+1 if ano ==
                       datetime.today().year else 13)
        for x in domain:
            winner = await get_best_user_of_range(medio, f"{ano}/{x}")
            if not (winner is None):
                output += f"**{intToMonth(x)}:** {winner['username']} - {winner['points']} puntos"
                if medio.upper() in MEDIA_TYPES:
                    output += f" -> {get_media_element(winner['parameters'],medio.upper())}\n"
                else:
                    output += "\n"
        title = f"🏆 Usuarios del mes ({ano})"
        if medio.upper() in MEDIA_TYPES:
            title += f" [{medio.upper()}]"
    else:
        # Iterate from 2020 until current year
        end = datetime.today().year
        domain = range(2020, end + 1)
        for x in domain:
            winner = await get_best_user_of_range(medio, f"{x}")
            if not (winner is None):
                output += f"**{x}:** {winner['username']} - {winner['points']} puntos"
                if medio.upper() in MEDIA_TYPES:
                    output += f" -> {get_media_element(winner['parameters'],medio.upper())}\n"
                else:
                    output += "\n"
        title = f"🏆 Usuarios del año"
        if medio.upper() in MEDIA_TYPES:
            title += f" [{medio.upper()}]"
    if output:
        embed = discord.Embed(title=title, color=0xd400ff)
        embed.add_field(name="---------------------",
                        value=output, inline=True)
    else:
        return {"embed": create_error_embed("No existen datos"), "view": MVPView(medio, ano)}

    return {"embed": embed, "view": MVPView(medio, ano)}


class MVPView(discord.ui.View):
    def __init__(self, medio, ano):
        super().__init__()

        # Make default the medio selected in the first select
        medio_select: Select = self.get_item("medio_select")

        medio_options = medio_select.options

        # Remove all default options
        for option in medio_options:
            if option.label == medio:
                option.default = True
            else:
                option.default = False

        # Make default the year selected in the second select
        year_select: Select = self.get_item("year_select")

        year_options = year_select.options

        # Remove all default options
        for option in year_options:
            if option.label == str(ano):
                option.default = True
            else:
                option.default = False

    @discord.ui.select(
        row=0,
        options=[discord.SelectOption(
            label=media_type, value=media_type) for media_type in MEDIA_TYPES]+[discord.SelectOption(label="Selecciona un medio", value="TOTAL", default=True)],
        placeholder="Selecciona un medio",
        custom_id="medio_select"
    )
    async def select_callback(self, select: Select, interaction: Interaction):
        year_select: Select = self.children[1]
        if len(year_select.values) > 0:
            year = year_select.values[0]
        else:
            year = "TOTAL"

        medio = select.values[0]

        message = await prepare_response(interaction, self)

        response = await mvp_command(medio, year)

        self.enable_all_items()

        year_select = self.get_item("year_select")

        select_option(select, medio)

        await message.edit(embed=response["embed"], view=self)

    @discord.ui.select(
        row=1,
        options=[discord.SelectOption(
            label=str(x), value=str(x)) for x in range(2020, datetime.today().year + 1)]+[discord.SelectOption(label="Selecciona un año", value="TOTAL", default=True)],
        placeholder="Selecciona un año",
        custom_id="year_select"
    )
    async def select_callback_1(self, select: Select, interaction: Interaction):
        medio_select: Select = self.children[0]

        if len(medio_select.values) > 0:
            medio = medio_select.values[0]
        else:
            medio = "TOTAL"

        year = select.values[0]

        message = await prepare_response(interaction, self)

        response = await mvp_command(medio, year)

        self.enable_all_items()

        select_option(select, year)

        await message.edit(embed=response["embed"], view=self)
