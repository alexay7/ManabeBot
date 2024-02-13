import discord

from discord import Interaction
from discord.ext.pages import Page, Paginator
from discord.ui.select import Select

from helpers.views import create_error_embed, select_option
from helpers.immersion.logs import MEDIA_TYPES, get_media_element, get_ranking_title, get_sorted_ranking


async def ranking_command(medio, periodo, chars):
    sortedlist = await get_sorted_ranking(periodo, medio, chars)

    # remove users with 0 points
    sortedlist = [user for user in sortedlist if (user["points"]
                                                  != 0) and (not chars or user["parameters"] != 0)]
    position = 1
    total_users = len(sortedlist)
    pages = []
    currpage = ""
    counter = 0
    for user in sortedlist[0:total_users]:
        counter += 1
        positiontext = str(position)+"º"
        if position == 1:
            positiontext = "🥇 "
        elif position == 2:
            positiontext = "🥈 "
        elif position == 3:
            positiontext = "🥉 "

        if chars:
            if user["parameters"] != 0:
                currpage += f"**{positiontext} {user['username']}:** {str(round(user['parameters'],2))} caracteres"
        else:
            currpage += f"**{positiontext} {user['username']}:** {str(round(user['points'],2))} puntos"
        if "param" in user:
            currpage += f" -> {get_media_element(user['param'],medio)}\n"
        else:
            currpage += "\n"
        if position == 3:
            currpage += "----------------------\n"
        if counter >= 10 or position == total_users:
            title = f"Ranking " + \
                get_ranking_title(
                    periodo, medio if not chars else "CARACTERES")
            embed = discord.Embed(color=0x5842ff)
            embed.add_field(name=title, value=currpage, inline=True)
            pages.append(Page(embeds=[embed]))
            currpage = ""
            counter = 0
        position += 1
    if len(sortedlist) > 0:
        return {"pages": pages, "view": RankingView(medio, periodo)}
    else:
        return {"embed": create_error_embed("Ningún usuario ha inmersado con este medio en el periodo de tiempo indicado"), "view": RankingView(medio, periodo)}


class RankingView(discord.ui.View):
    def __init__(self, medio="TOTAL", periodo="TOTAL"):
        super().__init__()

        self.periodo = periodo

        medio_select = self.get_item("medio")

        select_option(medio_select, medio)

    @discord.ui.select(
        row=1,
        options=[discord.SelectOption(label="Selecciona un medio", value="TOTAL", default=True)]+[discord.SelectOption(
            label=media_type, value=media_type) for media_type in MEDIA_TYPES + ["CARACTERES"]],
        placeholder="Selecciona un medio",
        custom_id="medio"
    )
    async def select_callback(self, select: Select, interaction: Interaction):
        medio = select.values[0]
        chars = False

        if medio == "CARACTERES":
            chars = True
            medio = "TOTAL"

        await interaction.response.defer()

        await interaction.delete_original_response()

        response = await ranking_command(medio, self.periodo, chars)

        select_option(select, medio)

        paginator = Paginator(
            pages=response["pages"], custom_view=self)

        await paginator.respond(interaction)
