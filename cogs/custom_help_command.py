import discord
from discord.ext import commands

# Modified help command.


class MyHelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["ayuda"])
    async def help(self, ctx):
        return await ctx.send("Comando en proceso de mejora, consulta <#892880230761504851> para ver el uso detallado de los comandos.")


def setup(bot):
    bot.add_cog(MyHelpCog(bot))
