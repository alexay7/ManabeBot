import discord

from quiz.checkHandler import checkHandler


class ButtonHandler(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.score = 0
        self.user_answer = None
        self.current_answer = None
        self.current_question = 0
        self.explanation = ""

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary)
    async def buttonA(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.user_answer = 1
        self.score, self.current_answer, self.current_question, self.explanation = await checkHandler(self.current_question, self.user_answer, self.current_answer, self.explanation, self.score, interaction, self)

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary)
    async def buttonB(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.user_answer = 2
        self.score, self.current_answer, self.current_question, self.explanation = await checkHandler(self.current_question, self.user_answer, self.current_answer, self.explanation, self.score, interaction, self)

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary)
    async def buttonC(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.user_answer = 3
        self.score, self.current_answer, self.current_question, self.explanation = await checkHandler(self.current_question, self.user_answer, self.current_answer, self.explanation, self.score, interaction, self)

    @discord.ui.button(label="4", style=discord.ButtonStyle.primary)
    async def buttonD(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.user_answer = 4
        self.score, self.current_answer, self.current_question, self.explanation = await checkHandler(self.current_question, self.user_answer, self.current_answer, self.explanation, self.score, interaction, self)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def buttonExit(self, button: discord.ui.Button, interaction: discord.Interaction):
        last_question = self.current_question - 1
        if last_question > 0:
            if self.score == last_question:
                emoji = "🏆"
            elif self.score > float(last_question) * 0.7:
                emoji = "🎖️"
            elif self.score > float(last_question) * 0.5:
                emoji = "😐"
            else:
                emoji = "⚠️"
            embed = discord.Embed(
                color=0x3344dd, title="Test terminado por el usuario")
            embed.add_field(
                name=" Preguntas acertadas: ", value=emoji + " " + str(self.score) + "/" + str(last_question) + " (" + str(round(int(self.score) * 100 / int(last_question), 2)) + "%)", inline=True)
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        self.stop()
        self.clear_items()
        if last_question > 0:
            await interaction.followup.send(embed=embed)
