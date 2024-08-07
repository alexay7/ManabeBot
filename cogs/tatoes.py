"""Cog de ejemplos de frases"""

import random
import os
from discord.ext import commands
from discord import Option, Embed, Color, File
from termcolor import cprint, COLORS

from helpers.general import send_response, send_error_message, set_processing
from helpers.tatoes import parse_and_lookup_sentence, get_example_sentences, gen_video_from_img_and_audio
from cogs.menus.tatoes import TatoesView


class Tatoes(commands.Cog):
    """ Cog de ejemplos de frases"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """Imprime un mensaje en la consola cuando el bot está listo"""
        cprint("- [✅] Cog de tatoes cargado con éxito",
               random.choice(list(COLORS.keys())))

    @commands.slash_command()
    async def tatoe(self, ctx, consulta: Option(str, "Consulta", required=True), word_index: Option(int, "Índice de palabra", required=False, default=0)):
        """Responde con ejemplos de frases dada una palabra"""

        await set_processing(ctx)

        definitions = await parse_and_lookup_sentence(consulta)

        if word_index < 0 or word_index >= len(definitions):
            await send_error_message(ctx, "El índice de palabra es inválido")

        examples = await get_example_sentences(consulta)

        if not examples:
            return await send_error_message(ctx, "No se encontraron ejemplos de frases para esta palabra")

        pages = []

        for example in examples:
            series_info = example["series_info"]
            sentence_info = example["sentence_info"]

            target_word = definitions[word_index]["word"] if definitions else consulta

            # Put ** around the target word in the sentence

            japanese_sentence = sentence_info["sentence"]

            if japanese_sentence:
                japanese_sentence = japanese_sentence.replace(
                    target_word, f"**{target_word}**")

            description = f"🇯🇵 {japanese_sentence}\n"

            if sentence_info["english"]:
                description += f"🇺🇸 {sentence_info['english']}\n"

            if sentence_info["spanish"]:
                description += f"🇪🇸 {sentence_info['spanish']}"

            embed = Embed(
                title=f"📺 {series_info['name']} - {series_info['season']} - Episodio {series_info['episode']}",
                description=description,
                color=Color.green())

            if series_info["cover"]:
                url = series_info["cover"].replace("\\", "/")
                # Encode url
                url = url.replace(" ", "%20")
                embed.set_thumbnail(
                    url=url)

            if definitions:
                # Add word definition
                embed.add_field(
                    name=f"Definición de {definitions[word_index]['word']}",
                    value=definitions[word_index]["definitions"])

            embed.set_footer(
                text="Powered by NadeDB || Creditos a la BrigadaSOS por su desarrollo")

            pages.append(
                {"embed": embed, "image": example["sentence_info"]["image"], "audio": example["sentence_info"]["audio"]})

        first_result = pages[0]

        video_path = None
        while not video_path:
            video_path = await gen_video_from_img_and_audio(
                first_result["image"], first_result["audio"])

            if not video_path:
                first_result = random.choice(pages)

                pages.remove(first_result)

        video = File(video_path, filename="video.mp4")
        embed = first_result["embed"]

        return await send_response(ctx, embed=embed, file=video, view=TatoesView(pages))


def setup(bot):
    """Añade el cog al bot"""
    bot.add_cog(Tatoes(bot))
