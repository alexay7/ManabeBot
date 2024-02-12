from discord.ext import commands
from termcolor import cprint


class ZZZ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("===============================================")
        cprint(
            f"\n🎉 AJRBot listo con usuario {self.bot.user}\n", "blue", attrs=["bold"])
        print("===============================================")


def setup(bot):
    bot.add_cog(ZZZ(bot))
