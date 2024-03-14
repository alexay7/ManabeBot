import calendar
import discord

from datetime import datetime
from discord.ext.pages import Paginator, Page

from helpers.immersion.divisions import calculate_promotions_demotions


async def league_command(division: int, divisions):
    if division:
        league = "LIGA Manabe" if division == 1 else "LIGA 上手"

    high_div = divisions[0]
    low_div = divisions[1]

    # Create copy of the high division to avoid modifying the original list
    high_div_aux = high_div.copy()

    promotions, demotions = calculate_promotions_demotions(
        high_div_aux, low_div)

    # Get short month name and year
    month = datetime.now().month
    year = datetime.now().year
    month_year = f"{calendar.month_abbr[month]} {year}"

    position = 1
    if division == 1:
        currpage = ""
        for user in high_div:
            positiontext = str(position)+"º"
            if position == 1:
                positiontext = "🥇 "
            elif position == 2:
                positiontext = "🥈 "
            elif position == 3:
                positiontext = "🥉 "
            elif (10 - len(demotions)) < position:
                positiontext = "⬇️ "
            currpage += f"**{positiontext} {user['username']}:** {str(round(user['points'],2))} puntos"
            position += 1
            currpage += "\n"
            if position == 4:
                currpage += "----------------------\n"

        title = f"════ {league} {month_year} ════"
        embed = discord.Embed(color=0xffb434)
        embed.add_field(name=title, value=currpage, inline=True)

        return {"type": "embed", "embed": embed, "view": LeagueView(divisions, division=division)}

    else:
        total_users = len(low_div)
        currpage = ""
        counter = 0
        pages = []
        for user in low_div:
            counter += 1
            positiontext = str(position)+"º"

            if (10-len(promotions)) <= 10-position:
                positiontext = "⬆️ "

            currpage += f"**{positiontext} {user['username']}:** {str(round(user['points'],2))} puntos"
            currpage += "\n"
            if counter >= 10 or position == total_users:
                title = f"════ {league} {month_year} ════"
                embed = discord.Embed(color=0x5842ff)
                embed.add_field(name=title, value=currpage, inline=True)
                pages.append(Page(embeds=[embed]))
                currpage = ""
                counter = 0
            position += 1
        if len(low_div) > 0:
            return {"type": "paginator", "pages": pages, "view": LeagueView(divisions, division=division)}


class LeagueView(discord.ui.View):
    def __init__(self, divisions, division, periodo="MES"):
        super().__init__()

        self.periodo = periodo
        self.division = division
        self.divisions = divisions

        if division == 1:
            self.get_item("primera").disabled = True
        else:
            self.get_item("segunda").disabled = True

    @discord.ui.button(label="🏅 Liga Manabe", style=discord.ButtonStyle.primary, custom_id="primera")
    async def first_div(self, button: discord.Button, interaction: discord.Interaction):
        # Venimos de paginator
        await interaction.response.defer()

        await interaction.delete_original_response()

        response = await league_command(1, self.divisions)

        self.enable_all_items()

        button.disabled = True

        await interaction.followup.send(embed=response["embed"], view=self)

    @discord.ui.button(label="🥈 Liga 上手", style=discord.ButtonStyle.secondary, custom_id="segunda")
    async def second_div(self, button: discord.Button, interaction: discord.Interaction):
        # Venimos de embed
        await interaction.response.defer()

        await interaction.delete_original_response()

        response = await league_command(2, self.divisions)

        self.enable_all_items()

        button.disabled = True

        paginator = Paginator(
            pages=response["pages"], custom_view=self)

        await paginator.respond(interaction)
