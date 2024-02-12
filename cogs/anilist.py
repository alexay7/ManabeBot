import random
import discord

from discord.ext import commands
from termcolor import cprint, COLORS

from helpers.anilist import MEDIA, get_anilist_id, get_anilist_planning, get_media_info
from helpers.general import send_error_message, send_response, set_processing


class Anilist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        cprint("- [✅] Cog de anilist cargado con éxito",
               random.choice(list(COLORS.keys())))

    @commands.command(aliases=["animeomanga", "animevsmanga", "animeormanga"])
    async def animeormangaprefix(self, ctx, title=""):
        if title == "":
            return await send_error_message(ctx, "Tienes que escribir el nombre de la franquicia")
        await self.animeormanga(ctx, title)

    @commands.slash_command()
    async def animeormanga(self, ctx,
                           title: discord.Option(str, "Título de la franquicia a analizar", required=True)):
        await set_processing(ctx)
        results = await get_media_info(title)

        main = results["data"]["Media"]

        relations = results["data"]["Media"]["relations"]["edges"]

        animes = []

        mangas = [main]

        season = 99999

        for relation in relations:
            if relation["node"]["type"] == "ANIME" and relation["relationType"] in ["SEQUEL", "PREQUEL", "PARENT", "ADAPTATION", "ALTERNATIVE", "SOURCE"] and relation["node"]["format"] in ["TV", "MOVIE", "ONA"]:
                animes.append(relation["node"])

                if relation["node"]["seasonInt"] and relation["node"]["seasonInt"] < season:
                    main["title"] = relation["node"]["title"]
                    season = relation["node"]["seasonInt"]
            elif relation["node"]["type"] == "MANGA" and relation["relationType"] in ["SEQUEL", "PREQUEL", "PARENT"] and relation["node"]["format"] == "MANGA":
                mangas.append(relation["node"])

        if len(animes) == 0:
            return await send_error_message(ctx, "No existe anime para esa serie.")

        if len(mangas) == 0:
            return await send_error_message(ctx, "No existe manga para esa serie.")

        mean_anime_score = 0
        mean_manga_score = 0

        for anime in animes:
            if anime["meanScore"]:
                mean_anime_score += anime["meanScore"]
            else:
                animes.remove(anime)

        for manga in mangas:
            if manga["meanScore"]:
                mean_manga_score += manga["meanScore"]
            else:
                mangas.remove(manga)

        mean_anime_score = mean_anime_score / len(animes)
        mean_manga_score = mean_manga_score / len(mangas)

        if mean_anime_score == 0:
            return await send_error_message(ctx, "Ese anime todavía no tiene puntuación.")

        if mean_manga_score == 0:
            return await send_error_message(ctx, "Ese manga todavía no tiene puntuación.")

        if mean_anime_score > mean_manga_score:
            best_type = "anime"
            worst_type = "manga"
        elif mean_anime_score < mean_manga_score:
            best_type = "manga"
            worst_type = "anime"
        else:
            embed = discord.Embed(
                title=f"Tanto el anime como el manga de {main['title']['native']} tienen la misma puntuación")
            embed.set_thumbnail(
                url=main["coverImage"]["extraLarge"])
            embed.add_field(name="Puntuación",
                            value=main["meanScore"])
            embed.add_field(
                name="Link", value=main["siteUrl"], inline=False)
            return await send_response(ctx, embed=embed)

        embed = discord.Embed(
            title=f"El {best_type} de {main['title']['native']} es mejor que el {worst_type}")
        embed.set_thumbnail(
            url=main["coverImage"]["extraLarge"])
        embed.add_field(name="Puntuación del manga",
                        value=str(round(mean_manga_score, 2)))
        embed.add_field(name="Puntuación del anime",
                        value=str(round(mean_anime_score, 2)))
        embed.add_field(
            name="Link", value=main["siteUrl"], inline=False)

        return await send_response(ctx, embed=embed)

    @commands.slash_command()
    async def randommedia(self, ctx,
                          medio: discord.Option(str, "Elegir entre anime o manga aleatorios", choices=MEDIA, required=True),
                          username: discord.Option(str, "Nombre de usuario de anilist", required=True),
                          status: discord.Option(str, "Estado de visualización (visto/no visto)", choices=["En proceso", "Planeando", "Completado", "Dropeado", "Pausado"], required=True),
                          minvols: discord.Option(int, "Número mínimo de volúmenes (en caso de manga)", min_value=1, required=False, default=0),
                          maxvols: discord.Option(int, "Número máximo de volúmenes (en caso de manga)", min_value=1, required=False, default=10000),
                          mediumstatus: discord.Option(str, "Estado de publicación", choices=[
                                                       "Terminado", "En proceso"], required=False)
                          ):
        """Elige un manga o anime aleatorio de tu lista de anilist según los parámetros indicados"""
        formatted_status = ""

        if mediumstatus:
            formatted_status = mediumstatus.replace(
                "Terminado", "FINISHED").replace("En proceso", "RELEASING")
            if formatted_status not in ["FINISHED", "RELEASING"]:
                formatted_status = ""

        status = status.replace("En proceso", "CURRRENT").replace("Planeando", "PLANNING").replace(
            "Completado", "COMPLETED").replace("Dropeado", "DROPPED").replace("Pausado", "PAUSED")

        user_id = await get_anilist_id(username)
        if user_id == -1:
            await send_error_message(ctx, "Esa cuenta de anilist no existe o es privada, cambia tus ajustes de privacidad.")
            return
        nextPage = True
        page = 1
        await set_processing(ctx)
        result = []
        while nextPage:
            planning = await get_anilist_planning(page, user_id, medio.upper(), status)
            nextPage = planning["data"]["Page"]["pageInfo"]["hasNextPage"]
            for media in planning["data"]["Page"]["mediaList"]:
                element = {
                    "name": media["media"]["title"]["native"],
                    "romaji": media["media"]["title"]["romaji"],
                    "mean": media["media"]["meanScore"],
                    "status": media["media"]["status"],
                    "volumes": media["media"]["volumes"] or 0,
                    "image": media["media"]["coverImage"]["large"],
                    "episodes": media["media"]["episodes"],
                    "url": media["media"]["siteUrl"]
                }
                if (element["volumes"] and (element["volumes"] <= int(maxvols) and element["volumes"] >= int(minvols))) or medio == "ANIME" or element["status"] == "RELEASING":
                    if ((formatted_status != "" and element["status"] == formatted_status) or formatted_status == ""):
                        result.append(element)

            page += 1
        if len(result) == 0:
            await send_error_message(ctx, "No hay nada en tu lista que cumpla los parámetros seleccionados")
            return
        chosen = random.choice(result)
        embed = discord.Embed(
            title=f"El {medio} seleccionado es: ", color=0x24b14d, description=chosen["url"])
        embed.set_thumbnail(
            url=chosen["image"])
        embed.add_field(
            name="Título", value=f"{chosen['name']}", inline=False)
        embed.add_field(name="Nota media", value=chosen['mean'], inline=False)
        embed.add_field(
            name="Estado", value=chosen["status"], inline=False)
        if medio.upper() == "MANGA":
            volumes = chosen["volumes"]
            if volumes != 0:
                embed.add_field(
                    name="Volúmenes", value=volumes, inline=False)
        else:
            embed.add_field(
                name="Capítulos", value=chosen["episodes"], inline=False)
        await send_response(ctx, embed=embed)

    @commands.command(aliases=["randommedia"])
    async def randomprefix(self, ctx, medio, username="", volumes=10000):
        if medio.upper() not in MEDIA:
            await send_error_message(self, ctx, "Los medios disponibles son manga o anime.")
            return
        if username == "":
            return await send_error_message(ctx, "Tienes que escribir tu nombre de usuario de anilist")
        if volumes < 1:
            return await send_error_message(ctx, "El mínimo de volúmenes es 1")
        await self.random(ctx, medio, username, volumes)


def setup(bot):
    bot.add_cog(Anilist(bot))
