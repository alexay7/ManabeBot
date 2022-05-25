"""Cog responsible for the level-up rank system."""

import json
import random
import re
import discord
import time
import aiohttp
from discord.ext import commands

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    kotobabotid = data_dict["kotoba_id"]
    join_quiz_channel_ids = data_dict["join_quiz_1_id"]
    announcement_channel_id = data_dict["otaku_channel_id"]
    quizranks = data_dict["quizranks"]
    mycommands = data_dict["mycommands"]
    mycommands = {int(key): value for key, value in mycommands.items()}
    myrankstructure = data_dict["rank_structure"]
#############################################################


class Quiz(commands.Cog):
    """Commands in relation to the Quiz."""

    def __init__(self, bot):
        self.bot = bot

    async def getjson(self, url):
        async with self.aiosession.get(url) as resp:
            return await resp.json()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        await self.bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name="Cosas japonesas| .help"))
        self.aiosession = aiohttp.ClientSession()

    @commands.command()
    async def levelup(self, ctx):
        """
        Mostrar el comando que necesitas para subir al siguiente nivel.
        """
        if ctx.channel.id not in join_quiz_channel_ids:
            await ctx.send(
                "Este comando solo puede ser usado en <#796084920790679612>.")
            return

        member = await self.myguild.fetch_member(ctx.author.id)
        for role in member.roles:
            if role.id in quizranks:
                # String is cut down for easy copy and paste.
                currentcommand = re.search(
                    r"`(.*)`", mycommands[role.id]).group(1)
                await ctx.send(currentcommand)

        await ctx.send(
            "Usa este comando para subir de nivel.\nPara ver todos los niveles disponibles escribe `.levelupall`")

    @commands.command()
    async def levelupall(self, ctx):
        """
        Mostrar todos los comandos para subir de nivel (via MP).
        """
        message_list = []
        message_list.append(
            "Escribe `.help` para ver una lista con todos los comandos.\n")

        for rankid in mycommands:
            levelupmesssage = mycommands[rankid]
            message_list.append(levelupmesssage)

        # Delete final level message.
        del message_list[-1]

        message = "\n".join(message_list)

        await ctx.author.create_dm()
        private_channel = ctx.author.dm_channel
        await private_channel.send(message)

    # Quiz reward function.
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == kotobabotid:
            kotobaembeds = message.embeds
            try:
                if kotobaembeds:
                    for embed in kotobaembeds:
                        fields = embed.fields
                        if 'Ended' in embed.title:
                            for field in fields:
                                if "[View a report for this game]" in field.value:
                                    quizid = re.search(
                                        r'game_reports/([^)]*)\)', field.value).group(1)
                                    jsonurl = f"https://kotobaweb.com/api/game_reports/{quizid}"

                                    # kotobadict = json.loads(requests.get(jsonurl).text)
                                    print("Download kotobabot json.")
                                    start = time.time()
                                    kotobadict = await self.getjson(jsonurl)
                                    end = time.time()
                                    print(
                                        f"Finished downloading kotoba json with runtime: {end - start} seconds")

                                    usercount = len(kotobadict["participants"])
                                    questioncount = len(
                                        kotobadict["questions"])
                                    mainuserid = int(
                                        kotobadict["participants"][0]["discordUser"]["id"])
                                    scorelimit = kotobadict["settings"]["scoreLimit"]
                                    failedquestioncount = questioncount - scorelimit
                                    answertimelimitinms = kotobadict["settings"]["answerTimeLimitInMs"]
                                    fontcolor = kotobadict["settings"]["fontColor"]
                                    bgcolor = kotobadict["settings"]["backgroundColor"]
                                    fontsize = kotobadict["settings"]["fontSize"]
                                    font = kotobadict["settings"]["font"]
                                    shuffle = kotobadict["settings"]["shuffle"]
                                    isloaded = kotobadict["isLoaded"]
                                    myscore = kotobadict["scores"][0]["score"]

                                    # Multideck quiz
                                    if len(kotobadict["decks"]) == 1:
                                        quizname = kotobadict["sessionName"]
                                    else:
                                        quizname = ""
                                        for deckdict in kotobadict["decks"]:
                                            addname = deckdict["name"]
                                            quizname += " " + addname

                                    startindex = 0
                                    endindex = 0

                                    mc = kotobadict["decks"][0]["mc"]

                                    try:
                                        startindex = kotobadict["decks"][0]["startIndex"]
                                        endindex = kotobadict["decks"][0]["endIndex"]

                                    except KeyError:
                                        pass

                                    try:
                                        requirements = myrankstructure[quizname]
                                        reqscorelimit, reqanswertime, reqfontsize, reqfont, newrankid, reqfailed = requirements
                                    except KeyError:
                                        print("Not a ranked quiz.")
                                        return

                                    if fontcolor != "rgba(241,115,255,1)" or bgcolor != "rgba(0,0,0,1)":
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Ajustes de color erróneos. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Wrong color settings.")
                                        return

                                    if startindex != 0 or endindex != 0 or mc or shuffle is False or isloaded:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Ajustes ilegales detectados. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Cheat settings detected.")
                                        return

                                    if scorelimit != myscore:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Quiz fallado. Usa el siguiente comando para volverlo a intentar:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[quizranks.index(newrankid)-1]]).group(1)}")
                                        print("Score and limit don't match.")
                                        return

                                    if scorelimit < reqscorelimit:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Puntuación mínima establecida demasiado baja. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Score too low.")
                                        return

                                    if usercount > 1:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Demasiados usuarios, haz el quiz solo y usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Too many users.")
                                        return

                                    if reqanswertime < answertimelimitinms:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send(
                                                "Tiempo establecido para contestar demasiado alto. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Answer time too long.")
                                        return

                                    if reqfontsize < fontsize:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Tamaño de fuente demasiado grande. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Font size too big.")
                                        return

                                    if reqfont != 'any':
                                        if font not in reqfont:
                                            if message.channel.id in join_quiz_channel_ids:
                                                await message.channel.send(
                                                    "Fuente no permitida. Usa el siguiente comando:")
                                                await message.channel.send(
                                                    f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")

                                            print("Font not correct.")
                                            return

                                    if failedquestioncount < 0:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Quiz abortado. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Negative fails (Quiz aborted).")
                                        return

                                    if failedquestioncount > reqfailed:
                                        if message.channel.id in join_quiz_channel_ids:
                                            await message.channel.send("Demasiadas preguntas incorrectas. Usa el siguiente comando:")
                                            await message.channel.send(
                                                f"{re.search(r'`(.*)`', mycommands[list(mycommands.keys())[0]]).group(1)}")
                                        print("Too many failed.")
                                        return

                                    if message.channel.id not in join_quiz_channel_ids:
                                        await message.channel.send(
                                            "Los tests solo serán evaluados en <#796084920790679612>.")
                                        return

                                    quizwinner = self.myguild.get_member(
                                        mainuserid)
                                    for role in quizwinner.roles:
                                        if role.id in quizranks:
                                            print("Role ID:", role.id)
                                            currentroleid = role.id

                                    if quizranks.index(currentroleid) <= quizranks.index(newrankid) - 1:
                                        currentrole = self.myguild.get_role(
                                            currentroleid)
                                        newrole = self.myguild.get_role(
                                            newrankid)
                                        await quizwinner.remove_roles(currentrole)
                                        await quizwinner.add_roles(newrole)
                                        announcementchannel = self.bot.get_channel(
                                            announcement_channel_id)
                                        await announcementchannel.send(f'<@!{mainuserid}> ha aprobado el {quizname}!\n'
                                                                       f'Escribe `.levelup` para ver el comando para subir al siguiente nivel.')

            except TypeError:
                pass

    @commands.command()
    async def arreglar(self, ctx):
        quizwinner = self.myguild.get_member(
            331444118469214220)
        for role in quizwinner.roles:
            if role.id in quizranks:
                print("Role ID:", role.id)
                currentroleid = role.id

        if quizranks.index(currentroleid) <= quizranks.index(892868169729986600) - 1:
            currentrole = self.myguild.get_role(
                currentroleid)
            newrole = self.myguild.get_role(
                892868169729986600)
            await quizwinner.remove_roles(currentrole)
            await quizwinner.add_roles(newrole)
            announcementchannel = self.bot.get_channel(
                announcement_channel_id)
            await announcementchannel.send(f'<@!{331444118469214220}> ha aprobado el {quizname}!\n'
                                           f'Escribe `.levelup` para ver el comando para subir al siguiente nivel.')

    @commands.command()
    async def generatequiz(self, ctx):
        "Genera un quiz semi-aleatorio (no cuenta para subir de nivel)."
        if ctx.channel.id not in join_quiz_channel_ids:
            await ctx.send(
                "Este bot solo puede ser usado en <#796084920790679612>.")
            return
        basis = "k!quiz"
        quiz_selection = ['N3', 'N2', 'N1', 'suugaku', 'pasokon', 'rikagaku', 'igaku',
                          'shinrigaku', 'keizai', 'houritsu', 'kenchiku', 'buddha', 'nature', 'animals', 'birds',
                          'bugs', 'fish', 'plants', 'vegetables', 'tokyo', 'places_full', 'rtk_vocab', 'common',
                          'common_nojlpt', 'k33', 'hard', 'haard', 'insane', 'ranobe', 'numbers', 'yojijukugo',
                          'myouji', 'namae', 'cope', 'jpdefs', 'jpdefs', 'jouyou']

        my_quiz_length = random.randint(2, 5)
        my_quizzes = ""
        for i in range(my_quiz_length):
            if i == 0:
                my_quizzes = quiz_selection[random.randint(0, 36)]
            else:
                my_quizzes = my_quizzes + "+" + \
                    quiz_selection[random.randint(0, 36)]

        score_limit = random.randint(10, 20)

        pacers = ["nodelay", "faster", "fast", ""]
        mypacing = pacers[random.randint(0, 3)]

        answer_time = random.randint(7, 14)
        atl = f"atl={answer_time}"

        additional_answer_wait = random.randint(0, 3)
        aaww = f"aaww={additional_answer_wait}"

        dauq = "dauq=1"
        daaq = "daaq=1"

        font_list = [1, 3, 4, 5, 7, 9, 10, 13, 15, 23]
        myfont = f"font={font_list[random.randint(0, 9)]}"

        message = f"{basis} {my_quizzes} {atl} {aaww} {dauq} {daaq} {myfont} {score_limit} {mypacing}"
        await ctx.send(message)


def setup(bot):
    bot.add_cog(Quiz(bot))
