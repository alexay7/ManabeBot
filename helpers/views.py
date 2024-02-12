import discord

from discord.interactions import Interaction
from discord.ui import View


def enable_buttons(view: View):
    for child in view.children:
        child.disabled = False


async def prepare_response(interaction: Interaction, view: View):
    view.disable_all_items()

    # Embed de cargando
    embed_loading = discord.Embed(
        title="Cargando...", color=0xd400ff)

    await interaction.response.defer()

    message = await interaction.edit_original_response(embed=embed_loading, view=view, attachments=[])

    return message


def select_option(select, option):
    # Search an the id of an option with default=True, it may not exist
    default_option = next(
        (x for x in select.options if x.default), None)

    # If there is a default option, set it to False in the options
    if default_option:
        default_option.default = False

    # Search the option index in select.options for medio
    try:
        index = [x.label for x in select.options].index(option)

        select.options[index].default = True
    except ValueError:
        ...


def create_error_embed(message: str):
    return discord.Embed(title="Error", description=message, color=0xff0000)
