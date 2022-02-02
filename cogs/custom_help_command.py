import discord
from discord.ext import commands

# Modified help command.


class MyHelpCommand(commands.MinimalHelpCommand):

    async def send_pages(self):
        destination = self.get_destination()
        myembed = discord.Embed(color=discord.Color.blurple(), description='')
        for page in self.paginator.pages:
            myembed.description += page
        await destination.send(embed=myembed)

    def add_bot_commands_formatting(self, commands, heading):
        if commands:
            lines = []
            for command in commands:
                commandline = f"`{command.name}` {command.help}"
                if(len(command.aliases) != 0):
                    commandline += "\nOtros usos:"
                    for element in command.aliases:
                        commandline += f"\n - `{element}`"
                lines.append(commandline + "\n")

            joined = '\n'.join(lines)
            self.paginator.add_line(joined)

    def get_opening_note(self):
        return "Comandos disponibles:"

    def get_command_signature(self, command):
        return None


class MyHelpCog(commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self


def setup(bot):
    bot.add_cog(MyHelpCog(bot))
