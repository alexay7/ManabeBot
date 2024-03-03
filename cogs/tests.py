"""Cog responsible for tests."""

import asyncio
import random
import discord
import json

from time import sleep
from discord.ext import commands

from helpers.general import send_error_message
from helpers.mongo import tests_db
from termcolor import cprint, COLORS

from helpers.mongo import kotoba_db
from helpers.kotoba import level_user

# BOT'S COMMANDS

CATEGORIES = ["VOCABULARIO", "GRAMATICA"]
TYPES = ["KANJI", "CONTEXTO", "PARAFRASES", "USO",
         "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA", "FORMACION"]
LEVELS = {
    "N5": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR"]},
    "N4": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA"]},
    "N3": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA"]},
    "N2": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR", "ORTOGRAFIA", "FORMACION"]},
    "N1": {"TYPES": ["KANJI", "CONTEXTO", "PARAFRASES", "USO", "GRAMATICAFRASES", "ORDENAR"]}}


def checkanswer(reaction, answer):
    return reaction == answer


def emojiToInt(reaction):
    if reaction == "1️⃣":
        return 1
    if reaction == "2️⃣":
        return 2
    if reaction == "3️⃣":
        return 3
    if reaction == "4️⃣":
        return 4
    return 0


def question_params(question):
    if question == "kanji":
        name = "Lectura de Kanjis (漢字読み)"
        description = "_____の言葉の読み方として最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 10
    elif question == "contexto":
        name = "Contexto (文脈規定)"
        description = "_____に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 20
    elif question == "parafrases":
        name = "Parafraseo (言い換え類義)"
        description = "_____の言葉に意味が最も近ものを、１・２・３・４から一つ選びなさい。"
        time = 20
    elif question == "uso":
        name = "Uso de palabras (用法)"
        description = "次の言葉の使い方として最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 30
    elif question == "gramaticafrases":
        name = "Gramática (文法形式の判断)"
        description = "次の文の_____に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 15
    elif question == "ordenar":
        name = "Ordenar frases (文の組み立て)"
        description = "次の文の＿★＿に入れる最も良いものを、１・２・３・４から一つ選びなさい。"
        time = 40
    elif question == "ortografia":
        name = "Ortografía ()",
        description = "問題＿＿＿の言葉を漢字で書くとき、最もよいものを１・２・３・４から一つ選びなさい。"
        time = 30
    elif question == "formacion":
        name = "Formación de palabras ()"
        description = "問題（　　　）に入れるのに最もよいものを、１・２・３・４から一つ選びなさい。"
        time = 20
    else:
        name = "No implementado",
        description = "no implementado"
        time = 60
    return name, description, time


with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    main_guild = general_config["trusted_guilds"][0]

with open("config/kotoba.json", encoding="utf8") as json_file:
    kotoba_config = json.load(json_file)
    noken_ranks = kotoba_config["noken_ranks"]
    grammar_messages = kotoba_config["grammar_messages"]
    grammar_messages = {int(key): value for key,
                        value in grammar_messages.items()}
    announcement_channel = kotoba_config["announcement_channel"]
    kotoba_tests = kotoba_config["kotoba_tests"]
    short_level_up_messages = kotoba_config["short_level_up_messages"]


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False
        self.tasks = dict()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(main_guild)
        cprint("- [✅] Cog de tests cargado con éxito",
               random.choice(list(COLORS.keys())))

    @commands.command()
    async def test(self, ctx, level, param=None, questionnum=None, maxfails=None):
        if ctx.message.author == self.bot:
            return
        users = tests_db.users
        exercises = tests_db.exercises
        preset_questions = False
        questions = []
        if level.lower() == "help":
            embed = discord.Embed(color=0x00e1ff, title="Tipos de quiz",
                                  description="Uso: .test [tipo] [número de preguntas (def: 5)] [modo veloz (def: false)]")
            embed.add_field(
                name="Vocabulario *[.test vocabulario]*", value="**Lectura de Kanjis** *[.test kanji]*: Debes seleccionar la respuesta con la lectura del kanji entre paréntesis.\n**Contexto** *[.test contexto]*: Debes llenar el hueco en la frase con la palabra más adecuada.\n**Parafrases** *[.test parafrases]*: Debes seleccionar la palabra con el significado más parecido a la palabra entre paréntesis dentro de la frase.\n**Uso** *[.test uso]*: Debes seleccionar la frase donde la palabra indicada esté bien utilizada.", inline=False)
            embed.add_field(
                name="Gramática *[.test gramatica]*", value="**Gramática de frases** *[.test gramaticafrases]*: Debes seleccionar la forma gramatical más adecuada en el hueco de la frase.\n**Ordenar frases** *[.test ordenar]*: Debes seleccionar la parte de la frase que encaja en el hueco señalado con una estrella.", inline=False)
            embed.add_field(
                name="Modo veloz", value="Activar este modo hará que tengas menos tiempo para responder a las preguntas. (def: 1 min)")
            embed.set_footer(
                text="Puedes ver de nuevo esta información escribiendo [.test help]")
            return await ctx.send(embed=embed)
        elif level.lower() == "random":
            return await send_error_message(ctx, "Tienes que concretar el nivel!")
        elif level.upper() in TYPES:
            return await send_error_message(ctx, "Tienes que concretar el nivel!")
        elif level.lower() == "stop":
            try:
                self.tasks[ctx.message.author.id].close()
                embed = discord.Embed(
                    title="‼️ El test ha sido detenido.", color=0xffff00)
                return await ctx.send(embed=embed)
            except KeyError:
                return await send_error_message(ctx, "No has iniciado ningún test.")
        elif level.lower() == "retry":
            questionnum = 10
            if param:
                questionnum = int(param)
            foundUser = users.find_one(
                {"user_id": ctx.message.author.id})
            random.shuffle(foundUser["questions_failed"])
            for elem in foundUser["questions_failed"][:questionnum]:
                questions.append(exercises.find_one({"_id": elem}))
            preset_questions = True
            questionnum = len(questions)
            if len(questions) == 0:
                return await send_error_message(ctx, "No tienes preguntas falladas!")
        elif level.upper() in LEVELS and not param:
            questionnum = 10
            for elem in exercises.aggregate([{"$match": {"level": level.upper()}}, {"$sample": {"size": int(10)}}]):
                questions.append(elem)
        elif level.upper() in LEVELS and param:
            if questionnum:
                if questionnum.lower() == "true":
                    questionnum = 5
            else:
                questionnum = 5

            if param.isnumeric():
                questionnum = param
                for elem in exercises.aggregate([{"$match": {"level": level.upper()}}, {"$sample": {"size": int(questionnum)}}]):
                    questions.append(elem)
            elif param.lower() == "random":
                param = random.choice(LEVELS[level.upper()]["TYPES"]).lower()
                for elem in exercises.aggregate([{"$match": {"type": param.lower(), "level": level.upper()}}, {"$sample": {"size": int(questionnum)}}]):
                    questions.append(elem)
            elif param.upper() in LEVELS[level.upper()]["TYPES"]:
                for elem in exercises.aggregate([{"$match": {"type": param.lower(), "level": level.upper()}}, {"$sample": {"size": int(questionnum)}}]):
                    questions.append(elem)
            elif param.upper() in CATEGORIES:
                for elem in exercises.aggregate([{"$match": {"category": param.lower(), "level": level.upper()}}, {"$sample": {"size": int(questionnum)}}]):
                    questions.append(elem)
            else:
                categories = ""
                for elem in LEVELS[level.upper()]["TYPES"]:
                    categories += elem + ", "
                categories = categories[:-2]
                return await send_error_message(ctx, "Categorías admitidas para el " + level.upper() + ": " + categories + ".")

        points = 0
        fails = 0
        question_counter = 1
        user_data = {
            "user_id": ctx.message.author.id
        }
        try:
            users.insert(user_data)
        except:
            ...
        for question in questions:
            qname, explain, timemax = question_params(question.get("type"))
            ""
            qs = question.get("question").replace("＿", " ＿ ").replace(
                "*", " ( ", 1).replace("*", ") ", 1).replace("_", "\_") + "\n"
            counter = 1
            anwserArr = ""
            for elem in question.get("answers"):
                anwserArr += str(counter) + ") " + elem + "\n"
                counter += 1
            answer = question.get("correct")
            # embed = discord.Embed(
            #     title="", color=0x00e1ff, description=qs)
            embed = discord.Embed(color=0x00e1ff, title=qname, description="Pregunta " +
                                  str(question_counter) + " de " + str(questionnum) + ".")
            embed.add_field(
                name="Pregunta", value=qs, inline=True)
            embed.add_field(name="Posibles Respuestas",
                            value=anwserArr, inline=False)
            embed.set_footer(
                text="Enunciado: " + explain)
            output = await ctx.send(embed=embed)
            await output.add_reaction("1️⃣")
            await output.add_reaction("2️⃣")
            await output.add_reaction("3️⃣")
            await output.add_reaction("4️⃣")

            def check(reaction, user):
                return user == ctx.message.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

            timeout = False
            try:
                self.tasks[ctx.message.author.id] = self.bot.wait_for(
                    'reaction_add', timeout=60, check=check)
                guess = await self.tasks[ctx.message.author.id]
            except asyncio.TimeoutError:
                timeout = True
            except RuntimeError:
                return

            if not timeout:
                userans = emojiToInt(guess[0].emoji)

            if timeout:
                incorrect = discord.Embed(
                    title="⌛ Muy lento!", description=question.get("explanation"), color=0xff2929)
                await ctx.send(embed=incorrect)
                users.update_one({"user_id": ctx.message.author.id}, {
                                 "$addToSet": {"questions_failed": question.get("_id")}})
                # await onlyUserReaction(userans)
                sleep(3)
            elif checkanswer(userans, answer):
                if (preset_questions):
                    users.update_one({"user_id": ctx.message.author.id}, {
                                     "$pull": {"questions_failed": question.get("_id")}})
                correct = discord.Embed(
                    title="✅ Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".", color=0x24b14d)
                await ctx.send(embed=correct)
                points += 1
                # userans = await onlyUserReaction(userans)
                sleep(2)
            else:
                incorrect = discord.Embed(

                    title="❌Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".", color=0xff2929, description="Tu Respuesta: " + str(userans) + ") " + question.get("answers")[userans - 1] + ".\n\n" + question.get("explanation"))
                await ctx.send(embed=incorrect)
                fails += 1
                if maxfails and fails >= int(maxfails):
                    break
                users.update_one({"user_id": ctx.message.author.id}, {
                    "$addToSet": {"questions_failed": question.get("_id")}})
                # await onlyUserReaction(userans)
                sleep(3)

            question_counter += 1

        if points == questionnum:
            emoji = "🏆"
        elif points > float(questionnum) * 0.7:
            emoji = "🎖️"
        elif points > float(questionnum) * 0.5:
            emoji = "😐"
        else:
            emoji = "⚠️"

        embed = discord.Embed(color=0x3344dd, title="Quiz terminado")
        embed.add_field(
            name=" Preguntas acertadas: ", value=emoji + " " + str(points) + "/" + str(questionnum) + " (" + str(round(int(points) * 100 / int(questionnum), 2)) + "%)", inline=True)
        output = await ctx.send(embed=embed)

        # If it is a grammar test
        if param and param.lower() == "gramatica" and int(questionnum) == 15 and points > 12:
            user_grades = kotoba_db.usergrades

            if level.upper() == "N5":
                newrankid = noken_ranks[0]
                currentroleid = 0
                shortname = "JLPT N5 Reading Quiz"
            elif level.upper() == "N4":
                newrankid = noken_ranks[1]
                currentroleid = noken_ranks[0]
                shortname = "JLPT N4 Reading Quiz"
            elif level.upper() == "N3":
                newrankid = noken_ranks[2]
                currentroleid = noken_ranks[1]
                shortname = "JLPT N3 Reading Quiz"
            elif level.upper() == "N2":
                newrankid = noken_ranks[3]
                currentroleid = noken_ranks[2]
                shortname = "JLPT N2 Reading Quiz"
            elif level.upper() == "N1":
                newrankid = noken_ranks[4]
                currentroleid = noken_ranks[3]
                shortname = "JLPT N1 Reading Quiz"
            else:
                return

            currentroleid = 0
            for role in ctx.message.author.roles:
                if role.id in noken_ranks:
                    currentroleid = role.id

            # If the index of the current role is higher than the index of the new role, stop
            if currentroleid != 0 and noken_ranks.index(currentroleid) >= noken_ranks.index(newrankid):
                return

            # Check if the user has already passed the level
            user_grade = user_grades.find_one(
                {"userId": ctx.message.author.id, "level": newrankid})

            if user_grade:
                if "vocab" in user_grade:
                    announcementchannel = self.bot.get_channel(
                        announcement_channel)
                    await level_user(announcementchannel, ctx.message.author, self.myguild, shortname, currentroleid)
                    user_grades.delete_one(
                        {"_id": user_grade["_id"]})

                    await ctx.send(f'¡Enhorabuena! Has aprobado el examen del {shortname}!')
                    return

            user_grades.insert_one(
                {"userId": ctx.message.author.id, "level": newrankid, "grammar": True})

            requirements = kotoba_tests[shortname.strip(
            )]
            reqscorelimit, reqanswertime, reqfontsize, reqfont, newrankid, reqfailed, shortname, reqAntiOcr, reqStartIndex, reqEndIndex, image_name = requirements

            # Decirle al usuario que ha aprobado el examen de vocabulario y que ahora tiene que hacer el de gramática
            await ctx.send(f'¡Enhorabuena! Has aprobado el examen de gramática de{shortname}.\n\nAhora tienes que hacer el examen de vocabulario para que te sea concedido el rol. Escribe `{short_level_up_messages[str(newrankid)]}` en <#796084920790679612> para hacerlo.')

    @commands.command()
    async def testaño(self, ctx, year, month):
        if ctx.message.author == self.bot:
            return
        users = tests_db.users
        exercises = tests_db.exercises
        questionnum = 40
        preset_questions = False
        questions = []
        for elem in exercises.aggregate([{"$match": {"year": int(year), "period": month.capitalize()}}]):
            questions.append(elem)
        points = 0
        question_counter = 1
        user_data = {
            "user_id": ctx.message.author.id
        }
        try:
            users.insert(user_data)
        except:
            print("Ya existe")
        for question in questions:
            qname, explain, timemax = question_params(question.get("type"))
            ""
            qs = question.get("question").replace("＿", " ＿ ").replace(
                "*", " ( ", 1).replace("*", ") ", 1).replace("_", "\_") + "\n"
            counter = 1
            anwserArr = ""
            for elem in question.get("answers"):
                anwserArr += str(counter) + ") " + elem + "\n"
                counter += 1
            answer = question.get("correct")
            # embed = discord.Embed(
            #     title="", color=0x00e1ff, description=qs)
            qname = qname + " - JLPT N1 " + month.capitalize() + ", " + year
            embed = discord.Embed(color=0x00e1ff, title=qname, description="Pregunta " +
                                  str(question_counter) + " de " + str(questionnum) + ".")
            embed.add_field(
                name="Pregunta", value=qs, inline=True)
            embed.add_field(name="Posibles Respuestas",
                            value=anwserArr, inline=False)
            embed.set_footer(
                text="Enunciado: " + explain)
            output = await ctx.send(embed=embed)
            await output.add_reaction("1️⃣")
            await output.add_reaction("2️⃣")
            await output.add_reaction("3️⃣")
            await output.add_reaction("4️⃣")

            def check(reaction, user):
                return user == ctx.message.author and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

            timeout = False
            try:
                self.tasks[ctx.message.author.id] = self.bot.wait_for(
                    'reaction_add', timeout=timemax, check=check)
                guess = await self.tasks[ctx.message.author.id]
            except asyncio.TimeoutError:
                timeout = True
            except RuntimeError:
                return

            if not timeout:
                userans = emojiToInt(guess[0].emoji)

            if timeout:
                incorrect = discord.Embed(
                    title="⌛ Muy lento!", description=question.get("explanation"), color=0xff2929)
                await ctx.send(embed=incorrect)
                users.update_one({"user_id": ctx.message.author.id}, {
                                 "$addToSet": {"questions_failed": question.get("_id")}})
                # await onlyUserReaction(userans)
                sleep(3)
            elif checkanswer(userans, answer):
                if preset_questions:
                    users.update_one({"user_id": ctx.message.author.id}, {
                                     "$pull": {"questions_failed": question.get("id")}})
                correct = discord.Embed(
                    title="✅ Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".", color=0x24b14d)
                await ctx.send(embed=correct)
                points += 1
                # userans = await onlyUserReaction(userans)
                sleep(2)
            else:
                incorrect = discord.Embed(
                    title="❌ Tu Respuesta: " + str(userans) + ") " + question.get("answers")[userans - 1] + ".", color=0xff2929, description="Respuesta Correcta: " + str(answer) + ") " + question.get("answers")[answer - 1] + ".\n\n" + question.get("explanation"))
                await ctx.send(embed=incorrect)
                users.update_one({"user_id": ctx.message.author.id}, {
                    "$addToSet": {"questions_failed": question.get("_id")}})
                # await onlyUserReaction(userans)
                sleep(3)

            question_counter += 1

        if points == questionnum:
            emoji = "🏆"
        elif points > float(questionnum) * 0.7:
            emoji = "🎖️"
        elif points > float(questionnum) * 0.5:
            emoji = "😐"
        else:
            emoji = "⚠️"
        embed = discord.Embed(color=0x3344dd, title="Quiz terminado")
        embed.add_field(
            name=" Preguntas acertadas: ", value=emoji + " " + str(points) + "/" + str(questionnum) + " (" + str(round(int(points) * 100 / int(questionnum), 2)) + "%)", inline=True)
        output = await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Test(bot))
