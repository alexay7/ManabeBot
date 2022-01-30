"Some error handling."
import discord
import re
import json
from discord.ext import commands
from discord.ext.commands import CommandNotFound

#############################################################
# Variables (Temporary)
with open(f"cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    admin_user_id = data_dict["kaigen_user_id"]
    quizranks = data_dict["quizranks"]
    mycommands = data_dict["mycommands"]
    mycommands = {int(key): value for key, value in mycommands.items()}

#############################################################


class ErrorHandler(commands.Cog):
    """Commands in relation to the Quiz."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        if(self.myguild):
            admin_user = self.myguild.get_member(admin_user_id)
            await admin_user.create_dm()
            self.private_admin_channel = admin_user.dm_channel

        # await self.private_admin_channel.send("Bot started.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Argumento necesario: {error.param}")
            return
        elif isinstance(error, commands.errors.CommandNotFound):
            await ctx.message.add_reaction('❓')
            return
        elif isinstance(error, commands.errors.CommandOnCooldown):
            await ctx.send(f'Tienes que esperar {int(error.retry_after)} segundos antes de volver a usar ese comando.')
            return
        elif isinstance(error, commands.errors.PrivateMessageOnly):
            await ctx.send(f"Este comando solo esta disponible via MP")
            return
        elif isinstance(error, commands.errors.MaxConcurrencyReached):
            await ctx.send("Ya hay un usuario usando este comando! De uno en uno...")
            return
        elif ctx.command and ctx.command.name == "levelup":
            await ctx.send(f"Ha ocurrido un error")
            member = await self.myguild.fetch_member(ctx.author.id)
            for role in member.roles:
                if role.id in quizranks:
                    # String is cut down for easy copy and paste.
                    currentcommand = re.search(
                        r"`(.*)`", mycommands[role.id]).group(1)
                    await ctx.send(currentcommand)
            return

        else:
            await self.private_admin_channel.send(f"{str(error)}\n\nTriggered by: `{ctx.message.content}`\n"
                                                  f"Here: {ctx.message.jump_url}")
            raise error


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
