import json
import os
from unicodedata import name
from urllib import parse
import discord
from discord.ext import commands
from pymongo import MongoClient, errors
from helpers.anilist import get_media_info_by_id
from helpers.general import send_error_message, send_response, set_processing

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    admin_users = general_config["admin_users"]
    main_guild = general_config["trusted_guilds"][2]

with open("config/manga.json") as json_file:
    manga_config = json.load(json_file)
    output_channel = manga_config["output_channel"]
    petitions_channels = manga_config["petitions_channels"]
    notification_channel = manga_config["notification_channel"]
    defects_channel = manga_config["defects_channel"]

with open("config/komga.json", encoding="utf8") as json_file:
    komga_files = json.load(json_file)
# ====================================================


class DefectModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.InputText(label="Id de Anilist del manga"))
        self.add_item(discord.ui.InputText(
            label="Defecto del que quieres informar", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Informe de defectos", color=0xff3333)
        embed.add_field(name="Manga que tiene defectos:",
                        value=self.children[0].value)
        embed.add_field(name="Descripción", value=self.children[1].value)

        channel = await interaction.guild.fetch_channel(defects_channel)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Gracias <@{interaction.user.id}> por tu colaboración. Tu aviso ha sido recibido con éxito.")


class Manga(commands.Cog):
    def __init__(self, bot: discord.bot.Bot):
        self.bot = bot
        try:
            client = MongoClient(os.getenv("MONGOURL"),
                                 serverSelectionTimeoutMS=10000)
            client.server_info()
            db = client.komga
            self.db = db.mangas
            print("Conectado con éxito con mongodb [mangas]")
        except errors.ServerSelectionTimeoutError:
            print("Ha ocurrido un error intentando conectar con la base de datos")
            exit(1)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de gestión de manga cargado con éxito")

    # Waits for reactions on output channel for warning the user when a petition has been accomplished
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id in output_channel:
            channel = await self.bot.fetch_channel(payload.channel_id)
            notifications = await self.bot.fetch_channel(notification_channel)
            petitionserver = self.bot.get_guild(main_guild)
            message = await channel.fetch_message(payload.message_id)

            requester = await petitionserver.fetch_member(message.embeds[0].fields[1].value)
            await message.delete()
            await notifications.send(f"Interesados: ||{requester.mention}||")
        elif payload.guild_id == main_guild:
            if payload.member.bot:
                return
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            if str(payload.emoji) == "📋" and (message.embeds[0].title in ["Búsqueda de mangas", "¡Hay nuevos volúmenes de un manga!", "¡Se ha añadido un nuevo manga!"]):
                found_manga = self.db.find_one(
                    {"idAnilist": int(message.embeds[0].fields[2].value)})
                if found_manga:
                    found_interested = self.db.find_one(
                        {"idAnilist": int(message.embeds[0].fields[2].value), "interested": payload.user_id})
                    if found_interested:
                        embed = discord.Embed(color=0xff2929)
                        embed.add_field(
                            name="❌", value="Ya estás suscrito a ese manga!", inline=False, delete_after=10.0)
                        return await channel.send(embed=embed)
                    self.db.update_one({"idAnilist": int(message.embeds[0].fields[2].value)}, {
                        "$push": {"interested": payload.user_id}})
                    embed = discord.Embed(
                        title="Subscripción realizada con éxito", color=0x30ffa0)
                    embed.add_field(name="Nombre del manga",
                                    value=found_manga["title"])
                    embed.add_field(name="Id de anilist",
                                    value=found_manga["idAnilist"])
                    embed.set_thumbnail(url=found_manga["thumbnail"])
                    embed.set_footer(
                        text="Serás informado cuando nuevos volúmenes sean subidos a komga. Si quieres desuscribirte reacciona con ❌ a este mensaje")
                    message = await channel.send(embed=embed, delete_after=30.0)
                    await message.add_reaction("❌")

            if str(payload.emoji) == "❌" and message.embeds[0].title == "Subscripción realizada con éxito":
                updated = self.db.update_one({"idAnilist": int(message.embeds[0].fields[1].value)}, {
                    "$pull": {"interested": payload.user_id}})
                if updated.modified_count > 0:
                    embed = discord.Embed(
                        title="Subscripción eliminada con éxito", color=0xff6060)
                    embed.set_footer(
                        text="Ya no serás informado cuando nuevos volúmenes sean subidos a komga.")
                    await message.delete()
                    return await channel.send(embed=embed, delete_after=30.0)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id == main_guild:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            if str(payload.emoji) == "📋" and (message.embeds[0].title in ["Búsqueda de mangas", "¡Hay nuevos volúmenes de un manga!", "¡Se ha añadido un nuevo manga!"]):
                updated = self.db.update_one({"idAnilist": int(message.embeds[0].fields[2].value)}, {
                    "$pull": {"interested": payload.user_id}})
                if updated.modified_count > 0:
                    embed = discord.Embed(
                        title="Subscripción eliminada con éxito", color=0xff6060)
                    embed.set_footer(
                        text="Ya no serás informado cuando nuevos volúmenes sean subidos a komga.")
                    return await channel.send(embed=embed, delete_after=30.0)

    # Analize messages in search of anilist links to receive the petition

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        if ctx.message.channel.id in petitions_channels:
            if "anilist.co/manga/" in message.content:
                manga = parse.urlsplit(message.content).path.split("/")
                found_manga = self.db.find_one({"idAnilist": int(manga[2])})
                if found_manga:
                    await message.add_reaction("❌")
                    return await send_error_message(ctx, "¡Ese manga ya está en komga!")
                response = await get_media_info_by_id(manga[2])
                if response.status_code == 200:
                    if response.json()["data"]["Media"]["meanScore"] is None or int(response.json()["data"]["Media"]["meanScore"]) < 65:
                        await message.add_reaction("❌")
                        badgrade = discord.Embed(color=0xff2929)
                        badgrade.add_field(
                            name="❌", value="Nota media demasiado baja", inline=False)
                        await ctx.send(embed=badgrade, delete_after=10.0)
                        return
                    output = self.bot.get_channel(output_channel[0])
                    embed = discord.Embed(
                        title="Nueva petición de manga", description="Ha llegado una nueva petición de manga", color=0x24b14d)
                    embed.set_author(
                        name=ctx.message.author, icon_url=ctx.message.author.avatar)
                    embed.set_thumbnail(
                        url=response.json()["data"]["Media"]["coverImage"]["large"])
                    embed.add_field(
                        name="Nombre", value=response.json()["data"]["Media"]["title"]["native"], inline=True)
                    embed.add_field(
                        name="UserId", value=ctx.message.author.id, inline=True)
                    embed.add_field(
                        name="Volúmenes", value=response.json()["data"]["Media"]["volumes"], inline=True)
                    embed.add_field(
                        name="Nota Media", value=response.json()["data"]["Media"]["meanScore"], inline=False)
                    embed.add_field(
                        name="Link", value=message.content, inline=False)
                    await output.send(embed=embed)
                    await message.add_reaction("✅")
                else:
                    await message.add_reaction("❌")
                    notfound = discord.Embed(color=0xff2929)
                    notfound.add_field(
                        name="❌", value="Manga no encontrado en anilist", inline=False)
                    await ctx.send(embed=notfound, delete_after=10.0)
                    return
            else:
                if not ctx.message.author.bot:
                    await message.delete()

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def updatevolumes(self, ctx,
                            anilistid: discord.Option(int, "Id de manga a actualizar", required=True),
                            volnum: discord.Option(int, "Número de mangas nuevos", required=False, default=1)):
        """[ADMIN] Actualiza el número de volúmenes de un manga"""
        if ctx.user.id in admin_users:
            await set_processing(ctx)
            found_manga = self.db.update_one({"idAnilist": anilistid}, {
                                             "$inc": {"volumes": volnum}})
            if found_manga.modified_count < 1:
                return await send_error_message(ctx, "Ese manga no está en komga.")
            updated_manga = self.db.find_one({"idAnilist": anilistid})

            if updated_manga['totalVolumes'] < updated_manga['volumes']:
                found_manga = self.db.update_one({"idAnilist": anilistid},
                                                 {"$set": {"totalVolumes": updated_manga['volumes']}})

            # Embed for admin
            admin_embed = discord.Embed(title="Manga modificado con éxito")
            admin_embed.add_field(name="Nombre del manga",
                                  value=updated_manga["title"])
            admin_embed.add_field(name="Volúmenes nuevos",
                                  value=updated_manga["volumes"])
            await send_response(ctx, embed=admin_embed)

            new_volumes = ""
            for elem in range(updated_manga["volumes"] - volnum, updated_manga["volumes"]):
                new_volumes += f"{updated_manga['title']} 第{elem + 1}巻\n"

            interested = ""
            for elem in updated_manga["interested"]:
                interested += f"<@{elem}> "

            notify_embed = discord.Embed(
                title="¡Hay nuevos volúmenes de un manga!")
            notify_embed.add_field(
                name="Nombre del manga", value=updated_manga["title"], inline=False)
            notify_embed.set_thumbnail(url=updated_manga["thumbnail"])
            notify_embed.add_field(
                name="Volúmenes añadidos", value=f">>> {new_volumes}", inline=False)
            notify_embed.add_field(
                name="Id del manga", value=updated_manga["idAnilist"], inline=False)
            notify_embed.add_field(name="Link de komga",
                                   value=f"[{updated_manga['title']}](https://leermangarapido.duckdns.org/series/{updated_manga['komgaId']})")
            notify_embed.set_footer(
                text=f"Para suscribirte a este manga reacciona con 📋 a este mensaje")

            petitions = await self.bot.fetch_channel(notification_channel)
            message = await petitions.send(embed=notify_embed)
            await message.add_reaction("📋")
            if interested != "":
                await petitions.send(f">>> Personas interesadas: ||{interested}||")

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def addmanga(self, ctx,
                       anilist: discord.Option(int, "Id de anilist", required=True),
                       volúmenes: discord.Option(int, "Número de volúmenes", required=True),
                       volúmenestotales: discord.Option(int, "Número de volúmenes que existen", required=True),
                       komgaid: discord.Option(str, "Id de komga", required=True),
                       interesado: discord.Option(str, "Id del usuario que ha pedido el manga", required=False)):
        """[ADMIN] Añadir mangas a la base de datos"""
        if ctx.user.id in admin_users:
            await set_processing(ctx)
            response = await get_media_info_by_id(anilist)

            manga_info = response.json()["data"]["Media"]

            if interesado:
                interested = [interesado]
            else:
                interested = []

            new_manga = {
                "title": manga_info["title"]["native"],
                "totalVolumes": volúmenestotales,
                "volumes": volúmenes,
                "idAnilist": anilist,
                "interested": interested,
                "thumbnail": manga_info["coverImage"]["large"],
                "komgaId": komgaid
            }

            try:
                self.db.insert_one(new_manga)
            except errors.DuplicateKeyError:
                return await send_error_message(ctx, "Ese manga ya existe")

            embed = discord.Embed(
                title=f"Nuevo manga añadido", color=0x00afff)
            embed.set_thumbnail(
                url=manga_info["coverImage"]["large"])
            embed.add_field(
                name="Título", value=f"{manga_info['title']['native']}", inline=False)
            embed.add_field(name="Nota media",
                            value=manga_info['meanScore'], inline=False)

            await send_response(ctx, embed=embed)

            notify_embed = discord.Embed(
                title="¡Se ha añadido un nuevo manga!")
            notify_embed.add_field(
                name="Nombre del manga", value=new_manga["title"], inline=False)
            notify_embed.set_thumbnail(url=new_manga["thumbnail"])
            notify_embed.add_field(
                name="Volúmenes totales", value=f"{volúmenes}", inline=False)
            notify_embed.add_field(
                name="Id del manga", value=anilist, inline=False)
            notify_embed.add_field(name="Link de komga",
                                   value=f"[{new_manga['title']}](https://leermangarapido.duckdns.org/series/{komgaid})")
            notify_embed.set_footer(
                text=f"Para suscribirte a este manga reacciona con 📋 a este mensaje")
            petitions = await self.bot.fetch_channel(notification_channel)
            message = await petitions.send(embed=notify_embed)
            await message.add_reaction("📋")
            if interesado:
                await petitions.send(f"Interesados: ||<@{interesado}>||")

    @ commands.slash_command()
    async def subscribe(self, ctx,
                        anilistid: discord.Option(int, "Id de anilist al que te quieres suscribir", required=True)):
        """Suscríbete a las actualizaciones de un manga"""
        if ctx.guild.id != main_guild:
            return
        await set_processing(ctx)
        found_manga = self.db.find_one({"idAnilist": anilistid})
        if found_manga:
            found_interested = self.db.find_one(
                {"idAnilist": anilistid, "interested": ctx.user.id})
            if found_interested:
                return await send_error_message(ctx, "Ya estás suscrito a ese manga!")
            self.db.update_one({"idAnilist": anilistid}, {
                               "$push": {"interested": ctx.author.id}})
            embed = discord.Embed(
                title="Subscripción realizada con éxito", color=0x30ffa0)
            embed.add_field(name="Nombre del manga",
                            value=found_manga["title"])
            embed.set_thumbnail(url=found_manga["thumbnail"])
            embed.set_footer(
                text="Serás informado cuando nuevos volúmenes sean subidos a komga.")
            return await send_response(ctx, embed=embed, ephemeral=True)
        else:
            return await send_error_message(ctx, "Ese manga no está en komga. Puedes solicitarlo en <#1005119887200489552>.")

    @ commands.slash_command()
    async def unsubscribe(self, ctx,
                          anilistid: discord.Option(int, "Id de anilist del que te quieras desuscribir", required=True)):
        """Desuscríbete de las actualizaciones de un manga"""
        if ctx.guild.id != main_guild:
            return
        await set_processing(ctx)
        found_manga = self.db.find_one({"idAnilist": anilistid})
        if found_manga:
            found_interested = self.db.find_one(
                {"idAnilist": anilistid, "interested": ctx.user.id})
            if not found_interested:
                return await send_error_message(ctx, "No estás suscrito a ese manga!")
            self.db.update_one({"idAnilist": anilistid}, {
                               "$pull": {"interested": ctx.author.id}})
            embed = discord.Embed(
                title="Subscripción eliminada con éxito", color=0xff6060)
            embed.set_footer(
                text="Ya no serás informado cuando nuevos volúmenes sean subidos a komga.")
            return await send_response(ctx, embed=embed, ephemeral=True)
        else:
            return await send_error_message(ctx, "Ese manga no está en komga. Puedes solicitarlo en <#1005119887200489552>.")

    @ commands.slash_command()
    async def buscarmanga(self, ctx,
                          anilistid: discord.Option(int, "Id de anilist del manga a buscar", required=False),
                          title: discord.Option(str, "Título en kanji del manga a buscar", required=False)):
        """Busca mangas de komga por el id de anilist o el título en kanji"""
        if ctx.guild.id != main_guild:
            return
        if not anilistid and not title:
            return await send_error_message(ctx, "Debes rellenar al menos uno de los dos campos")
        await set_processing(ctx)
        pipeline = [{"idAnilist": anilistid}]
        if title:
            pipeline.append({"title": {"$regex": title}})
        found_manga = self.db.find_one(
            {"$or": pipeline})
        if not found_manga:
            return await send_error_message(ctx, "Ese manga no está en komga. Puedes solicitarlo en <#1005119887200489552>.")
        embed = discord.Embed(
            title="Búsqueda de mangas", color=0x301fa0)
        embed.add_field(name="Nombre del manga",
                        value=found_manga["title"], inline=True)
        embed.add_field(name="Volúmenes del manga",
                        value=found_manga["volumes"], inline=False)
        embed.add_field(name="Id de anilist",
                        value=found_manga["idAnilist"], inline=True)
        embed.add_field(name="Link de komga",
                        value=f"[{found_manga['title']}](https://leermangarapido.duckdns.org/series/{found_manga['komgaId']})")
        embed.set_thumbnail(url=found_manga["thumbnail"])
        # Añadir campo con enlace a komga
        embed.set_footer(
            text="Para suscribirte a este manga reacciona con 📋 a este mensaje")
        message = await send_response(ctx, embed=embed)
        await message.add_reaction("📋")

    @ commands.slash_command()
    async def informar(self, ctx):
        """Denuncia mangas defectuosos para que puedan ser arreglados"""
        if ctx.channel.id != defects_channel:
            return
        await set_processing(ctx)
        modal = DefectModal(title="Informar sobre manga defectuoso")
        await ctx.send_modal(modal)

    @ commands.slash_command()
    async def komgainfo(self, ctx):
        """Obtener información sobre komga"""
        await set_processing(ctx)
        data = self.db.aggregate([
            {
                '$group': {
                    '_id': '_id',
                    'totalVolumes': {
                        '$sum': '$volumes'
                    },
                    'totalSeries': {
                        '$sum': 1
                    },
                    "wantedVolumes": {
                        '$sum': {'$subtract': ["$totalVolumes", "$volumes"]}
                    }
                }
            }
        ])
        for result in data:
            info = result
        embed = discord.Embed(title="Información Komga AJR", color=0xf4f344)
        embed.add_field(
            name="Datos:", value=f">>> `Total de Series de Manga`: {info['totalSeries']} Series\n`Total de Volúmenes`: {info['totalVolumes']} Volúmenes\n`Total de Volúmenes no Encontrados`: {info['wantedVolumes']} Volúmenes", inline=False)
        links = ""
        if ctx.guild.id == main_guild:
            links = "[Komga](https://leermangarapido.duckdns.org/)"
        else:
            links = "[Servidor de Peticiones](https://discord.gg/57hUwdTNBh)"
        embed.add_field(name="Links",
                        value=links)
        await send_response(ctx, embed=embed)

    @ commands.command(aliases=["komgainfo"])
    async def komgainfoprefix(self, ctx):
        await self.komgainfo(ctx)

    @commands.command()
    async def adjustmanga(self, ctx):
        all_mangas = self.db.find({"patatas": {"$exists": False}})
        await set_processing(ctx)
        for manga in all_mangas:
            response = await get_media_info_by_id(manga["idAnilist"])
            print(response.json())
            volumes = response.json()["data"]["Media"]["volumes"]
            if volumes:
                self.db.update_one({"idAnilist": manga["idAnilist"], "totalVolumes": {"$exists": False}}, {"$set": {
                                   "totalVolumes": volumes, "patatas": True}})
            else:
                self.db.update_one({"idAnilist": manga["idAnilist"]}, {
                                   "$set": {"patatas": True}})
                print(response.json()["data"]["Media"]["title"]["native"])

    # @commands.command()
    # async def apaño(self, ctx):
    #     channel = await self.bot.fetch_channel("1005120258589335673")
    #     await channel.send(f"Interesados: <@236273286189678592>")


def setup(bot):
    bot.add_cog(Manga(bot))
