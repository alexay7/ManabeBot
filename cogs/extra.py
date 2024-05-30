
import json
import random
import re
import discord
from matplotlib.ticker import MaxNLocator
import requests
import discord
import requests
import matplotlib.pyplot as plt

from datetime import datetime
from time import gmtime, strftime
from dateutil.tz import gettz
from discord.raw_models import RawReactionActionEvent
from discord import Member, Guild, Option
from time import gmtime, sleep
from discord.ext import commands
from discord.ext import commands, tasks
from termcolor import cprint, COLORS

from helpers.general import intToMonth, send_error_message, send_response, set_processing, get_clock_emoji

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    admin_users = general_config["admin_users"]
    main_guild = general_config["trusted_guilds"][1]

with open("config/roles.json", encoding="utf-8") as roles_file:
    roles_config = json.load(roles_file)
# ====================================================


def sanitize_input(input_string):
    # Remove any characters that are not alphanumeric, spaces, or common punctuation
    return re.sub(r"[^a-zA-Z0-9\s,.!?-]", "", input_string)


class Extra(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.bot.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        cprint("- [✅] Cog de cosas random cargado con éxito",
               random.choice(list(COLORS.keys())))
        self.update_clock.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if "?inmersar" in message.content:
            channel = message.channel
            sleep(2)
            time = message.content.split(" ")[1]
            if time and int(time) > 16:
                immerse_role = discord.utils.get(
                    message.guild.roles, id=865660735761678386)
                await message.author.remove_roles(immerse_role)
                await send_error_message(channel, "El tiempo máximo permitido es de 16 horas, si quieres desconectar más tiempo plantéate desinstalar Discord.")

        if "ajr" in message.content.lower():
            # Replace "ajr" with "manabe" and send the message with webhooks
            webhook = await message.channel.create_webhook(name=message.author.name)
            compiled = re.compile(re.escape("ajr"), re.IGNORECASE)
            msg = compiled.sub("manabe", message.content).strip()
            await webhook.send(
                content=msg, username=message.author.display_name, avatar_url=message.author.display_avatar)

            webhooks = await message.channel.webhooks()
            for webhook in webhooks:
                await webhook.delete()

            await message.delete()

        if "ayuda," in message.content.lower():
            match = re.search(r"(?i)ayuda, (.*)", message.content)
            if match:
                content = match.group(1)

                # Sanitize the extracted content
                content = sanitize_input(content)

                # Construct Google search link
                google = f"https://www.google.com/search?q={content.replace(' ', '+')}"
            else:
                # Handle the case where "ayuda," is not found
                content = ""
                google = ""

            # Send the message with the link
            await message.channel.send(google)

        if message.channel.id == 1216787655573114971 and message.author.id == 302050872383242240 and message.interaction:
            channel = self.bot.get_channel(1216787655573114971)

            # Search the message with the ranking with id 1219439399167856682
            rank_message = await channel.fetch_message(1219439399167856682)

            # Ranking has format - name: interactions, ignore the title and the last line
            ranking = rank_message.content.split("\n")[2:-1]

            real_ranking = {}

            # Create ranking with the message
            for user in ranking:
                user = user.split(":")
                points = int(user[1].strip())
                username = user[0].strip().replace(
                    "- ", "")

                if message.interaction.user.name == username:
                    points += 1

                real_ranking[username] = points

            # Edit the message with the new ranking
            ranking_message = "```md\n# Ranking de bumps\n"
            for user, interactions in real_ranking.items():
                ranking_message += f"- {user}: {interactions}\n"
            ranking_message += "```"

            await rank_message.edit(content=ranking_message)

    @commands.command()
    async def updatebumps(self, ctx):
        # Get channel with id 1216787655573114971
        channel = self.bot.get_channel(1216787655573114971)

        # Get all messages from channel with interactions
        messages = await channel.history(limit=1000).flatten()

        # Create a ranking with the interaction user
        ranking = {}

        for message in messages:
            if message.interaction:
                user = message.interaction.user
                if user.name in ranking:
                    ranking[user.name] += 1
                else:
                    ranking[user.name] = 1

        # Sort the ranking
        ranking = dict(
            sorted(ranking.items(), key=lambda item: item[1], reverse=True))

        # Send the ranking to the channel without embed in one message
        ranking_message = "```md\n# Ranking de bumps\n"
        for user, interactions in ranking.items():
            ranking_message += f"- {user}: {interactions}\n"
        ranking_message += "```"

        rank_message = await channel.fetch_message(1219439399167856682)
        await rank_message.edit(content=ranking_message)

    @commands.command(aliases=["crecimientomanabe", "manabeusers", "usuariosmanabe"])
    async def get_total_members_by_day(self, ctx):
        # Get all members from the guild
        guild = self.bot.get_guild(654351832734498836)
        members = guild.members

        # Get the date they joined
        joined = [member.joined_at for member in members]

        # Sort the dates
        joined = sorted(joined)

        # Create a dictionary with the date and the number of members. This is the members of the day before plus the new members that day
        total_members = {}
        total = 0
        for date in joined:
            date = date.strftime("%Y-%m")
            if date in total_members:
                total_members[date] += 1
            else:
                total_members[date] = total+1
            total += 1

        # Create the plot
        fig1, ax = plt.subplots(figsize=(7, 5))
        plt.plot(list(total_members.keys()), list(total_members.values()))
        plt.xlabel("Fecha")
        plt.ylabel("Miembros")
        plt.title("Miembros totales en Manabe")
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Decrease desnity of the x axis
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True, prune='both'))
        ax.set_facecolor('#36393f')  # Color de fondo similar al de Discord
        fig1.set_facecolor('#36393f')

        ax.title.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(axis='x', colors='white')  # Change tick labels color
        ax.tick_params(axis='y', colors='white')  # Change tick labels color

        plt.savefig("temp/image.png", bbox_inches="tight")
        plt.close()
        file = discord.File("temp/image.png", filename="image.png")

        await ctx.send(file=file)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        message_id = str(payload.message_id)
        if message_id in roles_config.keys():
            guild: Guild = await self.bot.fetch_guild(654351832734498836)
            user: Member = await guild.fetch_member(payload.user_id)
            role_config = roles_config[message_id]
            if str(payload.emoji) == role_config["emoji"]:
                newrole = discord.utils.get(
                    guild.roles, id=int(role_config["role"]))
                await user.add_roles(newrole)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        message_id = str(payload.message_id)
        if message_id in roles_config.keys():
            guild: Guild = await self.bot.fetch_guild(654351832734498836)
            user: Member = await guild.fetch_member(payload.user_id)
            role_config = roles_config[message_id]
            if str(payload.emoji) == role_config["emoji"]:
                newrole = discord.utils.get(
                    guild.roles, id=int(role_config["role"]))
                await user.remove_roles(newrole)

    @commands.slash_command(guild_ids=[main_guild])
    async def say(self, ctx,
                  message: discord.Option(str, "Mensaje a enviar", required=True),
                  channel: discord.Option(str, "Canal a enviar", required=True)):
        "Comando para hablar a través del bot"

        if ctx.author.id == 615896601554190346:
            channel = self.bot.get_channel(int(channel))
            await channel.send(message)
            await ctx.respond("Enviado")

    @tasks.loop(minutes=10)
    async def update_clock(self):
        channel = self.bot.get_channel(1160718763965022258)

        if not channel:
            return

        now = datetime.now()

        emoji = await get_clock_emoji(now.hour, now.minute)

        await channel.edit(name=f"{emoji} {now.strftime('%H:%M Hora ES')}")

    @commands.slash_command()
    async def kalise(self, ctx):
        "Comprobar si el bot está online"
        photos = ["https://www.alimarket.es/media/images/2014/detalle_art/152964/32612_preview.jpg", "https://pbs.twimg.com/profile_images/446190654356324352/nFIIKVXx_400x400.jpeg",
                  "https://s03.s3c.es/imag/_v0/225x250/d/4/e/kalise-iniesta.jpg", "https://static.abc.es/Media/201303/27/iniesta-kalise--644x362.jpg", "https://img.europapress.es/fotoweb/fotonoticia_20110407192259_1200.jpg", "https://estaticos-cdn.prensaiberica.es/clip/69f0a4ff-9686-400f-85bd-bfdf4751102c_alta-libre-aspect-ratio_default_0.jpg", "https://i.vimeocdn.com/video/226816102-f50001ce1c20544e3ed9d17584b8a9cdec8d5a3e35c39f37a8dc8b3b249a5a79-d?f=webp", "https://i.ytimg.com/vi/iRe1GFRCwWg/maxresdefault.jpg"]
        await send_response(ctx, random.choice(photos))

    @commands.command(aliases=["kalise"])
    async def kaliseprefix(self, ctx):
        await self.kalise(ctx)

    countries = [
        {
            "title": "Hora Japonesa 🇯🇵",
            "tz": "Japan"
        },
        {
            "title": "Hora Española 🇪🇸",
            "tz": "Spain"
        },
        {
            "title": "Hora en Argentina 🇦🇷",
            "tz": "America/Argentina/Buenos_Aires"
        },
        {
            "title": "Hora en Uruguay 🇺🇾",
            "tz": "America/Montevideo"
        },
        {
            "title": "Hora en Puerto Rico 🇵🇷",
            "tz": "America/Puerto_Rico"
        },
        {
            "title": "Hora en República Dominicana 🇩🇴",
            "tz": "America/Santo_Domingo"
        },
        {
            "title": "Hora en Cuba 🇨🇺",
            "tz": "America/Havana"
        },
        {
            "title": "Hora en Bolivia 🇧🇴",
            "tz": "America/La_Paz"
        },
        {
            "title": "Hora en Paraguay 🇵🇾",
            "tz": "America/Asuncion"
        },
        {
            "title": "Hora en Chile 🇨🇱",
            "tz": "Chile/Continental"
        },
        {
            "title": "Hora en Venezuela 🇻🇪",
            "tz": "America/Caracas"
        },
        {
            "title": "Hora en Perú 🇵🇪",
            "tz": "America/Lima"
        },
        {
            "title": "Hora en Colombia 🇨🇴",
            "tz": "America/Bogota"
        },
        {
            "title": "Hora en Ecuador 🇪🇨",
            "tz": "America/Guayaquil"
        },
        {
            "title": "Hora en Panamá 🇵🇦",
            "tz": "America/Panama"
        },
        {
            "title": "Hora en México 🇲🇽",
            "tz": "America/Mexico_City"
        },
        {
            "title": "Hora en Costa Rica 🇨🇷",
            "tz": "America/Costa_Rica"
        },
        {
            "title": "Hora en El Salvador 🇸🇻",
            "tz": "America/El_Salvador"
        },
        {
            "title": "Hora en Guatemala 🇬🇹",
            "tz": "America/Guatemala"
        },
        {
            "title": "Hora en Honduras 🇭🇳",
            "tz": "America/Tegucigalpa"
        },
        {
            "title": "Hora en Nicaragua 🇳🇮",
            "tz": "America/Managua"
        }
    ]

    @ commands.slash_command()
    async def japantime(self, ctx):
        "Muestra la hora actual y la de Japón."
        hours = ""

        for country in self.countries:
            local = datetime.now(gettz(country["tz"]))

            hours += f"- \"{country['title']}\": {strftime('%H:%M', gmtime(int(local.hour) * 3600 + int(local.minute) * 60))} del {local.day} de {intToMonth(local.month)} de {local.year}\n"

        await ctx.send(
            f"```matlab\n{hours}```")

    @ commands.command(aliases=['tiempojapon', 'horajapon', 'japonhora', 'japontiempo', 'japantime', "hora", "horalocal", "time", "localtime"])
    async def japantimeprefix(self, ctx):
        await self.japantime(ctx)

    @ commands.slash_command()
    async def yenaeuro(self, ctx,
                       yenes: discord.Option(int, "Cantidad de yenes a convertir", required=True)):
        "Convierte yenes a euros"
        await set_processing(ctx)

        # Contactar con https://economia.awesomeapi.com.br/last/EUR-JPY que devuelve en formato JSON
        url = "https://economia.awesomeapi.com.br/last/EUR-JPY"
        # Make a GET request to fetch the content
        req = requests.get(url)
        # Parse the json content
        data = req.json()

        # Obtener el valor de la moneda
        value = float(data["EURJPY"]["bid"])

        # Calcular el valor en euros
        result = round(yenes / value, 2)

        await send_response(ctx, str(yenes) + "¥ equivalen a " + str(result) + "€")

    @ commands.command(aliases=['jpytoeur', 'yentoeuro', 'jpyaeur', "yenaeuro"])
    async def yenaeuroprefix(self, ctx, yenes=0):
        if yenes == 0:
            return await send_error_message(ctx, "Debes indicar una cantidad de yenes")
        await self.yenaeuro(ctx, yenes)

    @ commands.slash_command()
    async def euroayen(self, ctx,
                       euros: discord.Option(int, "Cantidad de euros a convertir", required=True)):
        "Convierte euros a yenes"
        await set_processing(ctx)

        # Contactar con https://economia.awesomeapi.com.br/last/EUR-JPY que devuelve en formato JSON
        url = "https://economia.awesomeapi.com.br/last/EUR-JPY"
        # Make a GET request to fetch the content
        req = requests.get(url)
        # Parse the json content
        data = req.json()

        # Obtener el valor de la moneda
        value = float(data["EURJPY"]["bid"])

        # Calcular el valor en euros
        result = round(euros * value, 2)

        await send_response(ctx, str(euros) + "€ equivalen a " + str(result) + "¥")

    @ commands.command(aliases=['eurtojpy', 'eurotoyen', 'eurajpy', 'euroayen'])
    async def euroayenprefix(self, ctx, euros=0):
        if euros == 0:
            return await send_error_message(ctx, "Debes indicar una cantidad de yenes")
        await self.euroayen(ctx, euros)

    @ commands.slash_command()
    @ commands.cooldown(1, 300, commands.BucketType.user)
    async def yoji(self, ctx):
        "Obtiene un yoji aleatorio de jisho.org (cooldown de 5 min)"

        page = random.randint(1, 100)
        response = requests.get(
            f"https://jisho.org/api/v1/search/words?keyword=%23yoji&page={page}")
        element = random.randint(0, len(response.json()["data"]) - 1)
        element = response.json()["data"][element]
        kanji = element["japanese"][0]["word"]
        furigana = element["japanese"][0]["reading"]
        meaninggroup = element["senses"][0]["english_definitions"]
        meanings = meaninggroup[0]
        for element in meaninggroup[1:]:
            meanings += ", " + element

        embed = discord.Embed(title="Yoji aleatorio de Manabe",
                              description="Recibe un yojijukugo aleatorio de jisho.org", color=0x24b14d)
        embed.set_author(
            name="IniestaBot", icon_url="https://cdn.discordapp.com/avatars/892168738193936424/c08307c917ffb2fe9e4f59b66db66c9e.webp?size=48")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/icons/654351832734498836/6909a6a37d50d4010169c388c56c2746.webp?size=96")
        embed.add_field(name="Palabra", value=kanji, inline=True)
        embed.add_field(name="Lectura", value=furigana, inline=True)
        embed.add_field(
            name="Significados", value=meanings, inline=False)
        embed.set_footer(
            text="Si quieres obtener otra palabra, escribe .randomyoji dentro de 5 minutos.")
        await send_response(ctx, embed=embed)

    @ commands.cooldown(1, 300, commands.BucketType.user)
    @ commands.command(aliases=["aleatorio", 'randomyoji', 'yojialeatorio', 'yoji', 'yojijukugo'])
    async def yoji_(self, ctx):
        await self.yoji(ctx)

    # @commands.command()
    # async def anunciar(self, ctx):
    #     channel = self.bot.get_channel(1167606735360503859)
    #     embed = discord.Embed(title="🎮 ¡Club de VN y juegs🎮
    #                           description="Reacciona a este mensaje con 🎮 para recibir notificaciones sobre el club de VN y juegos", color=discord.Color.from_rgb(230, 126, 34), url="https://discord.com/channels/654351832734498836/1142399071236132944")
    #     embed.set_footer(
    #         text="Al recibir el rol entiendes que podrás recibir varias notificaciones en relación a la participación en las actividades del mes")

    #     await channel.send(embed=embed)

    @commands.slash_command()
    async def grammar(self, ctx, clave: discord.Option(str, "Id de la lección", required=False), forma_gramatical: discord.Option(str, "Punto gramatical que te interesa", required=False)):
        """Comando para obtener información de diferentes puntos gramaticales"""
        with open("config/grammar.json", "r", encoding="utf-8") as file:
            grammar = json.load(file)

        if clave:
            resultado = None

            for elemento in grammar:
                if elemento['id'] == clave:
                    resultado = elemento
                    break

            embed = discord.Embed(title=resultado["titulo"])

            embed.add_field(
                name=f"📕 {resultado['subtitulo']} 📕", value=f" ")

            resultado = resultado["texto"].split("\nç\n")
            for elem in resultado:
                embed.add_field(name=" ",
                                value=elem, inline=False)
                embed.set_footer(
                    text="Explicación cortesía de http://www.guidetojapanese.org/spanish/")
            return await send_response(ctx, embed=embed)

        elif forma_gramatical:
            resultados = []
            for elemento in grammar:
                if "formas" in elemento and isinstance(elemento["formas"], list):
                    for forma in elemento["formas"]:
                        if forma_gramatical == forma:
                            resultados.append(elemento)
                            break

            if len(resultados) > 1:
                embed = discord.Embed(color=0x442255,
                                      title="Se han encontrado varios resultados con esa forma", description="```Para ver el contenido usa el comando /grammar rellenando el campo \"Clave\" con la clave debajo de cada entrada gramatical```")

                for result in resultados:
                    embed.add_field(
                        value=f"Clave: **__{result['id']}__**", name=f"{result['titulo']} || {result['subtitulo']}", inline=False)
                await send_response(ctx, embed=embed, delete_after=30.0)
            elif len(resultados) == 0:
                return await send_error_message(ctx, "No se ha encontrado esa forma gramatical")
            else:
                embed = discord.Embed(
                    title=resultados[0]["titulo"], color=0x11abad)

                embed.add_field(
                    name=f"📕 {resultados[0]['subtitulo']} 📕", value=f" ")

                resultado = resultados[0]["texto"].split("\nç\n")
                for elem in resultado:
                    embed.add_field(name=" ",
                                    value=elem, inline=False)
                embed.set_footer(
                    text="Explicación cortesía de http://www.guidetojapanese.org/spanish/")
                return await send_response(ctx, embed=embed)

        else:
            await send_error_message(ctx, "Debes rellenar la forma gramatical a buscar o la clave del elemento!")

    @commands.command(aliases=["grammar", "gramatica"])
    async def grammar_(self, ctx, forma_gramatical: str = None):
        await self.grammar(ctx, None, forma_gramatical)

    @commands.slash_command()
    async def anison(self, ctx,
                     nombre: Option(str, "Nombre del anime o canción", required=False),
                     option: Option(str, "Anime o canción", required=False, default="anime", choices=["anime", "cancion"]),
                     tipo: Option(str, "Tipo de anison", required=False, default="random", choices=["random", "opening", "ending"])):
        "Obtiene una anison aleatoria"

        url = "https://animethemes.moe/api/graphql"

        has = "animethemeentries" if option == "anime" else "song"
        if tipo == "random":
            tipo = ""
        elif tipo == "opening":
            tipo = "OP"
        else:
            tipo = "ED"

        query = '''
        query RandomTheme {
            searchTheme(
        args: {
            sortBy: "random"
            filters: [{ key: "has", value: "'''+has+'''" }, { key: "nsfw", value: "false" },{ key: "type", value: "'''+tipo+'''" 	}]
            query: "'''+nombre+'''"
        }
    ) {
                data {
                    entries {
                        videos {
                            link
                        }
                    }
                    anime {
                        name
                        year
                        season
                        resources {
                            link
                        }
                        images {
                            link
                        }
                    }
                    song {
                        title
                    }
                    type
                }
            }
        }
        '''
        response = requests.post(url, json={'query': query})
        data = response.json()

        # Crear el embed con la información obtenida
        embed = discord.Embed(title="Anison Aleatoria",
                              color=discord.Color.blue())
        # choose random entry
        entry = random.choice(data['data']['searchTheme']['data'])

        anime_name = entry['anime']['name']
        song_title = entry['song']['title']

        link = entry["entries"][0]["videos"][0]["link"]

        embed.add_field(name="Vídeo", value=link, inline=False)
        embed.add_field(
            name="Anime", value=f"[{anime_name}]({entry['anime']['resources'][1]['link']})", inline=False)
        embed.add_field(name="Song", value=song_title, inline=False)
        embed.add_field(name="Type", value=entry['type'], inline=False)
        embed.set_image(url=entry['anime']['images'][0]['link'])

        await send_response(ctx, embed=embed, content=link)

    @commands.command(aliases=["anison"])
    async def anison_(self, ctx):

        # Get query form message
        q = ctx.message.content.split(" ")[1:]

        await self.anison(ctx, " ".join(q), "", "")


def setup(bot):
    bot.add_cog(Extra(bot))
