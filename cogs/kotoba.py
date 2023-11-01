import json
import re
import aiohttp
import discord
from discord.ext import commands

from helpers.general import send_error_message, send_response

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    main_guild = general_config["trusted_guilds"][0]

with open("config/kotoba.json", encoding="utf8") as json_file:
    kotoba_config = json.load(json_file)
    kotoba_id = kotoba_config["kotoba_bot"]
    kotoba_tests = kotoba_config["kotoba_tests"]
    kotoba_channels = kotoba_config["kotoba_channels"]
    levelup_messages = kotoba_config["levelup_messages"]
    levelup_messages = {int(key): value for key,
                        value in levelup_messages.items()}
    quiz_ranks = kotoba_config["quiz_ranks"]
    announcement_channel = kotoba_config["announcement_channel"]
# ====================================================


class Kotoba(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def getjson(self, url):
        async with self.aiosession.get(url) as resp:
            return await resp.json()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(main_guild)
        self.aiosession = aiohttp.ClientSession()
        print("Cog de kotoba cargado con éxito")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == kotoba_id:
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
                                    kotobadict = await self.getjson(jsonurl)
                                    usercount = len(kotobadict["participants"])
                                    questioncount = len(
                                        kotobadict["questions"])
                                    mainuserid = int(
                                        kotobadict["participants"][0]["discordUser"]["id"])
                                    scorelimit = kotobadict["settings"]["scoreLimit"]
                                    failedquestioncount = questioncount - scorelimit
                                    answertimelimitinms = kotobadict["settings"]["answerTimeLimitInMs"]
                                    hardcore = "hardcore" in kotobadict["rawStartCommand"]
                                    fontsize = kotobadict["settings"]["fontSize"]
                                    font = kotobadict["settings"]["font"]
                                    shuffle = kotobadict["settings"]["shuffle"]
                                    isloaded = kotobadict["isLoaded"]
                                    effect = kotobadict["settings"]["effect"] if (
                                        "effect" in kotobadict["settings"]) else ""
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
                                    print(quizname)
                                    endindex = 0

                                    mc = kotobadict["decks"][0]["mc"]

                                    try:
                                        startindex = kotobadict["decks"][0]["startIndex"]
                                        endindex = kotobadict["decks"][0]["endIndex"]

                                    except KeyError:
                                        pass

                                    try:
                                        requirements = kotoba_tests[quizname.strip(
                                        )]
                                        reqscorelimit, reqanswertime, reqfontsize, reqfont, newrankid, reqfailed, shortname = requirements
                                    except KeyError:
                                        print("Ese no es un test del Noken")
                                        return

                                    if effect != "antiocr":
                                        print(message.channel,
                                              "Ajustes de color erróneos. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if startindex != 0 or endindex != 0 or mc or shuffle is False or isloaded:
                                        print(message.channel,
                                              "Ajustes no permitidos detectados. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if not hardcore:
                                        print(message.channel,
                                              "Modo hardcore no detectado. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if scorelimit < reqscorelimit:
                                        print(
                                            message.channel, "Puntuación mínima establecida demasiado baja. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if usercount > 1:
                                        print(message.channel,
                                              "Demasiados usuarios, haz el quiz solo!")
                                        return

                                    if reqanswertime < answertimelimitinms:
                                        print(message.channel,
                                              "Tiempo establecido para contestar demasiado alto. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if reqfontsize < fontsize:
                                        print(
                                            message.channel, "Tamaño de fuente demasiado grande. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if reqfont != 'any':
                                        if font not in reqfont:
                                            print(message.channel,
                                                  "Fuente no permitida. Revisa que el comando coincida con el indicado por .levelup")
                                            return

                                    if failedquestioncount < 0:
                                        print(message.channel,
                                              "Quiz abortado por el usuario.")
                                        return

                                    if failedquestioncount > reqfailed:
                                        print(
                                            message.channel, "Demasiadas respuestas incorrectas. Revisa que el comando coincida con el indicado por .levelup")
                                        return

                                    if scorelimit != myscore:
                                        await send_error_message(message.channel,
                                                                 "Quiz fallado. ¡Más suerte la próxima vez!")
                                        return

                                    if message.channel.id not in kotoba_channels and message.channel.parent_id not in kotoba_channels:
                                        await send_error_message(message.channel,
                                                                 "Los tests solo serán evaluados en <#796084920790679612>.")
                                        return

                                    quizwinner = self.myguild.get_member(
                                        mainuserid)
                                    currentroleid = 0
                                    for role in quizwinner.roles:
                                        if role.id in quiz_ranks:
                                            print("Role ID:", role.id)
                                            currentroleid = role.id

                                    if currentroleid not in quiz_ranks or quiz_ranks.index(currentroleid) <= quiz_ranks.index(newrankid) - 1:
                                        newrole = self.myguild.get_role(
                                            newrankid)
                                        if currentroleid != 0:
                                            currentrole = self.myguild.get_role(
                                                currentroleid)
                                            await quizwinner.remove_roles(currentrole)
                                        await quizwinner.add_roles(newrole)
                                        announcementchannel = self.bot.get_channel(
                                            announcement_channel)
                                        # await announcementchannel.send(f'<@!{mainuserid}> ha aprobado el examen de{shortname}!\n'
                                        #                                f'Escribe `.levelup` en <#796084920790679612> para ver los requisitos del siguiente nivel.')

            except TypeError:
                pass

    @commands.slash_command()
    async def levelup(self, ctx):
        """Mostrar el comando que necesitas para subir al siguiente nivel."""
        if ctx.channel.id not in kotoba_channels:
            await send_error_message(ctx,
                                     "Este comando solo puede ser usado en <#796084920790679612>.")
            return

        member = await self.myguild.fetch_member(ctx.author.id)
        for role in member.roles:
            if role.id in quiz_ranks:
                # String is cut down for easy copy and paste.
                await send_response(ctx, levelup_messages[role.id], ephemeral=True)
                return

        await send_response(ctx,
                            levelup_messages[654352144664887297], ephemeral=True)

    @commands.command(aliases=["levelup"])
    async def levelupprefix(self, ctx):
        await self.levelup(ctx)

    @commands.slash_command()
    async def levelupall(self, ctx):
        """Mostrar todos los comandos para subir de nivel."""
        message_list = []
        for rankid in levelup_messages:
            levelupmesssage = levelup_messages[rankid]
            message_list.append(levelupmesssage)

        # Delete final level message.
        del message_list[-1]
        message = "\n".join(message_list)

        await send_response(ctx, message, ephemeral=True)

    @commands.command(aliases=["levelupall"])
    async def levelupallprefix(self, ctx):
        await self.levelupall(ctx)


def setup(bot):
    bot.add_cog(Kotoba(bot))
