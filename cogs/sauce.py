"""Cog responsible for sauce."""

import json
import discord
import os
from discord.ext import commands
from saucenao_api import SauceNao
from discord import Embed

#############################################################
# Variables (Temporary)
with open("cogs/myguild.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]
    join_quiz_channel_ids = data_dict["join_quiz_1_id"]
    admin_id = data_dict["kaigen_user_id"]
#############################################################

# BOT'S COMMANDS


class Sauce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @ commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(guild_id)
        # await self.private_admin_channel.send("Connected to db successfully")

    @commands.command()
    async def sauce(self, ctx, url=None):
        sauce = SauceNao(os.getenv("SAUCE_TOKEN"))

        if(ctx.message.reference):
            msg = await ctx.fetch_message(ctx.message.reference.message_id)
            if len(msg.attachments) > 0:
                url = msg.attachments[0].url
            else:
                url = msg.content.replace("$sauce ", "")
        else:
            if len(ctx.message.attachments) > 0:
                url = ctx.message.attachments[0].url

        if url is None:
            await ctx.send("Nada encontrado")

        best = sauce.from_url(url)[0]

        if best:
            embed = Embed(color=0x5842ff)
            embed.set_thumbnail(url=best.thumbnail)
            embed.add_field(name="Parecido",
                            value=best.similarity, inline=False)
            embed.add_field(name="Nombre", value=best.title, inline=True)
            embed.add_field(name="Autor", value=best.author, inline=True)
            embed.add_field(name="Enlace", value=best.urls[0], inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nada encontrado")


def setup(bot):
    bot.add_cog(Sauce(bot))
