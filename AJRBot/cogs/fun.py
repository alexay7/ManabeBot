"""Cog responsible for random things."""

import json
import random
import re
from attr import has
import discord
import time
import aiohttp
from discord.ext import commands
from datetime import datetime, timezone
from dateutil.tz import gettz
from bs4 import BeautifulSoup
import requests
from time import strftime
from time import gmtime

with open(f"cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]


class Extra(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def getjson(self, url):
        async with self.aiosession.get(url) as resp:
            return await resp.json()

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        self.aiosession = aiohttp.ClientSession()

    @commands.command()
    async def japantime(self, ctx):
        "Muestra la hora actual y la de Japón."
        local = datetime.now(gettz('Spain'))
        local_japan = datetime.now(gettz('Japan'))

        def intToMonth(number):
            if number == 1:
                return "Enero"
            if number == 2:
                return "Febrero"
            if number == 3:
                return "Marzo"
            if number == 4:
                return "Abril"
            if number == 5:
                return "Mayo"
            if number == 6:
                return "Junio"
            if number == 7:
                return "Julio"
            if number == 8:
                return "Agosto"
            if number == 9:
                return "Septiembre"
            if number == 10:
                return "Octubre"
            if number == 11:
                return "Noviembre"
            return "Diciembre"

        localtime = strftime("%H:%M", gmtime(
            int(local.hour)*3600+int(local.minute)*60))

        japantime = strftime("%H:%M", gmtime(
            int(local_japan.hour)*3600+int(local_japan.minute)*60))

        await ctx.send(
            f"Hora Local: {localtime} del {local.day} de {intToMonth(local.month)} de {local.year}\nHora Japonesa: {japantime} del {local_japan.day} de {intToMonth(local_japan.month)} de {local_japan.year}")

    @commands.command(aliases=['canigotojapan'])
    async def japonabierto(self, ctx):
        "Te dice si las fronteras de Japón están abiertas para el turismo o no"
        url = "https://canigotojapan.com"

        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
        }

        # Make a GET request to fetch the raw HTML content
        req = requests.get(url, headers)

        # Parse the html content
        soup = BeautifulSoup(req.content, 'html.parser')

        await ctx.send(soup.find("h2").text)


def setup(bot):
    bot.add_cog(Extra(bot))
