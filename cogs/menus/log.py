import json
import discord

from helpers.general import send_error_message
from helpers.views import create_error_embed
from helpers.immersion.logs import bonus_log, remove_log, unbonus_log


async def unmark_as_bonus(ctx, old_embed, user):
    if "AJR" not in old_embed.title:
        await send_error_message(ctx, "Este log no está marcado como bonus")
        return

    log_id = old_embed.description.split(" ")[2].replace("#", "")

    new_points_aux = await unbonus_log(log_id, user)

    if new_points_aux < 0:
        await send_error_message(ctx, "Este log no está marcado como bonus")
        return

    old_points = float(
        old_embed.fields[2].value.split(" ")[0])
    old_points_added = float(old_embed.fields[2].value.split(" ")[
        1].replace("(+", "").replace(")", ""))
    new_points = old_points-old_points_added+new_points_aux

    old_embed.remove_field(2)
    old_embed.insert_field_at(
        index=2, name="Puntos", value=f"{round(new_points,2)} (+{round(new_points_aux,2)})", inline=True)
    old_embed.title = old_embed.title.replace(
        " (club AJR)", "")
    old_embed.color = 0x24b14d
    return old_embed


async def mark_as_bonus(ctx, old_embed, user):
    if "AJR" in old_embed.title:
        await send_error_message(ctx, "Este log ya está marcado como bonus")
        return

    log_id = old_embed.description.split(" ")[2].replace("#", "")

    new_points_aux = await bonus_log(log_id, user)

    if new_points_aux < 0:
        await send_error_message(ctx, "Este log ya está marcado como bonus")
        return

    old_points = float(
        old_embed.fields[2].value.split(" ")[0])
    old_points_added = float(old_embed.fields[2].value.split(" ")[
        1].replace("(+", "").replace(")", ""))
    new_points = old_points-old_points_added+new_points_aux

    old_embed.remove_field(2)
    old_embed.insert_field_at(
        index=2, name="Puntos (x1.4)", value=f"{round(new_points,2)} (+{round(new_points_aux,2)})", inline=True)
    old_embed.title = old_embed.title+" (club AJR)"
    old_embed.color = 0xbf9000

    return old_embed


async def delete_log(old_embed, user):
    log_id = old_embed.description.split(" ")[2].replace("#", "")

    await remove_log(user, log_id)

    logdeleted = discord.Embed(color=0x24b14d)
    logdeleted.add_field(
        name="✅", value=f"Log {old_embed.description.split(' ')[2]} eliminado con éxito", inline=False)
    return logdeleted


class BonusButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🟢", style=discord.ButtonStyle.blurple, custom_id="bonus")

    async def callback(self, interaction: discord.Interaction):
        # Extraer id del footer del embed
        userId = int(interaction.message.embeds[0].footer.text.split(" ")[-1])

        # Si el usuario no es el dueño del log, no hacer nada
        if userId != interaction.user.id and userId not in admin_users:
            error_embed = create_error_embed(
                "No puedes editar logs de otros usuarios")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        self.disabled = True

        # Get message
        message = interaction.message

        await interaction.response.defer()

        new_embed = await mark_as_bonus(interaction.channel, message.embeds[0], userId)

        # Delete this button and enable the one for unmark
        self.view.remove_item(self)
        self.view.add_item(UnBonusButton())

        await interaction.edit_original_response(embed=new_embed, view=self.view)


class UnBonusButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔴", style=discord.ButtonStyle.blurple, custom_id="unbonus")

    async def callback(self, interaction: discord.Interaction):
        # Extraer id del footer del embed
        userId = int(interaction.message.embeds[0].footer.text.split(" ")[-1])

        # Si el usuario no es el dueño del log, no hacer nada
        if userId != interaction.user.id and userId not in admin_users:
            error_embed = create_error_embed(
                "No puedes editar logs de otros usuarios")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

        self.disabled = True

        # Get message
        message = interaction.message

        await interaction.response.defer()

        new_embed = await unmark_as_bonus(interaction.channel, message.embeds[0], userId)

        # Delete this button
        self.view.remove_item(self)
        self.view.add_item(BonusButton())

        await interaction.edit_original_response(embed=new_embed, view=self.view)


with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    admin_users = general_config["admin_users"]


class LogView(discord.ui.View):
    def __init__(self, bonus=False):
        super().__init__(timeout=None)

        if bonus:
            self.add_item(UnBonusButton())
        else:
            self.add_item(BonusButton())

    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.red, custom_id="delete")
    async def delete_callback(self, button: discord.Button, interaction: discord.Interaction):
        # Extraer id del footer del embed
        userId = int(interaction.message.embeds[0].footer.text.split(" ")[-1])

        # Si el usuario no es el dueño del log, no hacer nada
        if userId != interaction.user.id and userId not in admin_users:
            error_embed = create_error_embed(
                "No puedes eliminar logs de otros usuarios")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

        await interaction.response.defer()

        message = interaction.message

        new_embed = await delete_log(message.embeds[0], userId)

        self.clear_items()

        await interaction.edit_original_response(embed=new_embed, view=self, delete_after=10)
