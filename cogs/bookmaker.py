import discord
import json
from discord.utils import find
from discord.ext import commands
from discord.raw_models import RawReactionActionEvent
from helpers.general import send_error_message, send_response
from datetime import datetime
from discord.message import Message
from typing import List
from discord.channel import DMChannel

# ================ GENERAL VARIABLES ================
with open("config/general.json") as json_file:
    general_config = json.load(json_file)
    trusted_guilds = general_config["trusted_guilds"]
# ====================================================


class Bookmark(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de bookmarks cargado con éxito")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        sent_messages: List[Message] = []

        if hasattr(channel, "guild"):
            user_reacted = find(
                lambda m: m.id == payload.user_id, channel.guild.members)
        else:
            dm_channel: DMChannel = channel
            user_reacted = dm_channel.recipient

        if str(payload.emoji) == "🔖" and hasattr(channel, "guild") and channel.guild.id in trusted_guilds:
            fecha = datetime.now().replace(microsecond=0).isoformat()
            texto = f"**Marcador Creado:** {fecha}\n{message.jump_url}"
            embed = discord.Embed(
                color=0x22b24d)
            embed.set_author(name=f"{message.author.name} ({message.author.id})",
                             icon_url=message.author.avatar)
            embed.add_field(
                name="Mensaje", value=message.content, inline=False)
            embed.set_footer(text=f"Mensaje enviado: {fecha}")

            if len(message.attachments) > 0:
                embed.add_field(name="Inserciones",
                                value=message.attachments[0])
                embed.set_image(url=message.attachments[0])

            if len(message.embeds) > 0:
                embed.add_field(name="Embed Original", value="", inline=False)
                embed.remove_field(0)
                sent_messages.append(await user_reacted.send(texto, embed=embed))
                message.embeds[0].color = 0x000000
                sent_messages.append(await user_reacted.send(embed=message.embeds[0]))
                return

            sent_messages.append(await user_reacted.send(texto, embed=embed))

            for mes in sent_messages:
                await mes.add_reaction("🗑️")

        if str(payload.emoji) == "🗑️" and hasattr(channel, "me"):
            if f"{payload.user_id}" != f"{channel.me.id}":
                await message.delete()


def setup(bot):
    bot.add_cog(Bookmark(bot))
