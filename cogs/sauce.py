import os
import discord
from discord.ext import commands

from saucenao_api import SauceNao, errors

from helpers.general import send_error_message


class Sauce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de salsa cargado con éxito")

    @commands.command(aliases=["salsa"])
    async def sauce(self, ctx, url=None):
        sauce = SauceNao(os.getenv("SAUCE_TOKEN"))
        if ctx.message.reference:
            msg = await ctx.fetch_message(ctx.message.reference.message_id)
            if len(msg.attachments) > 0:
                url = msg.attachments[0].url
            else:
                url = msg.content.replace(".sauce ", "")
        else:
            if len(ctx.message.attachments) > 0:
                url = ctx.message.attachments[0].url

        try:
            best = sauce.from_url(url)[0]
        except errors.UnknownClientError:
            return await send_error_message(ctx, "Nada encontrado")

        if best and len(best.urls) > 0:
            if best.similarity > 60:
                embed = discord.Embed(
                    color=0x5842ff, title="✅ He encontrado algo!")
            else:
                embed = discord.Embed(
                    color=0x5842ff, title="🤨 No estoy muy seguro, buscas esto?")
            embed.set_thumbnail(url=best.thumbnail)
            embed.add_field(name="Nombre", value=best.title, inline=True)
            embed.add_field(name="Autor", value=best.author, inline=True)
            embed.add_field(name="Parecido",
                            value=best.similarity, inline=False)
            embed.add_field(name="Enlace", value=best.urls[0], inline=False)
            return await ctx.send(embed=embed)
        else:
            return await send_error_message(self, ctx, "Nada encontrado")


def setup(bot):
    bot.add_cog(Sauce(bot))
