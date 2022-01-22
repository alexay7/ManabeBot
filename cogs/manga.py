"""Cog responsible for manga petitions."""

import json
from multiprocessing.connection import wait
import discord
from discord.ext import commands
from datetime import datetime, timezone
from dateutil.tz import gettz
from bs4 import BeautifulSoup
import requests
from time import sleep, strftime
from time import gmtime
import random
from urllib import parse

#############################################################
# Variables (Temporary)
with open(f"cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    petitions_channel = data_dict["manga_petitions_channel_id"]
    admin_user_id = data_dict["kaigen_user_id"]
    outputchannel = data_dict["receivepetitionsid"]
#############################################################


def anilistApi(id):
    # Here we define our query as a multi-line string
    query = '''
    query ($id: Int) { # Define which variables will be used in the query (id)
    Media (id: $id, type: MANGA) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
        id
        title {
        native
        }
        volumes
        meanScore
        coverImage{
            large
        }
    }
    }
    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'id': id
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    return requests.post(url, json={'query': query, 'variables': variables})


class Manga(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if(payload.channel_id == outputchannel):
            channel = await self.bot.fetch_channel(payload.channel_id)
            petitions = await self.bot.fetch_channel(petitions_channel[1])
            petitionserver = self.bot.get_guild(guild_id)
            message = await channel.fetch_message(payload.message_id)

            requester = await petitionserver.fetch_member(
                message.embeds[0].fields[1].value)
            try:
                await message.delete()
                await petitions.send(f"Hola {requester.mention},\nEl manga {message.embeds[0].fields[0].value} que solicitaste ya está disponible en Komga.")
            except:
                print("El usuario abandonó el servidor")

    async def searchAnilist(self, message):
        ctx = await self.bot.get_context(message)
        if(ctx.message.channel.id in petitions_channel):
            if "anilist.co/manga/" in message.content:
                manga = parse.urlsplit(message.content).path.split("/")
                response = anilistApi(manga[2])
                if(response.status_code == 200):
                    output = self.bot.get_channel(outputchannel)
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
                    embed = discord.Embed()
                    embed.add_field(
                        name="✅", value="Petición enviada con éxito", inline=False)
                    tempmes = await ctx.send(embed=embed, delete_after=5.0)
                else:
                    await ctx.send("Ha habido un error leyendo los datos de ese manga.")


def setup(bot):
    bot.add_cog(Manga(bot))
