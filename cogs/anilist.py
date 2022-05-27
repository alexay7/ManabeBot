import random
import re
import discord
from discord.ext import commands
import requests

from cogs.fun import send_error_message

MEDIUMS = ["MANGA", "ANIME"]


async def get_anilist_id(username):
    query = '''
    query ($username: String){
  User(name:$username){
        id
        }
    }
    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'username': username
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    res = requests.post(
        url, json={'query': query, 'variables': variables}).json()

    if("errors" in res):
        print(res)
        return -1
    else:
        return res["data"]["User"]["id"]


async def get_anilist_logs(user_id, page, date):
    query = '''
    query($page:Int, $userId:Int,$date:FuzzyDateInt){
  Page(page:$page,perPage:50){
    pageInfo{
      hasNextPage
      lastPage
      currentPage
    }
    mediaList(userId: $userId,type:ANIME,sort:STARTED_ON,status:COMPLETED,completedAt_lesser:20220201,completedAt_greater:$date) {
      id
      media{
        title {
          romaji
          english
          native
          userPreferred
        },
        format,
        episodes,
        duration
      },
      completedAt {
        year
        month
        day
      },
      startedAt {
        year
        month
        day
      }
      status
  }
  }
}

    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'userId': user_id,
        'page': page,
        'date': date
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    return requests.post(
        url, json={'query': query, 'variables': variables}).json()


async def get_anilist_planning(page, user_id, media):
    query = '''
    query($page:Int, $userId:Int,$media:MediaType){
    Page(page:$page,perPage:50){
    pageInfo{
      hasNextPage
      lastPage
      currentPage
    }
    mediaList(userId: $userId,type:$media,status:PLANNING) {
      id
      media{
        title {
          romaji
          english
          native
          userPreferred
        },
        meanScore,
        status,
        volumes,
        coverImage {
            large
        },
        episodes,
        siteUrl
      }
  }
  }
}

    '''

    # Define our query variables and values that will be used in the query request
    variables = {
        'userId': user_id,
        'page': page,
        'media': media
    }

    url = 'https://graphql.anilist.co'

    # Make the HTTP Api request
    return requests.post(
        url, json={'query': query, 'variables': variables}).json()


class Anilist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def random(self, ctx, medium, username):
        if(medium.upper() not in MEDIUMS):
            await send_error_message(self, ctx, "Los medios disponibles son manga o anime.")
            return
        user_id = await get_anilist_id(username)
        if(user_id == -1):
            await send_error_message(self, ctx, "Esa cuenta de anilist no existe o es privada, cambia tus ajustes de privacidad.")
            return
        nextPage = True
        page = 1
        result = []
        while nextPage:
            planning = await get_anilist_planning(page, user_id, medium.upper())
            nextPage = planning["data"]["Page"]["pageInfo"]["hasNextPage"]
            for media in planning["data"]["Page"]["mediaList"]:
                element = {
                    "name": media["media"]["title"]["native"],
                    "romaji": media["media"]["title"]["romaji"],
                    "mean": media["media"]["meanScore"],
                    "status": media["media"]["status"],
                    "volumes": media["media"]["volumes"],
                    "image": media["media"]["coverImage"]["large"],
                    "episodes": media["media"]["episodes"],
                    "url": media["media"]["siteUrl"]
                }
                result.append(element)

            page += 1
        chosen = random.choice(result)
        embed = discord.Embed(
            title=f"El {medium} seleccionado es: ", color=0x24b14d, description=chosen["url"])
        embed.set_thumbnail(
            url=chosen["image"])
        embed.add_field(
            name="Título", value=f"{chosen['name']}", inline=False)
        embed.add_field(name="Nota media", value=chosen['mean'], inline=False)
        embed.add_field(
            name="Estado", value=chosen["status"], inline=False)
        if(medium.upper() == "MANGA"):
            volumes = chosen["volumes"]
            if volumes is None:
                volumes = "Todavía se está publicando"
            embed.add_field(
                name="Volúmenes", value=volumes, inline=False)
        else:
            embed.add_field(
                name="Capítulos", value=chosen["episodes"], inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Anilist(bot))
