from asyncio import sleep
from copy import copy
import json
import discord

from helpers.test import getQuestion, question_params


async def checkHandler(current_question, user_answer, current_answer, explanation, score, interaction: discord.Interaction, view: discord.ui.View):
    with open(f"temp/test-{interaction.user.id}.json", encoding="utf8") as json_file:
        questions = json.load(json_file)
    print(current_answer)
    print(current_question)
    if user_answer and current_answer:
        if user_answer == current_answer:
            view.children[user_answer - 1].style = discord.ButtonStyle.success
            # embed para respuesta correcta
            score += 1
        else:
            # embed para respuesta incorrecta
            view.children[user_answer - 1].style = discord.ButtonStyle.danger
            view.children[current_answer -
                          1].style = discord.ButtonStyle.success
        explained_embed = interaction.message.embeds[0]
        explained_embed.add_field(
            name="Explicación", value=explanation)
        view.disable_all_items()
        await interaction.response.edit_message(embed=explained_embed, view=view)
    else:
        aux = copy(view.children)
        view.clear_items()
        await interaction.response.edit_message(view=view)
        for elem in aux:
            view.add_item(elem)

    questionnum = len(questions)

    if current_question < questionnum:
        question = getQuestion(interaction.user.id, current_question)
        qname, explain, timemax = question_params(question.get("type"))
        qs = question.get("question").replace("＿", " ＿ ").replace(
            "*", " ( ", 1).replace("*", ") ", 1).replace("_", "\_") + "\n"
        counter = 1
        anwserArr = ""
        for elem in question.get("answers"):
            anwserArr += str(counter) + ") " + elem + "\n"
            counter += 1
        current_answer = question.get("correct")

        embed = discord.Embed(color=0x00e1ff, title=qname,
                              description="Pregunta " + str(current_question + 1) + " de " + str(questionnum) + ".")
        embed.add_field(
            name="Pregunta", value=qs, inline=True)
        embed.add_field(name="Posibles Respuestas",
                        value=anwserArr, inline=False)
        embed.set_footer(
            text="Enunciado: " + explain)
        current_question += 1
        explanation = question.get("explanation")
        for button in view.children:
            if 'Cancelar' not in button.label:
                button.style = discord.ButtonStyle.primary
        view.enable_all_items()
        await sleep(1)
        await interaction.followup.send(embed=embed, view=view)
        return score, current_answer, current_question, explanation
    else:
        view.stop()
        view.clear_items()
        if score == questionnum:
            emoji = "🏆"
        elif score > float(questionnum) * 0.7:
            emoji = "🎖️"
        elif score > float(questionnum) * 0.5:
            emoji = "😐"
        else:
            emoji = "⚠️"
        embed = discord.Embed(color=0x3344dd, title="Quiz terminado")
        embed.add_field(
            name=" Preguntas acertadas: ", value=emoji + " " + str(score) + "/" + str(questionnum) + " (" + str(round(int(score) * 100 / int(questionnum), 2)) + "%)", inline=True)

        await interaction.followup.send(embed=embed, view=view)
        return 0, 0, 0, 0
