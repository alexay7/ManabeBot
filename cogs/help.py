import json
from re import U
import discord
from discord.ext import commands
from helpers.general import send_error_message

from helpers.help import CATEGORIES, COMMANDS

# ================ GENERAL VARIABLES ================
with open("config/help.json", encoding="utf8") as json_file:
    help_commands = json.load(json_file)
# ====================================================


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de ayuda cargado con éxito")

    @commands.command()
    async def help(self, ctx, command=""):
        command = command.replace("ó", "o")
        if command.upper() in COMMANDS:
            command = help_commands["commands"][command.lower()]

            embed = discord.Embed(title="__<:Reportadito:853315899511930910> Manual IniestaBot2.0 <:Reportadito:853315899511930910>__",
                                  color=0xaabbff)
            embed.add_field(
                name=f'`{command["comando"]}` - {command["short_description"]}', value=f"```css\n{command['uso']}```")
            embed.add_field(name="Descripción",
                            value=f">>> *{command['descripcion']}*", inline=False)
            embed.set_footer(
                text="Para buscar información sobre un comando, escribe .help [nombre del comando]")
            if "Extra" in command:
                for elem in command["Extra"]:
                    embed.add_field(name=elem["name"],
                                    value=f"```ini\n{elem['value']}```", inline=False)
            await ctx.send(embed=embed)
        elif command.upper() in CATEGORIES:
            command_list = ""
            for name, info in help_commands["commands"].items():
                if info["categoria"] == command.lower():
                    command_list += f"`{info['comando']}` - {info['short_description']}\n"

            embed = discord.Embed(title="__<:Reportadito:853315899511930910> Manual IniestaBot2.0 <:Reportadito:853315899511930910>__",
                                  color=0xaabbff, description=f'*{help_commands["categories"][command.lower()]["descripcion"]}*')
            embed.add_field(name="Comandos:",
                            value=f">>> {command_list}", inline=False)
            embed.set_footer(
                text="Para buscar información sobre un comando, escribe .help [nombre del comando]")

            await ctx.send(embed=embed)
        elif command == "":
            embed = discord.Embed(title="__<:Reportadito:853315899511930910> Manual IniestaBot2.0 <:Reportadito:853315899511930910>__",
                                  color=0xaabbff, description="Usa uno de los comandos de abajo para recibir ayuda")
            embed.add_field(
                name='Categorías', value=f">>> <:karenread:1004469959222640650>`.help inmersión` | Comandos sobre el logueo de inmersión\n📖`.help kotoba` | Comandos sobre los ranked quiz del bot kotoba\n✅`.help tests` | Comandos sobre los tests JLPT\n🎌`.help extras` | Comandos variados")
            embed.set_footer(
                text="Para buscar información sobre un comando, escribe .help [nombre del comando]")

            await ctx.send(embed=embed)
        else:
            await send_error_message(ctx, "No existe ningún comando o categoría con ese nombre")


def setup(bot):
    bot.add_cog(Help(bot))
