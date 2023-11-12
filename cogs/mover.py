import discord
from discord.ext import commands, tasks
from discord import ApplicationContext, TextChannel
import aiohttp
import asyncio
import io


async def descargar_imagen(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as respuesta:
            if respuesta.status == 200:
                # Lee los datos de la respuesta y devuelve un objeto discord.File
                return discord.File(io.BytesIO(await respuesta.read()), filename="imagen.png")
            else:
                return None


class Mover(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot: discord.bot.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de mover mensajes cargado con éxito")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        twitter = False
        new_message = message.content
        if ("https://twitter" in message.content or
                "https://www.twitter" in message.content):
            new_message = new_message.replace("twitter", "fxtwitter")
            twitter = True
        elif ("https://x.com" in message.content or
                "https://www.x.com" in message.content):
            new_message = new_message.replace("x.com", "fxtwitter.com")
            twitter = True

        if twitter:
            await message.delete()
            channel: TextChannel = await self.bot.fetch_channel(message.channel.id)

            webhook = await channel.create_webhook(name=message.author.name)
            await webhook.send(
                content=new_message, username=message.author.display_name, avatar_url=message.author.display_avatar)

            webhooks = await channel.webhooks()
            for webhook in webhooks:
                await webhook.delete()

    @commands.command(aliases=["move"])
    async def movemessage(self, ctx: ApplicationContext, channel_id):
        if ctx.author.id == 615896601554190346:
            message_ids = ctx.message.content.split(" ")[2:]
            await ctx.message.delete()

            for message_id in message_ids:

                message = await ctx.fetch_message(message_id)

                channel: TextChannel = await self.bot.fetch_channel(channel_id)

                files = []

                for objeto in message.attachments:
                    url = objeto.url
                    imagen_file = await descargar_imagen(url)
                    files.append(imagen_file)

                webhook = await channel.create_webhook(name=message.author.name)
                await webhook.send(
                    content=message.content, files=files, username=message.author.display_name, avatar_url=message.author.display_avatar)

                webhooks = await channel.webhooks()
                for webhook in webhooks:
                    await webhook.delete()
                await message.delete()


def setup(bot):
    bot.add_cog(Mover(bot))
